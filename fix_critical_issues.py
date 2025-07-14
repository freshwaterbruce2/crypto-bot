#!/usr/bin/env python3
"""
Fix critical issues in the trading bot
- Format string errors
- Nonce issues
- Balance type errors
"""

import os
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_format_string_errors():
    """Fix the format string error in enhanced_trade_executor_with_assistants.py"""
    file_path = "src/trading/enhanced_trade_executor_with_assistants.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Ensure asset_balance is always a float, not a dict
    fixes = [
        # Fix the balance retrieval to ensure it's a float
        (
            r'asset_balance = await self\.balance_manager\.get_balance_for_asset\(base_asset\)',
            '''# Get balance and ensure it's a float
                    balance_result = await self.balance_manager.get_balance_for_asset(base_asset)
                    if isinstance(balance_result, dict):
                        # Handle dict response from balance manager
                        asset_balance = float(balance_result.get('free', 0) or balance_result.get('total', 0) or 0)
                    else:
                        asset_balance = float(balance_result or 0)'''
        ),
        # Fix the balance manager get_balance call
        (
            r'asset_balance = await self\.balance_manager\.get_balance\(base_asset\)',
            '''# Get balance and ensure it's a float
                        balance_result = await self.balance_manager.get_balance(base_asset)
                        if isinstance(balance_result, dict):
                            asset_balance = float(balance_result.get('free', 0) or balance_result.get('total', 0) or 0)
                        else:
                            asset_balance = float(balance_result or 0)'''
        ),
        # Fix enhanced balance detection
        (
            r'balance_data = await self\._get_enhanced_balance_for_asset\(base_asset\)',
            '''balance_data = await self._get_enhanced_balance_for_asset(base_asset)
                        # Ensure balance_data is a float
                        if isinstance(balance_data, dict):
                            asset_balance = float(balance_data.get('free', 0) or balance_data.get('total', 0) or 0)
                        else:
                            asset_balance = float(balance_data or 0)'''
        )
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content)
    
    # Fix 2: Add type checking before formatting
    # Add a helper function at the top of the execute_trade method
    helper_function = '''
    def _ensure_float(self, value, default=0.0):
        """Ensure value is a float for formatting"""
        if value is None:
            return default
        if isinstance(value, dict):
            # Try to extract numeric value from dict
            return float(value.get('free', value.get('total', default)))
        try:
            return float(value)
        except (TypeError, ValueError):
            logger.warning(f"[EXECUTION] Could not convert {value} to float, using {default}")
            return default
'''
    
    # Insert helper function after class definition
    class_match = re.search(r'class EnhancedTradeExecutorWithAssistants.*?:\n', content)
    if class_match:
        insert_pos = class_match.end()
        # Find the next method definition
        next_method = content.find('\n    def ', insert_pos)
        if next_method > 0:
            content = content[:next_method] + helper_function + content[next_method:]
    
    # Fix 3: Replace all float formatting with safe version
    # Find all instances of variable formatting with .Xf
    content = re.sub(
        r'(\w+_balance|asset_balance|balance|tracked_amount|final_balance)(\.8f|\.2f|\.6f)',
        r'self._ensure_float(\1)\2',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    logger.info(f"Fixed format string errors in {file_path}")

def fix_nonce_issues():
    """Fix nonce issues in Kraken SDK exchange"""
    file_path = "src/exchange/kraken_sdk_exchange.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Ensure nonce is properly imported and initialized
    if 'from ..utils.kraken_nonce_manager import KrakenNonceManager' not in content:
        # Add import at the top
        import_section = re.search(r'(import.*?\n\n)', content, re.DOTALL)
        if import_section:
            content = content[:import_section.end()] + 'from ..utils.kraken_nonce_manager import KrakenNonceManager\n' + content[import_section.end():]
    
    # Ensure nonce manager is initialized in __init__
    if 'self.nonce_manager = KrakenNonceManager()' not in content:
        init_match = re.search(r'def __init__\(self.*?\):\n.*?""".*?"""', content, re.DOTALL)
        if init_match:
            content = content[:init_match.end()] + '\n        # Initialize nonce manager\n        self.nonce_manager = KrakenNonceManager()\n' + content[init_match.end():]
    
    # Fix the nonce addition in _execute_private_request
    nonce_fix = '''
                # Add nonce to params - CRITICAL FIX FOR 2025
                if params is None:
                    params = {}
                
                # Get fresh nonce for every request
                nonce = self.nonce_manager.get_nonce("rest_api")
                params["nonce"] = str(nonce)
                
                # Log nonce for debugging
                logger.debug(f"[KRAKEN_SDK] Using nonce: {nonce} for {method}")
'''
    
    # Find where to insert nonce fix
    execute_match = re.search(r'if method in direct_endpoints:.*?endpoint = direct_endpoints\[method\]', content, re.DOTALL)
    if execute_match:
        content = content[:execute_match.end()] + nonce_fix + content[execute_match.end():]
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    logger.info(f"Fixed nonce issues in {file_path}")

def fix_balance_manager():
    """Fix balance manager to always return floats"""
    file_path = "src/trading/unified_balance_manager.py"
    
    if not os.path.exists(file_path):
        logger.warning(f"{file_path} not found, skipping")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add helper method to ensure float returns
    helper_method = '''
    def _ensure_float(self, value, default=0.0):
        """Ensure value is a float"""
        if value is None:
            return default
        if isinstance(value, dict):
            return float(value.get('free', value.get('total', default)))
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
'''
    
    # Insert after class definition
    class_match = re.search(r'class UnifiedBalanceManager.*?:\n.*?""".*?"""', content, re.DOTALL)
    if class_match:
        content = content[:class_match.end()] + helper_method + content[class_match.end():]
    
    # Fix get_balance method to return float
    content = re.sub(
        r'async def get_balance\(self, asset: str\).*?return.*?$',
        lambda m: m.group(0).rstrip() + '\n        # Ensure float return\n        return self._ensure_float(balance)',
        content,
        flags=re.MULTILINE
    )
    
    # Fix get_balance_for_asset method
    content = re.sub(
        r'async def get_balance_for_asset\(self, asset: str\).*?return.*?$',
        lambda m: m.group(0).rstrip() + '\n        # Ensure float return\n        return self._ensure_float(balance)',
        content,
        flags=re.MULTILINE
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    logger.info(f"Fixed balance manager in {file_path}")

def main():
    """Run all fixes"""
    logger.info("Starting critical fixes...")
    
    try:
        fix_format_string_errors()
    except Exception as e:
        logger.error(f"Error fixing format strings: {e}")
    
    try:
        fix_nonce_issues()
    except Exception as e:
        logger.error(f"Error fixing nonce issues: {e}")
    
    try:
        fix_balance_manager()
    except Exception as e:
        logger.error(f"Error fixing balance manager: {e}")
    
    logger.info("Critical fixes completed!")
    
    # Create a simple test to verify fixes
    logger.info("\nTesting fixes...")
    
    # Test 1: Check if _ensure_float method was added
    with open("src/trading/enhanced_trade_executor_with_assistants.py", 'r') as f:
        if '_ensure_float' in f.read():
            logger.info("✓ Format string fix applied")
        else:
            logger.error("✗ Format string fix failed")
    
    # Test 2: Check nonce fix
    with open("src/exchange/kraken_sdk_exchange.py", 'r') as f:
        content = f.read()
        if 'nonce = self.nonce_manager.get_nonce("rest_api")' in content and 'params["nonce"] = str(nonce)' in content:
            logger.info("✓ Nonce fix applied")
        else:
            logger.error("✗ Nonce fix failed")

if __name__ == "__main__":
    main()