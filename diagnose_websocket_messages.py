#!/usr/bin/env python3
"""
WebSocket V2 Message Diagnostic Tool
===================================

This tool connects to Kraken WebSocket V2 and logs the exact raw messages
being received to help identify the "unknown message types" issue.
"""

import asyncio
import json
import logging
import time
from datetime import datetime

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('websocket_diagnostics.log')
    ]
)

logger = logging.getLogger(__name__)

# Import WebSocket components
try:
    from kraken.spot import SpotWSClient
    KRAKEN_SDK_AVAILABLE = True
except ImportError as e:
    logger.error(f"Kraken SDK not available: {e}")
    KRAKEN_SDK_AVAILABLE = False
    exit(1)


class DiagnosticBot(SpotWSClient):
    """Diagnostic bot to capture raw WebSocket messages"""
    
    def __init__(self):
        """Initialize diagnostic bot"""
        super().__init__()
        self.message_count = 0
        self.message_types = {}
        self.channel_types = {}
        
    async def on_message(self, message):
        """Log every raw message received"""
        self.message_count += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        logger.info(f"[RAW_MESSAGE_{self.message_count}] {timestamp}")
        logger.info(f"[RAW_MESSAGE_{self.message_count}] Type: {type(message)}")
        logger.info(f"[RAW_MESSAGE_{self.message_count}] Content: {json.dumps(message, indent=2, default=str)}")
        
        # Analyze message structure
        if isinstance(message, dict):
            channel = message.get('channel', 'NO_CHANNEL')
            msg_type = message.get('type', 'NO_TYPE')
            method = message.get('method', 'NO_METHOD')
            
            # Track statistics
            channel_key = f"channel={channel}"
            type_key = f"type={msg_type}"
            method_key = f"method={method}"
            
            self.channel_types[channel_key] = self.channel_types.get(channel_key, 0) + 1
            self.message_types[type_key] = self.message_types.get(type_key, 0) + 1
            if method != 'NO_METHOD':
                self.message_types[method_key] = self.message_types.get(method_key, 0) + 1
            
            logger.info(f"[MESSAGE_ANALYSIS_{self.message_count}] Channel: '{channel}', Type: '{msg_type}', Method: '{method}'")
            
            # Special attention to problematic messages
            if channel == 'unknown' or msg_type == 'unknown':
                logger.error(f"[PROBLEMATIC_MESSAGE_{self.message_count}] Found unknown channel/type:")
                logger.error(f"[PROBLEMATIC_MESSAGE_{self.message_count}] Full message structure:")
                for key, value in message.items():
                    logger.error(f"[PROBLEMATIC_MESSAGE_{self.message_count}]   {key}: {value} ({type(value)})")
        
        print("-" * 80)
        
        # Print statistics every 10 messages
        if self.message_count % 10 == 0:
            self.print_statistics()
    
    def print_statistics(self):
        """Print message statistics"""
        logger.info(f"[STATISTICS] Total messages received: {self.message_count}")
        logger.info("[STATISTICS] Channel distribution:")
        for channel, count in sorted(self.channel_types.items()):
            logger.info(f"[STATISTICS]   {channel}: {count}")
        logger.info("[STATISTICS] Type/Method distribution:")
        for msg_type, count in sorted(self.message_types.items()):
            logger.info(f"[STATISTICS]   {msg_type}: {count}")


async def main():
    """Main diagnostic function"""
    logger.info("=== WebSocket V2 Message Diagnostics Starting ===")
    
    if not KRAKEN_SDK_AVAILABLE:
        logger.error("Kraken SDK not available - cannot proceed")
        return
    
    # Create diagnostic bot
    bot = DiagnosticBot()
    
    try:
        logger.info("Starting WebSocket connection...")
        
        # Subscribe to some basic channels for testing (using correct SDK V2 format)
        try:
            await bot.subscribe(
                params={
                    'channel': 'ticker',
                    'symbol': ['SHIB/USDT', 'XBT/USDT']
                }
            )
            logger.info("Subscribed to ticker")
        except Exception as e:
            logger.error(f"Failed to subscribe to ticker: {e}")
        
        try:
            await bot.subscribe(
                params={
                    'channel': 'ohlc',
                    'symbol': ['SHIB/USDT'],
                    'interval': 1
                }
            )
            logger.info("Subscribed to OHLC")
        except Exception as e:
            logger.error(f"Failed to subscribe to OHLC: {e}")
        
        try:
            await bot.subscribe(
                params={
                    'channel': 'book',
                    'symbol': ['SHIB/USDT'],
                    'depth': 10
                }
            )
            logger.info("Subscribed to orderbook")
        except Exception as e:
            logger.error(f"Failed to subscribe to orderbook: {e}")
        
        # Run for 30 seconds to capture messages
        logger.info("Capturing messages for 30 seconds...")
        await asyncio.sleep(30)
        
    except Exception as e:
        logger.error(f"Error during diagnostic: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        logger.info("=== Final Statistics ===")
        bot.print_statistics()
        logger.info("=== WebSocket V2 Message Diagnostics Complete ===")


if __name__ == "__main__":
    asyncio.run(main())