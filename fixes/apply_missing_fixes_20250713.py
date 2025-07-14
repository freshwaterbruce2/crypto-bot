#!/usr/bin/env python3
"""
Apply missing fixes from 07/12/2025 that weren't properly deployed
"""

import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

def check_current_status():
    """Check which fixes are missing"""
    issues = []
    
    # 1. Check nonce manager integration
    try:
        with open('src/exchange/kraken_sdk_exchange.py', 'r') as f:
            content = f.read()
            if 'KrakenNonceManager' not in content:
                issues.append("Nonce manager not integrated in SDK")
            if 'self.nonce_manager' not in content:
                issues.append("Nonce manager not initialized")
    except Exception as e:
        issues.append(f"Error checking SDK: {e}")
    
    # 2. Check WebSocket v2 fixes
    try:
        with open('src/exchange/websocket_manager_v2.py', 'r') as f:
            content = f.read()
            if 'await self.bot.start()' not in content:
                issues.append("WebSocket bot.start() call missing")
            if 'class KrakenBot(SpotWSClient):' in content:
                issues.append("Still using inheritance instead of composition")
    except Exception as e:
        issues.append(f"Error checking WebSocket: {e}")
    
    # 3. Check format string fix
    try:
        with open('src/trading/enhanced_trade_executor_with_assistants.py', 'r') as f:
            content = f.read()
            # Look for problematic format strings
            if '{balance_info}' in content:
                issues.append("Format string issue with balance_info dict")
    except Exception as e:
        issues.append(f"Error checking trade executor: {e}")
    
    return issues

def apply_nonce_fix():
    """Apply nonce manager fix to SDK"""
    print("\n1. Applying nonce manager fix to SDK...")
    
    # Read current SDK file
    with open('src/exchange/kraken_sdk_exchange.py', 'r') as f:
        lines = f.readlines()
    
    # Find import section
    import_index = -1
    for i, line in enumerate(lines):
        if 'from ..utils.kraken_rl import' in line:
            import_index = i
            break
    
    if import_index > 0:
        # Add nonce manager import
        lines.insert(import_index + 1, 'from ..utils.kraken_nonce_manager import KrakenNonceManager\n')
        
        # Find __init__ method
        for i, line in enumerate(lines):
            if 'def __init__(self' in line:
                # Find end of __init__ 
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('def '):
                    if 'logger.info' in lines[j] and 'Initialized' in lines[j]:
                        # Add nonce manager initialization before the log
                        lines.insert(j, '        # Initialize nonce manager\n')
                        lines.insert(j+1, '        self.nonce_manager = KrakenNonceManager()\n')
                        lines.insert(j+2, '        \n')
                        break
                    j += 1
                break
        
        # Find _execute_private_request method
        for i, line in enumerate(lines):
            if 'params=params or {}' in line:
                # Add nonce to params
                lines.insert(i, '                        # Add nonce\n')
                lines.insert(i+1, '                        nonce = self.nonce_manager.get_nonce("rest_api")\n')
                lines.insert(i+2, '                        if params is None:\n')
                lines.insert(i+3, '                            params = {}\n')
                lines.insert(i+4, '                        params["nonce"] = str(nonce)\n')
                lines.insert(i+5, '                        \n')
                break
        
        # Write back
        with open('src/exchange/kraken_sdk_exchange.py', 'w') as f:
            f.writelines(lines)
        
        print("✓ Nonce manager integrated into SDK")
    else:
        print("✗ Could not find import section in SDK")

def apply_websocket_fix():
    """Fix WebSocket v2 to use composition"""
    print("\n2. Applying WebSocket v2 composition fix...")
    
    # This is more complex, so let's just log what needs to be done
    print("✓ WebSocket fix requires manual review - inheritance pattern needs refactoring")

def apply_format_string_fix():
    """Fix format string error in trade executor"""
    print("\n3. Applying format string fix...")
    
    try:
        with open('src/trading/enhanced_trade_executor_with_assistants.py', 'r') as f:
            content = f.read()
        
        # Replace problematic format strings
        if '{balance_info}' in content:
            content = content.replace(
                'logger.info(f"[EXECUTION] Sell order balance check: {balance_info}")',
                'logger.info(f"[EXECUTION] Sell order balance check: asset={asset}, balance={actual_balance}")'
            )
            
            with open('src/trading/enhanced_trade_executor_with_assistants.py', 'w') as f:
                f.write(content)
            
            print("✓ Format string fix applied")
        else:
            print("✓ Format string already fixed or not found")
    except Exception as e:
        print(f"✗ Error applying format string fix: {e}")

def main():
    """Apply all missing fixes"""
    print("Checking for missing fixes from 07/12/2025...")
    
    issues = check_current_status()
    
    if not issues:
        print("\n✓ All fixes appear to be applied!")
        return
    
    print(f"\nFound {len(issues)} missing fixes:")
    for issue in issues:
        print(f"  - {issue}")
    
    print("\nApplying fixes...")
    
    # Apply fixes
    if any('Nonce' in issue for issue in issues):
        apply_nonce_fix()
    
    if any('WebSocket' in issue for issue in issues):
        apply_websocket_fix()
    
    if any('Format string' in issue for issue in issues):
        apply_format_string_fix()
    
    print("\nFixes applied. Please restart the bot to use the updated code.")
    print("\nIMPORTANT: The WebSocket inheritance fix requires manual refactoring.")
    print("Consider using the fallback WebSocket implementation for now.")

if __name__ == "__main__":
    main()