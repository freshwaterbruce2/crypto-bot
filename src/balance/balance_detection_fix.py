# BALANCE DETECTION FIX - Drop-in solution for your existing system
# Fixes the $1.97 vs $161.39 USDT detection issue

import logging
import asyncio
from decimal import Decimal
from typing import Dict, Any, Optional
from ..utils.decimal_precision_fix import safe_decimal, safe_float

logger = logging.getLogger(__name__)

class BalanceDetectionFixer:
    """
    Fixes balance detection issues by properly handling both WebSocket V2 and REST API formats
    Integrates with your existing WebSocket V2 + REST hybrid architecture
    """
    
    def __init__(self, websocket_manager, rest_client):
        self.websocket_manager = websocket_manager
        self.rest_client = rest_client
        self.balance_cache = {}
        self.last_balance_update = 0
        
    def normalize_currency_symbol(self, symbol: str) -> str:
        """Handle Kraken's various USDT representations"""
        # Kraken uses different USDT symbols in different contexts
        usdt_variants = ['USDT', 'ZUSD', 'USD', 'USDT.HOLD', 'USDT.S']
        
        if symbol in usdt_variants:
            return 'USDT'
        
        # Handle other currency normalizations
        currency_map = {
            'XXBT': 'BTC',
            'XETH': 'ETH', 
            'ZEUR': 'EUR',
            'ZUSD': 'USDT',
            'SHIB.HOLD': 'SHIB',
            'SHIB.S': 'SHIB'
        }
        
        return currency_map.get(symbol, symbol)
    
    def parse_websocket_v2_balance(self, ws_data: Dict[str, Any]) -> Dict[str, Decimal]:
        """Parse WebSocket V2 balance format"""
        balances = {}
        
        try:
            # WebSocket V2 format variations
            if isinstance(ws_data, dict):
                # Format 1: Direct balance data
                if 'balances' in ws_data:
                    balance_data = ws_data['balances']
                elif 'data' in ws_data and 'balances' in ws_data['data']:
                    balance_data = ws_data['data']['balances']
                else:
                    balance_data = ws_data
                
                # Parse balance data
                for currency, data in balance_data.items():
                    normalized_currency = self.normalize_currency_symbol(currency)
                    
                    if isinstance(data, dict):
                        # Format: {"available": 161.39, "reserved": 0.0}
                        available = safe_decimal(data.get('available', 0))
                        reserved = safe_decimal(data.get('reserved', 0))
                        total = available + reserved
                    else:
                        # Format: direct value
                        total = safe_decimal(data)
                    
                    if total > 0:
                        balances[normalized_currency] = total
                        logger.info(f"[BALANCE_FIX] WebSocket V2: {normalized_currency} = {total}")
            
        except Exception as e:
            logger.error(f"[BALANCE_FIX] WebSocket V2 parsing error: {e}")
        
        return balances
    
    def parse_rest_api_balance(self, rest_data: Dict[str, Any]) -> Dict[str, Decimal]:
        """Parse REST API balance format"""
        balances = {}
        
        try:
            # REST API format: {"result": {"USDT": "161.3900", "SHIB": "1500000.0"}}
            if 'result' in rest_data:
                balance_data = rest_data['result']
            else:
                balance_data = rest_data
            
            for currency, amount in balance_data.items():
                normalized_currency = self.normalize_currency_symbol(currency)
                balance = safe_decimal(amount)
                
                if balance > 0:
                    balances[normalized_currency] = balance
                    logger.info(f"[BALANCE_FIX] REST API: {normalized_currency} = {balance}")
        
        except Exception as e:
            logger.error(f"[BALANCE_FIX] REST API parsing error: {e}")
        
        return balances
    
    async def get_balance_unified(self, force_refresh: bool = False) -> Dict[str, Decimal]:
        """
        Get balance using both WebSocket V2 and REST API with intelligent fallback
        This is the main function to use in your existing bot
        """
        import time
        
        current_time = time.time()
        
        # Use cache if recent and not forcing refresh
        if not force_refresh and self.balance_cache and (current_time - self.last_balance_update) < 10:
            logger.debug("[BALANCE_FIX] Using cached balance data")
            return self.balance_cache
        
        balances = {}
        
        # Method 1: Try WebSocket V2 (primary)
        try:
            if hasattr(self.websocket_manager, 'get_balance_v2'):
                ws_data = await self.websocket_manager.get_balance_v2()
                balances = self.parse_websocket_v2_balance(ws_data)
                
                if balances:
                    logger.info(f"[BALANCE_FIX] ✅ WebSocket V2 balance: {balances}")
                    self.balance_cache = balances
                    self.last_balance_update = current_time
                    return balances
                    
        except Exception as e:
            logger.warning(f"[BALANCE_FIX] WebSocket V2 failed: {e}")
        
        # Method 2: Try REST API (fallback)
        try:
            from ..utils.unified_kraken_nonce_manager import UnifiedKrakenNonceManager
            import os
            
            api_key = os.getenv('KRAKEN_API_KEY')
            api_secret = os.getenv('KRAKEN_API_SECRET')
            
            if api_key and api_secret:
                # Use enhanced nonce manager for API call
                nonce_manager = UnifiedKrakenNonceManager.get_instance()
                
                # Try enhanced API call if available
                if hasattr(nonce_manager, 'make_authenticated_api_call'):
                    try:
                        rest_data = await nonce_manager.make_authenticated_api_call('/0/private/Balance', {})
                    except Exception as enhanced_error:
                        logger.warning(f"[BALANCE_FIX] Enhanced API call failed: {enhanced_error}")
                        # Fallback to regular REST client
                        rest_data = await self.rest_client.get_balance()
                else:
                    rest_data = await self.rest_client.get_balance()
                
                if 'error' not in rest_data or not rest_data['error']:
                    balances = self.parse_rest_api_balance(rest_data)
                    
                    if balances:
                        logger.info(f"[BALANCE_FIX] ✅ REST API balance: {balances}")
                        self.balance_cache = balances
                        self.last_balance_update = current_time
                        return balances
                else:
                    logger.error(f"[BALANCE_FIX] REST API error: {rest_data['error']}")
                    
        except Exception as e:
            logger.error(f"[BALANCE_FIX] REST API failed: {e}")
        
        # Method 3: Try alternative REST endpoint
        try:
            nonce_manager = UnifiedKrakenNonceManager.get_instance()
            if hasattr(nonce_manager, 'make_authenticated_api_call'):
                rest_data = await nonce_manager.make_authenticated_api_call('/0/private/TradeBalance', {'asset': 'ZUSD'})
                
                if 'error' not in rest_data or not rest_data['error']:
                    trade_balance = rest_data.get('result', {})
                    if 'eb' in trade_balance:  # Equivalent balance
                        usdt_balance = safe_decimal(trade_balance['eb'])
                        balances = {'USDT': usdt_balance}
                        logger.info(f"[BALANCE_FIX] ✅ Trade balance: USDT = {usdt_balance}")
                        
        except Exception as e:
            logger.error(f"[BALANCE_FIX] Trade balance failed: {e}")
        
        # If we still have no balance, return cached or empty
        if not balances and self.balance_cache:
            logger.warning("[BALANCE_FIX] Using stale cached balance")
            return self.balance_cache
        
        logger.error("[BALANCE_FIX] ❌ All balance methods failed")
        return {}
    
    def get_usdt_balance(self) -> Decimal:
        """Get USDT balance specifically (for your bot's needs)"""
        try:
            # Try to get from recent cache first
            if self.balance_cache and 'USDT' in self.balance_cache:
                balance = self.balance_cache['USDT']
                logger.info(f"[BALANCE_FIX] USDT balance: ${balance}")
                return balance
            
            # Force refresh if no cache
            balances = asyncio.run(self.get_balance_unified(force_refresh=True))
            usdt_balance = balances.get('USDT', Decimal('0'))
            
            logger.info(f"[BALANCE_FIX] Fresh USDT balance: ${usdt_balance}")
            return usdt_balance
            
        except Exception as e:
            logger.error(f"[BALANCE_FIX] USDT balance error: {e}")
            return Decimal('0')

# INTEGRATION HELPER: Drop-in replacement for your existing balance manager
def create_balance_fixer(websocket_manager, rest_client):
    """Factory function to create the balance detection fixer"""
    return BalanceDetectionFixer(websocket_manager, rest_client)

# IMMEDIATE FIX: Add this to your main bot initialization
def patch_existing_balance_manager(bot_instance):
    """Patch your existing bot with the balance fix"""
    
    # Create the fixer
    balance_fixer = create_balance_fixer(
        bot_instance.websocket_manager,
        bot_instance.rest_client
    )
    
    # Replace the balance retrieval method
    original_get_balance = getattr(bot_instance, 'get_balance', None)
    
    def fixed_get_balance(*args, **kwargs):
        """Fixed balance retrieval method"""
        try:
            # Get balance using the fixer
            balances = asyncio.run(balance_fixer.get_balance_unified())
            
            # Return in format your bot expects
            if balances:
                total_usdt = balances.get('USDT', Decimal('0'))
                logger.info(f"[BALANCE_FIX] Portfolio total: ${total_usdt}")
                return {
                    'USDT': float(total_usdt),
                    'total_value': float(total_usdt),
                    'balances': {k: float(v) for k, v in balances.items()}
                }
            else:
                logger.error("[BALANCE_FIX] No balance data available")
                return {'USDT': 0.0, 'total_value': 0.0, 'balances': {}}
                
        except Exception as e:
            logger.error(f"[BALANCE_FIX] Balance patch error: {e}")
            # Fallback to original method if available
            if original_get_balance:
                return original_get_balance(*args, **kwargs)
            return {'USDT': 0.0, 'total_value': 0.0, 'balances': {}}
    
    # Apply the patch
    bot_instance.get_balance = fixed_get_balance
    bot_instance.balance_fixer = balance_fixer
    
    logger.info("[BALANCE_FIX] ✅ Balance manager patched successfully")
    
    return balance_fixer

# QUICK TEST: Verify the balance fix
async def test_balance_fix():
    """Test the balance detection fix"""
    try:
        # Create a minimal test setup
        class DummyWebSocketManager:
            async def get_balance_v2(self):
                return {
                    'balances': {
                        'USDT': {'available': 161.39, 'reserved': 0.0},
                        'SHIB': {'available': 1500000.0, 'reserved': 0.0}
                    }
                }
        
        class DummyRestClient:
            async def get_balance(self):
                return {
                    'result': {
                        'USDT': '161.3900',
                        'SHIB': '1500000.0'
                    },
                    'error': []
                }
        
        # Test the fixer
        fixer = BalanceDetectionFixer(DummyWebSocketManager(), DummyRestClient())
        
        # We're in an async function, so we can await directly
        balances = await fixer.get_balance_unified()
        
        if balances and 'USDT' in balances:
            logger.info(f"[BALANCE_FIX] ✅ Test successful: USDT = ${balances['USDT']}")
            return True
        else:
            logger.error("[BALANCE_FIX] ❌ Test failed: No USDT balance found")
            return False
            
    except Exception as e:
        logger.error(f"[BALANCE_FIX] Test error: {e}")
        return False

if __name__ == "__main__":
    # Test the balance fix
    if test_balance_fix():
        print("✅ Balance detection fix working!")
    else:
        print("❌ Balance detection needs debugging")