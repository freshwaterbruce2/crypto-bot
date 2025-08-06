#!/usr/bin/env python3
"""
Kraken Pro Client Usage Examples
================================

Comprehensive examples showing how to use the new KrakenProClient
with WebSocket V2, V1 fallbacks, and REST API integration.

This demonstrates:
1. Basic client initialization and Pro account detection
2. Real-time data streaming with automatic fallbacks
3. Fee-free trading for Pro accounts
4. WebSocket connection management
5. Health monitoring and diagnostics
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exchange.kraken_pro_client import ConnectionMode, KrakenProClient
from utils.professional_logging_system import setup_professional_logging


async def example_1_basic_setup():
    """Example 1: Basic client setup and Pro account detection."""

    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Setup and Pro Account Detection")
    print("="*60)

    # Method 1: Using context manager (recommended)
    async with KrakenProClient() as client:
        # Verify Pro account status
        pro_status = await client.verify_pro_account_status()

        print(f"Pro Account: {pro_status.is_pro_account}")
        print(f"Fee Schedule: {pro_status.fee_schedule}")
        print(f"Maker Fee: {pro_status.maker_fee}%")
        print(f"Taker Fee: {pro_status.taker_fee}%")
        print(f"WebSocket Token Available: {pro_status.websocket_token_available}")
        print(f"Available Features: {[f.value for f in pro_status.available_features]}")

        # Get connection status
        conn_status = client.get_connection_status()
        print("\nConnection Health:")
        print(f"  WebSocket V2: {conn_status['connection_health']['websocket_v2_status']}")
        print(f"  WebSocket V1: {conn_status['connection_health']['websocket_v1_status']}")
        print(f"  REST API: {conn_status['connection_health']['rest_api_status']}")
        print(f"  Fallback Mode: {conn_status['connection_health']['fallback_mode']}")


async def example_2_real_time_data():
    """Example 2: Real-time data with automatic fallbacks."""

    print("\n" + "="*60)
    print("EXAMPLE 2: Real-time Data with Automatic Fallbacks")
    print("="*60)

    async with KrakenProClient() as client:
        # Test real-time ticker data for multiple pairs
        test_pairs = ["BTC/USD", "ETH/USD", "ADA/USD"]

        print("Fetching real-time ticker data...")

        for pair in test_pairs:
            try:
                ticker_data = await client.get_real_time_ticker(pair)

                if ticker_data.get("result") and pair in ticker_data["result"]:
                    pair_data = ticker_data["result"][pair]

                    # Extract key information
                    last_price = pair_data.get("c", ["N/A"])[0]  # Last trade closed price
                    bid_price = pair_data.get("b", ["N/A"])[0]   # Best bid price
                    ask_price = pair_data.get("a", ["N/A"])[0]   # Best ask price
                    volume = pair_data.get("v", ["N/A"])[1]      # 24h volume

                    print(f"{pair}:")
                    print(f"  Last Price: ${last_price}")
                    print(f"  Bid: ${bid_price}")
                    print(f"  Ask: ${ask_price}")
                    print(f"  24h Volume: {volume}")
                    print()

            except Exception as e:
                print(f"Error fetching {pair}: {e}")


async def example_3_streaming_data():
    """Example 3: Streaming real-time data with callback processing."""

    print("\n" + "="*60)
    print("EXAMPLE 3: Streaming Real-time Data (10 seconds)")
    print("="*60)

    # Callback function to process streaming data
    async def data_callback(data):
        """Process incoming streaming data."""
        # Simple data processing example
        if isinstance(data, dict):
            method = data.get("method", "unknown")
            channel = data.get("channel", "unknown")

            if method == "rest_polling":
                # REST API polling data
                symbol = data.get("symbol", "unknown")
                print(f"📡 REST: {channel} data for {symbol}")
            elif "ticker" in str(data).lower():
                # WebSocket ticker data
                print("🔴 WebSocket: Ticker update received")
            else:
                print(f"📊 Data: {method}/{channel}")

    async with KrakenProClient(connection_mode=ConnectionMode.HYBRID) as client:
        # Start streaming ticker data
        channels = ["ticker"]
        symbols = ["BTC/USD", "ETH/USD"]

        print(f"Starting data stream for {symbols} on channels {channels}")
        print("Streaming for 10 seconds...")

        # Start streaming task
        stream_task = await client.stream_real_time_data(
            channels=channels,
            symbols=symbols,
            callback=data_callback
        )

        # Let it stream for 10 seconds
        await asyncio.sleep(10)

        # Cancel streaming
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass

        print("Streaming stopped.")


async def example_4_pro_trading():
    """Example 4: Pro account trading with fee-free execution."""

    print("\n" + "="*60)
    print("EXAMPLE 4: Pro Account Trading (DEMO - No actual trades)")
    print("="*60)

    async with KrakenProClient() as client:
        # Verify Pro account features
        pro_status = await client.verify_pro_account_status()

        if pro_status.is_pro_account:
            print("✅ Pro Account Detected - Fee-free trading available!")

            # Demo order (validation only - won't execute)
            print("\nDemo Order Placement (validate=True):")
            try:
                order_response = await client.place_order(
                    pair="BTC/USD",
                    side="buy",
                    order_type="limit",
                    volume="0.001",  # Small amount
                    price="30000",   # Well below market
                    validate=True    # IMPORTANT: Only validate, don't execute
                )

                if order_response.get("result"):
                    print("✅ Order validation successful")
                    result = order_response["result"]
                    print(f"Order Details: {result}")
                else:
                    print("❌ Order validation failed")
                    print(f"Error: {order_response}")

            except Exception as e:
                print(f"Order placement error: {e}")
        else:
            print("Standard account detected - normal fees apply")

        # Show current account balance
        print("\nAccount Balance:")
        balance_data = await client.get_account_balance()

        if balance_data.get("result"):
            result = balance_data["result"]

            # Show Pro account enhancements if available
            if "_pro_account" in result:
                print("✅ Pro Account Features Active")
                print(f"   Fee Schedule: {result.get('_fee_schedule', 'N/A')}")

            # Show non-zero balances
            balances = {k: v for k, v in result.items()
                       if not k.startswith("_") and float(v) > 0}

            if balances:
                print("Non-zero Balances:")
                for asset, amount in list(balances.items())[:5]:
                    print(f"  {asset}: {amount}")
            else:
                print("All balances are zero")


async def example_5_connection_monitoring():
    """Example 5: Connection health monitoring and diagnostics."""

    print("\n" + "="*60)
    print("EXAMPLE 5: Connection Health Monitoring")
    print("="*60)

    async with KrakenProClient() as client:
        # Perform comprehensive health check
        health = await client.health_check()

        print(f"Overall Status: {health['overall_status']}")
        print(f"Timestamp: {health['timestamp']}")

        print("\nDetailed Health Checks:")
        for component, status in health.get("checks", {}).items():
            comp_status = status.get("status", "unknown")
            print(f"  {component}: {comp_status}")

            # Show additional details for some components
            if component == "rest_api" and "checks" in status:
                rest_checks = status["checks"]
                print(f"    - API Connectivity: {rest_checks.get('api_connectivity', {}).get('status', 'unknown')}")
                print(f"    - Authentication: {rest_checks.get('authentication', {}).get('status', 'unknown')}")
            elif component in ["websocket_v2", "websocket_v1"]:
                connected = status.get("connected", False)
                print(f"    - Connected: {connected}")

        # Show connection status
        print("\nConnection Status:")
        conn_status = client.get_connection_status()

        active_connections = conn_status["connection_health"]["active_connections"]
        print(f"Active Connections: {active_connections}")

        fallback_mode = conn_status["connection_health"]["fallback_mode"]
        print(f"Fallback Mode: {fallback_mode}")

        # Test all connections
        print("\nTesting Connections...")
        connection_test = await client.test_connection()
        print(f"Connection Test Result: {'✅ PASSED' if connection_test else '❌ FAILED'}")


async def example_6_error_handling():
    """Example 6: Error handling and recovery patterns."""

    print("\n" + "="*60)
    print("EXAMPLE 6: Error Handling and Recovery")
    print("="*60)

    # Test with different connection modes
    modes_to_test = [
        ConnectionMode.HYBRID,
        ConnectionMode.REST_POLLING
    ]

    for mode in modes_to_test:
        print(f"\nTesting connection mode: {mode.value}")

        try:
            client = KrakenProClient(connection_mode=mode)
            await client.start()

            # Test basic connectivity
            server_time = await client.rest_client.get_server_time()
            if server_time.get("result"):
                print(f"✅ {mode.value}: Server time sync successful")

            # Test account access
            balance = await client.get_account_balance()
            if balance.get("result"):
                print(f"✅ {mode.value}: Account balance access successful")

            # Clean shutdown
            await client.close()
            print(f"✅ {mode.value}: Clean shutdown successful")

        except Exception as e:
            print(f"❌ {mode.value}: Error - {e}")


async def main():
    """Run all examples."""

    # Setup logging
    setup_professional_logging(
        log_level="INFO",
        console_output=True,
        file_output=False  # Keep console clean for examples
    )

    print("KRAKEN PRO CLIENT USAGE EXAMPLES")
    print("="*70)
    print("This will demonstrate the key features of the KrakenProClient")
    print("with your existing API credentials.")
    print()

    try:
        # Run examples
        await example_1_basic_setup()
        await example_2_real_time_data()
        await example_3_streaming_data()
        await example_4_pro_trading()
        await example_5_connection_monitoring()
        await example_6_error_handling()

        print("\n" + "="*70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("The KrakenProClient is ready for integration into your trading bot.")
        print()
        print("Key Benefits:")
        print("✅ WebSocket V2 support with V1 fallback")
        print("✅ REST API fallback for maximum reliability")
        print("✅ Pro account fee-free trading detection")
        print("✅ Automatic connection health monitoring")
        print("✅ Comprehensive error handling and recovery")
        print("✅ Real-time data streaming with multiple protocols")

    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nExamples failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
