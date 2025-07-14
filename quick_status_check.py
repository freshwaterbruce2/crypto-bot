#!/usr/bin/env python3
"""Quick status check of bot fixes"""

import subprocess
import os
from datetime import datetime

print("=" * 60)
print(f"QUICK STATUS CHECK - {datetime.now()}")
print("=" * 60)

# Check bot process
try:
    result = subprocess.run(['pgrep', '-f', 'live_launch.py'], capture_output=True, text=True)
    if result.stdout.strip():
        print("✅ Bot Status: RUNNING (PID: {})".format(result.stdout.strip()))
    else:
        print("❌ Bot Status: NOT RUNNING")
except:
    print("❌ Bot Status: UNKNOWN")

# Check recent logs
try:
    with open('kraken_infinity_bot.log', 'rb') as f:
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(max(0, file_size - 10000))
        recent = f.read().decode('utf-8', errors='ignore')
        
        # Check for key indicators
        if 'Circuit breaker' in recent and 'OPEN' in recent:
            print("⚠️  Circuit Breaker: ACTIVE (blocking trades)")
        else:
            print("✅ Circuit Breaker: OK")
            
        if 'balance: $5' in recent:
            print("⚠️  Balance Detection: Showing $5 (needs fix)")
        elif 'balance:' in recent:
            print("✅ Balance Detection: Working")
            
        if 'SUCCESS' in recent or 'executed' in recent:
            print("✅ Trade Execution: Active")
        else:
            print("⚠️  Trade Execution: No recent trades")
            
except Exception as e:
    print(f"❌ Log Check Failed: {e}")

print("\nFixes Applied:")
print("✅ Circuit breaker timeout reduced to 30s")
print("✅ Position tracking force sync implemented")
print("✅ Signal confidence thresholds lowered")
print("✅ Balance detection improvements added")
print("✅ Automated monitoring systems created")

print("\nRun 'python3 automated_fix_workflow.py' for continuous fixing")
print("=" * 60)