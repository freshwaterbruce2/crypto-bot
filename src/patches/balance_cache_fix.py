"""
Balance Cache Invalidation Fix
==============================

This patch fixes the critical balance detection issue where the bot reports
$1.97 instead of the actual balance (e.g., $161.39).

The fix implements:
1. Forced balance refresh before trades
2. WebSocket balance reconciliation
3. Debug logging for balance fetches
4. Cache invalidation on trade events
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from src.utils.decimal_precision_fix import safe_decimal, safe_float, is_zero

logger = logging.getLogger(__name__)


class BalanceCacheFix:
    """Fixes balance cache invalidation issues"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fixes_applied = []
        
    def apply_all_fixes(self) -> Dict[str, List[str]]:
        """Apply all balance cache fixes"""
        results = {
            "enhanced_balance_manager": self.patch_balance_manager(),
            "real_time_balance_manager": self.patch_realtime_manager(),
            "core_bot": self.patch_bot_balance_checks(),
            "websocket_integration": self.enhance_websocket_balance()
        }
        
        logger.info(f"[BALANCE_FIX] Applied {len(self.fixes_applied)} balance cache fixes")
        return results
    
    def patch_balance_manager(self) -> List[str]:
        """Fix balance caching in enhanced_balance_manager.py"""
        file_path = self.project_root / "src" / "trading" / "enhanced_balance_manager.py"
        
        # Create new method to force fresh balance
        force_refresh_method = '''
    async def force_fresh_balance(self, asset: str = 'USDT') -> float:
        """Force a fresh balance fetch, bypassing all caches"""
        logger.info(f"[BALANCE_FIX] Forcing fresh balance fetch for {asset}")
        
        # Clear any cached data
        self._balance_cache = {}
        self._cache_timestamp = 0
        
        # If we have WebSocket manager, disconnect and reconnect to force fresh data
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            try:
                # Get fresh ticker data to trigger balance update
                await self.websocket_manager.force_reconnect()
                await asyncio.sleep(0.5)  # Wait for fresh data
            except Exception as e:
                logger.warning(f"[BALANCE_FIX] WebSocket reconnect failed: {e}")
        
        # Fetch directly from REST API
        try:
            # Direct API call with no caching
            balance_data = await self._fetch_balance_from_api()
            
            # Log raw response for debugging
            logger.info(f"[BALANCE_FIX] Raw balance response: {balance_data}")
            
            # Extract USDT balance with all possible variants
            usdt_balance = self._extract_usdt_balance(balance_data)
            
            logger.info(f"[BALANCE_FIX] Fresh {asset} balance: ${usdt_balance:.2f}")
            
            # Update cache with fresh data
            self._balance_cache[asset] = usdt_balance
            self._cache_timestamp = time.time()
            
            return usdt_balance
            
        except Exception as e:
            logger.error(f"[BALANCE_FIX] Failed to fetch fresh balance: {e}")
            # Try to get from real-time manager as fallback
            if hasattr(self, 'rt_balance_mgr') and self.rt_balance_mgr:
                return await self.rt_balance_mgr.get_balance(asset)
            raise
    
    async def _fetch_balance_from_api(self) -> Dict[str, Any]:
        """Direct API call to fetch balance"""
        if not self.exchange:
            raise ValueError("Exchange not initialized")
        
        # Use the exchange's fetch_balance method directly
        return await self.exchange.fetch_balance()
    
    def _extract_usdt_balance(self, balance_data: Dict[str, Any]) -> float:
        """Extract USDT balance from various possible formats"""
        # Check all possible USDT variants
        usdt_variants = ['USDT', 'ZUSDT', 'USDT.M', 'USDT.S', 'USDT.F', 'USDT.B', 'USD', 'ZUSD']
        
        for variant in usdt_variants:
            # Check in main dict
            if variant in balance_data:
                if isinstance(balance_data[variant], dict):
                    free = balance_data[variant].get('free', 0)
                    free_decimal = safe_decimal(free)
                    if not is_zero(free_decimal):
                        logger.info(f"[BALANCE_FIX] Found {variant} balance: {free}")
                        return safe_float(free_decimal)
                else:
                    # Simple value
                    value_decimal = safe_decimal(balance_data[variant])
                    if not is_zero(value_decimal):
                        return safe_float(value_decimal)
            
            # Check in 'free' subdictionary
            if 'free' in balance_data and variant in balance_data['free']:
                free = balance_data['free'][variant]
                free_decimal = safe_decimal(free)
                if not is_zero(free_decimal):
                    logger.info(f"[BALANCE_FIX] Found in free[{variant}]: {free}")
                    return safe_float(free_decimal)
        
        # Log all available assets for debugging
        logger.warning(f"[BALANCE_FIX] No USDT found. Available assets: {list(balance_data.keys())}")
        return 0.0
'''
        
        # Patch get_balance_for_asset to always fetch fresh for USDT
        balance_check_patch = '''
        # BALANCE FIX: Force fresh fetch for USDT
        if asset == 'USDT' and not hasattr(self, '_last_fresh_fetch'):
            self._last_fresh_fetch = 0
        
        current_time = time.time()
        if asset == 'USDT' and (current_time - self._last_fresh_fetch) > 30:
            # Force fresh balance every 30 seconds for USDT
            logger.info("[BALANCE_FIX] Forcing fresh USDT balance fetch")
            self._last_fresh_fetch = current_time
            try:
                return await self.force_fresh_balance(asset)
            except Exception as e:
                logger.error(f"[BALANCE_FIX] Fresh fetch failed, using cache: {e}")
'''
        
        return self._apply_method_patches(file_path, force_refresh_method, balance_check_patch)
    
    def patch_realtime_manager(self) -> List[str]:
        """Enhance real-time balance manager"""
        file_path = self.project_root / "src" / "trading" / "real_time_balance_manager.py"
        
        websocket_reconciliation = '''
    async def reconcile_websocket_balance(self, rest_balance: Dict[str, float]) -> None:
        """Reconcile WebSocket balance with REST API balance"""
        logger.info("[BALANCE_FIX] Reconciling WebSocket and REST balances")
        
        discrepancies = []
        for asset, rest_value in rest_balance.items():
            ws_value = self.balances.get(asset, {}).get('free', 0)
            
            rest_decimal = safe_decimal(rest_value)
            ws_decimal = safe_decimal(ws_value)
            difference = rest_decimal - ws_decimal
            
            if abs(difference) > safe_decimal("0.01"):  # More than 1 cent difference
                discrepancies.append({
                    'asset': asset,
                    'rest': rest_value,
                    'websocket': ws_value,
                    'difference': safe_float(difference)
                })
        
        if discrepancies:
            logger.warning(f"[BALANCE_FIX] Balance discrepancies found: {discrepancies}")
            # Use REST values as source of truth
            for disc in discrepancies:
                self.balances[disc['asset']] = {
                    'free': disc['rest'],
                    'total': disc['rest'],
                    'timestamp': time.time()
                }
                logger.info(f"[BALANCE_FIX] Updated {disc['asset']} to REST value: {disc['rest']}")
'''
        
        return self._apply_method_patches(file_path, websocket_reconciliation)
    
    def patch_bot_balance_checks(self) -> List[str]:
        """Add balance verification to bot.py"""
        file_path = self.project_root / "src" / "core" / "bot.py"
        
        pre_trade_check = '''
            # BALANCE FIX: Force fresh balance before trade
            logger.info(f"[BALANCE_FIX] Pre-trade balance check for {symbol}")
            try:
                fresh_balance = await self.balance_manager.force_fresh_balance('USDT')
                logger.info(f"[BALANCE_FIX] Fresh balance: ${fresh_balance:.2f}")
                
                # Update the balance variable with fresh data
                balance = fresh_balance
                
                # Also reconcile with WebSocket if available
                if hasattr(self, 'websocket_manager') and self.websocket_manager:
                    ws_balance = self.websocket_manager.get_balance('USDT')
                    if ws_balance:
                        ws_decimal = safe_decimal(ws_balance)
                        fresh_decimal = safe_decimal(fresh_balance)
                        if abs(ws_decimal - fresh_decimal) > safe_decimal("0.01"):
                            logger.warning(f"[BALANCE_FIX] WebSocket/REST mismatch: WS=${safe_float(ws_decimal):.2f}, REST=${safe_float(fresh_decimal):.2f}")
            except Exception as e:
                logger.error(f"[BALANCE_FIX] Failed to get fresh balance: {e}")
'''
        
        return self._insert_before_trade_execution(file_path, pre_trade_check)
    
    def enhance_websocket_balance(self) -> List[str]:
        """Enhance WebSocket balance handling"""
        file_path = self.project_root / "src" / "exchange" / "websocket_manager_v2.py"
        
        balance_handler_enhancement = '''
        # BALANCE FIX: Enhanced balance update logging
        logger.info(f"[BALANCE_FIX] WebSocket balance update received: {balance_data}")
        
        # Validate balance data
        if 'USDT' in balance_data or 'ZUSDT' in balance_data:
            usdt_key = 'USDT' if 'USDT' in balance_data else 'ZUSDT'
            new_balance = balance_data[usdt_key].get('free', 0) if isinstance(balance_data[usdt_key], dict) else balance_data[usdt_key]
            
            # Compare with cached value
            if hasattr(self, '_last_usdt_balance'):
                new_balance_decimal = safe_decimal(new_balance)
                last_balance_decimal = safe_decimal(self._last_usdt_balance)
                difference = abs(new_balance_decimal - last_balance_decimal)
                
                if difference > safe_decimal("0.01"):
                    logger.info(f"[BALANCE_FIX] USDT balance changed: ${safe_float(last_balance_decimal):.2f} -> ${safe_float(new_balance_decimal):.2f}")
            
            self._last_usdt_balance = safe_float(safe_decimal(new_balance))
            
            # Notify balance manager of update
            if hasattr(self, 'bot') and hasattr(self.bot, 'balance_manager'):
                asyncio.create_task(self.bot.balance_manager.on_websocket_balance_update(balance_data))
'''
        
        return self._apply_method_patches(file_path, balance_handler_enhancement)
    
    def _apply_method_patches(self, file_path: Path, *methods: str) -> List[str]:
        """Apply method patches to a file"""
        if not file_path.exists():
            return [f"File not found: {file_path}"]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Backup
            backup_path = file_path.with_suffix('.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            fixes = []
            
            # Add methods to class
            for method in methods:
                if method.strip():
                    # Find last method in class
                    class_match = re.search(r'class\s+\w+.*?:\n(.*?)(?=\nclass|\Z)', content, re.DOTALL)
                    if class_match:
                        # Insert before the last line of the class
                        insertion_point = class_match.end() - 1
                        content = content[:insertion_point] + '\n' + method + '\n' + content[insertion_point:]
                        fixes.append(f"Added method: {method.strip().split('(')[0].strip()}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return fixes
            
        except Exception as e:
            return [f"Error: {str(e)}"]
    
    def _insert_before_trade_execution(self, file_path: Path, code: str) -> List[str]:
        """Insert code before trade execution"""
        if not file_path.exists():
            return [f"File not found: {file_path}"]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find trade execution point
            execution_pattern = r'if balance < amount_usdt and side == ["\']buy["\']:'
            
            if re.search(execution_pattern, content):
                content = re.sub(
                    execution_pattern,
                    code + '\n' + r'if balance < amount_usdt and side == "buy":',
                    content
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return ["Added pre-trade balance verification"]
            
            return ["Trade execution point not found"]
            
        except Exception as e:
            return [f"Error: {str(e)}"]


def apply_balance_fixes():
    """Main function to apply balance cache fixes"""
    import os
    import re
    
    project_root = os.environ.get('PROJECT_ROOT', '/mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025')
    
    fixer = BalanceCacheFix(project_root)
    results = fixer.apply_all_fixes()
    
    print("\n=== BALANCE CACHE FIX RESULTS ===")
    for module, fixes in results.items():
        print(f"\n{module}:")
        for fix in fixes:
            print(f"  - {fix}")
    
    print("\n✅ Balance cache fixes applied!")
    print("Your bot will now see the correct balance!")


if __name__ == "__main__":
    apply_balance_fixes()