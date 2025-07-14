"""
Kraken Connection Manager - Modular Connection Management

Handles Kraken exchange connection state and health monitoring.
Extracted from monolithic kraken_exchange.py for better maintainability.
"""

import asyncio
import time
import logging
from typing import Optional
import ccxt.async_support as ccxt_async

logger = logging.getLogger(__name__)


class ConnectionState:
    """Track connection state and health metrics."""
    
    def __init__(self):
        self.connected = False
        self.uptime_start = None
        
    def mark_connected(self):
        self.connected = True
        self.uptime_start = time.time()
        
    def mark_disconnected(self):
        self.connected = False
        self.uptime_start = None
        
    def get_uptime(self) -> float:
        if self.uptime_start:
            return time.time() - self.uptime_start
        return 0.0


class KrakenConnectionManager:
    """Manages Kraken exchange connections with health monitoring."""
    
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        self.state = ConnectionState()
        self.exchange: Optional[ccxt_async.kraken] = None
        
        logger.info(f"[CONNECTION] Initialized for {'sandbox' if sandbox else 'live'}")

    
    async def connect(self) -> bool:
        """Establish connection to Kraken exchange with optimal settings."""
        try:
            # Create CCXT exchange instance with proven settings
            config = {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "enableRateLimit": True,
                "rateLimit": 2000,  # Conservative 2-second delay
                "timeout": 30000,   # 30-second timeout  
                "sandbox": self.sandbox,
                "options": {
                    "adjustForTimeDifference": True,
                    "recvWindow": 30000,
                },
            }
            
            self.exchange = ccxt_async.kraken(config)
            
            # Add delay before first API call to prevent rate limiting
            await asyncio.sleep(2.0)
            
            # Test connection with markets load
            await self.exchange.load_markets()
            await asyncio.sleep(1.5)  # Additional delay
            
            # Verify credentials with balance check
            await self.exchange.fetch_balance()
            
            self.state.mark_connected()
            logger.info("[CONNECTION] Successfully connected to Kraken")
            return True
            
        except Exception as e:
            logger.error(f"[CONNECTION] Failed to connect: {e}")
            self.state.mark_disconnected()
            return False
    
    async def disconnect(self) -> None:
        """Close exchange connection gracefully."""
        if self.exchange:
            try:
                await self.exchange.close()
                logger.info("[CONNECTION] Disconnected successfully")
            except Exception as e:
                logger.error(f"[CONNECTION] Error during disconnect: {e}")
            finally:
                self.exchange = None
                self.state.mark_disconnected()

    
    def is_connected(self) -> bool:
        """Check if exchange connection is active."""
        return self.state.connected and self.exchange is not None
    
    async def health_check(self) -> dict:
        """Perform connection health check."""
        health = {
            "connected": self.is_connected(),
            "uptime": self.state.get_uptime(),
            "exchange_online": False
        }
        
        if self.is_connected():
            try:
                # Quick health test with markets check
                if self.exchange.markets:
                    health["exchange_online"] = True
            except Exception as e:
                logger.warning(f"[HEALTH] Health check failed: {e}")
                
        return health
    
    def get_stats(self) -> dict:
        """Get connection manager statistics."""
        return {
            "connected": self.is_connected(),
            "uptime": self.state.get_uptime(),
            "sandbox": self.sandbox
        }


# Export main class
__all__ = ["KrakenConnectionManager", "ConnectionState"]
