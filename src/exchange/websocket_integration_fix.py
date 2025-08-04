"""
WebSocket Integration Fix - Repairs nonce and authentication issues
"""

import logging
import time
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


async def fix_invalid_nonce_errors(bot_instance) -> bool:
    """Fix invalid nonce errors by resetting nonce managers and clearing auth state"""
    try:
        logger.info("[WEBSOCKET_FIX] Starting invalid nonce error repair...")
        
        # 1. Reset nonce managers with fresh timestamps
        if hasattr(bot_instance, 'exchange') and bot_instance.exchange:
            exchange = bot_instance.exchange
            
            # Force reset unified nonce manager with recovery
            if hasattr(exchange, 'nonce_manager') and exchange.nonce_manager:
                # Use the unified manager's recovery method
                exchange.nonce_manager.handle_invalid_nonce_error("websocket_fix")
                logger.info("[WEBSOCKET_FIX] Triggered nonce recovery in unified manager")
            
            # Clear any cached authentication state
            if hasattr(exchange, '_auth_headers'):
                exchange._auth_headers = {}
                logger.info("[WEBSOCKET_FIX] Cleared cached auth headers")
            
            # Reset any API session state
            if hasattr(exchange, 'api_session') and exchange.api_session:
                try:
                    await exchange.api_session.close()
                    exchange.api_session = None
                    logger.info("[WEBSOCKET_FIX] Reset API session")
                except Exception as e:
                    logger.warning(f"[WEBSOCKET_FIX] Error closing API session: {e}")
        
        # 2. Force save unified nonce manager state
        try:
            from src.utils.unified_kraken_nonce_manager import get_unified_nonce_manager
            manager = get_unified_nonce_manager()
            manager.force_save()
            logger.info("[WEBSOCKET_FIX] Forced save of unified nonce manager state")
        except Exception as e:
            logger.warning(f"[WEBSOCKET_FIX] Error saving nonce state: {e}")
        
        # 3. Force garbage collection to clear any lingering state
        import gc
        gc.collect()
        
        logger.info("[WEBSOCKET_FIX] Invalid nonce error repair completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"[WEBSOCKET_FIX] Error during nonce fix: {e}")
        return False


async def apply_deferred_balance_integration(bot_instance) -> bool:
    """Apply deferred balance integration after balance manager is initialized"""
    try:
        logger.info("[WEBSOCKET_FIX] Applying deferred balance integration...")
        
        # Ensure balance manager is properly initialized
        if hasattr(bot_instance, 'balance_manager') and bot_instance.balance_manager:
            balance_manager = bot_instance.balance_manager
            
            # Force refresh balance cache
            if hasattr(balance_manager, 'force_refresh'):
                await balance_manager.force_refresh()
                logger.info("[WEBSOCKET_FIX] Forced balance cache refresh")
            
            # Reset any balance synchronization state
            if hasattr(balance_manager, 'reset_sync_state'):
                balance_manager.reset_sync_state()
                logger.info("[WEBSOCKET_FIX] Reset balance sync state")
        
        # Ensure WebSocket V2 is properly initialized
        if hasattr(bot_instance, 'websocket_manager') and bot_instance.websocket_manager:
            ws_manager = bot_instance.websocket_manager
            
            # Reset connection state if needed
            if hasattr(ws_manager, 'reset_connection_state'):
                ws_manager.reset_connection_state()
                logger.info("[WEBSOCKET_FIX] Reset WebSocket connection state")
        
        logger.info("[WEBSOCKET_FIX] Deferred balance integration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"[WEBSOCKET_FIX] Error during deferred balance integration: {e}")
        return False


def force_nonce_reset_for_api_key(api_key: str, buffer_minutes: int = 5) -> bool:
    """Force reset nonce using unified manager's recovery mechanism"""
    try:
        from src.utils.unified_kraken_nonce_manager import get_unified_nonce_manager
        
        manager = get_unified_nonce_manager()
        # Trigger recovery which adds 60 second buffer automatically
        manager.handle_invalid_nonce_error("websocket_fix_manual")
        
        logger.info(f"[WEBSOCKET_FIX] Triggered nonce recovery with automatic buffer")
        return True
        
    except Exception as e:
        logger.error(f"[WEBSOCKET_FIX] Error force resetting nonce: {e}")
        return False


def clear_all_authentication_caches() -> bool:
    """Clear all authentication caches and state"""
    try:
        import os
        
        # Find and remove old nonce state files
        base_dir = os.path.dirname(os.path.dirname(__file__))
        for file in os.listdir(base_dir):
            if file.startswith('nonce_state_') and file.endswith('.json'):
                try:
                    os.remove(os.path.join(base_dir, file))
                    logger.info(f"[WEBSOCKET_FIX] Removed old nonce state file: {file}")
                except Exception as e:
                    logger.warning(f"[WEBSOCKET_FIX] Could not remove {file}: {e}")
        
        # Clear Python cache files
        import shutil
        cache_dirs = [
            os.path.join(base_dir, 'src', 'utils', '__pycache__'),
            os.path.join(base_dir, 'src', 'exchange', '__pycache__'),
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                    logger.info(f"[WEBSOCKET_FIX] Cleared cache directory: {cache_dir}")
                except Exception as e:
                    logger.warning(f"[WEBSOCKET_FIX] Could not clear cache {cache_dir}: {e}")
        
        logger.info("[WEBSOCKET_FIX] Authentication cache clearing completed")
        return True
        
    except Exception as e:
        logger.error(f"[WEBSOCKET_FIX] Error clearing authentication caches: {e}")
        return False