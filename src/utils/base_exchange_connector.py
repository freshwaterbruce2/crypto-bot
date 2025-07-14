"""
Base Exchange Connector
Unified connection handling for all exchange implementations
"""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseExchangeConnector(ABC):
    """Base class for all exchange connectors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the exchange"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the exchange"""
        pass
    
    async def ensure_connection(self) -> bool:
        """Ensure we have a valid connection"""
        if not self.is_connected:
            return await self.connect()
        return True
    
    def _handle_connection_error(self, error: Exception) -> bool:
        """Handle connection errors with retry logic"""
        self.connection_attempts += 1
        logger.error(f"Connection error (attempt {self.connection_attempts}): {error}")
        
        if self.connection_attempts >= self.max_connection_attempts:
            logger.error("Max connection attempts reached")
            return False
        
        return True
    
    def reset_connection_state(self):
        """Reset connection state for retry"""
        self.is_connected = False
        self.connection_attempts = 0


class KrakenConnector(BaseExchangeConnector):
    """Kraken-specific exchange connector"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.client = None
    
    async def connect(self) -> bool:
        """Connect to Kraken exchange"""
        try:
            if not self.api_key or not self.api_secret:
                logger.error("Missing Kraken API credentials")
                return False
            
            # Initialize Kraken client here
            # This is a placeholder - actual implementation would use the appropriate Kraken SDK
            self.is_connected = True
            self.connection_attempts = 0
            logger.info("Successfully connected to Kraken")
            return True
            
        except Exception as e:
            return self._handle_connection_error(e)
    
    async def disconnect(self) -> bool:
        """Disconnect from Kraken"""
        try:
            if self.client:
                # Close connection
                pass
            
            self.is_connected = False
            logger.info("Disconnected from Kraken")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Kraken: {e}")
            return False
