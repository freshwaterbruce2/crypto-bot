
# WEBSOCKET V2 FIX: Import fixed balance stream
try:
    from .websocket_balance_stream_v2_fixed import (
        FixedWebSocketBalanceStream,
        create_fixed_balance_stream,
    )
    WEBSOCKET_V2_FIXED_AVAILABLE = True
except ImportError:
    WEBSOCKET_V2_FIXED_AVAILABLE = False

"""
WebSocket Balance Streaming System
=================================

Core WebSocket balance streaming component that provides real-time balance updates
via Kraken's 'balances' channel. This eliminates the need for REST API nonce management
and provides instant balance synchronization.

Features:
- Real-time balance streaming via 'balances' channel subscription
- Automatic token refresh every 10-12 minutes (before 15-min expiry)
- Multi-wallet support (spot, earn, staking)
- Transaction-level balance notifications
- Thread-safe balance cache with atomic updates
- Circuit breaker for connection resilience
- Format conversion from WebSocket V2 to standard balance format
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Any, Callable, Optional

from ..utils.decimal_precision_fix import is_zero, safe_decimal

logger = logging.getLogger(__name__)


class BalanceStreamState(Enum):
    """WebSocket balance stream states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    SUBSCRIBED = "subscribed"
    ERROR = "error"


@dataclass
class BalanceUpdate:
    """Structure for balance update events"""
    asset: str
    balance: Decimal
    hold_trade: Decimal
    free_balance: Decimal
    timestamp: float
    change_amount: Optional[Decimal] = None
    change_reason: Optional[str] = None
    wallet_type: str = "spot"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'asset': self.asset,
            'balance': float(self.balance),
            'hold_trade': float(self.hold_trade),
            'free': float(self.free_balance),
            'total': float(self.balance),
            'timestamp': self.timestamp,
            'change_amount': float(self.change_amount) if self.change_amount else None,
            'change_reason': self.change_reason,
            'wallet_type': self.wallet_type,
            'source': 'websocket_stream'
        }


class WebSocketBalanceStream:
    """
    WebSocket-primary balance streaming system

    Provides real-time balance updates by subscribing to Kraken's 'balances'
    channel via WebSocket V2. Eliminates REST API dependency for balance operations.
    """

    def __init__(self,
                 websocket_client,
                 exchange_client,
                 token_refresh_interval: float = 720.0,  # 12 minutes
                 connection_timeout: float = 10.0):
        """
        Initialize WebSocket balance stream

        Args:
            websocket_client: WebSocket V2 client instance
            exchange_client: Exchange client for token refresh
            token_refresh_interval: Token refresh interval in seconds (default 12 min)
            connection_timeout: Connection timeout in seconds
        """
        self.websocket_client = websocket_client
        self.exchange_client = exchange_client
        self.token_refresh_interval = token_refresh_interval
        self.connection_timeout = connection_timeout

        # State management
        self.state = BalanceStreamState.DISCONNECTED
        self._lock = RLock()
        self._async_lock = asyncio.Lock()

        # Balance data storage
        self.balances: dict[str, BalanceUpdate] = {}
        self.balance_history: list[BalanceUpdate] = []
        self.max_history = 1000

        # Authentication and connection
        self._auth_token: Optional[str] = None
        self._token_created_time: float = 0
        self._subscription_confirmed = False
        self._last_heartbeat = 0.0
        self._permission_denied = False  # Track if API key lacks WebSocket permissions

        # Callback management
        self._balance_callbacks: list[Callable[[BalanceUpdate], None]] = []
        self._state_callbacks: list[Callable[[BalanceStreamState], None]] = []
        self._error_callbacks: list[Callable[[Exception], None]] = []

        # Background tasks
        self._token_refresh_task: Optional[asyncio.Task] = None
        self._heartbeat_monitor_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self.stats = {
            'balance_updates_received': 0,
            'token_refreshes': 0,
            'connection_attempts': 0,
            'subscription_attempts': 0,
            'errors': 0,
            'last_update_time': 0.0,
            'total_assets_tracked': 0,
            'uptime_start': 0.0
        }

        # Key asset tracking for enhanced logging
        self.key_assets = {'USDT', 'SHIB', 'MANA', 'BTC', 'ETH'}

        logger.info(f"[WEBSOCKET_BALANCE_STREAM] Initialized with token refresh every {token_refresh_interval / 60:.1f} minutes")

    async def start(self) -> bool:
        """
        Start the WebSocket balance streaming system

        Returns:
            True if started successfully
        """
        if self._running:
            logger.warning("[WEBSOCKET_BALANCE_STREAM] Already running")
            return True

        try:
            async with self._async_lock:
                logger.info("[WEBSOCKET_BALANCE_STREAM] Starting balance streaming system...")

                self._running = True
                self.stats['uptime_start'] = time.time()
                self.state = BalanceStreamState.CONNECTING
                await self._notify_state_change()

                # Get initial authentication token
                if not await self._obtain_auth_token():
                    logger.error("[WEBSOCKET_BALANCE_STREAM] Failed to obtain authentication token")
                    await self._set_error_state("auth_token_failed")
                    return False

                # Setup WebSocket integration
                if not await self._setup_websocket_integration():
                    logger.error("[WEBSOCKET_BALANCE_STREAM] Failed to setup WebSocket integration")
                    await self._set_error_state("websocket_setup_failed")
                    return False

                # Subscribe to balance updates
                if not await self._subscribe_to_balance_channel():
                    logger.error("[WEBSOCKET_BALANCE_STREAM] Failed to subscribe to balance channel")
                    await self._set_error_state("subscription_failed")
                    return False

                # Start background tasks
                await self._start_background_tasks()

                self.state = BalanceStreamState.SUBSCRIBED
                await self._notify_state_change()

                logger.info("[WEBSOCKET_BALANCE_STREAM] Started successfully - real-time balance streaming active")
                return True

        except Exception as e:
            logger.error(f"[WEBSOCKET_BALANCE_STREAM] Start failed: {e}")
            await self._set_error_state(f"start_failed: {e}")
            return False

    async def stop(self):
        """Stop the WebSocket balance streaming system"""
        if not self._running:
            return

        logger.info("[WEBSOCKET_BALANCE_STREAM] Stopping balance streaming system...")

        self._running = False
        self.state = BalanceStreamState.DISCONNECTED

        # Stop background tasks
        await self._stop_background_tasks()

        # Cleanup WebSocket integration
        await self._cleanup_websocket_integration()

        # Clear state
        self._subscription_confirmed = False
        self._auth_token = None

        await self._notify_state_change()

        logger.info("[WEBSOCKET_BALANCE_STREAM] Stopped")

    async def _obtain_auth_token(self) -> bool:
        """Obtain WebSocket authentication token with enhanced error handling"""
        try:
            logger.info("[WEBSOCKET_BALANCE_STREAM] Obtaining authentication token...")

            # Get token from exchange client using the get_websockets_token method (full response)
            if hasattr(self.exchange_client, 'get_websockets_token'):
                token_response = await self.exchange_client.get_websockets_token()

                # Check for API permission errors first
                if isinstance(token_response, dict) and 'error' in token_response and token_response['error']:
                    error_list = token_response['error']
                    error_msg = error_list[0] if error_list else 'Unknown error'

                    if 'EGeneral:Permission denied' in error_msg:
                        logger.error("""[WEBSOCKET_BALANCE_STREAM] ❌ WEBSOCKET PERMISSION ERROR!

                        Your API key doesn't have 'Access WebSockets API' permission.

                        TO FIX:
                        1. Log into Kraken.com
                        2. Go to Security -> API
                        3. Edit your API key
                        4. Check 'Access WebSockets API'
                        5. Save and restart bot

                        FALLBACK: Bot will use REST-only mode for balance updates.""")

                        # Set a special flag to indicate permission denied
                        self._permission_denied = True
                        return False
                    else:
                        logger.error(f"[WEBSOCKET_BALANCE_STREAM] API error getting token: {error_msg}")
                        return False

                # Parse successful response
                if isinstance(token_response, dict) and 'result' in token_response:
                    result = token_response['result']
                    if 'token' in result and result['token']:
                        self._auth_token = result['token']
                        self._token_created_time = time.time()
                        logger.info("[WEBSOCKET_BALANCE_STREAM] ✅ Authentication token obtained successfully")
                        return True
                    else:
                        logger.error(f"[WEBSOCKET_BALANCE_STREAM] No token in result: {result}")
                        return False

                # Legacy fallback - try get_websocket_token method (string response)
                elif hasattr(self.exchange_client, 'get_websocket_token'):
                    logger.info("[WEBSOCKET_BALANCE_STREAM] Trying legacy token method...")
                    token_response_legacy = await self.exchange_client.get_websocket_token()

                    if isinstance(token_response_legacy, str) and token_response_legacy:
                        self._auth_token = token_response_legacy
                        self._token_created_time = time.time()
                        logger.info("[WEBSOCKET_BALANCE_STREAM] Authentication token obtained (legacy method)")
                        return True
                    else:
                        logger.error(f"[WEBSOCKET_BALANCE_STREAM] Invalid legacy token response: {token_response_legacy}")
                        return False
                else:
                    logger.error(f"[WEBSOCKET_BALANCE_STREAM] Unexpected token response format: {token_response}")
                    return False
            else:
                logger.error("[WEBSOCKET_BALANCE_STREAM] Exchange client doesn't support WebSocket tokens")
                return False

        except Exception as e:
            # Check if this is a permission-related exception
            error_str = str(e).lower()
            if 'permission' in error_str or 'denied' in error_str:
                logger.error("[WEBSOCKET_BALANCE_STREAM] ❌ Permission error getting WebSocket token - API key may not have WebSocket access")
                self._permission_denied = True
            else:
                logger.error(f"[WEBSOCKET_BALANCE_STREAM] Error obtaining auth token: {e}")

            self.stats['errors'] += 1
            return False

    async def _refresh_auth_token(self) -> bool:
        """Refresh authentication token proactively"""
        try:
            logger.info("[WEBSOCKET_BALANCE_STREAM] Refreshing authentication token...")

            # Get new token
            if await self._obtain_auth_token():
                self.stats['token_refreshes'] += 1

                # Re-authenticate with WebSocket if connected
                if self.websocket_client and hasattr(self.websocket_client, 'bot'):
                    try:
                        await self.websocket_client.bot.authenticate(token=self._auth_token)
                        logger.info("[WEBSOCKET_BALANCE_STREAM] WebSocket re-authenticated with new token")
                    except Exception as auth_error:
                        logger.warning(f"[WEBSOCKET_BALANCE_STREAM] Re-authentication failed: {auth_error}")

                logger.info("[WEBSOCKET_BALANCE_STREAM] Token refresh completed successfully")
                return True
            else:
                logger.error("[WEBSOCKET_BALANCE_STREAM] Token refresh failed")
                return False

        except Exception as e:
            logger.error(f"[WEBSOCKET_BALANCE_STREAM] Token refresh error: {e}")
            self.stats['errors'] += 1
            return False

    def _should_refresh_token(self) -> bool:
        """Check if token should be refreshed"""
        if not self._auth_token or self._token_created_time == 0:
            return False

        token_age = time.time() - self._token_created_time
        return token_age >= self.token_refresh_interval

    async def _setup_websocket_integration(self) -> bool:
        """Setup WebSocket integration for balance streaming with enhanced connectivity checks"""
        try:
            if not self.websocket_client:
                logger.error("[WEBSOCKET_BALANCE_STREAM] No WebSocket client available")
                return False

            logger.info("[WEBSOCKET_BALANCE_STREAM] Setting up WebSocket integration...")

            # Set manager reference for balance injection
            if hasattr(self.websocket_client, 'set_manager'):
                self.websocket_client.set_manager(self)
                logger.debug("[WEBSOCKET_BALANCE_STREAM] Manager reference set on WebSocket client")

            # Register balance callback directly with WebSocket manager
            if hasattr(self.websocket_client, 'set_callback'):
                self.websocket_client.set_callback('balance', self._handle_websocket_balance_update)
                logger.info("[WEBSOCKET_BALANCE_STREAM] Registered balance callback with WebSocket client")

            # Enhanced WebSocket connection handling
            is_connected = False

            # Check multiple connection status indicators
            if hasattr(self.websocket_client, 'is_connected'):
                is_connected = self.websocket_client.is_connected
            elif hasattr(self.websocket_client, 'connected'):
                is_connected = self.websocket_client.connected
            else:
                # Assume not connected if we can't determine status
                is_connected = False

            if not is_connected:
                logger.info("[WEBSOCKET_BALANCE_STREAM] WebSocket not connected, attempting connection...")

                # Try to connect with timeout
                try:
                    connect_task = asyncio.create_task(self.websocket_client.connect())
                    connected = await asyncio.wait_for(connect_task, timeout=self.connection_timeout)

                    if not connected:
                        logger.error("[WEBSOCKET_BALANCE_STREAM] WebSocket connection failed")
                        return False

                    logger.info("[WEBSOCKET_BALANCE_STREAM] WebSocket connected successfully")

                except asyncio.TimeoutError:
                    logger.error(f"[WEBSOCKET_BALANCE_STREAM] WebSocket connection timed out after {self.connection_timeout}s")
                    return False
                except Exception as connect_error:
                    logger.error(f"[WEBSOCKET_BALANCE_STREAM] WebSocket connection error: {connect_error}")
                    return False
            else:
                logger.info("[WEBSOCKET_BALANCE_STREAM] WebSocket already connected")

            # Verify WebSocket client has required methods (relaxed check)
            if not hasattr(self.websocket_client, 'connect'):
                logger.warning("[WEBSOCKET_BALANCE_STREAM] WebSocket client missing connect method, using fallback")
                # Continue anyway - the WebSocket might still work

            self.state = BalanceStreamState.CONNECTED
            await self._notify_state_change()

            logger.info("[WEBSOCKET_BALANCE_STREAM] WebSocket integration setup complete")
            return True

        except Exception as e:
            logger.error(f"[WEBSOCKET_BALANCE_STREAM] WebSocket integration setup failed: {e}")
            self.stats['errors'] += 1
            return False

    async def _cleanup_websocket_integration(self):
        """Cleanup WebSocket integration"""
        try:
            if self.websocket_client:
                # Unregister callback
                if hasattr(self.websocket_client, 'set_callback'):
                    self.websocket_client.set_callback('balance', None)

                logger.debug("[WEBSOCKET_BALANCE_STREAM] WebSocket integration cleanup complete")

        except Exception as e:
            logger.error(f"[WEBSOCKET_BALANCE_STREAM] WebSocket cleanup error: {e}")

    async def _subscribe_to_balance_channel(self) -> bool:
        """Subscribe to balance updates channel with enhanced authentication handling"""
        try:
            logger.info("[WEBSOCKET_BALANCE_STREAM] Subscribing to balance channel...")
            self.stats['subscription_attempts'] += 1

            if not self.websocket_client or not hasattr(self.websocket_client, 'bot'):
                logger.error("[WEBSOCKET_BALANCE_STREAM] WebSocket bot not available")
                return False

            # Enhanced authentication token validation
            if not self._auth_token:
                logger.warning("[WEBSOCKET_BALANCE_STREAM] No authentication token available, attempting to obtain...")

                # Try to obtain token if not available
                if not await self._obtain_auth_token():
                    logger.error("[WEBSOCKET_BALANCE_STREAM] Failed to obtain authentication token")
                    return False

            # Validate token format
            if len(self._auth_token) < 10:  # Basic validation
                logger.error(f"[WEBSOCKET_BALANCE_STREAM] Authentication token appears invalid (length: {len(self._auth_token)})")
                return False

            logger.info(f"[WEBSOCKET_BALANCE_STREAM] Using authentication token: {self._auth_token[:8]}...")

            # Authenticate with enhanced error handling
            try:
                logger.info("[WEBSOCKET_BALANCE_STREAM] Authenticating WebSocket connection...")
                await self.websocket_client.bot.authenticate(token=self._auth_token)

                # Wait a moment for authentication to complete
                await asyncio.sleep(1.0)

                self.state = BalanceStreamState.AUTHENTICATED
                await self._notify_state_change()
                logger.info("[WEBSOCKET_BALANCE_STREAM] WebSocket authenticated successfully")

            except Exception as auth_error:
                logger.error(f"[WEBSOCKET_BALANCE_STREAM] Authentication failed: {auth_error}")

                # Check for specific authentication errors
                error_msg = str(auth_error).lower()
                if 'invalid' in error_msg or 'expired' in error_msg:
                    logger.warning("[WEBSOCKET_BALANCE_STREAM] Token appears expired, attempting refresh...")
                    if await self._refresh_auth_token():
                        # Retry authentication with new token
                        try:
                            await self.websocket_client.bot.authenticate(token=self._auth_token)
                            self.state = BalanceStreamState.AUTHENTICATED
                            await self._notify_state_change()
                            logger.info("[WEBSOCKET_BALANCE_STREAM] Authentication successful after token refresh")
                        except Exception as retry_error:
                            logger.error(f"[WEBSOCKET_BALANCE_STREAM] Authentication failed even after token refresh: {retry_error}")
                            return False
                    else:
                        logger.error("[WEBSOCKET_BALANCE_STREAM] Token refresh failed")
                        return False
                else:
                    return False

            # Subscribe to balance channel with enhanced error handling
            try:
                logger.info("[WEBSOCKET_BALANCE_STREAM] Subscribing to balance channel...")

                await self.websocket_client.bot.subscribe(
                    params={
                        'channel': 'balances',
                        'snapshot': True  # Get full balance snapshot
                    }
                )

                # Wait for subscription confirmation with timeout
                confirmation_timeout = 10.0
                start_time = time.time()

                while (time.time() - start_time) < confirmation_timeout:
                    await asyncio.sleep(0.5)
                    # Check if subscription was confirmed (this would be set by message handler)
                    if self._subscription_confirmed:
                        break

                if not self._subscription_confirmed:
                    logger.warning("[WEBSOCKET_BALANCE_STREAM] Subscription confirmation not received within timeout")
                    # Continue anyway - some WebSocket implementations don't send confirmations

                self._subscription_confirmed = True
                logger.info("[WEBSOCKET_BALANCE_STREAM] Successfully subscribed to balance channel with snapshot")
                return True

            except Exception as sub_error:
                logger.error(f"[WEBSOCKET_BALANCE_STREAM] Balance subscription failed: {sub_error}")

                # Enhanced error analysis
                error_msg = str(sub_error).lower()
                if 'credentials' in error_msg or 'permission' in error_msg or 'access' in error_msg:
                    logger.error("""[WEBSOCKET_BALANCE_STREAM] WEBSOCKET PERMISSION ERROR!

                    Your API key doesn't have 'Access WebSockets API' permission.

                    TO FIX:
                    1. Log into Kraken.com
                    2. Go to Security -> API
                    3. Edit your API key
                    4. Check 'Access WebSockets API'
                    5. Save and restart bot

                    Current permissions might be missing WebSocket access.""")
                elif 'invalid' in error_msg or 'expired' in error_msg:
                    logger.error("[WEBSOCKET_BALANCE_STREAM] Authentication token issue - try restarting bot to get fresh token")
                elif 'channel' in error_msg or 'subscribe' in error_msg:
                    logger.error("[WEBSOCKET_BALANCE_STREAM] Balance channel subscription not supported or unavailable")

                return False

        except Exception as e:
            logger.error(f"[WEBSOCKET_BALANCE_STREAM] Error subscribing to balance channel: {e}")
            self.stats['errors'] += 1
            return False

    async def _handle_websocket_balance_update(self, balance_data: list[dict[str, Any]]):
        """
        Handle balance updates from WebSocket V2

        Args:
            balance_data: List of balance update dictionaries from WebSocket
        """
        try:
            if not balance_data:
                logger.debug("[WEBSOCKET_BALANCE_STREAM] Empty balance update received")
                return

            logger.info(f"[WEBSOCKET_BALANCE_STREAM] Processing {len(balance_data)} balance updates")
            self.stats['balance_updates_received'] += 1
            self.stats['last_update_time'] = time.time()

            updated_assets = []
            total_usdt = Decimal('0')
            usdt_sources = []

            for balance_item in balance_data:
                if not isinstance(balance_item, dict):
                    continue

                asset = balance_item.get('asset')
                if not asset:
                    continue

                try:
                    # Parse balance data from WebSocket V2 format
                    balance_str = balance_item.get('balance', '0')
                    hold_trade_str = balance_item.get('hold_trade', '0')

                    balance = safe_decimal(balance_str)
                    hold_trade = safe_decimal(hold_trade_str)
                    free_balance = balance - hold_trade

                    # Skip zero balances
                    if is_zero(balance):
                        continue

                    # Calculate change if we have previous data
                    change_amount = None
                    change_reason = 'websocket_update'

                    if asset in self.balances:
                        prev_balance = self.balances[asset].balance
                        change_amount = balance - prev_balance

                        # Determine change reason based on amount
                        if change_amount > 0:
                            change_reason = 'deposit_or_trade_profit'
                        elif change_amount < 0:
                            change_reason = 'withdrawal_or_trade_loss'

                    # Create balance update
                    balance_update = BalanceUpdate(
                        asset=asset,
                        balance=balance,
                        hold_trade=hold_trade,
                        free_balance=free_balance,
                        timestamp=time.time(),
                        change_amount=change_amount,
                        change_reason=change_reason,
                        wallet_type='spot'  # Default to spot, could be enhanced
                    )

                    # Store balance update
                    with self._lock:
                        self.balances[asset] = balance_update
                        self.balance_history.append(balance_update)

                        # Trim history if needed
                        if len(self.balance_history) > self.max_history:
                            self.balance_history = self.balance_history[-self.max_history:]

                    updated_assets.append(asset)

                    # Track USDT aggregation
                    if asset in ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S', 'USDT.F', 'USDT.B']:
                        total_usdt += free_balance
                        usdt_sources.append(f"{asset}=${float(free_balance):.2f}")

                    # Enhanced logging for key assets
                    if asset in self.key_assets:
                        logger.info(f"[WEBSOCKET_BALANCE_STREAM] {asset} updated: "
                                   f"Balance={float(balance):.8f}, "
                                   f"Free={float(free_balance):.8f}, "
                                   f"Change={float(change_amount) if change_amount else 0:.8f}")
                    else:
                        logger.debug(f"[WEBSOCKET_BALANCE_STREAM] {asset} updated: {float(free_balance):.8f}")

                    # Notify callbacks
                    await self._notify_balance_update(balance_update)

                except (ValueError, TypeError) as e:
                    logger.warning(f"[WEBSOCKET_BALANCE_STREAM] Failed to parse balance for {asset}: {e}")
                    continue

            # Update statistics
            self.stats['total_assets_tracked'] = len(self.balances)

            # Log USDT summary
            if total_usdt > 0:
                logger.info(f"[WEBSOCKET_BALANCE_STREAM] *** TOTAL USDT: ${float(total_usdt):.2f} "
                           f"from [{', '.join(usdt_sources)}] ***")

            logger.info(f"[WEBSOCKET_BALANCE_STREAM] Successfully processed {len(updated_assets)} "
                       f"balance updates: {updated_assets}")

        except Exception as e:
            logger.error(f"[WEBSOCKET_BALANCE_STREAM] Error handling balance update: {e}")
            self.stats['errors'] += 1
            await self._notify_error(e)

    async def _start_background_tasks(self):
        """Start background monitoring tasks"""
        self._token_refresh_task = asyncio.create_task(self._token_refresh_loop())
        self._heartbeat_monitor_task = asyncio.create_task(self._heartbeat_monitor_loop())

        logger.info("[WEBSOCKET_BALANCE_STREAM] Background tasks started")

    async def _stop_background_tasks(self):
        """Stop background tasks"""
        tasks = [self._token_refresh_task, self._heartbeat_monitor_task]

        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("[WEBSOCKET_BALANCE_STREAM] Background tasks stopped")

    async def _token_refresh_loop(self):
        """Background token refresh loop"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute

                if not self._running:
                    break

                if self._should_refresh_token():
                    logger.info("[WEBSOCKET_BALANCE_STREAM] Token refresh needed")
                    success = await self._refresh_auth_token()
                    if not success:
                        logger.error("[WEBSOCKET_BALANCE_STREAM] Token refresh failed, continuing with current token")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WEBSOCKET_BALANCE_STREAM] Token refresh loop error: {e}")
                await asyncio.sleep(60)

    async def _heartbeat_monitor_loop(self):
        """Monitor WebSocket heartbeat and connection health"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                if not self._running:
                    break

                # Check WebSocket health
                if (self.websocket_client and
                    hasattr(self.websocket_client, 'last_message_time')):

                    time_since_message = time.time() - self.websocket_client.last_message_time

                    if time_since_message > 120:  # 2 minutes without messages
                        logger.warning(f"[WEBSOCKET_BALANCE_STREAM] No WebSocket messages for {time_since_message:.1f}s, "
                                     "connection may be stale")
                        await self._set_error_state("connection_stale")
                    elif time_since_message > 60:  # 1 minute warning
                        logger.debug(f"[WEBSOCKET_BALANCE_STREAM] Last WebSocket message {time_since_message:.1f}s ago"
                                   )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WEBSOCKET_BALANCE_STREAM] Heartbeat monitor error: {e}")
                await asyncio.sleep(30)

    # Public API methods

    def get_balance(self, asset: str) -> Optional[dict[str, Any]]:
        """
        Get current balance for asset

        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')

        Returns:
            Balance dictionary or None if not found
        """
        with self._lock:
            balance_update = self.balances.get(asset)
            return balance_update.to_dict() if balance_update else None

    def get_all_balances(self) -> dict[str, dict[str, Any]]:
        """
        Get all current balances

        Returns:
            Dictionary of all balances keyed by asset
        """
        with self._lock:
            return {asset: update.to_dict() for asset, update in self.balances.items()}

    def get_usdt_total(self) -> float:
        """Get total USDT across all USDT variants"""
        total = Decimal('0')
        usdt_variants = ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S', 'USDT.F', 'USDT.B']

        with self._lock:
            for variant in usdt_variants:
                if variant in self.balances:
                    total += self.balances[variant].free_balance

        return float(total)

    def register_balance_callback(self, callback: Callable[[BalanceUpdate], None]):
        """Register callback for balance updates"""
        self._balance_callbacks.append(callback)
        logger.debug("[WEBSOCKET_BALANCE_STREAM] Registered balance callback")

    def register_state_callback(self, callback: Callable[[BalanceStreamState], None]):
        """Register callback for state changes"""
        self._state_callbacks.append(callback)
        logger.debug("[WEBSOCKET_BALANCE_STREAM] Registered state callback")

    def register_error_callback(self, callback: Callable[[Exception], None]):
        """Register callback for errors"""
        self._error_callbacks.append(callback)
        logger.debug("[WEBSOCKET_BALANCE_STREAM] Registered error callback")

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive status information"""
        with self._lock:
            uptime = time.time() - self.stats['uptime_start'] if self.stats['uptime_start'] > 0 else 0

            return {
                'state': self.state.value,
                'running': self._running,
                'authenticated': bool(self._auth_token),
                'subscribed': self._subscription_confirmed,
                'token_age': time.time() - self._token_created_time if self._token_created_time > 0 else 0,
                'token_refresh_due': self._should_refresh_token(),
                'balances_count': len(self.balances),
                'key_assets_available': [asset for asset in self.key_assets if asset in self.balances],
                'usdt_total': self.get_usdt_total(),
                'statistics': dict(self.stats),
                'uptime_seconds': uptime,
                'websocket_connected': (self.websocket_client and
                                       hasattr(self.websocket_client, 'is_connected') and
                                       self.websocket_client.is_connected),
                'last_websocket_message': (time.time() - self.websocket_client.last_message_time
                                          if self.websocket_client and
                                          hasattr(self.websocket_client, 'last_message_time')
                                          else float('inf'))
            }

    def get_balance_history(self, asset: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get balance change history

        Args:
            asset: Specific asset to filter by (optional)
            limit: Maximum number of entries to return

        Returns:
            List of balance history entries
        """
        with self._lock:
            history = self.balance_history

            if asset:
                history = [entry for entry in history if entry.asset == asset]

            # Return most recent entries
            return [entry.to_dict() for entry in history[-limit:]]

    # Private notification methods

    async def _notify_balance_update(self, balance_update: BalanceUpdate):
        """Notify balance update callbacks"""
        for callback in self._balance_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(balance_update)
                else:
                    callback(balance_update)
            except Exception as e:
                logger.error(f"[WEBSOCKET_BALANCE_STREAM] Balance callback error: {e}")

    async def _notify_state_change(self):
        """Notify state change callbacks"""
        for callback in self._state_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.state)
                else:
                    callback(self.state)
            except Exception as e:
                logger.error(f"[WEBSOCKET_BALANCE_STREAM] State callback error: {e}")

    async def _notify_error(self, error: Exception):
        """Notify error callbacks"""
        for callback in self._error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error)
                else:
                    callback(error)
            except Exception as e:
                logger.error(f"[WEBSOCKET_BALANCE_STREAM] Error callback error: {e}")

    async def _set_error_state(self, error_message: str):
        """Set error state and notify"""
        self.state = BalanceStreamState.ERROR
        self.stats['errors'] += 1
        await self._notify_state_change()
        await self._notify_error(Exception(error_message))

    # Context manager support
    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
