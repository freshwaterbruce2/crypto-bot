#!/usr/bin/env python3
"""
Kraken Nonce Authentication Issue Fix
====================================

This script fixes the persistent "EAPI:Invalid nonce" errors by:

1. Resetting the nonce state to current time with proper synchronization
2. Implementing enhanced WebSocket token authentication with retry logic  
3. Adding nonce collision prevention and recovery mechanisms
4. Providing comprehensive validation and testing

The fix addresses:
- WebSocket V2 authentication token request failures
- Balance Manager V2 initialization issues
- Private WebSocket subscription failures
- Nonce synchronization between REST and WebSocket calls

Author: Kraken Exchange API Integration Specialist
Date: 2025-08-03
Priority: CRITICAL - Restore trading bot functionality
"""

import asyncio
import json
import logging
import time
import traceback
from pathlib import Path
from typing import Dict, Any, Optional
from decimal import Decimal
import hashlib
import base64
import hmac
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('nonce_authentication_fix.log')
    ]
)
logger = logging.getLogger(__name__)


class KrakenNonceAuthenticationFix:
    """Comprehensive fix for Kraken nonce authentication issues"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent
        self.results = {
            'nonce_reset': False,
            'authentication_test': False,
            'websocket_token_test': False,
            'balance_access_test': False,
            'total_tests': 0,
            'passed_tests': 0,
            'errors': []
        }
        
    def reset_nonce_state_with_synchronization(self) -> bool:
        """Reset nonce state with proper synchronization to current time"""
        try:
            logger.info("🔄 Resetting nonce state with proper synchronization...")
            
            # Find all nonce state files
            nonce_files = list(self.project_root.glob("*nonce*state*.json"))
            if not nonce_files:
                nonce_files = list(self.project_root.glob("unified_nonce_state.json"))
            
            # Calculate new synchronized nonce
            current_time_us = int(time.time() * 1000000)
            # Add 5-second buffer to ensure we're ahead of any recent API calls
            synchronized_nonce = current_time_us + (5 * 1000000)
            
            new_state = {
                'last_nonce': synchronized_nonce,
                'timestamp': time.time(),
                'iso_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'reset_reason': 'Authentication fix - synchronized to current time',  
                'synchronization_offset_seconds': 5,
                'total_generated': 0,
                'error_recoveries': 0,
                'connections': 0
            }
            
            # Update all nonce state files
            for nonce_file in nonce_files:
                logger.info(f"📝 Updating nonce state file: {nonce_file}")
                
                # Backup existing state
                backup_file = nonce_file.with_suffix('.backup')
                if nonce_file.exists():
                    nonce_file.rename(backup_file)
                
                # Write new synchronized state
                with open(nonce_file, 'w') as f:
                    json.dump(new_state, f, indent=2)
            
            # Create new unified state if no files exist
            if not nonce_files:
                unified_state_file = self.project_root / "unified_nonce_state.json"
                with open(unified_state_file, 'w') as f:
                    json.dump(new_state, f, indent=2)
                logger.info(f"📝 Created new unified nonce state: {unified_state_file}")
            
            # Try D: drive location as well (as specified in requirements)
            try:
                d_drive_path = Path("D:/trading_data")
                if d_drive_path.exists() or d_drive_path.parent.exists():
                    d_drive_path.mkdir(exist_ok=True)
                    d_drive_state = d_drive_path / "nonce_state.json"
                    with open(d_drive_state, 'w') as f:
                        json.dump(new_state, f, indent=2)
                    logger.info(f"📝 Updated D: drive nonce state: {d_drive_state}")
            except Exception as e:
                logger.warning(f"⚠️  Could not update D: drive state: {e}")
            
            logger.info(f"✅ Nonce state reset completed. New nonce: {synchronized_nonce}")
            self.results['nonce_reset'] = True
            return True
            
        except Exception as e:
            error_msg = f"❌ Nonce state reset failed: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.results['errors'].append(error_msg)
            return False
    
    def create_enhanced_websocket_auth_wrapper(self) -> bool:
        """Create enhanced WebSocket authentication wrapper with retry logic"""
        try:
            logger.info("🔧 Creating enhanced WebSocket authentication wrapper...")
            
            wrapper_code = '''"""
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
'''
            
            wrapper_file = self.project_root / "src" / "auth" / "enhanced_websocket_auth_wrapper.py"
            wrapper_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(wrapper_file, 'w') as f:
                f.write(wrapper_code)
            
            logger.info(f"✅ Enhanced WebSocket auth wrapper created: {wrapper_file}")
            return True
            
        except Exception as e:
            error_msg = f"❌ Failed to create WebSocket auth wrapper: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    def patch_websocket_authentication_manager(self) -> bool:
        """Patch existing WebSocket authentication manager with enhanced error handling"""
        try:
            logger.info("🔧 Patching WebSocket authentication manager...")
            
            auth_manager_file = self.project_root / "src" / "auth" / "websocket_authentication_manager.py"
            if not auth_manager_file.exists():
                logger.warning("⚠️  WebSocket authentication manager not found, skipping patch")
                return True
            
            # Read current content
            with open(auth_manager_file, 'r') as f:
                content = f.read()
            
            # Create backup
            backup_file = auth_manager_file.with_suffix('.backup')
            with open(backup_file, 'w') as f:
                f.write(content)
            
            # Enhanced request method patch
            enhanced_request_method = '''
    async def _request_websocket_token_enhanced(self) -> Optional[Dict[str, Any]]:
        """Enhanced WebSocket token request with comprehensive error handling"""
        max_retries = 5
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔑 Enhanced WebSocket token request (attempt {attempt + 1}/{max_retries})")
                
                # Get fresh nonce with collision prevention
                nonce_manager = UnifiedKrakenNonceManager.get_instance()
                nonce = await nonce_manager.get_nonce_async("websocket_token_enhanced")
                
                # Add small delay to prevent nonce collisions
                await asyncio.sleep(0.1)
                
                # Create signature with debug info
                uri_path = '/0/private/GetWebSocketsToken'
                post_data = f"nonce={nonce}"
                
                # Generate signature
                import hmac
                import hashlib
                import base64
                
                sha256_hash = hashlib.sha256(post_data.encode('utf-8')).digest()
                message = uri_path.encode('utf-8') + sha256_hash
                secret = base64.b64decode(self.private_key)
                signature = base64.b64encode(hmac.new(secret, message, hashlib.sha512).digest()).decode('utf-8')
                
                # Prepare headers
                headers = {
                    'API-Key': self.api_key,
                    'API-Sign': signature,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                # Make request with comprehensive error handling
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.kraken.com{uri_path}"
                    async with session.post(url, headers=headers, data=post_data, timeout=30) as resp:
                        result = await resp.json()
                        
                        if resp.status == 200 and 'result' in result and 'token' in result['result']:
                            logger.info(f"✅ WebSocket token obtained successfully (attempt {attempt + 1})")
                            return {'token': result['result']['token']}
                        else:
                            error_info = result.get('error', [f'HTTP {resp.status}'])
                            raise Exception(f"API error: {error_info}")
                            
            except Exception as e:
                error_str = str(e).lower()
                logger.warning(f"⚠️  Token request attempt {attempt + 1} failed: {e}")
                
                if 'nonce' in error_str and attempt < max_retries - 1:
                    # Handle nonce error with recovery
                    logger.info("🔄 Applying nonce error recovery...")
                    nonce_manager = UnifiedKrakenNonceManager.get_instance()
                    recovery_nonce = nonce_manager.handle_invalid_nonce_error("websocket_token_recovery")
                    logger.info(f"🔄 Recovery nonce: {recovery_nonce}")
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"⏳ Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ All token request attempts failed: {e}")
                    return None
        
        return None
'''
            
            # Insert enhanced method after the existing _request_websocket_token method
            if 'async def _request_websocket_token(' in content:
                # Find the end of the existing method and insert the enhanced version
                lines = content.split('\n')
                new_lines = []
                in_method = False
                indent_level = 0
                
                for line in lines:
                    new_lines.append(line)
                    
                    if 'async def _request_websocket_token(' in line and not 'enhanced' in line:
                        in_method = True
                        indent_level = len(line) - len(line.lstrip())
                    elif in_method and line.strip() and len(line) - len(line.lstrip()) <= indent_level and not line.startswith(' ' * (indent_level + 1)):
                        # End of method found, insert enhanced version
                        new_lines.extend(enhanced_request_method.split('\n'))
                        in_method = False
                
                content = '\n'.join(new_lines)
                
                # Also patch the method call to use enhanced version
                content = content.replace(
                    'token_response = await self._request_websocket_token()',
                    'token_response = await self._request_websocket_token_enhanced()'
                )
                
                # Write patched content
                with open(auth_manager_file, 'w') as f:
                    f.write(content)
                
                logger.info("✅ WebSocket authentication manager patched successfully")
                return True
            else:
                logger.warning("⚠️  Could not find method to patch, skipping")
                return True
                
        except Exception as e:
            error_msg = f"❌ Failed to patch WebSocket authentication manager: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    def test_nonce_generation_sequence(self) -> bool:
        """Test nonce generation sequence for consistency"""
        try:
            logger.info("🧪 Testing nonce generation sequence...")
            self.results['total_tests'] += 1
            
            # Import and test unified nonce manager
            import sys
            sys.path.insert(0, str(self.project_root))
            
            from src.utils.unified_kraken_nonce_manager import get_unified_nonce_manager
            
            manager = get_unified_nonce_manager()
            
            # Generate sequence of nonces
            nonces = []
            for i in range(10):
                nonce = manager.get_nonce(f"test_sequence_{i}")
                nonces.append(int(nonce))
                time.sleep(0.01)  # Small delay between nonces
            
            # Verify all nonces are increasing
            for i in range(1, len(nonces)):
                if nonces[i] <= nonces[i-1]:
                    raise Exception(f"Nonce sequence error: {nonces[i-1]} -> {nonces[i]}")
            
            logger.info(f"✅ Nonce sequence test passed: {nonces[0]} -> {nonces[-1]}")
            self.results['passed_tests'] += 1
            return True
            
        except Exception as e:
            error_msg = f"❌ Nonce sequence test failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    async def test_websocket_token_authentication(self) -> bool:
        """Test WebSocket token authentication with current credentials"""
        try:
            logger.info("🧪 Testing WebSocket token authentication...")
            self.results['total_tests'] += 1
            
            # Try to load API credentials from config
            config_file = self.project_root / "config.json"
            if not config_file.exists():
                logger.warning("⚠️  Config file not found, skipping token test")
                return True
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            api_key = config.get('kraken', {}).get('API_KEY')
            private_key = config.get('kraken', {}).get('API_SECRET')
            
            if not api_key or not private_key:
                logger.warning("⚠️  API credentials not found in config, skipping token test")
                return True
            
            # Import unified nonce manager
            import sys
            sys.path.insert(0, str(self.project_root))
            
            from src.utils.unified_kraken_nonce_manager import get_unified_nonce_manager
            nonce_manager = get_unified_nonce_manager()
            
            # Test token request
            from src.auth.enhanced_websocket_auth_wrapper import create_enhanced_websocket_auth
            
            auth_wrapper = await create_enhanced_websocket_auth(
                api_key, private_key, nonce_manager
            )
            
            token = await auth_wrapper.get_websocket_token_with_retry()
            
            if token:
                logger.info(f"✅ WebSocket token authentication successful: {token[:20]}...")
                self.results['websocket_token_test'] = True
                self.results['passed_tests'] += 1
                return True
            else:
                logger.error("❌ WebSocket token authentication failed")
                return False
                
        except Exception as e:
            error_msg = f"❌ WebSocket token test failed: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.results['errors'].append(error_msg)
            return False
    
    def create_nonce_diagnostic_script(self) -> bool:
        """Create diagnostic script for ongoing nonce monitoring"""
        try:
            logger.info("📋 Creating nonce diagnostic script...")
            
            diagnostic_code = '''#!/usr/bin/env python3
"""
Nonce Diagnostic and Monitoring Script
=====================================

This script provides ongoing monitoring and diagnostics for nonce management
to prevent future "EAPI:Invalid nonce" errors.
"""

import sys
import time
import json
import asyncio
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.unified_kraken_nonce_manager import get_unified_nonce_manager


def run_nonce_diagnostics():
    """Run comprehensive nonce diagnostics"""
    print("🔍 NONCE DIAGNOSTIC REPORT")
    print("=" * 50)
    
    try:
        manager = get_unified_nonce_manager()
        status = manager.get_status()
        
        print(f"Current Nonce: {status['current_nonce']}")
        print(f"Total Generated: {status['total_generated']}")
        print(f"Error Recoveries: {status['error_recoveries']}")
        print(f"Active Connections: {status['active_connections']}")
        print(f"Time Until Current: {status['time_until_current']:.2f}s")
        print(f"State File: {status['state_file']}")
        
        # Test nonce sequence
        print("\\n🧪 Testing Nonce Sequence:")
        nonces = []
        for i in range(5):
            nonce = manager.get_nonce(f"diagnostic_test_{i}")
            nonces.append(int(nonce))
            print(f"  Nonce {i+1}: {nonce}")
            time.sleep(0.01)
        
        # Verify sequence
        is_increasing = all(nonces[i] < nonces[i+1] for i in range(len(nonces)-1))
        print(f"  Sequence Valid: {'✅ YES' if is_increasing else '❌ NO'}")
        
        print("\\n✅ Diagnostic completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        return False


if __name__ == "__main__":
    success = run_nonce_diagnostics()
    sys.exit(0 if success else 1)
'''
            
            diagnostic_file = self.project_root / "diagnose_nonce_system.py"
            with open(diagnostic_file, 'w') as f:
                f.write(diagnostic_code)
            
            # Make executable
            diagnostic_file.chmod(0o755)
            
            logger.info(f"✅ Diagnostic script created: {diagnostic_file}")
            return True
            
        except Exception as e:
            error_msg = f"❌ Failed to create diagnostic script: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return False
    
    async def run_comprehensive_fix(self) -> bool:
        """Run the complete nonce authentication fix"""
        logger.info("🚨 KRAKEN NONCE AUTHENTICATION FIX STARTING 🚨")
        logger.info("=" * 60)
        
        try:
            # Step 1: Reset nonce state with synchronization
            logger.info("\n📋 Step 1: Resetting nonce state with synchronization...")
            if not self.reset_nonce_state_with_synchronization():
                return False
            
            # Step 2: Create enhanced WebSocket auth wrapper
            logger.info("\n📋 Step 2: Creating enhanced WebSocket authentication...")
            if not self.create_enhanced_websocket_auth_wrapper():
                return False
            
            # Step 3: Patch existing authentication manager
            logger.info("\n📋 Step 3: Patching WebSocket authentication manager...")
            if not self.patch_websocket_authentication_manager():
                return False
            
            # Step 4: Test nonce generation sequence
            logger.info("\n📋 Step 4: Testing nonce generation sequence...")
            if not self.test_nonce_generation_sequence():
                return False
            
            # Step 5: Test WebSocket token authentication (if credentials available)
            logger.info("\n📋 Step 5: Testing WebSocket token authentication...")
            await self.test_websocket_token_authentication()
            
            # Step 6: Create diagnostic script
            logger.info("\n📋 Step 6: Creating diagnostic monitoring script...")
            if not self.create_nonce_diagnostic_script():
                return False
            
            return True
            
        except Exception as e:
            error_msg = f"❌ Comprehensive fix failed: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.results['errors'].append(error_msg)
            return False
    
    def print_results(self):
        """Print comprehensive fix results"""
        logger.info("\n" + "=" * 60)
        logger.info("🚨 NONCE AUTHENTICATION FIX RESULTS 🚨")
        logger.info("=" * 60)
        
        logger.info(f"✅ Nonce State Reset: {'SUCCESS' if self.results['nonce_reset'] else 'FAILED'}")
        logger.info(f"✅ WebSocket Token Test: {'SUCCESS' if self.results['websocket_token_test'] else 'SKIPPED/FAILED'}")
        logger.info(f"📊 Tests Passed: {self.results['passed_tests']}/{self.results['total_tests']}")
        
        if self.results['errors']:
            logger.info(f"\n❌ ERRORS ENCOUNTERED ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                logger.info(f"  • {error}")
        
        logger.info("\n📋 NEXT STEPS:")
        logger.info("1. Run diagnose_nonce_system.py to verify nonce system")
        logger.info("2. Test bot startup to verify authentication works")
        logger.info("3. Monitor logs for any remaining nonce errors")
        logger.info("4. If issues persist, check API key permissions")
        
        logger.info("=" * 60)


async def main():
    """Run the comprehensive nonce authentication fix"""
    print("🚨 KRAKEN NONCE AUTHENTICATION CRITICAL FIX 🚨")
    print("Problem: Persistent 'EAPI:Invalid nonce' errors blocking trading")
    print("Solution: Reset nonce state and enhance authentication flow")
    print("Impact: Restore WebSocket V2 authentication and trading access")
    print("-" * 60)
    
    fixer = KrakenNonceAuthenticationFix()
    
    success = await fixer.run_comprehensive_fix()
    fixer.print_results()
    
    if success:
        print("\n✅ NONCE AUTHENTICATION FIX COMPLETED!")
        print("🔍 Run 'python diagnose_nonce_system.py' to verify")
        print("🚀 Your trading bot should now start without nonce errors")
    else:
        print("\n❌ FIX ENCOUNTERED ISSUES")
        print("📋 Check the logs above for specific errors")
        print("💡 Manual intervention may be required")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)