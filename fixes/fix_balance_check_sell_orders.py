#!/usr/bin/env python3
"""
Fix for balance check issue in sell orders
Problem: get_balance_for_asset returns 0 even when balance exists
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BalanceCheckFix:
    """Fix for balance checking issue in enhanced_trade_executor"""
    
    @staticmethod
    def diagnose_issue(log_output: str) -> Dict[str, Any]:
        """Diagnose the balance check issue from logs"""
        issues = []
        
        # Check 1: Balance exists in manager but returns 0
        if "Found ALGO in balances: 113.40765552" in log_output and "No ALGO balance to sell" in log_output:
            issues.append({
                'issue': 'Balance exists but get_balance_for_asset returns 0',
                'severity': 'CRITICAL',
                'details': 'The balance manager has the balance but it\'s not being returned properly'
            })
        
        # Check 2: Missing execution logs
        if "[EXECUTION] Trying ALGO balance" not in log_output:
            issues.append({
                'issue': 'Balance check loop not executing properly',
                'severity': 'HIGH',
                'details': 'The asset_balance is already 0 before the loop starts'
            })
        
        return {
            'issues': issues,
            'root_cause': 'The get_balance_for_asset method is not properly returning the balance value'
        }
    
    @staticmethod
    def generate_fix() -> str:
        """Generate the code fix for the balance check issue"""
        return '''
# Fix for enhanced_trade_executor_with_assistants.py around line 312-340

# Replace the balance checking section with:
if self.balance_manager:
    # Try multiple asset code variants to handle Kraken normalization issues
    asset_variants = _get_kraken_asset_variants(base_asset)
    
    # Initialize asset_balance properly
    asset_balance = 0.0
    
    for variant in asset_variants:
        try:
            # Get the balance - ensure we handle the return value properly
            balance_result = await self.balance_manager.get_balance_for_asset(variant)
            
            # Handle different return types
            if isinstance(balance_result, dict):
                asset_balance = float(balance_result.get('free', 0))
            elif isinstance(balance_result, (int, float)):
                asset_balance = float(balance_result)
            else:
                asset_balance = 0.0
            
            logger.info(f"[EXECUTION] Trying {variant} balance for {base_asset}: {asset_balance:.8f}")
            
            if asset_balance > 0:
                logger.info(f"[EXECUTION] Found {base_asset} balance using variant {variant}: {asset_balance:.8f}")
                break
        except Exception as e:
            logger.error(f"[EXECUTION] Error getting balance for {variant}: {e}")
            continue
    else:
        # Additional debug: Check all balances to see what assets are actually available
        try:
            all_balances = await self.balance_manager.get_all_balances()
            available_assets = [k for k, v in all_balances.items() if isinstance(v, (int, float)) and v > 0]
            logger.error(f"[EXECUTION] No {base_asset} balance found. Available assets: {available_assets}")
            
            # Try direct lookup in available assets
            for asset_key in available_assets:
                if asset_key.upper().endswith(base_asset.upper()) or base_asset.upper() in asset_key.upper():
                    asset_balance = safe_float(safe_decimal(all_balances[asset_key]))
                    logger.info(f"[EXECUTION] Found matching asset {asset_key} with balance: {asset_balance:.8f}")
                    break
        except Exception as e:
            logger.error(f"[EXECUTION] Error checking available balances: {e}")
'''

    @staticmethod
    def additional_fix_for_balance_manager() -> str:
        """Fix for the balance manager get_balance_for_asset method"""
        return '''
# Fix for unified_balance_manager.py get_balance_for_asset method

async def get_balance_for_asset(self, asset: str) -> float:
    """Get balance for specific asset with Kraken normalization support"""
    try:
        # DEBUG: Log the actual balance structure
        logger.info(f"[UBM] get_balance_for_asset({asset}) - balances keys: {list(self.balances.keys())}")
        if asset in self.balances:
            logger.info(f"[UBM] Found {asset} in balances: {self.balances[asset]} (type: {type(self.balances[asset])})")
        
        # First try the asset as-is
        balance = await self.get_balance(asset)
        logger.info(f"[UBM] get_balance({asset}) returned: {balance} (type: {type(balance)})")
        
        # Extract the free balance amount
        free_balance = 0.0
        
        if isinstance(balance, dict):
            free_balance = float(balance.get('free', 0))
            logger.info(f"[UBM] Dict balance, free: {free_balance}")
        elif isinstance(balance, (int, float)):
            free_balance = float(balance)
            logger.info(f"[UBM] Numeric balance: {free_balance}")
        
        # If we found a balance, return it
        if free_balance > 0:
            return free_balance
        
        # CRITICAL FIX: If not found, try Kraken asset code variants
        kraken_variants = self._get_kraken_asset_variants(asset)
        
        for variant in kraken_variants:
            if variant != asset:  # Skip the original asset we already tried
                balance = await self.get_balance(variant)
                if isinstance(balance, dict):
                    free_balance = float(balance.get('free', 0))
                    if free_balance > 0:
                        logger.info(f"[UBM] Found balance for {asset} using variant {variant}: {free_balance}")
                        return free_balance
                elif isinstance(balance, (int, float)):
                    free_balance = float(balance)
                    if free_balance > 0:
                        logger.info(f"[UBM] Found balance for {asset} using variant {variant}: {free_balance}")
                        return free_balance
        
        # Last resort: check raw balances
        if asset in self.balances:
            raw_balance = self.balances[asset]
            if isinstance(raw_balance, (int, float)):
                return float(raw_balance)
        
        logger.warning(f"[UBM] No balance found for {asset} or its variants")
        return 0.0
        
    except Exception as e:
        logger.error(f"[UBM] Error in get_balance_for_asset({asset}): {e}")
        return 0.0
'''

if __name__ == "__main__":
    # Test the diagnostic
    sample_log = """
    [INFO] [src.trading.unified_balance_manager] - [UBM] Found ALGO in balances: 113.40765552 (type: <class 'float'>)
    [INFO] [src.trading.unified_balance_manager] - [UBM] get_balance(ALGO) - converted to dict: {'free': 113.40765552, 'used': 0, 'total': 113.40765552}
    [ERROR] [src.trading.enhanced_trade_executor_with_assistants] - [EXECUTION] No ALGO balance to sell (tried variants: ['ALGO'])
    """
    
    fix = BalanceCheckFix()
    diagnosis = fix.diagnose_issue(sample_log)
    print("Diagnosis:", diagnosis)
    print("\nFix for enhanced_trade_executor:")
    print(fix.generate_fix())
    print("\nFix for balance_manager:")
    print(fix.additional_fix_for_balance_manager())