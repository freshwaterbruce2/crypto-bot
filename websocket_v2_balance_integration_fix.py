#!/usr/bin/env python3
"""
WebSocket V2 Balance Integration Fix
===================================

This script fixes the balance data flow from WebSocket V2 to the existing bot system.
It creates a proper integration bridge that ensures:

1. WebSocket V2 balance updates flow to BalanceManager V2
2. BalanceManager V2 data is accessible to trading logic
3. Existing bot callbacks receive balance updates
4. Balance data consistency across all components

The fix addresses the gap between the new WebSocket V2 system and the existing
bot architecture that expects the older WebSocket format.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import balance system components
from src.balance.balance_manager_v2 import BalanceManagerV2, BalanceManagerV2Config
from src.balance.websocket_balance_stream import BalanceUpdate, WebSocketBalanceStream
from src.config import load_config
from src.utils.custom_logging import configure_logging

# Import WebSocket data models
from src.websocket.kraken_websocket_v2 import KrakenWebSocketConfig, KrakenWebSocketV2

logger = configure_logging()


class WebSocketV2BalanceBridge:
    """
    Bridge component that connects WebSocket V2 balance system to existing bot

    This bridge:
    1. Receives balance updates from WebSocket V2
    2. Converts them to the format expected by existing bot components
    3. Distributes updates to all registered callbacks
    4. Maintains compatibility with legacy balance manager interfaces
    """

    def __init__(self,
                 websocket_client,
                 exchange_client,
                 existing_balance_manager=None):

        self.websocket_client = websocket_client
        self.exchange_client = exchange_client
        self.existing_balance_manager = existing_balance_manager

        # WebSocket V2 components
        self.balance_stream: Optional[WebSocketBalanceStream] = None
        self.balance_manager_v2: Optional[BalanceManagerV2] = None

        # Bridge state
        self.running = False
        self.initialized = False

        # Callback management - compatibility with existing bot
        self.balance_callbacks: list[Callable] = []
        self.update_callbacks: list[Callable] = []

        # Balance data cache for immediate access
        self.current_balances: dict[str, dict[str, Any]] = {}
        self.last_update_time = 0.0

        # Statistics
        self.stats = {
            'updates_received': 0,
            'updates_distributed': 0,
            'callback_errors': 0,
            'format_conversions': 0,
            'bridge_start_time': 0.0
        }

        logger.info("[WEBSOCKET_V2_BRIDGE] Bridge initialized")

    async def initialize(self) -> bool:
        """Initialize the WebSocket V2 balance bridge"""
        if self.initialized:
            logger.warning("[WEBSOCKET_V2_BRIDGE] Already initialized")
            return True

        logger.info("[WEBSOCKET_V2_BRIDGE] Initializing WebSocket V2 balance bridge...")

        try:
            self.stats['bridge_start_time'] = time.time()

            # Phase 1: Initialize Balance Manager V2 with WebSocket-first configuration
            logger.info("[WEBSOCKET_V2_BRIDGE] Phase 1: Setting up Balance Manager V2...")

            balance_config = BalanceManagerV2Config(
                websocket_primary_ratio=0.95,     # 95% WebSocket usage
                rest_fallback_ratio=0.05,         # 5% REST fallback
                balance_max_age=30.0,              # Fast updates
                enable_balance_validation=True,
                enable_balance_aggregation=True,
                enable_circuit_breaker=True,
                enable_performance_monitoring=True,
                enable_balance_callbacks=True     # Enable callback system
            )

            self.balance_manager_v2 = BalanceManagerV2(
                websocket_client=self.websocket_client,
                exchange_client=self.exchange_client,
                config=balance_config
            )

            # Initialize Balance Manager V2
            v2_initialized = await self.balance_manager_v2.initialize()
            if not v2_initialized:
                logger.error("[WEBSOCKET_V2_BRIDGE] Balance Manager V2 initialization failed")
                return False

            logger.info("[WEBSOCKET_V2_BRIDGE] ✅ Balance Manager V2 initialized")

            # Phase 2: Setup balance data flow bridge
            logger.info("[WEBSOCKET_V2_BRIDGE] Phase 2: Setting up balance data bridge...")

            # Register for balance updates from Balance Manager V2
            if hasattr(self.balance_manager_v2, 'register_callback'):
                self.balance_manager_v2.register_callback(self._on_balance_manager_v2_update)
                logger.info("[WEBSOCKET_V2_BRIDGE] Registered with Balance Manager V2 callbacks")

            # If we have WebSocket stream directly, also register with it
            if hasattr(self.balance_manager_v2, 'websocket_stream') and self.balance_manager_v2.websocket_stream:
                self.balance_manager_v2.websocket_stream.register_balance_callback(self._on_websocket_stream_update)
                logger.info("[WEBSOCKET_V2_BRIDGE] Registered with WebSocket stream callbacks")

            # Phase 3: Bridge with existing balance manager (if available)
            if self.existing_balance_manager:
                logger.info("[WEBSOCKET_V2_BRIDGE] Phase 3: Bridging with existing balance manager...")
                await self._setup_existing_balance_manager_bridge()

            self.initialized = True
            self.running = True

            # Phase 4: Perform initial balance sync
            logger.info("[WEBSOCKET_V2_BRIDGE] Phase 4: Performing initial balance sync...")
            await self._sync_initial_balances()

            logger.info("[WEBSOCKET_V2_BRIDGE] ✅ WebSocket V2 balance bridge initialized successfully")
            return True

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Initialization failed: {e}")
            import traceback
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Traceback: {traceback.format_exc()}")
            return False

    async def _setup_existing_balance_manager_bridge(self):
        """Setup bridge with existing balance manager"""
        try:
            # If existing balance manager has callback registration, register with it
            if hasattr(self.existing_balance_manager, 'register_callback'):
                # Register to receive updates from existing manager too (for bi-directional sync)
                self.existing_balance_manager.register_callback(self._on_existing_balance_manager_update)
                logger.info("[WEBSOCKET_V2_BRIDGE] Registered with existing balance manager")

            # If existing balance manager has process_websocket_update, we'll use it to send updates
            if hasattr(self.existing_balance_manager, 'process_websocket_update'):
                logger.info("[WEBSOCKET_V2_BRIDGE] Existing balance manager supports WebSocket updates")
            elif hasattr(self.existing_balance_manager, 'update_from_websocket'):
                logger.info("[WEBSOCKET_V2_BRIDGE] Existing balance manager supports legacy WebSocket updates")
            else:
                logger.warning("[WEBSOCKET_V2_BRIDGE] Existing balance manager has no WebSocket update methods")

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error setting up existing balance manager bridge: {e}")

    async def _sync_initial_balances(self):
        """Sync initial balance data across all systems"""
        try:
            # Get all balances from Balance Manager V2
            all_balances = await self.balance_manager_v2.get_all_balances()

            if all_balances:
                logger.info(f"[WEBSOCKET_V2_BRIDGE] Syncing {len(all_balances)} initial balances")

                # Convert to our bridge format
                converted_balances = {}
                for asset, balance_data in all_balances.items():
                    converted_balances[asset] = self._convert_balance_format(balance_data, asset)

                # Update our cache
                self.current_balances = converted_balances
                self.last_update_time = time.time()

                # Distribute to existing balance manager if available
                if self.existing_balance_manager:
                    await self._forward_to_existing_balance_manager(converted_balances)

                # Call registered callbacks
                await self._distribute_balance_update(converted_balances, source='initial_sync')

                logger.info(f"[WEBSOCKET_V2_BRIDGE] Initial balance sync completed: {len(converted_balances)} assets")
            else:
                logger.warning("[WEBSOCKET_V2_BRIDGE] No initial balances available from Balance Manager V2")

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Initial balance sync failed: {e}")

    async def _on_balance_manager_v2_update(self, asset: str, balance_data: dict[str, Any]):
        """Handle balance updates from Balance Manager V2"""
        try:
            self.stats['updates_received'] += 1

            # Convert format for bridge
            bridge_format = self._convert_balance_format(balance_data, asset)

            # Update cache
            self.current_balances[asset] = bridge_format
            self.last_update_time = time.time()

            # Forward to existing balance manager
            if self.existing_balance_manager:
                single_asset_update = {asset: bridge_format}
                await self._forward_to_existing_balance_manager(single_asset_update)

            # Distribute to registered callbacks
            await self._distribute_balance_update({asset: bridge_format}, source='balance_manager_v2')

            self.stats['updates_distributed'] += 1

            if asset in ['USDT', 'BTC', 'ETH', 'SHIB', 'MANA'] or balance_data.get('free', 0) > 1.0:
                logger.info(f"[WEBSOCKET_V2_BRIDGE] Balance update bridged: {asset} = {balance_data.get('free', 0):.8f}")

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error handling Balance Manager V2 update: {e}")
            self.stats['callback_errors'] += 1

    async def _on_websocket_stream_update(self, balance_update: BalanceUpdate):
        """Handle balance updates directly from WebSocket stream"""
        try:
            asset = balance_update.asset
            balance_data = balance_update.to_dict()

            # This is essentially the same as the Balance Manager V2 update,
            # but we get it directly from the stream for faster processing
            await self._on_balance_manager_v2_update(asset, balance_data)

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error handling WebSocket stream update: {e}")

    async def _on_existing_balance_manager_update(self, *args, **kwargs):
        """Handle updates from existing balance manager (for bi-directional sync)"""
        try:
            # This would handle updates coming from the existing balance manager
            # For now, we log it but don't take action to avoid loops
            logger.debug("[WEBSOCKET_V2_BRIDGE] Received update from existing balance manager")

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error handling existing balance manager update: {e}")

    def _convert_balance_format(self, balance_data: dict[str, Any], asset: str) -> dict[str, Any]:
        """Convert balance data to format expected by existing bot components"""
        try:
            self.stats['format_conversions'] += 1

            # Extract values with proper defaults
            free = balance_data.get('free', 0.0)
            used = balance_data.get('used', balance_data.get('hold_trade', 0.0))
            total = balance_data.get('total', balance_data.get('balance', free + used))

            # Create compatible format
            converted = {
                'asset': asset,
                'free': float(free),
                'used': float(used),
                'total': float(total),
                'balance': float(total),  # Legacy compatibility
                'timestamp': balance_data.get('timestamp', time.time()),
                'source': 'websocket_v2_bridge'
            }

            return converted

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Balance format conversion error for {asset}: {e}")
            return {
                'asset': asset,
                'free': 0.0,
                'used': 0.0,
                'total': 0.0,
                'balance': 0.0,
                'timestamp': time.time(),
                'source': 'websocket_v2_bridge_error'
            }

    async def _forward_to_existing_balance_manager(self, balances: dict[str, dict[str, Any]]):
        """Forward balance updates to existing balance manager"""
        try:
            if not self.existing_balance_manager:
                return

            # Try process_websocket_update method first (recommended)
            if hasattr(self.existing_balance_manager, 'process_websocket_update'):
                await self.existing_balance_manager.process_websocket_update(balances)
                logger.debug(f"[WEBSOCKET_V2_BRIDGE] Forwarded to existing balance manager via process_websocket_update: {len(balances)} assets")

            # Fallback to update_from_websocket method
            elif hasattr(self.existing_balance_manager, 'update_from_websocket'):
                await self.existing_balance_manager.update_from_websocket(balances)
                logger.debug(f"[WEBSOCKET_V2_BRIDGE] Forwarded to existing balance manager via update_from_websocket: {len(balances)} assets")

            # If no WebSocket methods, try setting balances directly
            elif hasattr(self.existing_balance_manager, 'balances'):
                # Direct update of balance cache (last resort)
                for asset, balance_data in balances.items():
                    self.existing_balance_manager.balances[asset] = balance_data
                logger.debug(f"[WEBSOCKET_V2_BRIDGE] Updated existing balance manager cache directly: {len(balances)} assets")

            else:
                logger.warning("[WEBSOCKET_V2_BRIDGE] Existing balance manager has no compatible update methods")

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error forwarding to existing balance manager: {e}")

    async def _distribute_balance_update(self, balances: dict[str, dict[str, Any]], source: str = 'unknown'):
        """Distribute balance updates to all registered callbacks"""
        try:
            # Call balance callbacks (expect balances dict)
            for callback in self.balance_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(balances, source=source)
                    else:
                        callback(balances, source=source)
                except Exception as callback_error:
                    logger.error(f"[WEBSOCKET_V2_BRIDGE] Balance callback error: {callback_error}")
                    self.stats['callback_errors'] += 1

            # Call update callbacks (might expect different format)
            for callback in self.update_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(balances)
                    else:
                        callback(balances)
                except Exception as callback_error:
                    logger.error(f"[WEBSOCKET_V2_BRIDGE] Update callback error: {callback_error}")
                    self.stats['callback_errors'] += 1

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error distributing balance update: {e}")

    # Public API methods for compatibility with existing bot

    def register_balance_callback(self, callback: Callable):
        """Register callback for balance updates (compatible with existing bot)"""
        self.balance_callbacks.append(callback)
        logger.info("[WEBSOCKET_V2_BRIDGE] Registered balance callback")

    def register_update_callback(self, callback: Callable):
        """Register callback for balance updates (alternative interface)"""
        self.update_callbacks.append(callback)
        logger.info("[WEBSOCKET_V2_BRIDGE] Registered update callback")

    async def get_balance(self, asset: str) -> Optional[dict[str, Any]]:
        """Get balance for specific asset (compatible interface)"""
        try:
            if self.balance_manager_v2:
                # Get from Balance Manager V2 (most up-to-date)
                balance_data = await self.balance_manager_v2.get_balance(asset)
                if balance_data:
                    return self._convert_balance_format(balance_data, asset)

            # Fallback to cached data
            return self.current_balances.get(asset)

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error getting balance for {asset}: {e}")
            return None

    async def get_all_balances(self) -> dict[str, dict[str, Any]]:
        """Get all balances (compatible interface)"""
        try:
            if self.balance_manager_v2:
                # Get from Balance Manager V2 (most up-to-date)
                all_balances = await self.balance_manager_v2.get_all_balances()
                if all_balances:
                    converted = {}
                    for asset, balance_data in all_balances.items():
                        converted[asset] = self._convert_balance_format(balance_data, asset)
                    return converted

            # Fallback to cached data
            return self.current_balances.copy()

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error getting all balances: {e}")
            return {}

    async def get_usdt_total(self) -> float:
        """Get total USDT across all variants"""
        try:
            if self.balance_manager_v2:
                return await self.balance_manager_v2.get_usdt_total()

            # Fallback calculation
            total = 0.0
            usdt_variants = ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S', 'USDT.F', 'USDT.B']
            for variant in usdt_variants:
                balance_data = self.current_balances.get(variant)
                if balance_data:
                    total += balance_data.get('free', 0.0)

            return total

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error getting USDT total: {e}")
            return 0.0

    async def force_refresh(self) -> bool:
        """Force refresh of balance data"""
        try:
            if self.balance_manager_v2:
                success = await self.balance_manager_v2.force_refresh()
                if success:
                    # Re-sync after refresh
                    await self._sync_initial_balances()
                return success

            return False

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Error during force refresh: {e}")
            return False

    def get_status(self) -> dict[str, Any]:
        """Get bridge status information"""
        uptime = time.time() - self.stats['bridge_start_time'] if self.stats['bridge_start_time'] > 0 else 0

        status = {
            'initialized': self.initialized,
            'running': self.running,
            'uptime_seconds': uptime,
            'cached_balances': len(self.current_balances),
            'last_update_time': self.last_update_time,
            'time_since_last_update': time.time() - self.last_update_time if self.last_update_time > 0 else float('inf'),
            'registered_callbacks': len(self.balance_callbacks) + len(self.update_callbacks),
            'statistics': dict(self.stats),
            'has_existing_balance_manager': self.existing_balance_manager is not None,
            'balance_manager_v2_available': self.balance_manager_v2 is not None
        }

        # Add Balance Manager V2 status if available
        if self.balance_manager_v2:
            try:
                v2_status = self.balance_manager_v2.get_status()
                status['balance_manager_v2_status'] = v2_status
            except Exception as e:
                status['balance_manager_v2_status'] = {'error': str(e)}

        return status

    async def shutdown(self):
        """Shutdown the bridge"""
        logger.info("[WEBSOCKET_V2_BRIDGE] Shutting down...")

        self.running = False

        try:
            if self.balance_manager_v2:
                await self.balance_manager_v2.shutdown()

            # Clear callbacks
            self.balance_callbacks.clear()
            self.update_callbacks.clear()

            # Clear cache
            self.current_balances.clear()

            self.initialized = False

            logger.info("[WEBSOCKET_V2_BRIDGE] Shutdown complete")

        except Exception as e:
            logger.error(f"[WEBSOCKET_V2_BRIDGE] Shutdown error: {e}")


class WebSocketV2BalanceIntegrationFix:
    """
    Main integration fix that creates and manages the bridge
    """

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = None
        self.exchange_client = None
        self.websocket_client = None
        self.bridge = None

    async def apply_fix(self, existing_bot=None) -> bool:
        """Apply the WebSocket V2 balance integration fix"""
        logger.info("=" * 60)
        logger.info("APPLYING WEBSOCKET V2 BALANCE INTEGRATION FIX")
        logger.info("=" * 60)

        try:
            # Load configuration
            self.config = load_config(self.config_path)
            if not self.config:
                logger.error("Failed to load configuration")
                return False

            # Setup exchange client
            from src.exchange.kraken_client import KrakenExchangeClient
            api_config = self.config['kraken_api']

            self.exchange_client = KrakenExchangeClient(
                api_key=api_config['api_key'],
                api_secret=api_config['api_secret']
            )

            await self.exchange_client.initialize()
            logger.info("✅ Exchange client initialized")

            # Setup WebSocket V2 client
            ws_config = KrakenWebSocketConfig()
            self.websocket_client = KrakenWebSocketV2(
                api_key=api_config['api_key'],
                api_secret=api_config['api_secret'],
                config=ws_config
            )

            self.websocket_client.set_exchange_client(self.exchange_client)

            # Connect WebSocket V2
            connected = await self.websocket_client.connect(private_channels=True)
            if connected:
                logger.info("✅ WebSocket V2 connected")
            else:
                logger.warning("⚠️ WebSocket V2 connection failed, will use REST fallback")

            # Get existing balance manager from bot if available
            existing_balance_manager = None
            if existing_bot and hasattr(existing_bot, 'balance_manager'):
                existing_balance_manager = existing_bot.balance_manager
                logger.info("✅ Found existing balance manager in bot")

            # Create and initialize bridge
            self.bridge = WebSocketV2BalanceBridge(
                websocket_client=self.websocket_client,
                exchange_client=self.exchange_client,
                existing_balance_manager=existing_balance_manager
            )

            bridge_initialized = await self.bridge.initialize()
            if not bridge_initialized:
                logger.error("❌ Bridge initialization failed")
                return False

            logger.info("✅ WebSocket V2 balance bridge initialized")

            # If we have an existing bot, integrate the bridge
            if existing_bot:
                await self._integrate_with_existing_bot(existing_bot)

            logger.info("🎉 WebSocket V2 balance integration fix applied successfully!")
            return True

        except Exception as e:
            logger.error(f"❌ Integration fix failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def _integrate_with_existing_bot(self, bot):
        """Integrate bridge with existing bot"""
        try:
            # Replace or enhance the bot's balance manager
            if hasattr(bot, 'balance_manager_v2'):
                # Bot already has V2 - replace it with our bridge
                bot.balance_manager_v2 = self.bridge
                logger.info("✅ Replaced bot's balance_manager_v2 with bridge")
            else:
                # Add V2 support to bot
                bot.balance_manager_v2 = self.bridge
                logger.info("✅ Added balance_manager_v2 bridge to bot")

            # If bot has WebSocket callbacks, register our bridge
            if hasattr(bot, '_handle_unified_balance_update'):
                self.bridge.register_balance_callback(bot._handle_unified_balance_update)
                logger.info("✅ Registered bridge with bot's balance update handler")

            # If bot has websocket_manager, integrate with it
            if hasattr(bot, 'websocket_manager') and bot.websocket_manager:
                # Try to set our bridge as a callback
                if hasattr(bot.websocket_manager, 'set_callback'):
                    bot.websocket_manager.set_callback('balance', self.bridge._distribute_balance_update)
                    logger.info("✅ Integrated bridge with bot's WebSocket manager")

        except Exception as e:
            logger.error(f"Error integrating bridge with existing bot: {e}")

    async def test_integration(self, duration: int = 60):
        """Test the integration for a specified duration"""
        if not self.bridge:
            logger.error("Bridge not initialized - run apply_fix() first")
            return False

        logger.info(f"Testing WebSocket V2 balance integration for {duration} seconds...")

        test_start = time.time()
        initial_stats = self.bridge.stats.copy()

        try:
            while (time.time() - test_start) < duration:
                await asyncio.sleep(5)

                # Get status
                status = self.bridge.get_status()
                elapsed = time.time() - test_start

                logger.info(f"[{elapsed:.0f}s] Bridge Status: "
                           f"{status['cached_balances']} balances, "
                           f"{status['statistics']['updates_received']} updates received, "
                           f"{status['statistics']['updates_distributed']} distributed")

                # Test balance access
                usdt_total = await self.bridge.get_usdt_total()
                if usdt_total > 0:
                    logger.info(f"[{elapsed:.0f}s] USDT Total: ${usdt_total:.2f}")

            # Final stats
            final_stats = self.bridge.stats
            updates_during_test = final_stats['updates_received'] - initial_stats['updates_received']

            logger.info("✅ Integration test completed!")
            logger.info(f"   Updates received during test: {updates_during_test}")
            logger.info(f"   Bridge uptime: {status['uptime_seconds']:.1f}s")
            logger.info(f"   Balance data available: {status['cached_balances']} assets")

            return updates_during_test > 0  # Success if we got at least one update

        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return False

    async def cleanup(self):
        """Cleanup the integration fix"""
        logger.info("Cleaning up WebSocket V2 balance integration fix...")

        try:
            if self.bridge:
                await self.bridge.shutdown()

            if self.websocket_client:
                await self.websocket_client.disconnect()

            if self.exchange_client:
                await self.exchange_client.close()

            logger.info("✅ Cleanup completed")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Main function to apply and test the integration fix"""
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket V2 Balance Integration Fix")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--test-duration", type=int, default=120, help="Test duration in seconds")
    parser.add_argument("--apply-only", action="store_true", help="Apply fix only, don't test")
    args = parser.parse_args()

    # Create integration fix
    integration_fix = WebSocketV2BalanceIntegrationFix(args.config)

    try:
        # Apply the fix
        success = await integration_fix.apply_fix()

        if not success:
            logger.error("❌ Failed to apply integration fix")
            sys.exit(1)

        if not args.apply_only:
            # Test the integration
            test_success = await integration_fix.test_integration(args.test_duration)

            if test_success:
                logger.info("🎉 Integration fix applied and tested successfully!")
                logger.info("   → WebSocket V2 balance data is now flowing to trading bot")
                logger.info("   → Real-time balance updates are working")
                logger.info("   → Balance data is available for trading decisions")
            else:
                logger.warning("⚠️ Integration fix applied but testing showed issues")
                logger.warning("   → Check WebSocket connection and API permissions")

        # Keep running to demonstrate the integration
        if not args.apply_only:
            logger.info("Integration fix is running. Press Ctrl+C to stop...")
            try:
                while True:
                    await asyncio.sleep(60)
                    status = integration_fix.bridge.get_status()
                    logger.info(f"Bridge running: {status['statistics']['updates_received']} total updates")
            except KeyboardInterrupt:
                logger.info("Stopping integration fix...")

    except KeyboardInterrupt:
        logger.info("Integration fix interrupted by user")
    except Exception as e:
        logger.error(f"Integration fix crashed: {e}")
        sys.exit(1)
    finally:
        await integration_fix.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
