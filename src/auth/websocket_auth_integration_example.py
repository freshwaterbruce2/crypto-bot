"""
WebSocket Authentication Integration Example
==========================================

Example showing how to integrate the enhanced WebSocket authentication manager
with your trading bot to solve "EAPI:Invalid nonce" and token expiry issues.

This example demonstrates:
1. Initializing the authentication manager
2. Integrating with WebSocket V2 manager
3. Handling authentication errors and recovery
4. Monitoring authentication status
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .websocket_authentication_manager import (
    WebSocketAuthenticationManager,
    WebSocketAuthenticationError,
    websocket_auth_context
)
from ..exchange.websocket_manager_v2 import KrakenProWebSocketManager

logger = logging.getLogger(__name__)


class EnhancedWebSocketIntegration:
    """
    Example integration class showing how to use enhanced authentication
    with WebSocket connections for reliable trading bot operation.
    """
    
    def __init__(self, exchange_client, api_key: str, private_key: str):
        """
        Initialize enhanced WebSocket integration.
        
        Args:
            exchange_client: Kraken exchange client
            api_key: API key
            private_key: Private key
        """
        self.exchange_client = exchange_client
        self.api_key = api_key
        self.private_key = private_key
        
        # WebSocket manager with enhanced authentication
        self.websocket_manager: Optional[KrakenProWebSocketManager] = None
        
        # Example symbols for demonstration
        self.symbols = ['SHIB/USDT', 'MATIC/USDT', 'AI16Z/USDT', 'BERA/USDT']
        
        logger.info("[WS_INTEGRATION] Enhanced WebSocket integration initialized")
    
    async def start_with_enhanced_authentication(self) -> bool:
        """
        Start WebSocket connection with enhanced authentication.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info("[WS_INTEGRATION] Starting WebSocket with enhanced authentication...")
            
            # Create WebSocket manager
            self.websocket_manager = KrakenProWebSocketManager(
                exchange_client=self.exchange_client,
                symbols=self.symbols,
                connection_id="enhanced_auth_example",
                visual_mode=True  # Enable visual monitoring
            )
            
            # Initialize enhanced authentication
            auth_success = await self.websocket_manager.initialize_authentication(
                api_key=self.api_key,
                private_key=self.private_key
            )
            
            if not auth_success:
                logger.error("[WS_INTEGRATION] Failed to initialize enhanced authentication")
                return False
            
            # Connect WebSocket
            connect_success = await self.websocket_manager.connect()
            if not connect_success:
                logger.error("[WS_INTEGRATION] Failed to connect WebSocket")
                return False
            
            logger.info("[WS_INTEGRATION] Enhanced WebSocket authentication started successfully")
            return True
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error starting enhanced authentication: {e}")
            return False
    
    async def demonstrate_authentication_monitoring(self) -> Dict[str, Any]:
        """
        Demonstrate authentication status monitoring.
        
        Returns:
            Comprehensive authentication status
        """
        if not self.websocket_manager:
            return {'error': 'WebSocket manager not initialized'}
        
        try:
            # Get comprehensive authentication status
            auth_status = self.websocket_manager.get_authentication_status()
            
            logger.info("[WS_INTEGRATION] Authentication Status Summary:")
            logger.info(f"  Enhanced Auth Available: {auth_status.get('enhanced_auth_manager_available', False)}")
            logger.info(f"  Legacy Token Available: {auth_status.get('legacy_auth_token_available', False)}")
            
            # Check enhanced authentication details
            if 'enhanced_authentication' in auth_status:
                enhanced = auth_status['enhanced_authentication']
                logger.info(f"  Token Valid: {enhanced.get('has_valid_token', False)}")
                logger.info(f"  Circuit Breaker Open: {enhanced.get('circuit_breaker_open', False)}")
                logger.info(f"  Successful Auths: {enhanced.get('statistics', {}).get('successful_auths', 0)}")
                logger.info(f"  Auth Failures: {enhanced.get('statistics', {}).get('auth_failures', 0)}")
            
            # Check token info
            if 'enhanced_token_info' in auth_status:
                token_info = auth_status['enhanced_token_info']
                logger.info(f"  Token Expires In: {token_info.get('expires_in_seconds', 0)} seconds")
                logger.info(f"  Token Age: {token_info.get('age_seconds', 0)} seconds")
                logger.info(f"  Needs Refresh: {token_info.get('needs_refresh', True)}")
            
            return auth_status
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error monitoring authentication: {e}")
            return {'error': str(e)}
    
    async def demonstrate_error_recovery(self) -> bool:
        """
        Demonstrate authentication error recovery.
        
        Returns:
            True if recovery test successful
        """
        if not self.websocket_manager or not self.websocket_manager.auth_manager:
            logger.error("[WS_INTEGRATION] Authentication manager not available for recovery test")
            return False
        
        try:
            logger.info("[WS_INTEGRATION] Testing authentication error recovery...")
            
            # Simulate an authentication error (for testing)
            test_error = "EAPI:Invalid nonce"
            
            # Use authentication manager to handle the error
            recovery_token = await self.websocket_manager.auth_manager.handle_authentication_error(test_error)
            
            if recovery_token:
                logger.info(f"[WS_INTEGRATION] Recovery successful - new token obtained: {recovery_token[:20]}...")
                return True
            else:
                logger.warning("[WS_INTEGRATION] Recovery failed - no token returned")
                return False
                
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error in recovery test: {e}")
            return False
    
    async def demonstrate_proactive_refresh(self) -> bool:
        """
        Demonstrate proactive token refresh.
        
        Returns:
            True if refresh successful
        """
        if not self.websocket_manager or not self.websocket_manager.auth_manager:
            logger.error("[WS_INTEGRATION] Authentication manager not available for refresh test")
            return False
        
        try:
            logger.info("[WS_INTEGRATION] Testing proactive token refresh...")
            
            # Force token refresh
            success = await self.websocket_manager.auth_manager.force_token_refresh()
            
            if success:
                logger.info("[WS_INTEGRATION] Proactive refresh successful")
                return True
            else:
                logger.warning("[WS_INTEGRATION] Proactive refresh failed")
                return False
                
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error in refresh test: {e}")
            return False
    
    async def run_comprehensive_demo(self) -> Dict[str, Any]:
        """
        Run comprehensive demonstration of enhanced authentication features.
        
        Returns:
            Results of all demonstration tests
        """
        results = {
            'timestamp': asyncio.get_event_loop().time(),
            'tests': {}
        }
        
        try:
            # Test 1: Start with enhanced authentication
            logger.info("[WS_INTEGRATION] === Starting Enhanced Authentication Demo ===")
            start_success = await self.start_with_enhanced_authentication()
            results['tests']['startup'] = {
                'success': start_success,
                'description': 'Initialize WebSocket with enhanced authentication'
            }
            
            if not start_success:
                results['overall_success'] = False
                return results
            
            # Test 2: Monitor authentication status
            logger.info("[WS_INTEGRATION] === Testing Authentication Monitoring ===")
            auth_status = await self.demonstrate_authentication_monitoring()
            results['tests']['monitoring'] = {
                'success': 'error' not in auth_status,
                'description': 'Monitor authentication status',
                'data': auth_status
            }
            
            # Test 3: Error recovery
            logger.info("[WS_INTEGRATION] === Testing Error Recovery ===")
            recovery_success = await self.demonstrate_error_recovery()
            results['tests']['error_recovery'] = {
                'success': recovery_success,
                'description': 'Handle authentication errors with recovery'
            }
            
            # Test 4: Proactive refresh
            logger.info("[WS_INTEGRATION] === Testing Proactive Refresh ===")
            refresh_success = await self.demonstrate_proactive_refresh()
            results['tests']['proactive_refresh'] = {
                'success': refresh_success,
                'description': 'Proactive token refresh before expiry'
            }
            
            # Test 5: Final status check
            logger.info("[WS_INTEGRATION] === Final Status Check ===")
            final_status = await self.demonstrate_authentication_monitoring()
            results['tests']['final_status'] = {
                'success': 'error' not in final_status,
                'description': 'Final authentication status check',
                'data': final_status
            }
            
            # Overall success
            results['overall_success'] = all(
                test.get('success', False) for test in results['tests'].values()
            )
            
            logger.info(f"[WS_INTEGRATION] === Demo Complete - Success: {results['overall_success']} ===")
            
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error in comprehensive demo: {e}")
            results['overall_success'] = False
            results['error'] = str(e)
        
        return results
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.websocket_manager:
                await self.websocket_manager.disconnect()
                logger.info("[WS_INTEGRATION] WebSocket manager disconnected")
        except Exception as e:
            logger.error(f"[WS_INTEGRATION] Error during cleanup: {e}")


async def run_integration_example():
    """
    Main function to run the WebSocket authentication integration example.
    
    This function demonstrates how to integrate enhanced authentication
    with your trading bot's WebSocket connections.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example credentials (replace with your actual credentials)
    API_KEY = "your_kraken_api_key_here"
    PRIVATE_KEY = "your_kraken_private_key_here"
    
    # Mock exchange client (replace with your actual exchange client)
    class MockExchangeClient:
        async def get_websocket_token(self):
            # This would normally make a real API request
            return {"token": "example_websocket_token_12345"}
    
    exchange_client = MockExchangeClient()
    
    # Create integration instance
    integration = EnhancedWebSocketIntegration(
        exchange_client=exchange_client,
        api_key=API_KEY,
        private_key=PRIVATE_KEY
    )
    
    try:
        # Run comprehensive demonstration
        results = await integration.run_comprehensive_demo()
        
        print("\n" + "="*80)
        print("ENHANCED WEBSOCKET AUTHENTICATION DEMO RESULTS")
        print("="*80)
        print(f"Overall Success: {results.get('overall_success', False)}")
        print(f"Tests Run: {len(results.get('tests', {}))}")
        
        for test_name, test_result in results.get('tests', {}).items():
            status = "✓ PASS" if test_result.get('success', False) else "✗ FAIL"
            print(f"{status} {test_name}: {test_result.get('description', '')}")
        
        if 'error' in results:
            print(f"Error: {results['error']}")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error running integration example: {e}")
    
    finally:
        # Cleanup
        await integration.cleanup()


# Context manager example for simpler usage
async def context_manager_example():
    """
    Example using the async context manager for simpler authentication management.
    """
    API_KEY = "your_kraken_api_key_here"
    PRIVATE_KEY = "your_kraken_private_key_here"
    
    # Mock exchange client
    class MockExchangeClient:
        async def get_websocket_token(self):
            return {"token": "example_websocket_token_12345"}
    
    exchange_client = MockExchangeClient()
    
    try:
        # Use context manager for automatic cleanup
        async with websocket_auth_context(
            exchange_client=exchange_client,
            api_key=API_KEY,
            private_key=PRIVATE_KEY,
            enable_debug=True
        ) as auth_manager:
            
            # Get WebSocket token
            token = await auth_manager.get_websocket_token()
            print(f"Got WebSocket token: {token[:20] if token else 'None'}...")
            
            # Get authentication status
            status = auth_manager.get_authentication_status()
            print(f"Auth status: {status.get('has_valid_token', False)}")
            
            # Authentication manager will be automatically stopped when exiting context
            
    except WebSocketAuthenticationError as e:
        print(f"Authentication error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    # Run the main integration example
    asyncio.run(run_integration_example())
    
    # Uncomment to run the context manager example instead
    # asyncio.run(context_manager_example())