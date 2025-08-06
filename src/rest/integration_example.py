"""
REST API Integration Example
===========================

Comprehensive example showing how to integrate all REST API components
with the existing WebSocket V2 system for optimal trading performance.

This example demonstrates:
- Strategic REST client initialization and usage
- Data validation between REST and WebSocket sources
- Fallback management during WebSocket failures
- Data source coordination for intelligent routing
- Performance monitoring and optimization

Usage:
    python -m src.rest.integration_example
"""

import asyncio
import logging
import os
from typing import Optional

from ..data.data_source_coordinator import DataSource, DataSourceCoordinator
from ..exchange.websocket_manager_v2 import WebSocketManagerV2
from .rest_data_validator import RestDataValidator
from .rest_fallback_manager import RestFallbackManager, ServiceLevel
from .strategic_rest_client import StrategicRestClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RestIntegrationExample:
    """
    Complete example of REST API integration with WebSocket V2 system.
    """

    def __init__(self):
        """Initialize the integration example."""
        # Load configuration
        self.api_key = os.getenv('KRAKEN_API_KEY')
        self.private_key = os.getenv('KRAKEN_PRIVATE_KEY')

        if not self.api_key or not self.private_key:
            raise ValueError("Please set KRAKEN_API_KEY and KRAKEN_PRIVATE_KEY environment variables")

        # Initialize components
        self.strategic_client: Optional[StrategicRestClient] = None
        self.websocket_manager: Optional[WebSocketManagerV2] = None
        self.data_validator: Optional[RestDataValidator] = None
        self.fallback_manager: Optional[RestFallbackManager] = None
        self.data_coordinator: Optional[DataSourceCoordinator] = None

        # Demo configuration
        self.demo_pairs = ['SHIBUSDT', 'ADAUSDT', 'DOGEUSDT']
        self.running = False

        logger.info("[INTEGRATION_EXAMPLE] Initialized REST integration example")

    async def initialize_all_components(self) -> None:
        """Initialize all components in the correct order."""
        logger.info("[INTEGRATION_EXAMPLE] Initializing components...")

        # 1. Initialize Strategic REST Client
        self.strategic_client = StrategicRestClient(
            api_key=self.api_key,
            private_key=self.private_key,
            max_batch_size=3,
            batch_timeout=1.5,
            emergency_only=False
        )
        await self.strategic_client.initialize()
        logger.info("✓ Strategic REST client initialized")

        # 2. Initialize WebSocket Manager (simplified for example)
        try:
            self.websocket_manager = WebSocketManagerV2(
                api_key=self.api_key,
                private_key=self.private_key
            )
            await self.websocket_manager.initialize()
            logger.info("✓ WebSocket manager initialized")
        except Exception as e:
            logger.warning(f"WebSocket manager initialization failed: {e}")
            self.websocket_manager = None

        # 3. Initialize Data Validator
        self.data_validator = RestDataValidator(
            strategic_client=self.strategic_client,
            websocket_manager=self.websocket_manager,
            validation_interval=30.0,
            tolerance_threshold=0.001
        )
        await self.data_validator.initialize()

        # Add critical pairs for validation
        for pair in self.demo_pairs:
            self.data_validator.add_critical_pair(pair)

        logger.info("✓ Data validator initialized")

        # 4. Initialize Fallback Manager
        self.fallback_manager = RestFallbackManager(
            strategic_client=self.strategic_client,
            websocket_manager=self.websocket_manager,
            health_check_interval=20.0,
            recovery_timeout=120.0
        )
        await self.fallback_manager.initialize()

        # Add service level callback
        self.fallback_manager.add_service_level_callback(self._on_service_level_change)
        logger.info("✓ Fallback manager initialized")

        # 5. Initialize Data Source Coordinator
        self.data_coordinator = DataSourceCoordinator(
            websocket_manager=self.websocket_manager,
            strategic_rest_client=self.strategic_client,
            fallback_manager=self.fallback_manager,
            cache_ttl=3.0,
            performance_window=50
        )
        await self.data_coordinator.initialize()
        logger.info("✓ Data source coordinator initialized")

        logger.info("[INTEGRATION_EXAMPLE] All components initialized successfully!")

    async def run_comprehensive_demo(self) -> None:
        """Run a comprehensive demonstration of all features."""
        logger.info("[INTEGRATION_EXAMPLE] Starting comprehensive demo...")

        self.running = True

        try:
            # Start continuous validation
            await self.data_validator.start_continuous_validation()

            # Demo 1: Basic data retrieval with automatic source selection
            await self._demo_automatic_data_retrieval()

            # Demo 2: Performance comparison between sources
            await self._demo_performance_comparison()

            # Demo 3: Data validation in action
            await self._demo_data_validation()

            # Demo 4: Fallback scenarios
            await self._demo_fallback_scenarios()

            # Demo 5: Batch operations
            await self._demo_batch_operations()

            # Demo 6: Emergency operations
            await self._demo_emergency_operations()

            # Demo 7: Performance monitoring and optimization
            await self._demo_performance_monitoring()

            # Let the system run for a bit to show continuous operation
            logger.info("[INTEGRATION_EXAMPLE] Running continuous operations for 60 seconds...")
            await asyncio.sleep(60)

        except KeyboardInterrupt:
            logger.info("[INTEGRATION_EXAMPLE] Demo interrupted by user")
        except Exception as e:
            logger.error(f"[INTEGRATION_EXAMPLE] Demo error: {e}")
        finally:
            await self._cleanup()

    async def _demo_automatic_data_retrieval(self) -> None:
        """Demonstrate automatic data retrieval with source selection."""
        logger.info("\n=== DEMO 1: Automatic Data Retrieval ===")

        try:
            # Get balance with automatic source selection
            logger.info("Getting balance data with automatic source selection...")
            balance = await self.data_coordinator.get_balance()
            logger.info(f"Balance retrieved: {len(balance.get('result', {}))} assets")

            # Get ticker data for demo pairs
            for pair in self.demo_pairs[:2]:  # Just first 2 pairs
                logger.info(f"Getting ticker data for {pair}...")
                ticker = await self.data_coordinator.get_ticker_data(pair)
                if 'result' in ticker and ticker['result']:
                    ticker_data = list(ticker['result'].values())[0]
                    price = ticker_data.get('c', ['N/A'])[0] if 'c' in ticker_data else 'N/A'
                    logger.info(f"{pair} current price: {price}")

                await asyncio.sleep(1)  # Avoid overwhelming

            # Get system status
            logger.info("Getting system status...")
            status = await self.data_coordinator.get_system_status()
            system_status = status.get('result', {}).get('status', 'unknown')
            logger.info(f"Kraken system status: {system_status}")

        except Exception as e:
            logger.error(f"Automatic data retrieval demo failed: {e}")

    async def _demo_performance_comparison(self) -> None:
        """Demonstrate performance comparison between sources."""
        logger.info("\n=== DEMO 2: Performance Comparison ===")

        try:
            # Test WebSocket source if available
            if self.websocket_manager:
                logger.info("Testing WebSocket performance...")
                start_time = asyncio.get_event_loop().time()
                try:
                    await self.data_coordinator.get_balance(source=DataSource.WEBSOCKET)
                    ws_time = asyncio.get_event_loop().time() - start_time
                    logger.info(f"WebSocket balance retrieval: {ws_time:.3f}s")
                except Exception as e:
                    logger.warning(f"WebSocket test failed: {e}")

            # Test REST source
            logger.info("Testing REST performance...")
            start_time = asyncio.get_event_loop().time()
            try:
                await self.data_coordinator.get_balance(source=DataSource.REST)
                rest_time = asyncio.get_event_loop().time() - start_time
                logger.info(f"REST balance retrieval: {rest_time:.3f}s")
            except Exception as e:
                logger.warning(f"REST test failed: {e}")

            # Show performance stats
            perf_stats = self.data_coordinator.get_performance_stats()
            logger.info("Current performance stats:")
            for source, stats in perf_stats['source_performance'].items():
                logger.info(
                    f"  {source}: {stats['success_rate']:.1%} success rate, "
                    f"{stats['average_response_time']:.3f}s avg response time"
                )

        except Exception as e:
            logger.error(f"Performance comparison demo failed: {e}")

    async def _demo_data_validation(self) -> None:
        """Demonstrate data validation between sources."""
        logger.info("\n=== DEMO 3: Data Validation ===")

        try:
            # Validate balance data
            logger.info("Validating balance data between sources...")
            balance_validation = await self.data_validator.validate_balance_data()

            logger.info("Balance validation result:")
            logger.info(f"  Valid: {balance_validation.is_valid}")
            logger.info(f"  Confidence: {balance_validation.confidence:.3f}")
            if balance_validation.discrepancies:
                logger.info(f"  Discrepancies: {balance_validation.discrepancies}")

            # Validate price data for a demo pair
            if self.demo_pairs:
                pair = self.demo_pairs[0]
                logger.info(f"Validating price data for {pair}...")
                price_validation = await self.data_validator.validate_price_data(pair)

                logger.info(f"Price validation result for {pair}:")
                logger.info(f"  Valid: {price_validation.is_valid}")
                logger.info(f"  Confidence: {price_validation.confidence:.3f}")
                if price_validation.discrepancies:
                    logger.info(f"  Discrepancies: {price_validation.discrepancies}")

            # Show validation stats
            validation_stats = self.data_validator.get_validation_stats()
            stats = validation_stats['stats']
            logger.info("Validation statistics:")
            logger.info(f"  Total validations: {stats['total_validations']}")
            logger.info(f"  Success rate: {stats['successful_validations']}/{stats['total_validations']}")
            logger.info(f"  Average confidence: {stats['average_confidence']:.3f}")

        except Exception as e:
            logger.error(f"Data validation demo failed: {e}")

    async def _demo_fallback_scenarios(self) -> None:
        """Demonstrate fallback scenarios."""
        logger.info("\n=== DEMO 4: Fallback Scenarios ===")

        try:
            # Show current service status
            service_status = self.fallback_manager.get_service_status()
            logger.info(f"Current service level: {service_status['service_level']}")
            logger.info(f"WebSocket healthy: {service_status['websocket_healthy']}")
            logger.info(f"REST healthy: {service_status['rest_healthy']}")

            # Simulate WebSocket failure (if we were to do it)
            logger.info("Note: In a real scenario, WebSocket failure would trigger automatic fallback")

            # Test emergency operations
            logger.info("Testing emergency balance check...")
            emergency_balance = await self.fallback_manager.emergency_get_balance()
            logger.info(f"Emergency balance check successful: {len(emergency_balance.get('result', {}))} assets")

            # Test emergency open orders
            logger.info("Testing emergency open orders check...")
            emergency_orders = await self.fallback_manager.emergency_get_open_orders()
            open_orders = emergency_orders.get('result', {}).get('open', {})
            logger.info(f"Emergency open orders check: {len(open_orders)} orders")

            # Show fallback stats
            fallback_stats = self.fallback_manager.get_fallback_stats()
            logger.info("Fallback statistics:")
            logger.info(f"  Total fallbacks: {fallback_stats['total_fallbacks']}")
            logger.info(f"  Emergency operations: {fallback_stats['emergency_operations']}")
            logger.info(f"  Recovery success rate: {fallback_stats['recovery_success_rate']:.1%}")

        except Exception as e:
            logger.error(f"Fallback scenarios demo failed: {e}")

    async def _demo_batch_operations(self) -> None:
        """Demonstrate batch operations for efficiency."""
        logger.info("\n=== DEMO 5: Batch Operations ===")

        try:
            # Add multiple ticker requests to batch
            logger.info("Adding ticker requests to batch...")
            for pair in self.demo_pairs:
                await self.strategic_client.add_to_batch(
                    'Ticker',
                    {'pair': pair},
                    priority=2
                )

            # Add historical data requests to batch
            logger.info("Adding historical data requests to batch...")
            for pair in self.demo_pairs[:2]:  # Just first 2 pairs
                await self.strategic_client.add_to_batch(
                    'OHLC',
                    {'pair': pair, 'interval': 5},
                    priority=1
                )

            # Trigger batch processing
            logger.info("Processing batch requests...")
            await asyncio.sleep(3)  # Wait for batch timeout

            # Show strategic client stats
            strategic_stats = self.strategic_client.get_strategic_stats()
            stats = strategic_stats['stats']
            logger.info("Strategic client statistics:")
            logger.info(f"  Total requests: {stats['total_requests']}")
            logger.info(f"  Batched requests: {stats['batched_requests']}")
            logger.info(f"  Emergency requests: {stats['emergency_requests']}")
            logger.info(f"  Nonce conflicts: {stats['nonce_conflicts']}")

        except Exception as e:
            logger.error(f"Batch operations demo failed: {e}")

    async def _demo_emergency_operations(self) -> None:
        """Demonstrate emergency operations."""
        logger.info("\n=== DEMO 6: Emergency Operations ===")

        try:
            # Test system status check
            logger.info("Emergency system status check...")
            system_status = await self.strategic_client.emergency_system_status()
            status = system_status.get('result', {}).get('status', 'unknown')
            logger.info(f"System status: {status}")

            # Test balance check
            logger.info("Emergency balance check...")
            balance = await self.strategic_client.emergency_balance_check()
            assets = balance.get('result', {})
            usdt_balance = assets.get('USDT', '0')
            logger.info(f"USDT balance: {usdt_balance}")

            # Show circuit breaker status
            cb_status = self.strategic_client.circuit_breaker.get_status()
            logger.info("Circuit breaker status:")
            logger.info(f"  State: {cb_status['state']}")
            logger.info(f"  Can execute: {cb_status['can_execute']}")
            logger.info(f"  Failure count: {cb_status['failure_count']}")

        except Exception as e:
            logger.error(f"Emergency operations demo failed: {e}")

    async def _demo_performance_monitoring(self) -> None:
        """Demonstrate performance monitoring and optimization."""
        logger.info("\n=== DEMO 7: Performance Monitoring ===")

        try:
            # Get comprehensive performance stats
            coordinator_stats = self.data_coordinator.get_performance_stats()

            logger.info("Data Coordinator Performance:")
            coord_stats = coordinator_stats['coordinator_stats']
            logger.info(f"  Total requests: {coord_stats['total_requests']}")
            logger.info(f"  WebSocket requests: {coord_stats['websocket_requests']}")
            logger.info(f"  REST requests: {coord_stats['rest_requests']}")
            logger.info(f"  Cache hit rate: {coord_stats['cache_hit_rate']:.1%}")
            logger.info(f"  Failover events: {coord_stats['failover_events']}")

            # Show source selection reasons
            selection_reasons = coordinator_stats['source_selection_reasons']
            logger.info("Source Selection Reasons:")
            for reason, count in selection_reasons.items():
                if count > 0:
                    logger.info(f"  {reason}: {count}")

            # Get optimization recommendations
            recommendations = self.data_coordinator.get_optimization_recommendations()
            if recommendations:
                logger.info("Optimization Recommendations:")
                for i, recommendation in enumerate(recommendations, 1):
                    logger.info(f"  {i}. {recommendation}")
            else:
                logger.info("No optimization recommendations at this time")

            # Show health checks
            logger.info("\nHealth Check Results:")

            # Strategic client health
            strategic_health = await self.strategic_client.health_check()
            logger.info(f"Strategic Client: {strategic_health['status']}")

            # Data validator health
            validator_health = await self.data_validator.health_check()
            logger.info(f"Data Validator: {validator_health['status']}")

            # Fallback manager health
            fallback_health = await self.fallback_manager.health_check()
            logger.info(f"Fallback Manager: {fallback_health['status']}")

            # Data coordinator health
            coordinator_health = await self.data_coordinator.health_check()
            logger.info(f"Data Coordinator: {coordinator_health['status']}")

        except Exception as e:
            logger.error(f"Performance monitoring demo failed: {e}")

    async def _on_service_level_change(self, old_level: ServiceLevel, new_level: ServiceLevel) -> None:
        """Handle service level changes."""
        logger.warning(
            f"[SERVICE_LEVEL_CHANGE] {old_level.value} → {new_level.value}"
        )

        if new_level == ServiceLevel.SERVICE_OUTAGE:
            logger.critical("⚠️  SERVICE OUTAGE DETECTED - Both WebSocket and REST failed!")
        elif new_level == ServiceLevel.EMERGENCY_ONLY:
            logger.warning("⚠️  EMERGENCY ONLY mode - Limited operations available")
        elif new_level == ServiceLevel.DEGRADED_SERVICE:
            logger.warning("⚠️  DEGRADED SERVICE - Using fallback operations")
        elif new_level == ServiceLevel.FULL_SERVICE:
            logger.info("✅ FULL SERVICE restored - All operations available")

    async def _cleanup(self) -> None:
        """Clean up all components."""
        logger.info("[INTEGRATION_EXAMPLE] Cleaning up components...")

        self.running = False

        # Stop data validator
        if self.data_validator:
            await self.data_validator.stop_continuous_validation()

        # Shutdown fallback manager
        if self.fallback_manager:
            await self.fallback_manager.shutdown()

        # Shutdown strategic client
        if self.strategic_client:
            await self.strategic_client.shutdown()

        # Close WebSocket manager
        if self.websocket_manager:
            try:
                await self.websocket_manager.close()
            except Exception as e:
                logger.warning(f"WebSocket cleanup error: {e}")

        logger.info("[INTEGRATION_EXAMPLE] Cleanup complete")


async def main():
    """Run the integration example."""
    example = RestIntegrationExample()

    try:
        await example.initialize_all_components()
        await example.run_comprehensive_demo()
    except Exception as e:
        logger.error(f"Integration example failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
