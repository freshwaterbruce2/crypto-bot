"""
Singleton Cleanup Handler
========================

Ensures exchange singleton is properly cleaned up on process exit.
"""

import asyncio
import atexit
import signal
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SingletonCleanupHandler:
    """Handles cleanup of the exchange singleton on process exit"""
    
    _instance: Optional['SingletonCleanupHandler'] = None
    _cleanup_registered = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._cleanup_registered:
            self._register_cleanup()
            self._cleanup_registered = True
    
    def _register_cleanup(self):
        """Register cleanup handlers for various exit scenarios"""
        # Register atexit handler for normal exit
        atexit.register(self._cleanup_sync)
        
        # Register signal handlers for abnormal exits
        for sig in [signal.SIGTERM, signal.SIGINT]:
            try:
                signal.signal(sig, self._signal_handler)
            except Exception as e:
                logger.warning(f"[CLEANUP] Could not register handler for {sig}: {e}")
        
        # Windows-specific signals
        if hasattr(signal, 'SIGBREAK'):
            try:
                signal.signal(signal.SIGBREAK, self._signal_handler)
            except Exception as e:
                logger.warning(f"[CLEANUP] Could not register SIGBREAK handler: {e}")
        
        logger.info("[CLEANUP] Singleton cleanup handlers registered")
    
    def _signal_handler(self, signum, frame):
        """Handle signals by triggering cleanup"""
        logger.info(f"[CLEANUP] Received signal {signum}, triggering cleanup...")
        self._cleanup_sync()
        # Re-raise the signal for default handling
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)
    
    def _cleanup_sync(self):
        """Synchronous cleanup wrapper"""
        try:
            # Try to get the current event loop
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop and not loop.is_closed():
                # Run the async cleanup
                if loop.is_running():
                    # Schedule the cleanup
                    asyncio.create_task(self._cleanup_async())
                else:
                    # Run the cleanup
                    loop.run_until_complete(self._cleanup_async())
            else:
                logger.warning("[CLEANUP] No event loop available for async cleanup")
                # Try synchronous cleanup as fallback
                self._cleanup_sync_fallback()
                
        except Exception as e:
            logger.error(f"[CLEANUP] Error during cleanup: {e}")
    
    async def _cleanup_async(self):
        """Async cleanup of exchange singleton"""
        try:
            from src.exchange.exchange_singleton import ExchangeSingleton
            await ExchangeSingleton.close()
            logger.info("[CLEANUP] Exchange singleton cleaned up successfully")
        except Exception as e:
            logger.error(f"[CLEANUP] Error cleaning up exchange singleton: {e}")
    
    def _cleanup_sync_fallback(self):
        """Synchronous fallback cleanup"""
        try:
            from src.exchange.exchange_singleton import ExchangeSingleton
            # Reset the singleton state at minimum
            ExchangeSingleton.reset()
            logger.info("[CLEANUP] Exchange singleton reset (sync fallback)")
        except Exception as e:
            logger.error(f"[CLEANUP] Error in sync fallback cleanup: {e}")


# Create the global instance
cleanup_handler = SingletonCleanupHandler()
