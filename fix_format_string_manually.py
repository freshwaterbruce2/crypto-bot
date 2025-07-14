#!/usr/bin/env python3
"""
Manual fix for format string errors in trade executor
"""

import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_format_string_errors():
    """Fix the format string error by ensuring balance variables are floats"""
    file_path = "src/trading/enhanced_trade_executor_with_assistants.py"
    
    logger.info(f"Reading {file_path}...")
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Count replacements
    replacements = 0
    
    # Fix 1: Add helper method after class definition if not exists
    if '_ensure_float' not in content:
        # Find the class definition
        class_match = re.search(r'(class EnhancedTradeExecutorWithAssistants.*?:\n.*?""".*?""")', content, re.DOTALL)
        if class_match:
            # Insert the helper method after the class docstring
            insert_pos = class_match.end()
            helper_method = '''
    
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
            content = content[:insert_pos] + helper_method + content[insert_pos:]
            logger.info("Added _ensure_float helper method")
            replacements += 1
    
    # Fix 2: Replace problematic float formatting patterns
    patterns_to_fix = [
        # Pattern for asset_balance formatting
        (r'logger\.info\(f"\[EXECUTION\] CRITICAL FIX: Using corrected {base_asset} balance: {asset_balance:.8f}"\)',
         'logger.info(f"[EXECUTION] CRITICAL FIX: Using corrected {base_asset} balance: {self._ensure_float(asset_balance):.8f}")'),
        
        # Pattern for balance formatting in general
        (r'logger\.info\(f"\[EXECUTION\] Current USDT balance: \${balance:.2f}"\)',
         'logger.info(f"[EXECUTION] Current USDT balance: ${self._ensure_float(balance):.2f}")'),
        
        # Fix tracked_amount formatting
        (r'logger\.info\(f"\[EXECUTION\] CRITICAL FIX: Found tracked position for {base_asset}: {tracked_amount:.8f}"\)',
         'logger.info(f"[EXECUTION] CRITICAL FIX: Found tracked position for {base_asset}: {self._ensure_float(tracked_amount):.8f}")'),
        
        # Fix actual exchange balance formatting
        (r'logger\.info\(f"\[EXECUTION\] CRITICAL FIX: Actual exchange balance for {base_asset}: {asset_balance:.8f}"\)',
         'logger.info(f"[EXECUTION] CRITICAL FIX: Actual exchange balance for {base_asset}: {self._ensure_float(asset_balance):.8f}")'),
        
        # Fix balance verification logging
        (r'logger\.info\(f"\[EXECUTION\] Balance verified after {attempt \+ 1} attempts: \${balance_check:.2f}"\)',
         'logger.info(f"[EXECUTION] Balance verified after {attempt + 1} attempts: ${self._ensure_float(balance_check):.2f}")'),
         
        # Fix warning messages
        (r'logger\.warning\(f"\[EXECUTION\] CRITICAL FIX: Position tracker shows {base_asset}: {tracked_amount:.8f} but exchange shows: {asset_balance:.8f}"\)',
         'logger.warning(f"[EXECUTION] CRITICAL FIX: Position tracker shows {base_asset}: {self._ensure_float(tracked_amount):.8f} but exchange shows: {self._ensure_float(asset_balance):.8f}")'),
         
        (r'logger\.warning\(f"\[EXECUTION\] CRITICAL FIX: Using exchange balance {asset_balance:.8f} to prevent overselling"\)',
         'logger.warning(f"[EXECUTION] CRITICAL FIX: Using exchange balance {self._ensure_float(asset_balance):.8f} to prevent overselling")'),
    ]
    
    for pattern, replacement in patterns_to_fix:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            replacements += 1
            logger.info(f"Fixed pattern: {pattern[:50]}...")
    
    # Fix 3: Ensure balance retrieval returns floats
    # Fix the balance retrieval sections
    balance_fixes = [
        # Fix get_balance_for_asset calls
        (r'asset_balance = await self\.balance_manager\.get_balance_for_asset\(base_asset\)',
         '''balance_result = await self.balance_manager.get_balance_for_asset(base_asset)
                    asset_balance = self._ensure_float(balance_result)'''),
        
        # Fix get_balance calls
        (r'asset_balance = await self\.balance_manager\.get_balance\(base_asset\)',
         '''balance_result = await self.balance_manager.get_balance(base_asset)
                        asset_balance = self._ensure_float(balance_result)'''),
    ]
    
    for pattern, replacement in balance_fixes:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            replacements += 1
            logger.info(f"Fixed balance retrieval pattern")
    
    # Write the fixed content
    logger.info(f"Writing fixed content back to {file_path}...")
    with open(file_path, 'w') as f:
        f.write(content)
    
    logger.info(f"Applied {replacements} fixes to {file_path}")
    
    # Verify the fix
    with open(file_path, 'r') as f:
        final_content = f.read()
        if '_ensure_float' in final_content:
            logger.info("✓ Successfully added _ensure_float method")
        else:
            logger.error("✗ Failed to add _ensure_float method")

def main():
    """Run the fix"""
    try:
        fix_format_string_errors()
        logger.info("Format string fixes completed successfully!")
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        raise

if __name__ == "__main__":
    main()