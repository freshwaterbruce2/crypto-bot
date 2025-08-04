import subprocess
import os
import sys

print("WSL and Claude Code Diagnostic Tool")
print("=" * 50)

# Test 1: Check if wsl.exe exists
wsl_path = r"C:\Windows\System32\wsl.exe"
print(f"\n1. Checking if WSL exists at {wsl_path}")
if os.path.exists(wsl_path):
    print("   [OK] WSL executable found")
    print(f"   File size: {os.path.getsize(wsl_path)} bytes")
else:
    print("   [FAIL] WSL executable NOT found")

# Test 2: Try to get WSL distributions
print("\n2. Attempting to list WSL distributions...")
try:
    # Try with shell=True
    result = subprocess.run([wsl_path, "--list"], 
                          capture_output=True, 
                          text=True, 
                          shell=True)
    if result.returncode == 0:
        print("   [OK] WSL distributions:")
        print(result.stdout)
    else:
        print(f"   [FAIL] Error code: {result.returncode}")
        print(f"   Error: {result.stderr}")
except Exception as e:
    print(f"   [FAIL] Exception: {e}")

# Test 3: Try alternative methods
print("\n3. Trying alternative launch methods...")

# Method A: Using os.system
print("   A. Using os.system()...")
try:
    exit_code = os.system(f'"{wsl_path}" --list 2>nul')
    print(f"      Exit code: {exit_code}")
except Exception as e:
    print(f"      Exception: {e}")

# Method B: Check environment variables
print("\n4. Checking environment variables...")
path_var = os.environ.get('PATH', '')
if 'System32' in path_var:
    print("   [OK] System32 is in PATH")
else:
    print("   [FAIL] System32 is NOT in PATH")

# Test 5: Testing batch file execution
print("\n5. Testing batch file execution...")
test_bat = r"C:\projects050625\projects\active\tool-crypto-trading-bot-2025\mcp_server\test_wsl.bat"
with open(test_bat, 'w') as f:
    f.write('@echo off\n')
    f.write('echo Testing WSL access...\n')
    f.write('C:\\Windows\\System32\\wsl.exe --list\n')
    f.write('echo Exit code: %errorlevel%\n')

try:
    result = subprocess.run([test_bat], capture_output=True, text=True, shell=True)
    print("   Batch file output:")
    print(result.stdout)
    if result.stderr:
        print("   Errors:")
        print(result.stderr)
except Exception as e:
    print(f"   Exception: {e}")
finally:
    # Clean up
    if os.path.exists(test_bat):
        os.remove(test_bat)

print("\n" + "=" * 50)
print("Diagnostic complete.")
