"""
Balance Manager Integration Example
==================================

This example demonstrates how to integrate the unified balance manager system
with the existing crypto trading bot architecture, including WebSocket V2
streaming, REST API fallback, and trading logic integration.

Usage:
    python -m src.balance.integration_example
"""

import asyncio
import logging
from typing import Any

from ..api.kraken_rest_client import KrakenRestClient
from ..config.config import load_config

# Import existing bot components
from ..websocket.kraken_websocket_v2 import KrakenWebSocketV2

# Import balance manager components
from .balance_manager import BalanceManager, BalanceManagerConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BalanceManagerIntegrationExample:
    """
    Example implementation showing balance manager integration
    """

    def __init__(self, config_path: str = None):
        """Initialize with configuration"""
        self.config = load_config(config_path) if config_path else {}

        # Extract API credentials
        self.api_key = self.config.get('kraken', {}).get('api_key', '')
        self.api_secret = self.config.get('kraken', {}).get('api_secret', '')

        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found in configuration")

        # Initialize clients
        self.websocket_client = None
        self.rest_client = None
        self.balance_manager = None

        # Example state
        self.running = False
        self.balance_updates_received = 0
        self.trading_decisions_made = 0

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing Balance Manager Integration Example...")

        try:
            # Initialize REST API client
            self.rest_client = KrakenRestClient(
                api_key=self.api_key,
                private_key=self.api_secret,
                account_tier='intermediate'  # Adjust based on your account
            )

            # Initialize WebSocket V2 client
            self.websocket_client = KrakenWebSocketV2(
                api_key=self.api_key,
                api_secret=self.api_secret
            )

            # Set exchange client reference for WebSocket authentication
            self.websocket_client.set_exchange_client(self.rest_client)

            # Create balance manager configuration
            balance_config = BalanceManagerConfig(
                cache_max_size=1000,
                cache_default_ttl=300.0,  # 5 minutes
                history_max_entries=10000,
                history_retention_hours=24 * 7,  # 1 week
                history_persistence_file='D:/trading_data/balance_history.json',
                enable_validation=True,
                validation_on_cache=True,
                validation_on_update=True,
                websocket_timeout=10.0,
                rest_api_timeout=15.0,
                enable_circuit_breaker=True,
                force_update_interval=600.0,  # 10 minutes
                cleanup_interval=300.0  # 5 minutes
            )

            # Initialize balance manager
            self.balance_manager = BalanceManager(
                websocket_client=self.websocket_client,
                rest_client=self.rest_client,
                config=balance_config
            )

            # Register balance update callbacks
            self._setup_balance_callbacks()

            # Initialize balance manager
            success = await self.balance_manager.initialize()
            if not success:
                raise RuntimeError("Failed to initialize balance manager")

            # Connect WebSocket
            ws_success = await self.websocket_client.connect(private_channels=True)
            if not ws_success:
                logger.warning("WebSocket connection failed, will use REST API fallback")

            logger.info("Balance Manager Integration initialized successfully")

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            await self.cleanup()
            raise

    def _setup_balance_callbacks(self):
        """Setup callbacks for balance events"""

        async def on_balance_update(balance_data: dict[str, Any]):
            """Handle balance updates"""
            self.balance_updates_received += 1
            asset = balance_data['asset']
            balance = balance_data['balance']
            free_balance = balance_data['free']

            logger.info(f"Balance Update: {asset} = {balance} (free: {free_balance}) from {balance_data['source']}")

            # Example: Make trading decision based on balance
            await self._process_balance_for_trading(balance_data)

        async def on_balance_change(balance_data: dict[str, Any]):
            """Handle significant balance changes"""
            asset = balance_data['asset']
            logger.info(f"Significant balance change detected for {asset}: {balance_data}")

            # Example: Log to trading journal or alert system
            await self._log_balance_change(balance_data)

        async def on_websocket_connected():
            """Handle WebSocket connection"""
            logger.info("WebSocket connected - real-time balance streaming active")

        async def on_websocket_disconnected():
            """Handle WebSocket disconnection"""
            logger.warning("WebSocket disconnected - falling back to REST API")

        async def on_fallback_activated(reason: str):
            """Handle fallback activation"""
            logger.info(f"Fallback activated: {reason}")

        async def on_validation_failed(validation_result):
            """Handle validation failures"""
            logger.warning(f"Balance validation failed: {validation_result.to_dict()}")

        async def on_error(error):
            """Handle errors"""
            logger.error(f"Balance manager error: {error}")

        # Register callbacks
        self.balance_manager.register_callback('balance_update', on_balance_update)
        self.balance_manager.register_callback('balance_change', on_balance_change)
        self.balance_manager.register_callback('websocket_connected', on_websocket_connected)
        self.balance_manager.register_callback('websocket_disconnected', on_websocket_disconnected)
        self.balance_manager.register_callback('fallback_activated', on_fallback_activated)
        self.balance_manager.register_callback('validation_failed', on_validation_failed)
        self.balance_manager.register_callback('error', on_error)

    async def _process_balance_for_trading(self, balance_data: dict[str, Any]):
        """Example trading logic based on balance updates"""
        try:
            asset = balance_data['asset']
            free_balance = balance_data['free']

            # Example: Check if we have enough USDT to make trades
            if asset == 'USDT' and free_balance < 10.0:
                logger.warning("Low USDT balance - may need to close positions")
                # Example: Trigger position closure logic
                await self._handle_low_balance_situation(asset, free_balance)

            # Example: Check if asset balance changed significantly
            elif asset != 'USDT' and free_balance > 0:
                logger.info(f"Have {free_balance} {asset} available for trading")
                # Example: Update trading strategy parameters
                await self._update_trading_parameters(asset, free_balance)

            self.trading_decisions_made += 1

        except Exception as e:
            logger.error(f"Error processing balance for trading: {e}")

    async def _handle_low_balance_situation(self, asset: str, balance: float):
        """Handle low balance situations"""
        logger.info(f"Handling low balance situation: {asset} = {balance}")

        # Example actions:
        # 1. Stop opening new positions
        # 2. Close existing positions if necessary
        # 3. Send alerts
        # 4. Adjust position sizes

        # Get all current balances to assess overall situation
        all_balances = await self.balance_manager.get_all_balances()

        # Calculate total portfolio value in USDT
        total_value = sum(
            bal_data['balance'] for bal_data in all_balances.values()
            if bal_data['asset'] == 'USDT'
        )

        logger.info(f"Total USDT value: {total_value}")

        # Example: If total value is too low, take emergency action
        if total_value < 5.0:
            logger.critical("Emergency: Very low balance - stopping all trading")
            # Stop trading logic would go here

    async def _update_trading_parameters(self, asset: str, balance: float):
        """Update trading parameters based on balance"""
        logger.debug(f"Updating trading parameters for {asset} with balance {balance}")

        # Example: Adjust position sizes based on available balance
        # This would integrate with your existing trading strategies
        pass

    async def _log_balance_change(self, balance_data: dict[str, Any]):
        """Log significant balance changes"""
        try:
            # Example: Save to trading journal
            log_entry = {
                'timestamp': balance_data['timestamp'],
                'asset': balance_data['asset'],
                'balance': balance_data['balance'],
                'change_type': 'balance_change',
                'source': balance_data['source']
            }

            # Example: Write to log file or database
            logger.info(f"Logged balance change: {log_entry}")

        except Exception as e:
            logger.error(f"Error logging balance change: {e}")

    async def run_example(self, duration_seconds: int = 300):
        """Run the integration example for a specified duration"""
        logger.info(f"Running balance manager example for {duration_seconds} seconds...")

        self.running = True
        start_time = asyncio.get_event_loop().time()

        try:
            while self.running and (asyncio.get_event_loop().time() - start_time) < duration_seconds:
                # Example periodic operations
                await self._periodic_balance_check()
                await asyncio.sleep(30)  # Check every 30 seconds

        except KeyboardInterrupt:
            logger.info("Example interrupted by user")
        except Exception as e:
            logger.error(f"Example error: {e}")
        finally:
            self.running = False
            await self.cleanup()

    async def _periodic_balance_check(self):
        """Perform periodic balance checks and demonstrations"""
        try:
            # Example 1: Get specific balance
            usdt_balance = await self.balance_manager.get_balance('USDT')
            if usdt_balance:
                logger.info(f"Current USDT balance: {usdt_balance['free']} (source: {usdt_balance['source']})")

            # Example 2: Get all balances
            all_balances = await self.balance_manager.get_all_balances()
            non_zero_count = len([b for b in all_balances.values() if b['balance'] > 0])
            logger.info(f"Total assets with balance: {non_zero_count}")

            # Example 3: Check balance manager status
            status = self.balance_manager.get_status()
            logger.info(f"Balance Manager Status - "
                       f"WebSocket: {'connected' if status['websocket']['connected'] else 'disconnected'}, "
                       f"Cache hit rate: {status['cache']['hit_rate_percent']:.1f}%, "
                       f"Total updates: {self.balance_updates_received}")

            # Example 4: Validate balances periodically
            if hasattr(self.balance_manager, 'validate_all_balances'):
                validation_result = await self.balance_manager.validate_all_balances()
                if not validation_result.is_valid:
                    logger.warning(f"Balance validation issues found: {len(validation_result.issues)}")

            # Example 5: Get balance history for analysis
            if usdt_balance:
                history_entries = self.balance_manager.history.get_asset_history('USDT', limit=5)
                if history_entries:
                    logger.info(f"Recent USDT balance changes: {len(history_entries)} entries")

        except Exception as e:
            logger.error(f"Periodic balance check error: {e}")

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up Balance Manager Integration...")

        try:
            if self.balance_manager:
                await self.balance_manager.shutdown()

            if self.websocket_client:
                await self.websocket_client.disconnect()

            if self.rest_client:
                await self.rest_client.close()

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

        logger.info("Cleanup complete")

    def print_summary(self):
        """Print example run summary"""
        print("\n" + "="*60)
        print("BALANCE MANAGER INTEGRATION EXAMPLE SUMMARY")
        print("="*60)
        print(f"Balance updates received: {self.balance_updates_received}")
        print(f"Trading decisions made: {self.trading_decisions_made}")

        if self.balance_manager:
            status = self.balance_manager.get_status()
            stats = self.balance_manager.get_statistics()

            print(f"WebSocket connected: {status['websocket']['connected']}")
            print(f"Cache hit rate: {status['cache']['hit_rate_percent']:.1f}%")
            print(f"Total API calls: {stats['rest_api_calls']}")
            print(f"Validation failures: {stats['validation_failures']}")
            print(f"Tracked assets: {status['tracked_assets']}")

        print("="*60)


async def main():
    """Main function to run the integration example"""
    try:
        # Initialize example
        example = BalanceManagerIntegrationExample()

        # Initialize components
        await example.initialize()

        # Run example for 5 minutes
        await example.run_example(duration_seconds=300)

        # Print summary
        example.print_summary()

    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    # Run the integration example
    asyncio.run(main())
