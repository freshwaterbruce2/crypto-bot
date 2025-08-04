@echo off
REM Balance Manager V2 Fixes Test Runner
REM ===================================

echo Starting Balance Manager V2 Fixes Test...
echo.

cd /d "C:\dev\tools\crypto-trading-bot-2025"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please ensure Python is installed and accessible
    pause
    exit /b 1
)

REM Run the test with proper error handling
echo Running test script...
python test_balance_manager_fixes.py

set TEST_EXIT_CODE=%ERRORLEVEL%

echo.
echo Test completed with exit code: %TEST_EXIT_CODE%

if %TEST_EXIT_CODE% == 0 (
    echo SUCCESS: All tests passed - Balance Manager V2 fixes are working!
) else if %TEST_EXIT_CODE% == 2 (
    echo CRITICAL: NONCE AUTHENTICATION ISSUES DETECTED - Requires immediate attention
) else (
    echo WARNING: Some tests failed or were inconclusive
)

echo.
echo Check balance_manager_test.log for detailed output
echo Test results saved to balance_manager_test_results_*.json

pause