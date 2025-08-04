"""
Enhanced WebSocket Authentication Wrapper with Nonce Fix
=======================================================

This wrapper provides robust WebSocket token authentication with:
- Automatic nonce collision recovery
- Exponential backoff retry logic
- Comprehensive error handling
- Integration with unified nonce manager
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable
import aiohttp
import json

logger = logging.getLogger(__name__)


class EnhancedWebSocketAuthWrapper:
    """Enhanced WebSocket authentication with nonce collision recovery"""
    
    def __init__(self, api_key: str, private_key: str, nonce_manager=None):
        self.api_key = api_key
        self.private_key = private_key
        self.nonce_manager = nonce_manager
        
        # Retry configuration
        self.max_retries = 5
        self.base_delay = 1.0
        self.max_delay = 30.0
        self.retry_multiplier = 2.0
        
        # Statistics
        self.token_requests = 0
        self.successful_requests = 0
        self.nonce_errors = 0
        self.retry_attempts = 0
    
    def _create_signature(self, uri_path: str, nonce: str, post_data: str = "") -> str:
        """Create HMAC-SHA512 signature for Kraken API"""
        import hmac
        import hashlib
        import base64
        
        # Prepare the message
        api_post = f"nonce={nonce}"
        if post_data:
            api_post += f"&{post_data}"
        
        # Create SHA256 hash
        sha256_hash = hashlib.sha256(api_post.encode('utf-8')).digest()
        
        # Create message for HMAC
        message = uri_path.encode('utf-8') + sha256_hash
        
        # Create HMAC-SHA512 signature
        secret = base64.b64decode(self.private_key)
        signature = hmac.new(secret, message, hashlib.sha512)
        
        return base64.b64encode(signature.digest()).decode('utf-8')
    
    async def get_websocket_token_with_retry(self) -> Optional[str]:
        """Get WebSocket token with automatic retry and nonce recovery"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔑 WebSocket token request attempt {attempt + 1}/{self.max_retries}")
                
                # Get fresh nonce from unified manager
                if self.nonce_manager:
                    nonce = await self.nonce_manager.get_nonce_async("websocket_token_request")
                else:
                    # Fallback to timestamp-based nonce
                    nonce = str(int(time.time() * 1000000))
                
                # Create authentication headers
                uri_path = "/0/private/GetWebSocketsToken"
                signature = self._create_signature(uri_path, nonce)
                
                headers = {
                    'API-Key': self.api_key,
                    'API-Sign': signature,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                # Prepare POST data
                post_data = f"nonce={nonce}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.kraken.com{uri_path}"
                    async with session.post(url, headers=headers, data=post_data) as response:
                        result = await response.json()
                        
                        if response.status == 200 and 'result' in result:
                            if 'token' in result['result']:
                                token = result['result']['token']
                                logger.info(f"✅ WebSocket token obtained successfully on attempt {attempt + 1}")
                                self.successful_requests += 1
                                return token
                            else:
                                raise Exception(f"No token in response: {result}")
                        else:
                            error_msg = result.get('error', [f'HTTP {response.status}'])
                            raise Exception(f"API error: {error_msg}")
                            
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                if 'nonce' in error_str:
                    logger.warning(f"⚠️  Nonce error on attempt {attempt + 1}: {e}")
                    self.nonce_errors += 1
                    
                    # Force nonce recovery if we have a nonce manager
                    if self.nonce_manager and hasattr(self.nonce_manager, 'handle_invalid_nonce_error'):
                        recovery_nonce = self.nonce_manager.handle_invalid_nonce_error("websocket_token_recovery")
                        logger.info(f"🔄 Nonce recovery applied: {recovery_nonce}")
                else:
                    logger.warning(f"⚠️  Request error on attempt {attempt + 1}: {e}")
                
                self.retry_attempts += 1
                
                # Calculate delay with exponential backoff
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (self.retry_multiplier ** attempt), self.max_delay)
                    logger.info(f"⏳ Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
        
        # All retries failed
        logger.error(f"❌ All {self.max_retries} WebSocket token requests failed. Last error: {last_error}")
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        return {
            'token_requests': self.token_requests,
            'successful_requests': self.successful_requests,
            'success_rate': self.successful_requests / max(self.token_requests, 1),
            'nonce_errors': self.nonce_errors,
            'retry_attempts': self.retry_attempts
        }


# Factory function for easy integration
async def create_enhanced_websocket_auth(api_key: str, private_key: str, nonce_manager=None) -> EnhancedWebSocketAuthWrapper:
    """Create enhanced WebSocket authentication wrapper"""
    return EnhancedWebSocketAuthWrapper(api_key, private_key, nonce_manager)
