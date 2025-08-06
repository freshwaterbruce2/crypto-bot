"""
Ultra-Fast Order Router
=======================

Optimized order routing for fee-free micro-scalping with sub-100ms execution.
Handles parallel order submission and automatic retries.

Features:
- Direct market order execution
- Parallel order processing
- Pre-validated order templates
- Automatic retry with backoff
- Performance monitoring
"""

import asyncio
import logging
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class OrderRequest:
    """Order request with pre-validated parameters"""
    symbol: str
    side: str  # 'buy' or 'sell'
    size: float
    order_type: str = 'market'
    price: Optional[float] = None
    metadata: dict[str, Any] = None
    priority: int = 0
    created_at: float = 0.0
    retry_count: int = 0


@dataclass
class OrderResult:
    """Result of order execution"""
    request: OrderRequest
    success: bool
    order_id: Optional[str]
    execution_time: float
    response: dict[str, Any]
    error: Optional[str] = None


class FastOrderRouter:
    """Ultra-fast order routing for high-frequency trading"""

    def __init__(self, exchange_client, config: dict[str, Any]):
        """Initialize fast order router"""
        self.exchange = exchange_client
        self.config = config

        # Performance targets
        self.target_execution_time = 0.1  # 100ms target
        self.max_execution_time = 0.5  # 500ms max
        self.max_retries = 2
        self.retry_delays = [0.1, 0.2]  # Exponential backoff

        # Order validation cache
        self.symbol_info_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = {}

        # Performance tracking
        self.execution_times = deque(maxlen=100)
        self.success_count = 0
        self.failure_count = 0
        self.retry_count = 0

        # Parallel execution
        self.max_concurrent_orders = 5
        self.order_semaphore = asyncio.Semaphore(self.max_concurrent_orders)
        self.executor = ThreadPoolExecutor(max_workers=3)

        # Pre-compiled order templates
        self.order_templates = self._create_order_templates()

        logger.info(f"[FAST_ROUTER] Initialized - Target: {self.target_execution_time*1000:.0f}ms")

    def _create_order_templates(self) -> dict[str, dict[str, Any]]:
        """Create pre-validated order templates"""
        return {
            'market_buy': {
                'type': 'market',
                'side': 'buy',
                'time_in_force': 'IOC'  # Immediate or cancel
            },
            'market_sell': {
                'type': 'market',
                'side': 'sell',
                'time_in_force': 'IOC'
            }
        }

    async def execute_order(self, request: OrderRequest) -> OrderResult:
        """Execute single order with optimal routing"""
        start_time = time.time()

        try:
            # Quick validation
            if not await self._validate_order(request):
                return OrderResult(
                    request=request,
                    success=False,
                    order_id=None,
                    execution_time=time.time() - start_time,
                    response={},
                    error="Validation failed"
                )

            # Execute with retries
            async with self.order_semaphore:
                result = await self._execute_with_retry(request)

            # Track performance
            execution_time = time.time() - start_time
            self.execution_times.append(execution_time)

            if result.success:
                self.success_count += 1
                if execution_time <= self.target_execution_time:
                    logger.debug(f"[FAST_ROUTER] ⚡ Ultra-fast execution: {execution_time*1000:.0f}ms")
            else:
                self.failure_count += 1

            result.execution_time = execution_time
            return result

        except Exception as e:
            logger.error(f"[FAST_ROUTER] Execution error: {e}")
            return OrderResult(
                request=request,
                success=False,
                order_id=None,
                execution_time=time.time() - start_time,
                response={},
                error=str(e)
            )

    async def execute_batch(self, requests: list[OrderRequest]) -> list[OrderResult]:
        """Execute multiple orders in parallel"""
        logger.info(f"[FAST_ROUTER] Executing batch of {len(requests)} orders")

        # Sort by priority
        sorted_requests = sorted(requests, key=lambda x: x.priority, reverse=True)

        # Execute in parallel
        tasks = []
        for request in sorted_requests:
            task = asyncio.create_task(self.execute_order(request))
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Log batch performance
        success_count = sum(1 for r in results if r.success)
        avg_time = sum(r.execution_time for r in results) / len(results) if results else 0

        logger.info(
            f"[FAST_ROUTER] Batch complete: {success_count}/{len(results)} successful, "
            f"Avg time: {avg_time*1000:.0f}ms"
        )

        return results

    async def _validate_order(self, request: OrderRequest) -> bool:
        """Fast order validation"""
        try:
            # Check minimum size
            if request.size < self.config.get('min_order_size_usdt', 2.0):
                return False

            # Check maximum size
            if request.size > self.config.get('max_order_size_usdt', 5.0):
                return False

            # Validate symbol (cached)
            if not await self._validate_symbol(request.symbol):
                return False

            return True

        except Exception as e:
            logger.error(f"[FAST_ROUTER] Validation error: {e}")
            return False

    async def _validate_symbol(self, symbol: str) -> bool:
        """Validate symbol with caching"""
        # Check cache
        if symbol in self.symbol_info_cache:
            cache_time = self.last_cache_update.get(symbol, 0)
            if time.time() - cache_time < self.cache_ttl:
                return self.symbol_info_cache[symbol]

        # Validate and cache
        try:
            # Quick check if symbol is in configured pairs
            if symbol in self.config.get('trade_pairs', []):
                self.symbol_info_cache[symbol] = True
                self.last_cache_update[symbol] = time.time()
                return True

            return False

        except Exception:
            return False

    async def _execute_with_retry(self, request: OrderRequest) -> OrderResult:
        """Execute order with automatic retry"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                # Add retry delay if not first attempt
                if attempt > 0:
                    self.retry_count += 1
                    delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                    await asyncio.sleep(delay)
                    logger.debug(f"[FAST_ROUTER] Retry {attempt} for {request.symbol}")

                # Execute order
                result = await self._execute_single_order(request)

                if result.success:
                    return result

                last_error = result.error

                # Don't retry certain errors
                if self._is_permanent_error(result.error):
                    return result

            except Exception as e:
                last_error = str(e)
                logger.error(f"[FAST_ROUTER] Attempt {attempt + 1} failed: {e}")

        # All retries failed
        return OrderResult(
            request=request,
            success=False,
            order_id=None,
            execution_time=0,
            response={},
            error=f"Max retries exceeded. Last error: {last_error}"
        )

    async def _execute_single_order(self, request: OrderRequest) -> OrderResult:
        """Execute single order through exchange"""
        try:
            # Build order parameters
            order_params = self._build_order_params(request)

            # Execute through exchange
            start_time = time.time()

            if request.order_type == 'market':
                response = await self.exchange.create_market_order(
                    symbol=request.symbol,
                    side=request.side,
                    amount=request.size,
                    params=order_params
                )
            else:
                # Limit order support (not used for fee-free micro-scalping)
                response = await self.exchange.create_limit_order(
                    symbol=request.symbol,
                    side=request.side,
                    amount=request.size,
                    price=request.price,
                    params=order_params
                )

            execution_time = time.time() - start_time

            # Parse response
            if response and response.get('id'):
                return OrderResult(
                    request=request,
                    success=True,
                    order_id=response['id'],
                    execution_time=execution_time,
                    response=response
                )
            else:
                return OrderResult(
                    request=request,
                    success=False,
                    order_id=None,
                    execution_time=execution_time,
                    response=response or {},
                    error="No order ID in response"
                )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[FAST_ROUTER] Order execution failed: {error_msg}")

            return OrderResult(
                request=request,
                success=False,
                order_id=None,
                execution_time=0,
                response={},
                error=error_msg
            )

    def _build_order_params(self, request: OrderRequest) -> dict[str, Any]:
        """Build order parameters from template"""
        # Get base template
        template_key = f"{request.order_type}_{request.side}"
        params = self.order_templates.get(template_key, {}).copy()

        # Add metadata
        if request.metadata:
            params['client_order_id'] = f"hft_{int(time.time() * 1000)}"
            params['metadata'] = request.metadata

        # Force IOC for micro-scalping
        params['time_in_force'] = 'IOC'

        return params

    def _is_permanent_error(self, error: Optional[str]) -> bool:
        """Check if error should not be retried"""
        if not error:
            return False

        permanent_errors = [
            'insufficient balance',
            'minimum order size',
            'invalid symbol',
            'market closed',
            'permissions',
            'invalid api key'
        ]

        error_lower = error.lower()
        return any(perma in error_lower for perma in permanent_errors)

    def get_performance_stats(self) -> dict[str, Any]:
        """Get router performance statistics"""
        total_orders = self.success_count + self.failure_count

        if self.execution_times:
            avg_time = sum(self.execution_times) / len(self.execution_times)
            min_time = min(self.execution_times)
            max_time = max(self.execution_times)

            # Calculate percentiles
            sorted_times = sorted(self.execution_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
        else:
            avg_time = min_time = max_time = p50 = p95 = 0

        return {
            'total_orders': total_orders,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': self.success_count / total_orders if total_orders > 0 else 0,
            'retry_count': self.retry_count,
            'retry_rate': self.retry_count / total_orders if total_orders > 0 else 0,
            'execution_times': {
                'average': avg_time,
                'min': min_time,
                'max': max_time,
                'p50': p50,
                'p95': p95,
                'target': self.target_execution_time,
                'below_target_pct': sum(1 for t in self.execution_times if t <= self.target_execution_time) / len(self.execution_times) if self.execution_times else 0
            }
        }

    async def create_market_buy(self, symbol: str, size: float, metadata: dict = None) -> OrderResult:
        """Convenience method for market buy orders"""
        request = OrderRequest(
            symbol=symbol,
            side='buy',
            size=size,
            order_type='market',
            metadata=metadata,
            created_at=time.time()
        )
        return await self.execute_order(request)

    async def create_market_sell(self, symbol: str, size: float, metadata: dict = None) -> OrderResult:
        """Convenience method for market sell orders"""
        request = OrderRequest(
            symbol=symbol,
            side='sell',
            size=size,
            order_type='market',
            metadata=metadata,
            created_at=time.time()
        )
        return await self.execute_order(request)
