"""
REST Data Validator for Crypto Trading Bot
=========================================

Cross-validation system that compares REST API data with WebSocket V2 data
to ensure data integrity and detect discrepancies in real-time.

Key Features:
- Cross-validation between REST and WebSocket data sources
- Automated discrepancy detection and resolution
- Periodic validation scheduling with smart intervals
- Data integrity monitoring and reporting
- Fallback validation when primary source fails

Usage:
    validator = RestDataValidator(strategic_client, websocket_manager)
    await validator.initialize()
    
    # Validate specific data
    is_valid = await validator.validate_balance_data(rest_data, ws_data)
    
    # Run continuous validation
    await validator.start_continuous_validation()
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .strategic_rest_client import StrategicRestClient

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Results from data validation."""
    is_valid: bool
    confidence: float  # 0.0 to 1.0
    discrepancies: List[str] = field(default_factory=list)
    rest_data: Optional[Dict[str, Any]] = None
    websocket_data: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    resolution_action: Optional[str] = None


@dataclass
class ValidationStats:
    """Statistics for validation operations."""
    total_validations: int = 0
    successful_validations: int = 0
    failed_validations: int = 0
    discrepancies_found: int = 0
    critical_discrepancies: int = 0
    average_confidence: float = 1.0
    last_validation: Optional[float] = None

    def update(self, result: ValidationResult):
        """Update stats with validation result."""
        self.total_validations += 1
        self.last_validation = result.timestamp

        if result.is_valid:
            self.successful_validations += 1
        else:
            self.failed_validations += 1

        if result.discrepancies:
            self.discrepancies_found += len(result.discrepancies)

            # Check for critical discrepancies
            critical_keywords = ['balance', 'order', 'price', 'volume']
            for discrepancy in result.discrepancies:
                if any(keyword in discrepancy.lower() for keyword in critical_keywords):
                    self.critical_discrepancies += 1

        # Update average confidence
        total_confidence = (self.average_confidence * (self.total_validations - 1) +
                          result.confidence)
        self.average_confidence = total_confidence / self.total_validations


class RestDataValidator:
    """
    Cross-validation system for REST and WebSocket data integrity.
    
    Provides comprehensive data validation, discrepancy detection,
    and automated resolution strategies to ensure data consistency.
    """

    def __init__(
        self,
        strategic_client: StrategicRestClient,
        websocket_manager: Optional[Any] = None,
        validation_interval: float = 60.0,
        tolerance_threshold: float = 0.001,
        max_validation_age: float = 300.0
    ):
        """
        Initialize REST data validator.
        
        Args:
            strategic_client: Strategic REST client instance
            websocket_manager: WebSocket manager for data comparison
            validation_interval: Seconds between automatic validations
            tolerance_threshold: Threshold for numerical comparisons
            max_validation_age: Maximum age of validation data to consider
        """
        self.strategic_client = strategic_client
        self.websocket_manager = websocket_manager
        self.validation_interval = validation_interval
        self.tolerance_threshold = tolerance_threshold
        self.max_validation_age = max_validation_age

        # Validation tracking
        self.stats = ValidationStats()
        self._validation_history: List[ValidationResult] = []
        self._discrepancy_patterns: Dict[str, int] = {}

        # Validation tasks
        self._validation_task: Optional[asyncio.Task] = None
        self._balance_validation_task: Optional[asyncio.Task] = None
        self._price_validation_task: Optional[asyncio.Task] = None

        # Configuration
        self._critical_pairs = set()  # Pairs requiring critical validation
        self._validation_lock = asyncio.Lock()

        # Thresholds for different data types
        self._balance_tolerance = 0.00001  # 1e-5 for balance precision
        self._price_tolerance = 0.001      # 0.1% for price differences
        self._volume_tolerance = 0.01      # 1% for volume differences

        # State
        self._initialized = False
        self._running = False

        logger.info(
            f"[REST_VALIDATOR] Initialized: "
            f"interval={validation_interval}s, tolerance={tolerance_threshold}"
        )

    async def initialize(self) -> None:
        """Initialize the validator."""
        if self._initialized:
            return

        # Ensure strategic client is ready
        if not self.strategic_client._initialized:
            await self.strategic_client.initialize()

        self._initialized = True
        logger.info("[REST_VALIDATOR] Validator initialized")

    async def start_continuous_validation(self) -> None:
        """Start continuous background validation."""
        if not self._initialized:
            await self.initialize()

        if self._running:
            return

        self._running = True

        # Start validation tasks
        self._validation_task = asyncio.create_task(self._continuous_validator())
        self._balance_validation_task = asyncio.create_task(self._balance_validator())
        self._price_validation_task = asyncio.create_task(self._price_validator())

        logger.info("[REST_VALIDATOR] Continuous validation started")

    async def stop_continuous_validation(self) -> None:
        """Stop continuous validation."""
        self._running = False

        # Cancel all validation tasks
        tasks = [self._validation_task, self._balance_validation_task, self._price_validation_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("[REST_VALIDATOR] Continuous validation stopped")

    async def _continuous_validator(self) -> None:
        """Background continuous validation task."""
        while self._running:
            try:
                await asyncio.sleep(self.validation_interval)

                # Perform comprehensive validation
                await self._perform_scheduled_validation()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[REST_VALIDATOR] Continuous validation error: {e}")
                await asyncio.sleep(30.0)  # Backoff on error

    async def _balance_validator(self) -> None:
        """Background balance validation task."""
        while self._running:
            try:
                await asyncio.sleep(self.validation_interval * 2)  # Less frequent

                if self.websocket_manager:
                    await self._validate_balance_consistency()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[REST_VALIDATOR] Balance validation error: {e}")
                await asyncio.sleep(60.0)

    async def _price_validator(self) -> None:
        """Background price validation task."""
        while self._running:
            try:
                await asyncio.sleep(self.validation_interval * 0.5)  # More frequent

                if self._critical_pairs and self.websocket_manager:
                    await self._validate_critical_prices()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[REST_VALIDATOR] Price validation error: {e}")
                await asyncio.sleep(30.0)

    # ====== VALIDATION METHODS ======

    async def validate_balance_data(
        self,
        rest_balance: Optional[Dict[str, Any]] = None,
        websocket_balance: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate balance data between REST and WebSocket sources.
        
        Args:
            rest_balance: REST balance data (fetched if None)
            websocket_balance: WebSocket balance data
            
        Returns:
            Validation result
        """
        async with self._validation_lock:
            try:
                # Fetch REST balance if not provided
                if rest_balance is None:
                    try:
                        rest_response = await self.strategic_client.validate_balance_snapshot()
                        rest_balance = rest_response.get('result', {})
                    except Exception as e:
                        return ValidationResult(
                            is_valid=False,
                            confidence=0.0,
                            discrepancies=[f"Failed to fetch REST balance: {e}"]
                        )

                # Get WebSocket balance if available
                if websocket_balance is None and self.websocket_manager:
                    try:
                        websocket_balance = await self._get_websocket_balance()
                    except Exception as e:
                        logger.warning(f"[REST_VALIDATOR] WebSocket balance unavailable: {e}")

                # Perform comparison
                result = self._compare_balance_data(rest_balance, websocket_balance)

                # Update statistics
                self.stats.update(result)
                self._validation_history.append(result)

                # Log result
                if result.is_valid:
                    logger.debug(f"[REST_VALIDATOR] Balance validation passed: confidence={result.confidence:.3f}")
                else:
                    logger.warning(f"[REST_VALIDATOR] Balance validation failed: {result.discrepancies}")

                return result

            except Exception as e:
                logger.error(f"[REST_VALIDATOR] Balance validation error: {e}")
                return ValidationResult(
                    is_valid=False,
                    confidence=0.0,
                    discrepancies=[f"Validation error: {e}"]
                )

    async def validate_price_data(
        self,
        pair: str,
        rest_price: Optional[Dict[str, Any]] = None,
        websocket_price: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate price data for a specific pair.
        
        Args:
            pair: Trading pair to validate
            rest_price: REST price data (fetched if None)
            websocket_price: WebSocket price data
            
        Returns:
            Validation result
        """
        try:
            # Fetch REST price if not provided
            if rest_price is None:
                try:
                    rest_response = await self.strategic_client._execute_strategic_request(
                        'Ticker',
                        {'pair': pair},
                        priority="normal"
                    )
                    rest_price = rest_response.get('result', {}).get(pair, {})
                except Exception as e:
                    return ValidationResult(
                        is_valid=False,
                        confidence=0.0,
                        discrepancies=[f"Failed to fetch REST price for {pair}: {e}"]
                    )

            # Get WebSocket price if available
            if websocket_price is None and self.websocket_manager:
                try:
                    websocket_price = await self._get_websocket_ticker(pair)
                except Exception as e:
                    logger.warning(f"[REST_VALIDATOR] WebSocket price unavailable for {pair}: {e}")

            # Perform comparison
            result = self._compare_price_data(pair, rest_price, websocket_price)

            # Update statistics
            self.stats.update(result)

            return result

        except Exception as e:
            logger.error(f"[REST_VALIDATOR] Price validation error for {pair}: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                discrepancies=[f"Validation error: {e}"]
            )

    async def validate_order_book_data(
        self,
        pair: str,
        depth: int = 10
    ) -> ValidationResult:
        """
        Validate order book data between sources.
        
        Args:
            pair: Trading pair
            depth: Order book depth to validate
            
        Returns:
            Validation result
        """
        try:
            # Fetch REST order book
            rest_response = await self.strategic_client.validate_order_book(pair, depth)
            rest_orderbook = rest_response.get('result', {}).get(pair, {})

            # Get WebSocket order book if available
            websocket_orderbook = None
            if self.websocket_manager:
                try:
                    websocket_orderbook = await self._get_websocket_orderbook(pair)
                except Exception as e:
                    logger.warning(f"[REST_VALIDATOR] WebSocket orderbook unavailable for {pair}: {e}")

            # Perform comparison
            result = self._compare_orderbook_data(pair, rest_orderbook, websocket_orderbook)

            # Update statistics
            self.stats.update(result)

            return result

        except Exception as e:
            logger.error(f"[REST_VALIDATOR] Order book validation error for {pair}: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                discrepancies=[f"Validation error: {e}"]
            )

    # ====== DATA COMPARISON METHODS ======

    def _compare_balance_data(
        self,
        rest_balance: Dict[str, Any],
        websocket_balance: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """Compare balance data from different sources."""
        discrepancies = []
        confidence = 1.0

        if not rest_balance:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                discrepancies=["No REST balance data"],
                rest_data=rest_balance,
                websocket_data=websocket_balance
            )

        if websocket_balance is None:
            # Can't compare, but REST data exists
            return ValidationResult(
                is_valid=True,
                confidence=0.5,  # Reduced confidence without comparison
                discrepancies=["No WebSocket data for comparison"],
                rest_data=rest_balance,
                websocket_data=websocket_balance
            )

        # Compare each asset balance
        for asset, rest_amount in rest_balance.items():
            ws_amount = websocket_balance.get(asset)

            if ws_amount is None:
                discrepancies.append(f"Asset {asset} missing in WebSocket data")
                confidence *= 0.9
                continue

            # Convert to Decimal for precise comparison
            try:
                rest_decimal = Decimal(str(rest_amount))
                ws_decimal = Decimal(str(ws_amount))

                # Calculate difference
                if rest_decimal == 0 and ws_decimal == 0:
                    continue  # Both zero, perfect match

                if rest_decimal == 0 or ws_decimal == 0:
                    if abs(rest_decimal - ws_decimal) > Decimal(str(self._balance_tolerance)):
                        discrepancies.append(
                            f"Balance mismatch for {asset}: REST={rest_decimal}, WS={ws_decimal}"
                        )
                        confidence *= 0.8
                else:
                    # Calculate percentage difference
                    diff_pct = abs(rest_decimal - ws_decimal) / max(rest_decimal, ws_decimal)

                    if diff_pct > Decimal(str(self._balance_tolerance)):
                        discrepancies.append(
                            f"Balance mismatch for {asset}: REST={rest_decimal}, WS={ws_decimal}, "
                            f"diff={diff_pct:.6f}"
                        )
                        confidence *= 0.8

            except (ValueError, TypeError) as e:
                discrepancies.append(f"Invalid balance format for {asset}: {e}")
                confidence *= 0.7

        # Check for assets in WebSocket but not in REST
        for asset in websocket_balance:
            if asset not in rest_balance:
                discrepancies.append(f"Asset {asset} missing in REST data")
                confidence *= 0.9

        return ValidationResult(
            is_valid=len(discrepancies) == 0,
            confidence=confidence,
            discrepancies=discrepancies,
            rest_data=rest_balance,
            websocket_data=websocket_balance
        )

    def _compare_price_data(
        self,
        pair: str,
        rest_price: Dict[str, Any],
        websocket_price: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """Compare price data from different sources."""
        discrepancies = []
        confidence = 1.0

        if not rest_price:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                discrepancies=[f"No REST price data for {pair}"],
                rest_data=rest_price,
                websocket_data=websocket_price
            )

        if websocket_price is None:
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                discrepancies=["No WebSocket price data for comparison"],
                rest_data=rest_price,
                websocket_data=websocket_price
            )

        # Compare key price fields
        price_fields = ['c', 'b', 'a']  # last, bid, ask

        for field in price_fields:
            rest_value = rest_price.get(field)
            ws_value = websocket_price.get(field)

            if rest_value is None or ws_value is None:
                continue

            # Extract price from array if needed
            if isinstance(rest_value, list) and len(rest_value) > 0:
                rest_value = rest_value[0]
            if isinstance(ws_value, list) and len(ws_value) > 0:
                ws_value = ws_value[0]

            try:
                rest_decimal = Decimal(str(rest_value))
                ws_decimal = Decimal(str(ws_value))

                if rest_decimal > 0 and ws_decimal > 0:
                    diff_pct = abs(rest_decimal - ws_decimal) / rest_decimal

                    if diff_pct > Decimal(str(self._price_tolerance)):
                        discrepancies.append(
                            f"Price mismatch for {pair}.{field}: "
                            f"REST={rest_decimal}, WS={ws_decimal}, diff={diff_pct:.4f}"
                        )
                        confidence *= 0.9

            except (ValueError, TypeError) as e:
                discrepancies.append(f"Invalid price format for {pair}.{field}: {e}")
                confidence *= 0.8

        return ValidationResult(
            is_valid=len(discrepancies) == 0,
            confidence=confidence,
            discrepancies=discrepancies,
            rest_data=rest_price,
            websocket_data=websocket_price
        )

    def _compare_orderbook_data(
        self,
        pair: str,
        rest_orderbook: Dict[str, Any],
        websocket_orderbook: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """Compare order book data from different sources."""
        discrepancies = []
        confidence = 1.0

        if not rest_orderbook:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                discrepancies=[f"No REST order book data for {pair}"],
                rest_data=rest_orderbook,
                websocket_data=websocket_orderbook
            )

        if websocket_orderbook is None:
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                discrepancies=["No WebSocket order book data for comparison"],
                rest_data=rest_orderbook,
                websocket_data=websocket_orderbook
            )

        # Compare bids and asks
        for side in ['bids', 'asks']:
            rest_levels = rest_orderbook.get(side, [])
            ws_levels = websocket_orderbook.get(side, [])

            if not rest_levels or not ws_levels:
                discrepancies.append(f"Missing {side} data in one source")
                confidence *= 0.8
                continue

            # Compare top levels (most important)
            max_levels = min(len(rest_levels), len(ws_levels), 5)

            for i in range(max_levels):
                rest_level = rest_levels[i]
                ws_level = ws_levels[i]

                # Compare price and volume
                try:
                    rest_price = Decimal(str(rest_level[0]))
                    ws_price = Decimal(str(ws_level[0]))
                    rest_volume = Decimal(str(rest_level[1]))
                    ws_volume = Decimal(str(ws_level[1]))

                    # Price comparison
                    if rest_price > 0 and ws_price > 0:
                        price_diff = abs(rest_price - ws_price) / rest_price
                        if price_diff > Decimal(str(self._price_tolerance)):
                            discrepancies.append(
                                f"Order book price mismatch {pair}.{side}[{i}]: "
                                f"REST={rest_price}, WS={ws_price}"
                            )
                            confidence *= 0.95

                    # Volume comparison
                    if rest_volume > 0 and ws_volume > 0:
                        volume_diff = abs(rest_volume - ws_volume) / rest_volume
                        if volume_diff > Decimal(str(self._volume_tolerance)):
                            discrepancies.append(
                                f"Order book volume mismatch {pair}.{side}[{i}]: "
                                f"REST={rest_volume}, WS={ws_volume}"
                            )
                            confidence *= 0.95

                except (ValueError, TypeError, IndexError) as e:
                    discrepancies.append(f"Invalid order book format {pair}.{side}[{i}]: {e}")
                    confidence *= 0.9

        return ValidationResult(
            is_valid=len(discrepancies) == 0,
            confidence=confidence,
            discrepancies=discrepancies,
            rest_data=rest_orderbook,
            websocket_data=websocket_orderbook
        )

    # ====== SCHEDULED VALIDATION ======

    async def _perform_scheduled_validation(self) -> None:
        """Perform scheduled comprehensive validation."""
        logger.debug("[REST_VALIDATOR] Performing scheduled validation")

        # Validate balance
        balance_result = await self.validate_balance_data()

        # Validate critical pairs
        for pair in self._critical_pairs:
            try:
                price_result = await self.validate_price_data(pair)
                if not price_result.is_valid:
                    logger.warning(f"[REST_VALIDATOR] Critical pair {pair} validation failed")
            except Exception as e:
                logger.error(f"[REST_VALIDATOR] Critical pair {pair} validation error: {e}")

        # Cleanup old validation history
        self._cleanup_validation_history()

    async def _validate_balance_consistency(self) -> None:
        """Validate balance consistency over time."""
        try:
            result = await self.validate_balance_data()

            if not result.is_valid and result.discrepancies:
                # Track patterns
                for discrepancy in result.discrepancies:
                    self._discrepancy_patterns[discrepancy] = (
                        self._discrepancy_patterns.get(discrepancy, 0) + 1
                    )

                # Log if pattern detected
                for pattern, count in self._discrepancy_patterns.items():
                    if count >= 3:  # Pattern threshold
                        logger.warning(
                            f"[REST_VALIDATOR] Recurring balance discrepancy pattern: "
                            f"{pattern} (count: {count})"
                        )

        except Exception as e:
            logger.error(f"[REST_VALIDATOR] Balance consistency validation error: {e}")

    async def _validate_critical_prices(self) -> None:
        """Validate prices for critical trading pairs."""
        for pair in list(self._critical_pairs):
            try:
                result = await self.validate_price_data(pair)

                if not result.is_valid:
                    logger.warning(
                        f"[REST_VALIDATOR] Critical price validation failed for {pair}: "
                        f"{result.discrepancies}"
                    )

            except Exception as e:
                logger.error(f"[REST_VALIDATOR] Critical price validation error for {pair}: {e}")

    # ====== WEBSOCKET INTEGRATION ======

    async def _get_websocket_balance(self) -> Optional[Dict[str, Any]]:
        """Get balance data from WebSocket manager."""
        if not self.websocket_manager:
            return None

        # This would integrate with the actual WebSocket manager
        # Implementation depends on the WebSocket manager interface
        try:
            if hasattr(self.websocket_manager, 'get_balance'):
                return await self.websocket_manager.get_balance()
            elif hasattr(self.websocket_manager, 'balance_cache'):
                return self.websocket_manager.balance_cache
        except Exception as e:
            logger.error(f"[REST_VALIDATOR] WebSocket balance fetch error: {e}")

        return None

    async def _get_websocket_ticker(self, pair: str) -> Optional[Dict[str, Any]]:
        """Get ticker data from WebSocket manager."""
        if not self.websocket_manager:
            return None

        try:
            if hasattr(self.websocket_manager, 'get_ticker'):
                return await self.websocket_manager.get_ticker(pair)
            elif hasattr(self.websocket_manager, 'ticker_cache'):
                return self.websocket_manager.ticker_cache.get(pair)
        except Exception as e:
            logger.error(f"[REST_VALIDATOR] WebSocket ticker fetch error for {pair}: {e}")

        return None

    async def _get_websocket_orderbook(self, pair: str) -> Optional[Dict[str, Any]]:
        """Get order book data from WebSocket manager."""
        if not self.websocket_manager:
            return None

        try:
            if hasattr(self.websocket_manager, 'get_orderbook'):
                return await self.websocket_manager.get_orderbook(pair)
            elif hasattr(self.websocket_manager, 'orderbook_cache'):
                return self.websocket_manager.orderbook_cache.get(pair)
        except Exception as e:
            logger.error(f"[REST_VALIDATOR] WebSocket orderbook fetch error for {pair}: {e}")

        return None

    # ====== MANAGEMENT METHODS ======

    def add_critical_pair(self, pair: str) -> None:
        """
        Add a trading pair to critical validation list.
        
        Args:
            pair: Trading pair to add
        """
        self._critical_pairs.add(pair)
        logger.info(f"[REST_VALIDATOR] Added critical pair: {pair}")

    def remove_critical_pair(self, pair: str) -> None:
        """
        Remove a trading pair from critical validation list.
        
        Args:
            pair: Trading pair to remove
        """
        self._critical_pairs.discard(pair)
        logger.info(f"[REST_VALIDATOR] Removed critical pair: {pair}")

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            'stats': {
                'total_validations': self.stats.total_validations,
                'successful_validations': self.stats.successful_validations,
                'failed_validations': self.stats.failed_validations,
                'discrepancies_found': self.stats.discrepancies_found,
                'critical_discrepancies': self.stats.critical_discrepancies,
                'average_confidence': self.stats.average_confidence,
                'last_validation': self.stats.last_validation
            },
            'config': {
                'validation_interval': self.validation_interval,
                'tolerance_threshold': self.tolerance_threshold,
                'critical_pairs': list(self._critical_pairs),
                'running': self._running
            },
            'recent_history': self._validation_history[-10:],  # Last 10 validations
            'discrepancy_patterns': dict(self._discrepancy_patterns)
        }

    def _cleanup_validation_history(self) -> None:
        """Clean up old validation history."""
        current_time = time.time()
        cutoff_time = current_time - self.max_validation_age

        # Remove old validation results
        self._validation_history = [
            result for result in self._validation_history
            if result.timestamp > cutoff_time
        ]

        # Clean up discrepancy patterns (keep only recent patterns)
        if len(self._discrepancy_patterns) > 100:
            # Keep only most frequent patterns
            sorted_patterns = sorted(
                self._discrepancy_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )
            self._discrepancy_patterns = dict(sorted_patterns[:50])

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform validator health check.
        
        Returns:
            Health status
        """
        health = {
            'timestamp': time.time(),
            'status': 'healthy',
            'checks': {}
        }

        # Check if running
        health['checks']['validation_running'] = {
            'status': 'healthy' if self._running else 'degraded',
            'running': self._running
        }

        # Check validation frequency
        if self.stats.last_validation:
            time_since_last = time.time() - self.stats.last_validation
            if time_since_last > self.validation_interval * 2:
                health['checks']['validation_frequency'] = {
                    'status': 'degraded',
                    'time_since_last': time_since_last
                }
                health['status'] = 'degraded'
            else:
                health['checks']['validation_frequency'] = {
                    'status': 'healthy',
                    'time_since_last': time_since_last
                }

        # Check validation success rate
        if self.stats.total_validations > 0:
            success_rate = self.stats.successful_validations / self.stats.total_validations
            if success_rate < 0.8:
                health['checks']['success_rate'] = {
                    'status': 'degraded',
                    'rate': success_rate
                }
                health['status'] = 'degraded'
            else:
                health['checks']['success_rate'] = {
                    'status': 'healthy',
                    'rate': success_rate
                }

        return health
