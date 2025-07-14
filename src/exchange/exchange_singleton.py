"""
Exchange Singleton Factory
=========================

Ensures only one exchange instance exists across the entire application.
This prevents connection pool exhaustion and nonce conflicts.
"""

import asyncio
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ExchangeSingleton:
    """Singleton factory for exchange instances"""
    
    _instance: Optional[Any] = None
    _lock = asyncio.Lock()
    _initialized = False
    
    @classmethod
    async def get_instance(cls, 
                          api_key: str = None, 
                          api_secret: str = None,
                          tier: str = 'starter',
                          config: Dict[str, Any] = None) -> Any:
        """
        Get or create the singleton exchange instance.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
            tier: API tier (starter, intermediate, pro)
            config: Bot configuration
            
        Returns:
            The singleton exchange instance
        """
        async with cls._lock:
            if cls._instance is None:
                logger.info("[EXCHANGE_SINGLETON] Creating new exchange instance")
                
                # Determine which implementation to use
                use_sdk = config.get('use_kraken_sdk', True) if config else True
                
                if use_sdk:
                    logger.info("[EXCHANGE_SINGLETON] Using Kraken SDK implementation")
                    from src.exchange.kraken_sdk_exchange import KrakenSDKExchange
                    cls._instance = KrakenSDKExchange(
                        api_key=api_key,
                        api_secret=api_secret,
                        tier=tier
                    )
                else:
                    logger.info("[EXCHANGE_SINGLETON] Using native implementation")
                    from src.exchange.kraken_exchange import KrakenExchange
                    cls._instance = KrakenExchange(
                        api_key=api_key,
                        api_secret=api_secret,
                        tier=tier
                    )
                
                # Configure connection pool
                if hasattr(cls._instance, 'configure_connection_pool'):
                    cls._instance.configure_connection_pool(
                        max_connections=5,  # Limit to prevent exhaustion
                        max_keepalive_connections=3
                    )
                    logger.info("[EXCHANGE_SINGLETON] Configured connection pool limits")
                
                # Initialize only once
                if not cls._initialized:
                    if not await cls._instance.connect():
                        raise Exception("Failed to connect to Kraken exchange")
                    
                    logger.info("[EXCHANGE_SINGLETON] Exchange connected successfully")
                    
                    # Load markets
                    await cls._instance.load_markets()
                    logger.info(f"[EXCHANGE_SINGLETON] Loaded {len(cls._instance.markets)} markets")
                    
                    # Apply balance fix wrapper
                    from src.exchange.balance_fix_wrapper import apply_balance_fix
                    cls._instance = apply_balance_fix(cls._instance)
                    logger.info("[EXCHANGE_SINGLETON] Applied balance detection fix")
                    
                    cls._initialized = True
            else:
                logger.debug("[EXCHANGE_SINGLETON] Returning existing exchange instance")
            
            return cls._instance
    
    @classmethod
    async def close(cls):
        """Close the singleton exchange instance"""
        async with cls._lock:
            if cls._instance:
                logger.info("[EXCHANGE_SINGLETON] Closing exchange instance")
                if hasattr(cls._instance, 'close'):
                    await cls._instance.close()
                cls._instance = None
                cls._initialized = False
    
    @classmethod
    def reset(cls):
        """Reset the singleton (for testing purposes)"""
        cls._instance = None
        cls._initialized = False
        logger.info("[EXCHANGE_SINGLETON] Singleton reset")


# Convenience function
async def get_exchange(api_key: str = None, 
                      api_secret: str = None,
                      tier: str = 'starter',
                      config: Dict[str, Any] = None) -> Any:
    """Get the singleton exchange instance"""
    return await ExchangeSingleton.get_instance(api_key, api_secret, tier, config)