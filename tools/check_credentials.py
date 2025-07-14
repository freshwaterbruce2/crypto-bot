#!/usr/bin/env python3
"""Quick API credential validator - Windows Safe"""
import os
from pathlib import Path

def quick_check():
    print("=== KRAKEN API CREDENTIAL QUICK CHECK ===")
    
    env_file = Path('.env')
    if not env_file.exists():
        print("[ERROR] .env file not found!")
        print("Run: setup_api_keys.bat")
        return False
    
    # Read .env file
    with open('.env', 'r') as f:
        content = f.read()
    
    key = secret = None
    for line in content.split('\n'):
        if line.startswith('KRAKEN_API_KEY='):
            key = line.split('=', 1)[1].strip()
        elif line.startswith('KRAKEN_SECRET='):
            secret = line.split('=', 1)[1].strip()
    
    # Check for placeholder values
    issues = []
    if not key or 'your_' in key or 'PUT_YOUR' in key:
        issues.append("[ERROR] API key is placeholder")
    if not secret or 'your_' in secret or 'PUT_YOUR' in secret:
        issues.append("[ERROR] Secret key is placeholder")
    
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
        print("\nSOLUTION:")
        print("1. Run: setup_api_keys.bat")
        print("2. Replace placeholder values with real credentials")
        return False
    else:
        print("[SUCCESS] API credentials look valid!")
        print(f"Key: {key[:8]}...{key[-4:]}")
        print(f"Secret: {'*' * 20}")
        return True

if __name__ == "__main__":
    quick_check()
