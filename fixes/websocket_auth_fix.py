#!/usr/bin/env python3
"""
WebSocket Authentication Fix for Kraken Trading Bot
==================================================

This fix addresses the following issues:
1. Ensures WebSocket token is properly obtained and used
2. Verifies API key has correct permissions
3. Fixes balance cache corruption issue
4. Ensures private channels connect properly
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class WebSocketAuthFix:
    """Fixes for WebSocket authentication issues"""
    
    @staticmethod
    async def verify_api_permissions(rest_client) -> bool:
        """
        Verify that API key has the required permissions.
        
        The API key must have:
        - Query Funds
        - Query Open Orders & Trades
        - Query Closed Orders & Trades
        - Other -> Access WebSockets API (CRITICAL!)
        """
        try:
            logger.info("[WS_AUTH_FIX] Verifying API key permissions...")
            
            # Test basic private endpoint access
            balance_result = await rest_client._private_request('Balance')
            if 'error' in balance_result and balance_result['error']:
                logger.error(f"[WS_AUTH_FIX] API key cannot access private endpoints: {balance_result['error']}")
                return False
            
            # Test WebSocket token endpoint specifically
            token_result = await rest_client._private_request('GetWebSocketsToken')
            if 'error' in token_result and token_result['error']:
                logger.error(f"[WS_AUTH_FIX] API key cannot get WebSocket token: {token_result['error']}")
                logger.error("[WS_AUTH_FIX] Please ensure your API key has 'Other -> Access WebSockets API' permission enabled!")
                return False
            
            if 'token' not in token_result:
                logger.error("[WS_AUTH_FIX] GetWebSocketsToken returned no token - check API permissions")
                return False
                
            logger.info("[WS_AUTH_FIX] API permissions verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"[WS_AUTH_FIX] Error verifying permissions: {e}")
            return False
    
    @staticmethod
    async def fix_balance_update_handler(websocket_manager):
        """
        Fix the balance update handler to properly process WebSocket v2 balance messages.
        """
        original_handler = websocket_manager._handle_balances_message
        
        async def fixed_balance_handler(message: Dict[str, Any]):
            """Enhanced balance handler that properly processes v2 format"""
            try:
                logger.debug(f"[WS_AUTH_FIX] Balance message received: {message}")
                
                # Handle different message types
                msg_type = message.get('type', '')
                channel = message.get('channel', '')
                
                if channel != 'balances':
                    # Not a balance message, pass through
                    return await original_handler(message)
                
                # Extract balance data based on message type
                data = message.get('data', [])
                
                if msg_type == 'snapshot':
                    # Initial balance snapshot
                    logger.info(f"[WS_AUTH_FIX] Processing balance snapshot with {len(data)} items")
                    
                    # Process each balance item
                    balances = {}
                    for item in data:
                        if isinstance(item, dict):
                            asset = item.get('asset', '')
                            balance = float(item.get('balance', 0))
                            
                            # Handle Kraken asset naming
                            if asset == 'ZUSDT':
                                asset = 'USDT'
                            elif asset == 'ZUSD':
                                asset = 'USD'
                            elif asset == 'XXBT':
                                asset = 'BTC'
                                
                            balances[asset] = balance
                            
                            if balance > 0.01:
                                logger.info(f"[WS_AUTH_FIX] Balance: {asset} = {balance:.8f}")
                    
                    # Update the balance manager if available
                    if hasattr(websocket_manager, 'balance_manager') and websocket_manager.balance_manager:
                        # Update real-time balance manager
                        if hasattr(websocket_manager.balance_manager, 'real_time_manager'):
                            rtm = websocket_manager.balance_manager.real_time_manager
                            if rtm:
                                async with rtm._balance_lock:
                                    rtm.balances = balances
                                    for asset in balances:
                                        rtm.last_update[asset] = time.time()
                                logger.info(f"[WS_AUTH_FIX] Updated real-time balance manager with {len(balances)} assets")
                
                elif msg_type == 'update':
                    # Balance update (after trade, deposit, etc)
                    logger.info(f"[WS_AUTH_FIX] Processing balance update")
                    
                # Call original handler for any additional processing
                await original_handler(message)
                
            except Exception as e:
                logger.error(f"[WS_AUTH_FIX] Error in fixed balance handler: {e}")
                # Still call original handler
                await original_handler(message)
        
        # Replace the handler
        websocket_manager._handle_balances_message = fixed_balance_handler
        logger.info("[WS_AUTH_FIX] Balance handler fixed")
    
    @staticmethod
    async def ensure_private_connection(websocket_manager) -> bool:
        """
        Ensure private WebSocket channels are properly connected.
        """
        try:
            # Check if auth manager is initialized
            if not websocket_manager.auth_manager:
                logger.error("[WS_AUTH_FIX] No auth manager available")
                return False
            
            # Initialize auth manager if needed
            if not websocket_manager.auth_manager.current_token:
                logger.info("[WS_AUTH_FIX] Initializing auth manager...")
                success = await websocket_manager.auth_manager.initialize()
                if not success:
                    logger.error("[WS_AUTH_FIX] Failed to initialize auth manager")
                    return False
            
            # Connect private channels if not connected
            if not websocket_manager.is_private_connected:
                logger.info("[WS_AUTH_FIX] Connecting to private channels...")
                success = await websocket_manager.connect_private_channels()
                if not success:
                    logger.error("[WS_AUTH_FIX] Failed to connect private channels")
                    return False
                    
            logger.info("[WS_AUTH_FIX] Private channels connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"[WS_AUTH_FIX] Error ensuring private connection: {e}")
            return False
    
    @staticmethod
    async def apply_all_fixes(websocket_manager, rest_client) -> bool:
        """
        Apply all WebSocket authentication fixes.
        
        Returns:
            bool: True if all fixes applied successfully
        """
        try:
            logger.info("[WS_AUTH_FIX] Applying WebSocket authentication fixes...")
            
            # 1. Verify API permissions
            if not await WebSocketAuthFix.verify_api_permissions(rest_client):
                logger.error("[WS_AUTH_FIX] API permission verification failed")
                logger.error("[WS_AUTH_FIX] Please ensure your API key has these permissions:")
                logger.error("[WS_AUTH_FIX]   - Query Funds")
                logger.error("[WS_AUTH_FIX]   - Query Open Orders & Trades") 
                logger.error("[WS_AUTH_FIX]   - Query Closed Orders & Trades")
                logger.error("[WS_AUTH_FIX]   - Other -> Access WebSockets API (CRITICAL!)")
                return False
            
            # 2. Fix balance update handler
            await WebSocketAuthFix.fix_balance_update_handler(websocket_manager)
            
            # 3. Ensure private connection
            if not await WebSocketAuthFix.ensure_private_connection(websocket_manager):
                logger.error("[WS_AUTH_FIX] Failed to establish private connection")
                return False
            
            # 4. Test balance updates
            logger.info("[WS_AUTH_FIX] Waiting for initial balance snapshot...")
            await asyncio.sleep(5)
            
            # Check if we have balance data
            if hasattr(websocket_manager, 'balance_manager') and websocket_manager.balance_manager:
                if hasattr(websocket_manager.balance_manager, 'real_time_manager'):
                    rtm = websocket_manager.balance_manager.real_time_manager
                    if rtm and rtm.balances:
                        usdt_balance = rtm.balances.get('USDT', 0)
                        logger.info(f"[WS_AUTH_FIX] Current USDT balance: ${usdt_balance:.2f}")
                        if usdt_balance > 0:
                            logger.info("[WS_AUTH_FIX] Balance updates working correctly!")
                        else:
                            logger.warning("[WS_AUTH_FIX] USDT balance is 0 - check if you have USDT in your account")
            
            logger.info("[WS_AUTH_FIX] All fixes applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"[WS_AUTH_FIX] Error applying fixes: {e}")
            return False


# Diagnostic function to check WebSocket health
async def diagnose_websocket_issues(websocket_manager, rest_client):
    """
    Diagnose common WebSocket authentication issues.
    """
    print("\n" + "="*60)
    print("WEBSOCKET AUTHENTICATION DIAGNOSTICS")
    print("="*60)
    
    issues_found = []
    
    # Check 1: API Permissions
    print("\n1. Checking API permissions...")
    try:
        token_result = await rest_client._private_request('GetWebSocketsToken')
        if 'error' in token_result and token_result['error']:
            issues_found.append("API key missing 'Access WebSockets API' permission")
            print("   ❌ FAILED: " + str(token_result['error']))
        else:
            print("   ✓ API can get WebSocket tokens")
    except Exception as e:
        issues_found.append(f"API permission check failed: {e}")
        print(f"   ❌ FAILED: {e}")
    
    # Check 2: Auth Manager State
    print("\n2. Checking auth manager state...")
    if not websocket_manager.auth_manager:
        issues_found.append("No auth manager initialized")
        print("   ❌ No auth manager found")
    else:
        token_info = websocket_manager.auth_manager.get_token_info()
        print(f"   Token valid: {token_info['is_valid']}")
        print(f"   Token age: {token_info.get('age_seconds', 'N/A')} seconds")
        print(f"   Refresh count: {token_info['refresh_count']}")
        print(f"   Refresh failures: {token_info['refresh_failures']}")
        
        if not token_info['is_valid']:
            issues_found.append("WebSocket token is invalid or expired")
    
    # Check 3: Private Connection State
    print("\n3. Checking private channel connection...")
    print(f"   Private connected: {websocket_manager.is_private_connected}")
    print(f"   Public connected: {websocket_manager.is_connected}")
    
    if not websocket_manager.is_private_connected:
        issues_found.append("Private channels not connected")
    
    # Check 4: Balance Manager State
    print("\n4. Checking balance manager...")
    if hasattr(websocket_manager, 'balance_manager') and websocket_manager.balance_manager:
        if hasattr(websocket_manager.balance_manager, 'real_time_manager'):
            rtm = websocket_manager.balance_manager.real_time_manager
            status = rtm.get_status() if rtm else {}
            print(f"   Real-time manager connected: {status.get('connected', False)}")
            print(f"   USDT balance: ${status.get('usdt_balance', 0):.2f}")
        else:
            issues_found.append("No real-time balance manager found")
    else:
        issues_found.append("No balance manager found")
    
    # Summary
    print("\n" + "="*60)
    if issues_found:
        print("ISSUES FOUND:")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("✓ No issues found!")
    print("="*60)
    
    return len(issues_found) == 0


if __name__ == "__main__":
    print("WebSocket Authentication Fix Module")
    print("This module provides fixes for common WebSocket authentication issues")