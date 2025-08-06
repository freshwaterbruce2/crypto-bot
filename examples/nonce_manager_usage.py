"""
Kraken Nonce Manager Usage Examples

Demonstrates how to use the thread-safe nonce management system
for Kraken WebSocket connections.
"""

import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def basic_usage_example():
    """Basic nonce generation example"""
    print("\n=== Basic Nonce Generation ===")

    # Get the global nonce manager
    nonce_manager = get_unified_nonce_manager()

    # Generate nonces for a connection
    connection_id = "my_websocket_1"

    for i in range(5):
        nonce = nonce_manager.get_nonce(connection_id)
        print(f"Nonce {i+1}: {nonce}")

    # Different connection gets different sequence
    connection_id_2 = "my_websocket_2"
    nonce2 = nonce_manager.get_nonce(connection_id_2)
    print(f"\nDifferent connection nonce: {nonce2}")


def batch_nonce_example():
    """Batch nonce generation for multiple requests"""
    print("\n=== Batch Nonce Generation ===")

    nonce_manager = get_unified_nonce_manager()
    connection_id = "batch_connection"

    # Get 10 nonces at once (useful for queuing multiple requests)
    batch_nonces = nonce_manager.get_batch_nonces(connection_id, 10)
    print(f"Generated batch of {len(batch_nonces)} nonces")
    print(f"First: {batch_nonces[0]}, Last: {batch_nonces[-1]}")


async def websocket_integration_example():
    """WebSocket coordinator integration example"""
    print("\n=== WebSocket Coordinator Example ===")

    # Get the coordinator
    coordinator = get_unified_nonce_manager()

    # Register a connection
    conn_id = "kraken_ws_main"
    coordinator.register_connection(conn_id)

    # Create authentication message
    api_key = "your_api_key_here"
    auth_msg = coordinator.create_auth_message(conn_id, api_key)
    print(f"Auth message: {auth_msg}")

    # Simulate successful use
    coordinator.mark_nonce_success(conn_id, auth_msg['reqid'])

    # Get statistics
    stats = coordinator.get_connection_stats(conn_id)
    print(f"\nConnection stats: {stats}")


def error_handling_example():
    """Demonstrate error recovery"""
    print("\n=== Error Handling Example ===")

    coordinator = get_unified_nonce_manager()
    conn_id = "error_test_conn"

    # Get a nonce
    nonce = coordinator.get_auth_nonce(conn_id)
    print(f"Original nonce: {nonce}")

    # Simulate nonce error
    recovery = coordinator.handle_nonce_error(
        conn_id,
        nonce,
        "EOrder:Invalid nonce"
    )

    print(f"Recovery strategy: {recovery}")
    print(f"New nonce after reset: {recovery.get('new_nonce')}")


def statistics_example():
    """Show nonce manager statistics"""
    print("\n=== Statistics Example ===")

    nonce_manager = get_unified_nonce_manager()

    # Generate some activity
    for i in range(3):
        conn_id = f"stats_conn_{i}"
        for j in range(5):
            nonce_manager.get_nonce(conn_id)

    # Get statistics
    stats = nonce_manager.get_statistics()
    print(f"Active connections: {stats['active_connections']}")
    print(f"Total nonces generated: {stats['total_nonces']}")
    print(f"Base nonce: {stats['base_nonce']}")


async def concurrent_usage_example():
    """Demonstrate thread-safe concurrent usage"""
    print("\n=== Concurrent Usage Example ===")

    nonce_manager = get_unified_nonce_manager()
    connection_id = "concurrent_test"

    async def generate_nonces(task_id):
        """Generate nonces from async task"""
        nonces = []
        for _ in range(5):
            nonce = nonce_manager.get_nonce(connection_id)
            nonces.append(nonce)
            await asyncio.sleep(0.01)  # Simulate work
        return task_id, nonces

    # Run multiple tasks concurrently
    tasks = [generate_nonces(i) for i in range(3)]
    results = await asyncio.gather(*tasks)

    # Check all nonces are unique
    all_nonces = []
    for task_id, nonces in results:
        print(f"Task {task_id} generated: {nonces[0]} to {nonces[-1]}")
        all_nonces.extend(nonces)

    print(f"\nTotal nonces: {len(all_nonces)}")
    print(f"Unique nonces: {len(set(all_nonces))}")
    print(f"All unique: {len(all_nonces) == len(set(all_nonces))}")


def practical_websocket_example():
    """Practical example for Kraken WebSocket"""
    print("\n=== Practical WebSocket Usage ===")

    # Initialize components
    nonce_manager = KrakenUnifiedUnifiedKrakenNonceManager()
    coordinator = get_unified_nonce_manager()

    # Connection setup
    connection_id = "kraken_main"
    coordinator.register_connection(connection_id)

    # Example 1: Subscribe to private channel
    subscribe_msg = {
        "event": "subscribe",
        "subscription": {
            "name": "ownTrades"
        }
    }

    # Add nonce
    nonce = coordinator.get_auth_nonce(connection_id)
    subscribe_msg["reqid"] = nonce

    print(f"Subscribe message with nonce: {subscribe_msg}")

    # Example 2: Place order with nonce
    order_nonce = coordinator.get_auth_nonce(connection_id)
    order_msg = {
        "event": "addOrder",
        "reqid": order_nonce,
        "ordertype": "limit",
        "type": "buy",
        "pair": "XBT/USD",
        "price": "40000",
        "volume": "0.001"
    }

    print(f"\nOrder message with nonce: {order_msg['reqid']}")

    # Example 3: Cancel order with nonce
    cancel_nonce = coordinator.get_auth_nonce(connection_id)
    cancel_msg = {
        "event": "cancelOrder",
        "reqid": cancel_nonce,
        "txid": ["ORDER-ID-HERE"]
    }

    print(f"\nCancel message with nonce: {cancel_msg['reqid']}")

    # All nonces are sequential
    print(f"\nNonces are sequential: {subscribe_msg['reqid']}, {order_msg['reqid']}, {cancel_msg['reqid']}")


async def main():
    """Run all examples"""
    print("Kraken Nonce Manager Examples")
    print("=" * 40)

    # Basic examples
    basic_usage_example()
    batch_nonce_example()

    # Async examples
    await websocket_integration_example()

    # Error handling
    error_handling_example()

    # Statistics
    statistics_example()

    # Concurrent usage
    await concurrent_usage_example()

    # Practical usage
    practical_websocket_example()


if __name__ == "__main__":
    asyncio.run(main())
