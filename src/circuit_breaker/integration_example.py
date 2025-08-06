"""
Circuit Breaker Integration Example
==================================

Example demonstrating how to integrate the circuit breaker system
with existing authentication and rate limiting systems in the trading bot.

This example shows:
- Integration with KrakenAuth for API authentication
- Integration with KrakenRateLimiter2025 for rate limiting
- Health monitoring for API endpoints
- Failure detection and circuit breaker decisions
- Recovery and retry logic
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Existing system imports
from ..auth.kraken_auth import KrakenAuth
from ..rate_limiting.kraken_rate_limiter import KrakenRateLimiter2025
from ..rate_limiting.rate_limit_config import RequestPriority

# Circuit breaker imports
from .circuit_breaker import (
    BreakerOpenError,
    BreakerTimeoutError,
    CircuitBreakerConfig,
    CircuitBreakerManager,
)
from .failure_detector import FailureDetector
from .health_monitor import HealthMonitor

logger = logging.getLogger(__name__)


class IntegratedKrakenAPIClient:
    """
    Example Kraken API client with integrated circuit breaker protection.
    
    Demonstrates how to combine authentication, rate limiting, health monitoring,
    and circuit breaker protection for robust API interactions.
    """

    def __init__(
        self,
        api_key: str,
        private_key: str,
        storage_dir: Optional[str] = None,
        enable_monitoring: bool = True
    ):
        """
        Initialize integrated API client.
        
        Args:
            api_key: Kraken API key
            private_key: Kraken private key
            storage_dir: Storage directory for persistent state
            enable_monitoring: Enable health monitoring
        """
        self.api_key = api_key
        self.private_key = private_key
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self.enable_monitoring = enable_monitoring

        # Initialize core components
        self._init_authentication()
        self._init_rate_limiting()
        self._init_circuit_breaker()
        self._init_monitoring()

        # Client state
        self._session = None
        self._running = False

        logger.info("Integrated Kraken API client initialized")

    def _init_authentication(self) -> None:
        """
        Initialize authentication system.
        """
        storage_dir = str(self.storage_dir / "auth") if self.storage_dir else None

        self.auth = KrakenAuth(
            api_key=self.api_key,
            private_key=self.private_key,
            storage_dir=storage_dir,
            enable_debug=False
        )

        logger.info("Authentication system initialized")

    def _init_rate_limiting(self) -> None:
        """
        Initialize rate limiting system.
        """
        persistence_path = None
        if self.storage_dir:
            persistence_path = str(self.storage_dir / "rate_limiter_state.json")

        self.rate_limiter = KrakenRateLimiter2025(
            account_tier="intermediate",
            api_key=self.api_key,
            enable_queue=True,
            enable_circuit_breaker=False,  # We'll use our own circuit breaker
            persistence_path=persistence_path
        )

        logger.info("Rate limiting system initialized")

    def _init_circuit_breaker(self) -> None:
        """
        Initialize circuit breaker system.
        """
        # Configure circuit breaker
        cb_config = CircuitBreakerConfig(
            failure_threshold=5,           # Open after 5 failures
            recovery_timeout=30.0,         # Wait 30s before recovery attempt
            success_threshold=3,           # Close after 3 successes
            max_recovery_attempts=5,       # Max 5 recovery attempts
            base_backoff=1.0,             # Start with 1s backoff
            max_backoff=300.0,            # Max 5 minutes backoff
            backoff_multiplier=2.0,       # Exponential backoff
            timeout=30.0,                 # 30s operation timeout
            monitoring_window=300.0,      # 5 minute failure analysis window
            health_check_interval=10.0,   # Health check every 10s
            persistent_state=True         # Persist state across restarts
        )

        storage_dir = str(self.storage_dir / "circuit_breaker") if self.storage_dir else None

        self.cb_manager = CircuitBreakerManager(
            default_config=cb_config,
            storage_dir=storage_dir
        )

        # Create circuit breakers for different API categories
        self.api_breaker = self.cb_manager.create_breaker("kraken_api")
        self.private_breaker = self.cb_manager.create_breaker("kraken_private")
        self.public_breaker = self.cb_manager.create_breaker("kraken_public")

        logger.info("Circuit breaker system initialized")

    def _init_monitoring(self) -> None:
        """
        Initialize health monitoring and failure detection.
        """
        if not self.enable_monitoring:
            self.health_monitor = None
            self.failure_detector = None
            return

        # Health monitoring
        storage_path = None
        if self.storage_dir:
            storage_path = str(self.storage_dir / "health_monitor_state.json")

        self.health_monitor = HealthMonitor(
            check_interval=30.0,
            alert_threshold=3,
            recovery_threshold=2,
            storage_path=storage_path
        )

        # Register health checks for Kraken endpoints
        self.health_monitor.register_http_health_check(
            name="kraken_public",
            url="https://api.kraken.com/0/public/SystemStatus",
            method="GET",
            expected_status=200,
            timeout=10.0,
            check_interval=60.0
        )

        # Failure detection
        detector_storage = None
        if self.storage_dir:
            detector_storage = str(self.storage_dir / "failure_detector_state.json")

        self.failure_detector = FailureDetector(
            analysis_window=300.0,  # 5 minutes
            max_events_per_service=1000,
            storage_path=detector_storage
        )

        logger.info("Health monitoring and failure detection initialized")

    async def start(self) -> None:
        """
        Start the integrated API client.
        """
        if self._running:
            return

        # Start rate limiter
        await self.rate_limiter.start()

        # Start circuit breaker monitoring
        await self.cb_manager.start_monitoring(interval=30.0)

        # Start health monitoring
        if self.health_monitor:
            await self.health_monitor.start()

        # Create HTTP session for API calls
        import aiohttp
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30.0)
        )

        self._running = True
        logger.info("Integrated API client started")

    async def stop(self) -> None:
        """
        Stop the integrated API client.
        """
        if not self._running:
            return

        self._running = False

        # Close HTTP session
        if self._session:
            await self._session.close()

        # Stop monitoring systems
        if self.health_monitor:
            await self.health_monitor.stop()

        await self.cb_manager.stop_monitoring()
        await self.rate_limiter.stop()

        # Cleanup
        self.auth.cleanup()
        self.cb_manager.cleanup()

        if self.failure_detector:
            self.failure_detector.cleanup()

        logger.info("Integrated API client stopped")

    async def make_api_call(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        is_private: bool = False,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Make an API call with full protection.
        
        Args:
            endpoint: API endpoint path
            params: Request parameters
            is_private: Whether this is a private API call
            priority: Request priority for rate limiting
            timeout: Request timeout
            
        Returns:
            API response data
            
        Raises:
            BreakerOpenError: If circuit breaker is open
            KrakenAuthError: If authentication fails
            Exception: Other API errors
        """
        if not self._running:
            raise RuntimeError("API client not started")

        # Choose appropriate circuit breaker
        if is_private:
            breaker = self.private_breaker
            service_name = "kraken_private"
        else:
            breaker = self.public_breaker
            service_name = "kraken_public"

        # Execute with circuit breaker protection
        try:
            result = await breaker.execute_async(
                self._protected_api_call,
                endpoint=endpoint,
                params=params,
                is_private=is_private,
                priority=priority,
                timeout=timeout
            )

            return result

        except (BreakerOpenError, BreakerTimeoutError) as e:
            logger.warning(f"Circuit breaker blocked API call to {endpoint}: {e}")
            raise

        except Exception as e:
            # Record failure for analysis
            if self.failure_detector:
                await self._record_api_failure(service_name, endpoint, e)

            raise

    async def _protected_api_call(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        is_private: bool = False,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Internal API call with rate limiting and authentication.
        
        Args:
            endpoint: API endpoint path
            params: Request parameters
            is_private: Whether this is a private API call
            priority: Request priority
            timeout: Request timeout
            
        Returns:
            API response data
        """
        start_time = time.time()

        try:
            # Apply rate limiting
            if not await self.rate_limiter.wait_for_rate_limit(
                endpoint=endpoint,
                priority=priority,
                timeout_seconds=timeout or 30.0
            ):
                raise Exception("Rate limit timeout")

            # Prepare request
            url = f"https://api.kraken.com{endpoint}"
            headers = {"User-Agent": "TradingBot/1.0"}

            # Add authentication for private endpoints
            if is_private:
                auth_headers = await self.auth.get_auth_headers_async(
                    endpoint, params
                )
                headers.update(auth_headers)

            # Prepare request data
            if params:
                if is_private:
                    # Add nonce for private requests
                    nonce = self.auth.nonce_manager.get_next_nonce()
                    params = {"nonce": nonce, **params}

                # URL-encode parameters
                import urllib.parse
                data = urllib.parse.urlencode(params)
            else:
                data = None

            # Make HTTP request
            async with self._session.request(
                method="POST" if is_private else "GET",
                url=url,
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=timeout or 30.0)
            ) as response:
                response_data = await response.json()

                # Check for API errors
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response_data}")

                if "error" in response_data and response_data["error"]:
                    error_messages = response_data["error"]
                    raise Exception(f"API Error: {', '.join(error_messages)}")

                # Record successful call
                response_time = (time.time() - start_time) * 1000

                if self.health_monitor:
                    await self._record_api_success(
                        "kraken_private" if is_private else "kraken_public",
                        endpoint,
                        response_time
                    )

                return response_data.get("result", {})

        except Exception as e:
            # Record failure
            response_time = (time.time() - start_time) * 1000

            if self.failure_detector:
                await self._record_api_failure(
                    "kraken_private" if is_private else "kraken_public",
                    endpoint,
                    e,
                    response_time
                )

            # Handle authentication errors
            if "nonce" in str(e).lower() or "invalid" in str(e).lower():
                # Attempt auth recovery
                try:
                    recovery_headers = self.auth.handle_auth_error(
                        str(e), endpoint, params
                    )
                    logger.info(f"Authentication error recovery attempted for {endpoint}")
                except Exception as auth_error:
                    logger.error(f"Authentication recovery failed: {auth_error}")

            raise

    async def _record_api_success(
        self,
        service_name: str,
        endpoint: str,
        response_time_ms: float
    ) -> None:
        """
        Record successful API call for monitoring.
        
        Args:
            service_name: Service name
            endpoint: API endpoint
            response_time_ms: Response time in milliseconds
        """
        if not self.health_monitor:
            return

        # Update health metrics
        try:
            service_health = self.health_monitor.get_service_health(service_name)
            if service_health:
                service_health.metrics.response_time_ms = response_time_ms
                service_health.metrics.last_updated = time.time()

        except Exception as e:
            logger.debug(f"Error recording API success: {e}")

    async def _record_api_failure(
        self,
        service_name: str,
        endpoint: str,
        error: Exception,
        response_time_ms: Optional[float] = None
    ) -> None:
        """
        Record API failure for analysis.
        
        Args:
            service_name: Service name
            endpoint: API endpoint
            error: Exception that occurred
            response_time_ms: Response time in milliseconds
        """
        if not self.failure_detector:
            return

        try:
            # Extract error details
            error_message = str(error)
            exception_type = type(error).__name__

            # Extract HTTP status code if available
            http_status_code = None
            if "HTTP" in error_message:
                import re
                match = re.search(r"HTTP (\d+)", error_message)
                if match:
                    http_status_code = int(match.group(1))

            # Record failure event
            failure_event = self.failure_detector.record_failure(
                service_name=service_name,
                error_message=error_message,
                exception_type=exception_type,
                http_status_code=http_status_code,
                response_time_ms=response_time_ms,
                context={
                    "endpoint": endpoint,
                    "timestamp": time.time()
                },
                metadata={
                    "api_key_hash": self.api_key[:8] + "..."
                }
            )

            # Analyze if circuit should open
            should_open, reason, analysis = self.failure_detector.should_open_circuit(
                service_name=service_name,
                failure_threshold=5
            )

            if should_open:
                logger.warning(
                    f"Failure analysis suggests opening circuit for {service_name}: {reason}"
                )

                # Force circuit breaker open based on failure analysis
                if service_name == "kraken_private":
                    self.private_breaker.force_open()
                elif service_name == "kraken_public":
                    self.public_breaker.force_open()

        except Exception as e:
            logger.debug(f"Error recording API failure: {e}")

    async def get_account_balance(self) -> Dict[str, Any]:
        """
        Example: Get account balance with full protection.
        
        Returns:
            Account balance information
        """
        return await self.make_api_call(
            endpoint="/0/private/Balance",
            is_private=True,
            priority=RequestPriority.NORMAL
        )

    async def get_ticker_info(self, pair: str) -> Dict[str, Any]:
        """
        Example: Get ticker information with full protection.
        
        Args:
            pair: Trading pair (e.g., "XBTUSD")
            
        Returns:
            Ticker information
        """
        return await self.make_api_call(
            endpoint="/0/public/Ticker",
            params={"pair": pair},
            is_private=False,
            priority=RequestPriority.LOW
        )

    async def place_order(
        self,
        pair: str,
        type_: str,
        ordertype: str,
        volume: str,
        price: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Example: Place order with full protection.
        
        Args:
            pair: Trading pair
            type_: Order type (buy/sell)
            ordertype: Order type (market/limit)
            volume: Order volume
            price: Order price (for limit orders)
            **kwargs: Additional order parameters
            
        Returns:
            Order placement result
        """
        params = {
            "pair": pair,
            "type": type_,
            "ordertype": ordertype,
            "volume": volume
        }

        if price:
            params["price"] = price

        params.update(kwargs)

        return await self.make_api_call(
            endpoint="/0/private/AddOrder",
            params=params,
            is_private=True,
            priority=RequestPriority.HIGH,  # High priority for trading
            timeout=45.0  # Longer timeout for order placement
        )

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            System status information
        """
        status = {
            "timestamp": time.time(),
            "running": self._running,
            "authentication": self.auth.get_comprehensive_status(),
            "rate_limiting": self.rate_limiter.get_status(),
            "circuit_breakers": self.cb_manager.get_aggregate_status()
        }

        if self.health_monitor:
            status["health_monitoring"] = self.health_monitor.get_global_health_status()

        if self.failure_detector:
            status["failure_detection"] = self.failure_detector.get_failure_statistics()

        return status

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


async def main():
    """
    Example usage of the integrated API client.
    """
    import os

    # Get API credentials from environment
    api_key = os.getenv("KRAKEN_API_KEY")
    private_key = os.getenv("KRAKEN_PRIVATE_KEY")

    if not api_key or not private_key:
        logger.error("Please set KRAKEN_API_KEY and KRAKEN_PRIVATE_KEY environment variables")
        return

    # Create integrated client
    async with IntegratedKrakenAPIClient(
        api_key=api_key,
        private_key=private_key,
        storage_dir="./circuit_breaker_data",
        enable_monitoring=True
    ) as client:

        try:
            # Test public API call
            logger.info("Testing public API call...")
            ticker = await client.get_ticker_info("XBTUSD")
            logger.info(f"BTC/USD ticker: {ticker}")

            # Test private API call
            logger.info("Testing private API call...")
            balance = await client.get_account_balance()
            logger.info(f"Account balance keys: {list(balance.keys())}")

            # Get system status
            logger.info("Getting system status...")
            status = client.get_system_status()

            # Print circuit breaker status
            cb_status = status["circuit_breakers"]
            logger.info(
                f"Circuit breaker status: {cb_status['total_breakers']} breakers, "
                f"health: {cb_status['health_summary']}"
            )

            # Print health monitoring status
            if "health_monitoring" in status:
                health_status = status["health_monitoring"]
                logger.info(
                    f"Health monitoring: {health_status['overall_status']}, "
                    f"{health_status['healthy_services']}/{health_status['total_services']} services healthy"
                )

        except BreakerOpenError as e:
            logger.error(f"Circuit breaker is open: {e}")

        except Exception as e:
            logger.error(f"API call failed: {e}")

        # Wait a bit to see monitoring in action
        logger.info("Waiting for monitoring data...")
        await asyncio.sleep(10)

        # Final status check
        final_status = client.get_system_status()
        logger.info(f"Final system status: {final_status['circuit_breakers']['health_summary']}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    asyncio.run(main())
