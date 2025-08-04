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

# Import cleanup handler to ensure it's registered
from src.exchange.singleton_cleanup import cleanup_handler


class ExchangeSingleton:
    """Singleton factory for exchange instances"""
    
    _instance: Optional[Any] = None
    _lock = asyncio.Lock()
    _initialized = False
    _closing = False  # Prevent race conditions during shutdown
    
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
            # Check if we're in the process of closing
            if cls._closing:
                logger.warning("[EXCHANGE_SINGLETON] Exchange is closing, cannot create new instance")
                raise Exception("Exchange singleton is shutting down")
            
            # Return existing instance if already created and still alive
            if cls._instance is not None and cls._initialized:
                # Check if the instance is still valid
                try:
                    # Quick health check - check if session is still alive
                    if hasattr(cls._instance, 'session') and cls._instance.session and cls._instance.session.closed:
                        logger.warning("[EXCHANGE_SINGLETON] Existing instance has closed session, recreating...")
                        cls._instance = None
                        cls._initialized = False
                    else:
                        logger.debug("[EXCHANGE_SINGLETON] Returning existing exchange instance")
                        return cls._instance
                except Exception as e:
                    logger.warning(f"[EXCHANGE_SINGLETON] Health check failed: {e}, recreating...")
                    cls._instance = None
                    cls._initialized = False
                
            # Create new instance
            logger.info("[EXCHANGE_SINGLETON] Creating new exchange instance")
            
            # Determine which implementation to use - handle both flat and nested config
            use_sdk = True  # Default to SDK
            raw_config = config  # For passing to exchange
            
            if config:
                # Check if this is a nested modular config
                if 'core' in config and isinstance(config['core'], dict):
                    # Extract the raw config from core section
                    raw_config = config['core']
                    logger.info("[EXCHANGE_SINGLETON] Using core config from modular structure")
                    
                    # Now check for SDK preference in the appropriate config
                    current_config = raw_config
                    
                    # Check for use_kraken_sdk flag
                    if 'use_kraken_sdk' in current_config:
                        use_sdk = current_config['use_kraken_sdk']
                    # Check kraken section for use_official_sdk
                    elif 'kraken' in current_config and isinstance(current_config['kraken'], dict):
                        use_sdk = current_config['kraken'].get('use_official_sdk', True)
                
                logger.info(f"[EXCHANGE_SINGLETON] Configuration check: use_sdk={use_sdk}")
                
                # SDK no longer available - always use native implementation
                logger.info("[EXCHANGE_SINGLETON] Using native Kraken implementation")
                from src.exchange.native_kraken_exchange import NativeKrakenExchange
                cls._instance = NativeKrakenExchange(
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
                    
                    # Initialize data coordination if available
                    if hasattr(cls._instance, 'set_data_coordinator'):
                        logger.info("[EXCHANGE_SINGLETON] Setting up data coordination integration")
                        # Data coordinator will be set by the bot during initialization
                    
                    # Configure for optimal WebSocket/REST coordination
                    if hasattr(cls._instance, 'configure_api_optimization'):
                        cls._instance.configure_api_optimization(
                            minimize_rest_calls=True,
                            batch_operations=True,
                            smart_nonce_management=True
                        )
                        logger.info("[EXCHANGE_SINGLETON] API optimization configured")
                    
                    # Balance management is now handled by new balance system
                    logger.info("[EXCHANGE_SINGLETON] Exchange instance ready with unified data coordination")
                    
                    cls._initialized = True
            else:
                logger.debug("[EXCHANGE_SINGLETON] Returning existing exchange instance")
            
            return cls._instance
    
    @classmethod
    async def close(cls):
        """Close the singleton exchange instance"""
        async with cls._lock:
            # Set closing flag to prevent new instances
            cls._closing = True
            
            if cls._instance:
                logger.info("[EXCHANGE_SINGLETON] Closing exchange instance")
                
                try:
                    # Save nonce state before closing
                    if hasattr(cls._instance, 'nonce_manager'):
                        cls._instance.nonce_manager.force_save()
                        logger.info("[EXCHANGE_SINGLETON] Nonce state saved before closing")
                    
                    # Close WebSocket connections if they exist
                    if hasattr(cls._instance, 'client') and hasattr(cls._instance.client, 'websocket'):
                        logger.info("[EXCHANGE_SINGLETON] Closing SDK WebSocket client...")
                        if hasattr(cls._instance.client.websocket, 'stop'):
                            await cls._instance.client.websocket.stop()
                    
                    # Close the exchange
                    if hasattr(cls._instance, 'close'):
                        await cls._instance.close()
                    
                    # Close any lingering connections
                    if hasattr(cls._instance, 'session') and cls._instance.session:
                        await cls._instance.session.close()
                        
                except Exception as e:
                    logger.error(f"[EXCHANGE_SINGLETON] Error during close: {e}")
                finally:
                    # Clear the instance
                    cls._instance = None
                    cls._initialized = False
                    cls._closing = False
                
                logger.info("[EXCHANGE_SINGLETON] Exchange closed and singleton cleared")
    
    @classmethod
    def reset(cls):
        """Reset the singleton (for testing purposes)"""
        cls._instance = None
        cls._initialized = False
        cls._closing = False
        logger.info("[EXCHANGE_SINGLETON] Singleton reset")


# Convenience function
async def get_exchange(api_key: str = None, 
                      api_secret: str = None,
                      tier: str = 'starter',
                      config: Dict[str, Any] = None) -> Any:
    """Get the singleton exchange instance"""
    return await ExchangeSingleton.get_instance(api_key, api_secret, tier, config)