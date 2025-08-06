#!/usr/bin/env python3
"""
Quick Public WebSocket Solution
Connects to Kraken's public WebSocket API for live price data
No authentication required - works immediately!
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, List

import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QuickPublicWebSocket:
    """Simple public WebSocket client for Kraken price data"""

    def __init__(self):
        self.ws_url = "wss://ws.kraken.com/v2"
        self.websocket = None
        self.running = False
        self.subscriptions = []
        self.price_data = {}

        # Focus on popular USDT pairs for quick demo
        self.usdt_pairs = [
            "BTC/USDT",
            "ETH/USDT",
            "SOL/USDT",
            "ADA/USDT",
            "DOT/USDT",
            "MATIC/USDT",
            "AVAX/USDT",
            "ATOM/USDT",
            "LINK/USDT",
            "UNI/USDT"
        ]

    async def connect(self):
        """Connect to public WebSocket"""
        try:
            logger.info("Connecting to Kraken public WebSocket...")
            self.websocket = await websockets.connect(self.ws_url)
            logger.info("✅ Connected to Kraken public WebSocket!")
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False

    async def subscribe_to_tickers(self, symbols: List[str]):
        """Subscribe to ticker updates for specified symbols"""
        if not self.websocket:
            logger.error("WebSocket not connected")
            return

        try:
            subscription_msg = {
                "method": "subscribe",
                "params": {
                    "channel": "ticker",
                    "symbol": symbols
                }
            }

            await self.websocket.send(json.dumps(subscription_msg))
            logger.info(f"📡 Subscribed to ticker updates for {len(symbols)} pairs")
            self.subscriptions.extend(symbols)

        except Exception as e:
            logger.error(f"❌ Subscription failed: {e}")

    async def handle_message(self, message: str):
        """Process incoming WebSocket messages"""
        try:
            data = json.loads(message)

            # Handle subscription confirmations
            if data.get("method") == "subscribe" and data.get("success"):
                logger.info("✅ Subscription confirmed")
                return

            # Handle ticker updates
            if data.get("channel") == "ticker":
                await self.process_ticker_update(data)

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {message[:100]}...")
        except Exception as e:
            logger.error(f"Message handling error: {e}")

    async def process_ticker_update(self, data: Dict):
        """Process ticker update messages"""
        try:
            ticker_data = data.get("data", [])

            for ticker in ticker_data:
                symbol = ticker.get("symbol")
                if not symbol:
                    continue

                # Extract price information
                last_price = float(ticker.get("last", 0))
                bid = float(ticker.get("bid", 0))
                ask = float(ticker.get("ask", 0))
                volume = float(ticker.get("volume", 0))
                change_24h = float(ticker.get("change", 0))
                change_pct = float(ticker.get("change_pct", 0))

                # Store price data
                self.price_data[symbol] = {
                    "last": last_price,
                    "bid": bid,
                    "ask": ask,
                    "volume": volume,
                    "change_24h": change_24h,
                    "change_pct": change_pct,
                    "timestamp": datetime.now().isoformat()
                }

                # Log price update (every 10th update to avoid spam)
                if len(self.price_data) % 10 == 0 or symbol == "BTC/USDT":
                    logger.info(
                        f"💰 {symbol}: ${last_price:,.4f} "
                        f"({change_pct:+.2f}%) "
                        f"Vol: {volume:,.0f}"
                    )

        except Exception as e:
            logger.error(f"Ticker processing error: {e}")

    async def display_price_summary(self):
        """Display current price summary every 30 seconds"""
        while self.running:
            try:
                await asyncio.sleep(30)

                if not self.price_data:
                    continue

                logger.info("\n" + "="*60)
                logger.info("📊 LIVE PRICE SUMMARY")
                logger.info("="*60)

                # Sort by market cap (BTC, ETH first)
                priority_order = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
                sorted_pairs = []

                for pair in priority_order:
                    if pair in self.price_data:
                        sorted_pairs.append(pair)

                # Add remaining pairs
                for pair in sorted(self.price_data.keys()):
                    if pair not in sorted_pairs:
                        sorted_pairs.append(pair)

                for symbol in sorted_pairs:
                    data = self.price_data[symbol]
                    logger.info(
                        f"{symbol:>12}: ${data['last']:>10,.4f} "
                        f"({data['change_pct']:>+6.2f}%) "
                        f"Vol: ${data['volume']:>12,.0f}"
                    )

                logger.info("="*60 + "\n")

            except Exception as e:
                logger.error(f"Display error: {e}")

    async def run(self):
        """Main run loop"""
        self.running = True

        try:
            # Connect to WebSocket
            if not await self.connect():
                return

            # Subscribe to ticker updates
            await self.subscribe_to_tickers(self.usdt_pairs)

            # Start price summary display task
            summary_task = asyncio.create_task(self.display_price_summary())

            logger.info("🚀 Quick Public WebSocket is running!")
            logger.info("📈 Receiving live price data from Kraken...")
            logger.info("⏹️  Press Ctrl+C to stop")

            # Main message handling loop
            async for message in self.websocket:
                if not self.running:
                    break
                await self.handle_message(message)

        except websockets.exceptions.ConnectionClosed:
            logger.warning("🔌 WebSocket connection closed")
        except KeyboardInterrupt:
            logger.info("🛑 Stopping by user request...")
        except Exception as e:
            logger.error(f"❌ Runtime error: {e}")
        finally:
            self.running = False
            if summary_task and not summary_task.done():
                summary_task.cancel()
            await self.cleanup()

    async def cleanup(self):
        """Clean shutdown"""
        if self.websocket:
            await self.websocket.close()
        logger.info("✅ Quick Public WebSocket stopped cleanly")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n🛑 Shutdown signal received...")
    sys.exit(0)


async def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🚀 Quick Public WebSocket Demo")
    print("=" * 50)
    print("📡 Connecting to Kraken public WebSocket API...")
    print("💰 Monitoring live USDT pair prices")
    print("🔓 No authentication required!")
    print("=" * 50)

    # Create and run WebSocket client
    client = QuickPublicWebSocket()
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
