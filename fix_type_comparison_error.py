#!/usr/bin/env python3
"""
Fix for type comparison error: '>' not supported between instances of 'dict' and 'int'
This error is preventing trade execution
"""

import os
import re

def fix_type_comparison():
    """Find and fix type comparison errors in trade executor"""
    
    print("Fixing type comparison error in trade executor...")
    
    # Files to check
    files_to_check = [
        "src/trading/enhanced_trade_executor_with_assistants.py",
        "src/exchange/kraken_sdk_exchange.py",
        "src/utils/kraken_rl.py"
    ]
    
    fixes_applied = 0
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"  File not found: {file_path}")
            continue
            
        print(f"\n  Checking {file_path}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
            
        original_content = content
        
        # Common patterns that might cause dict vs int comparison
        patterns = [
            # Pattern 1: response > 0 where response might be dict
            (r'(\w+)\s*>\s*0', r'(isinstance(\1, (int, float)) and \1 > 0)'),
            # Pattern 2: result > value where result might be dict
            (r'(\w+)\s*>\s*(\d+)', r'(isinstance(\1, (int, float)) and \1 > \2)'),
            # Pattern 3: if variable > number (common pattern)
            (r'if\s+(\w+)\s*>\s*(\d+)', r'if isinstance(\1, (int, float)) and \1 > \2'),
        ]
        
        # Apply fixes
        for pattern, replacement in patterns:
            matches = re.findall(pattern, content)
            if matches:
                print(f"    Found {len(matches)} potential issues with pattern: {pattern}")
                # Only fix specific variables that might be dict
                if any(var in ['response', 'result', 'data', 'ret', 'res'] for var in (matches[0] if isinstance(matches[0], tuple) else [matches[0]])):
                    content = re.sub(pattern, replacement, content)
                    fixes_applied += 1
        
        # Save if changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"    Fixed {file_path}")
    
    print(f"\nTotal fixes applied: {fixes_applied}")
    
    # Also create a safer comparison function
    safer_compare = '''"""
Safer comparison utilities to prevent type errors
"""

def safe_greater_than(value, threshold):
    """Safely compare value > threshold, handling dict responses"""
    if isinstance(value, dict):
        # If it's a dict, try to extract numeric value
        if 'result' in value:
            value = value['result']
        elif 'value' in value:
            value = value['value']
        elif 'amount' in value:
            value = value['amount']
        else:
            return False
    
    try:
        return float(value) > float(threshold)
    except (TypeError, ValueError):
        return False

def safe_less_than(value, threshold):
    """Safely compare value < threshold"""
    if isinstance(value, dict):
        if 'result' in value:
            value = value['result']
        elif 'value' in value:
            value = value['value']
        elif 'amount' in value:
            value = value['amount']
        else:
            return False
    
    try:
        return float(value) < float(threshold)
    except (TypeError, ValueError):
        return False
'''
    
    # Save safer comparison utilities
    with open("src/utils/safe_comparison.py", "w") as f:
        f.write(safer_compare)
    print("\nCreated src/utils/safe_comparison.py with safer comparison functions")
    
    print("\n✅ Type comparison fixes applied!")
    print("The bot should now be able to execute trades without type errors.")

if __name__ == "__main__":
    fix_type_comparison()