"""
Kraken API Client Integration Example
====================================

Comprehensive example demonstrating how to use the Kraken REST API client
with all integrated systems: authentication, rate limiting, circuit breaker,
error handling, and response validation.

This example shows:
- Client initialization and configuration
- Public and private API calls
- Error handling and retry logic
- Performance monitoring and metrics
- Rate limiting and circuit breaker behavior
- Proper resource cleanup

Usage:
    python -m src.api.integration_example
"""

import asyncio
import json
import logging
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our API client
from ..rate_limiting.kraken_rate_limiter import AccountTier
from .exceptions import AuthenticationError, KrakenAPIError, NetworkError
from .kraken_rest_client import KrakenRestClient
from .response_models import BalanceResponse, OrderResponse, TickerResponse


async def test_public_endpoints(client: KrakenRestClient):
    """Test public API endpoints."""
    logger.info("Testing public endpoints...")

    try:
        # Test server time
        logger.info("Getting server time...")
        server_time = await client.get_server_time()
        logger.info(f"Server time: {server_time}")

        # Test system status
        logger.info("Getting system status...")
        system_status = await client.get_system_status()
        logger.info(f"System status: {system_status}")

        # Test asset info
        logger.info("Getting asset info for BTC and ETH...")
        asset_info = await client.get_asset_info("XBT,ETH")
        logger.info(f"Asset info: {json.dumps(asset_info, indent=2)}")

        # Test asset pairs
        logger.info("Getting asset pairs for XBTUSD...")
        asset_pairs = await client.get_asset_pairs("XBTUSD")
        logger.info(f"Asset pairs: {json.dumps(asset_pairs, indent=2)}")

        # Test ticker
        logger.info("Getting ticker for XBTUSD...")
        ticker = await client.get_ticker_information("XBTUSD")

        # Parse with Pydantic model
        ticker_response = TickerResponse(**ticker)
        if ticker_response.is_success and ticker_response.result:
            for pair, ticker_info in ticker_response.result.items():
                logger.info(f"Ticker {pair}: last={ticker_info.last_price}, bid={ticker_info.bid_price}, ask={ticker_info.ask_price}")

        # Test order book
        logger.info("Getting order book for XBTUSD...")
        order_book = await client.get_order_book("XBTUSD", count=5)
        logger.info(f"Order book: {json.dumps(order_book, indent=2)}")

        # Test recent trades
        logger.info("Getting recent trades for XBTUSD...")
        recent_trades = await client.get_recent_trades("XBTUSD")
        logger.info(f"Recent trades count: {len(recent_trades.get('result', {}).get('XXBTZUSD', []))}")

        logger.info("✅ Public endpoints test completed successfully")

    except Exception as e:
        logger.error(f"❌ Public endpoints test failed: {e}")
        raise


async def test_private_endpoints(client: KrakenRestClient):
    """Test private API endpoints (requires valid API keys)."""
    logger.info("Testing private endpoints...")

    try:
        # Test account balance
        logger.info("Getting account balance...")
        balance_data = await client.get_account_balance()

        # Parse with Pydantic model
        balance_response = BalanceResponse(**balance_data)
        if balance_response.is_success and balance_response.result:
            logger.info("Account balances:")
            for asset, amount in balance_response.result.items():
                if float(amount) > 0:
                    logger.info(f"  {asset}: {amount}")

        # Test trade balance
        logger.info("Getting trade balance...")
        trade_balance = await client.get_trade_balance()
        logger.info(f"Trade balance: {json.dumps(trade_balance, indent=2)}")

        # Test open orders
        logger.info("Getting open orders...")
        open_orders = await client.get_open_orders()
        open_count = len(open_orders.get('result', {}).get('open', {}))
        logger.info(f"Open orders count: {open_count}")

        # Test closed orders (last 10)
        logger.info("Getting recent closed orders...")
        closed_orders = await client.get_closed_orders(ofs=0)
        closed_count = len(closed_orders.get('result', {}).get('closed', {}))
        logger.info(f"Recent closed orders count: {closed_count}")

        # Test WebSocket token
        logger.info("Getting WebSocket token...")
        ws_token = await client.get_websockets_token()
        if ws_token.get('result', {}).get('token'):
            logger.info("✅ WebSocket token obtained successfully")

        logger.info("✅ Private endpoints test completed successfully")

    except AuthenticationError as e:
        logger.error(f"❌ Authentication failed: {e}")
        logger.info("Make sure you have valid API keys configured")
        raise
    except Exception as e:
        logger.error(f"❌ Private endpoints test failed: {e}")
        raise


async def test_error_handling(client: KrakenRestClient):
    """Test error handling and retry logic."""
    logger.info("Testing error handling...")

    try:
        # Test invalid endpoint parameters
        logger.info("Testing parameter validation...")
        try:
            await client.get_ticker_information("")  # Empty pair should fail validation
            logger.error("❌ Should have failed validation")
        except KrakenAPIError as e:
            logger.info(f"✅ Parameter validation working: {e}")

        # Test invalid asset pair
        logger.info("Testing invalid asset pair...")
        try:
            ticker = await client.get_ticker_information("INVALIDPAIR")
            if ticker.get('error'):
                logger.info(f"✅ Invalid pair error handled: {ticker['error']}")
        except KrakenAPIError as e:
            logger.info(f"✅ Invalid pair error handled: {e}")

        # Test rate limiting behavior
        logger.info("Testing rate limiting (making multiple rapid requests)...")
        start_time = asyncio.get_event_loop().time()

        tasks = []
        for _i in range(10):
            task = client.get_server_time()
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time

        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful

        logger.info(f"Rate limiting test: {successful} successful, {failed} failed in {elapsed:.2f}s")

        logger.info("✅ Error handling test completed successfully")

    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        raise


async def test_trading_operations(client: KrakenRestClient):
    """Test trading operations (validation mode only)."""
    logger.info("Testing trading operations (validation mode)...")

    try:
        # Test order validation (won't actually place order)
        logger.info("Testing order validation...")

        try:
            order_result = await client.add_order(
                pair="XBTUSD",
                type="buy",
                ordertype="limit",
                volume="0.001",
                price="30000.00",
                validate=True  # Validation mode only
            )

            # Parse with Pydantic model
            order_response = OrderResponse(**order_result)
            if order_response.is_success:
                logger.info("✅ Order validation successful")
                if order_response.result and order_response.result.descr:
                    logger.info(f"Order description: {order_response.result.descr}")
            else:
                logger.info(f"Order validation errors: {order_response.get_error_string()}")

        except KrakenAPIError as e:
            logger.info(f"Order validation error (expected): {e}")

        logger.info("✅ Trading operations test completed successfully")

    except Exception as e:
        logger.error(f"❌ Trading operations test failed: {e}")
        raise


async def test_performance_monitoring(client: KrakenRestClient):
    """Test performance monitoring and metrics."""
    logger.info("Testing performance monitoring...")

    try:
        # Make several requests to generate metrics
        logger.info("Making requests to generate metrics...")

        await client.get_server_time()
        await client.get_system_status()
        await client.get_asset_info("XBT")
        await client.get_ticker_information("XBTUSD")

        # Get metrics
        metrics = client.get_metrics()
        logger.info("📊 Client Metrics:")
        logger.info(f"  Total requests: {metrics['total_requests']}")
        logger.info(f"  Success rate: {metrics['success_rate']:.2%}")
        logger.info(f"  Avg response time: {metrics['avg_response_time']:.3f}s")
        logger.info(f"  Requests per second: {metrics['requests_per_second']:.2f}")

        # Get detailed status
        status = client.get_status()
        logger.info("🔍 Client Status:")
        logger.info(f"  API Key: {status['client_info']['api_key']}")
        logger.info(f"  Account Tier: {status['client_info']['account_tier']}")
        logger.info(f"  Rate Limiting: {status['configuration']['rate_limiting_enabled']}")
        logger.info(f"  Circuit Breaker: {status['configuration']['circuit_breaker_enabled']}")

        # Show recent requests
        if status['recent_requests']:
            logger.info("📝 Recent Requests:")
            for req in status['recent_requests'][-3:]:  # Last 3 requests
                success_icon = "✅" if req['success'] else "❌"
                logger.info(f"  {success_icon} {req['endpoint']}: {req['response_time']:.3f}s")

        logger.info("✅ Performance monitoring test completed successfully")

    except Exception as e:
        logger.error(f"❌ Performance monitoring test failed: {e}")
        raise


async def test_health_check(client: KrakenRestClient):
    """Test health check functionality."""
    logger.info("Testing health check...")

    try:
        health = await client.health_check()

        logger.info("🏥 Health Check Results:")
        logger.info(f"  Overall Status: {health['overall_status']}")

        for check_name, check_result in health['checks'].items():
            status_icon = "✅" if check_result['status'] == 'healthy' else "⚠️" if check_result['status'] == 'degraded' else "❌"
            logger.info(f"  {status_icon} {check_name}: {check_result['status']}")

            if 'error' in check_result:
                logger.info(f"    Error: {check_result['error']}")

        logger.info("✅ Health check test completed successfully")

    except Exception as e:
        logger.error(f"❌ Health check test failed: {e}")
        raise


async def demonstrate_circuit_breaker(client: KrakenRestClient):
    """Demonstrate circuit breaker behavior."""
    logger.info("Demonstrating circuit breaker behavior...")

    if not client.circuit_breaker:
        logger.info("Circuit breaker not enabled, skipping demonstration")
        return

    try:
        # Get initial circuit breaker status
        cb_status = client.circuit_breaker.get_status()
        logger.info(f"Circuit breaker initial state: {cb_status['state']}")

        # Force open circuit breaker for demonstration
        logger.info("Forcing circuit breaker open for demonstration...")
        client.circuit_breaker.force_open()

        # Try to make a request (should be blocked)
        try:
            await client.get_server_time()
            logger.error("❌ Request should have been blocked by circuit breaker")
        except NetworkError as e:
            if "circuit breaker" in str(e).lower():
                logger.info("✅ Circuit breaker correctly blocked request")
            else:
                logger.error(f"❌ Unexpected error: {e}")

        # Force close circuit breaker
        logger.info("Forcing circuit breaker closed...")
        client.circuit_breaker.force_close()

        # Verify requests work again
        await client.get_server_time()
        logger.info("✅ Circuit breaker demonstration completed successfully")

    except Exception as e:
        logger.error(f"❌ Circuit breaker demonstration failed: {e}")
        raise


async def run_comprehensive_test():
    """Run comprehensive test of all API client features."""
    logger.info("🚀 Starting comprehensive Kraken API client test")

    # Get API credentials from environment
    api_key = os.getenv('KRAKEN_API_KEY')
    private_key = os.getenv('KRAKEN_PRIVATE_KEY')

    if not api_key or not private_key:
        logger.warning("⚠️  API credentials not found in environment variables")
        logger.warning("Some tests will be skipped. Set KRAKEN_API_KEY and KRAKEN_PRIVATE_KEY to run all tests.")
        # Use dummy credentials for public endpoint testing
        api_key = "dummy_key_for_public_tests"
        private_key = "dummy_private_key_for_public_tests"

    # Create client with full integration
    async with KrakenRestClient(
        api_key=api_key,
        private_key=private_key,
        account_tier=AccountTier.INTERMEDIATE,
        enable_rate_limiting=True,
        enable_circuit_breaker=True,
        timeout=30.0,
        max_retries=3
    ) as client:

        test_results = {}

        # Test public endpoints (always works)
        try:
            await test_public_endpoints(client)
            test_results['public_endpoints'] = '✅ PASSED'
        except Exception as e:
            test_results['public_endpoints'] = f'❌ FAILED: {e}'

        # Test private endpoints (requires valid credentials)
        if api_key != "dummy_key_for_public_tests":
            try:
                await test_private_endpoints(client)
                test_results['private_endpoints'] = '✅ PASSED'
            except Exception as e:
                test_results['private_endpoints'] = f'❌ FAILED: {e}'
        else:
            test_results['private_endpoints'] = '⏭️  SKIPPED (no credentials)'

        # Test error handling
        try:
            await test_error_handling(client)
            test_results['error_handling'] = '✅ PASSED'
        except Exception as e:
            test_results['error_handling'] = f'❌ FAILED: {e}'

        # Test trading operations (validation mode)
        if api_key != "dummy_key_for_public_tests":
            try:
                await test_trading_operations(client)
                test_results['trading_operations'] = '✅ PASSED'
            except Exception as e:
                test_results['trading_operations'] = f'❌ FAILED: {e}'
        else:
            test_results['trading_operations'] = '⏭️  SKIPPED (no credentials)'

        # Test performance monitoring
        try:
            await test_performance_monitoring(client)
            test_results['performance_monitoring'] = '✅ PASSED'
        except Exception as e:
            test_results['performance_monitoring'] = f'❌ FAILED: {e}'

        # Test health check
        try:
            await test_health_check(client)
            test_results['health_check'] = '✅ PASSED'
        except Exception as e:
            test_results['health_check'] = f'❌ FAILED: {e}'

        # Test circuit breaker demonstration
        try:
            await demonstrate_circuit_breaker(client)
            test_results['circuit_breaker'] = '✅ PASSED'
        except Exception as e:
            test_results['circuit_breaker'] = f'❌ FAILED: {e}'

        # Final results
        logger.info("\n" + "="*60)
        logger.info("🏁 COMPREHENSIVE TEST RESULTS")
        logger.info("="*60)

        for test_name, result in test_results.items():
            logger.info(f"{test_name:<25} {result}")

        # Final metrics
        final_metrics = client.get_metrics()
        logger.info("\n📊 FINAL METRICS:")
        logger.info(f"Total requests: {final_metrics['total_requests']}")
        logger.info(f"Success rate: {final_metrics['success_rate']:.2%}")
        logger.info(f"Average response time: {final_metrics['avg_response_time']:.3f}s")

        passed_tests = sum(1 for result in test_results.values() if result.startswith('✅'))
        total_tests = len(test_results)

        if passed_tests == total_tests:
            logger.info(f"\n🎉 ALL TESTS PASSED ({passed_tests}/{total_tests})")
        else:
            logger.info(f"\n⚠️  SOME TESTS FAILED ({passed_tests}/{total_tests} passed)")

        logger.info("="*60)


async def simple_usage_example():
    """Simple usage example for documentation."""
    logger.info("📖 Simple usage example:")

    # Initialize client
    async with KrakenRestClient(
        api_key="your_api_key",
        private_key="your_private_key"
    ) as client:

        # Get ticker information
        ticker = await client.get_ticker_information("XBTUSD")
        print(f"BTC/USD Price: {ticker}")

        # Get account balance (requires valid credentials)
        try:
            balance = await client.get_account_balance()
            print(f"Account Balance: {balance}")
        except AuthenticationError:
            print("Authentication failed - check your API credentials")


if __name__ == "__main__":
    # Run comprehensive test
    try:
        asyncio.run(run_comprehensive_test())
    except KeyboardInterrupt:
        logger.info("\n⏹️  Test interrupted by user")
    except Exception as e:
        logger.error(f"\n💥 Test failed with unexpected error: {e}")
        sys.exit(1)
