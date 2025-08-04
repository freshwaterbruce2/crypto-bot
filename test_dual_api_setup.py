#!/usr/bin/env python3
"""
Test Dual API Setup
===================

Test script to verify the dual API key configuration is working correctly.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.utils.dual_api_credentials import (
    get_credentials_manager,
    get_rest_credentials, 
    get_websocket_credentials,
    has_dual_key_setup
)

def test_credential_loading():
    """Test that credentials load correctly"""
    print("🔐 Testing Dual API Credential Loading...")
    
    try:
        manager = get_credentials_manager()
        status = manager.get_status()
        
        print(f"   ✅ REST API Available: {status['rest_available']}")
        print(f"   ✅ WebSocket API Available: {status['websocket_available']}")
        print(f"   ✅ Separate Keys: {status['separate_keys']}")
        print(f"   ✅ Nonce Protection: {status['nonce_collision_protected']}")
        
        if status['rest_available']:
            print(f"   📋 REST Key Preview: {status['rest_key_preview']}")
        
        if status['websocket_available']:
            print(f"   📋 WebSocket Key Preview: {status['websocket_key_preview']}")
        
        return status['rest_available'] and status['websocket_available']
        
    except Exception as e:
        print(f"   ❌ Credential loading failed: {e}")
        return False

def test_rest_credentials():
    """Test REST API credentials"""
    print("\n🌐 Testing REST API Credentials...")
    
    try:
        rest_creds = get_rest_credentials()
        
        print(f"   ✅ REST API Key: {rest_creds.api_key[:8]}...")
        print(f"   ✅ REST API Secret: {rest_creds.api_secret[:8]}...")
        print(f"   ✅ Service Type: {rest_creds.service_type}")
        
        # Validate key format
        if len(rest_creds.api_key) < 20:
            print(f"   ⚠️  REST API key seems short: {len(rest_creds.api_key)} chars")
            return False
        
        if len(rest_creds.api_secret) < 40:
            print(f"   ⚠️  REST API secret seems short: {len(rest_creds.api_secret)} chars")
            return False
        
        print("   ✅ REST credentials format valid")
        return True
        
    except Exception as e:
        print(f"   ❌ REST credential test failed: {e}")
        return False

def test_websocket_credentials():
    """Test WebSocket API credentials"""
    print("\n📡 Testing WebSocket API Credentials...")
    
    try:
        ws_creds = get_websocket_credentials()
        
        print(f"   ✅ WebSocket API Key: {ws_creds.api_key[:8]}...")
        print(f"   ✅ WebSocket API Secret: {ws_creds.api_secret[:8]}...")
        print(f"   ✅ Service Type: {ws_creds.service_type}")
        
        # Validate key format
        if len(ws_creds.api_key) < 20:
            print(f"   ⚠️  WebSocket API key seems short: {len(ws_creds.api_key)} chars")
            return False
        
        if len(ws_creds.api_secret) < 40:
            print(f"   ⚠️  WebSocket API secret seems short: {len(ws_creds.api_secret)} chars")
            return False
        
        print("   ✅ WebSocket credentials format valid")
        return True
        
    except Exception as e:
        print(f"   ❌ WebSocket credential test failed: {e}")
        return False

def test_nonce_separation():
    """Test that we have proper nonce separation"""
    print("\n🔒 Testing Nonce Collision Protection...")
    
    try:
        rest_creds = get_rest_credentials()
        ws_creds = get_websocket_credentials()
        
        if rest_creds.api_key == ws_creds.api_key:
            print("   ⚠️  Same API key used for both services")
            print("   ⚠️  Nonce collisions may still occur") 
            print("   💡 Consider creating separate API keys for optimal performance")
            return False
        else:
            print("   ✅ Different API keys detected")
            print("   ✅ Nonce collision protection active")
            print("   🎉 Optimal dual-key setup confirmed!")
            return True
            
    except Exception as e:
        print(f"   ❌ Nonce separation test failed: {e}")
        return False

def main():
    """Run all dual API tests"""
    print("🚀 DUAL API KEY SETUP VALIDATION")
    print("=" * 40)
    
    tests = [
        ("Credential Loading", test_credential_loading),
        ("REST API Credentials", test_rest_credentials),
        ("WebSocket API Credentials", test_websocket_credentials),
        ("Nonce Separation", test_nonce_separation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("\n" + "=" * 40)
    print("📊 DUAL API VALIDATION SUMMARY")
    print("=" * 40)
    print(f"Tests: {passed}/{total} passed")
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    if passed == total:
        print("\n🎉 DUAL API SETUP SUCCESSFUL!")
        print("✅ Separate API keys configured correctly")
        print("✅ Nonce collision protection active")
        print("✅ Ready for nonce-free trading!")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed")
        print("🔧 Check your API key configuration")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        sys.exit(1)