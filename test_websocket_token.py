#!/usr/bin/env python3
"""
Test WebSocket Token Manager
============================

Test script to verify WebSocket authentication tokens work with the WebSocket API key.
"""

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.utils.websocket_token_manager import get_websocket_token_manager
from src.utils.dual_api_credentials import get_websocket_credentials

async def test_websocket_credentials():
    """Test WebSocket credentials are loaded"""
    print("🔐 Testing WebSocket Credentials...")
    
    try:
        ws_creds = get_websocket_credentials()
        
        print(f"   ✅ WebSocket API Key: {ws_creds.api_key[:8]}...")
        print(f"   ✅ WebSocket API Secret: {ws_creds.api_secret[:8]}...")
        print(f"   ✅ Service Type: {ws_creds.service_type}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ WebSocket credentials test failed: {e}")
        return False

async def test_websocket_token_request():
    """Test WebSocket token request using WebSocket credentials"""
    print("\n📡 Testing WebSocket Token Request...")
    
    try:
        token_manager = get_websocket_token_manager()
        
        print("   🔄 Requesting WebSocket authentication token...")
        token = await token_manager.get_websocket_token()
        
        if token:
            print(f"   ✅ WebSocket token obtained: {token[:16]}...")
            print(f"   ✅ Token length: {len(token)} characters")
            
            # Check token status
            status = token_manager.get_status()
            print(f"   ✅ Token valid: {status['token_valid']}")
            print(f"   ✅ Time until expiry: {status['time_until_expiry']:.0f} seconds")
            
            return True
        else:
            print("   ❌ Failed to obtain WebSocket token")
            return False
            
    except Exception as e:
        print(f"   ❌ WebSocket token test failed: {e}")
        return False

async def main():
    """Run WebSocket token tests"""
    print("🚀 WEBSOCKET TOKEN MANAGER TEST")
    print("=" * 40)
    
    tests = [
        ("WebSocket Credentials", test_websocket_credentials),
        ("WebSocket Token Request", test_websocket_token_request)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("\n" + "=" * 40)
    print("📊 WEBSOCKET TOKEN TEST SUMMARY")
    print("=" * 40)
    print(f"Tests: {passed}/{total} passed")
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    if passed == total:
        print("\n🎉 WEBSOCKET TOKEN SYSTEM WORKING!")
        print("✅ WebSocket API key can authenticate")
        print("✅ Permission issue should be resolved")
        print("✅ Ready to test full bot launch")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed")
        print("🔧 Check WebSocket API key permissions")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        sys.exit(1)