@echo off
REM ============================================================================
REM PAPER TRADING SETUP VALIDATOR
REM This script validates the paper trading environment setup
REM ============================================================================

title Paper Trading Setup Validator
color 0E

echo.
echo ==========================================
echo    🔧 PAPER TRADING SETUP VALIDATOR
echo ==========================================
echo.
echo This script will validate your paper trading
echo environment is properly configured.
echo.

REM Change to the project directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python not found
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo ✅ Python found: 
python --version
echo.

REM Check if validation script exists
if not exist "validate_paper_trading_setup.py" (
    echo ❌ ERROR: Validation script not found
    echo Please ensure you're in the correct directory
    pause
    exit /b 1
)

echo 🔍 Running comprehensive setup validation...
echo.

REM Run the validation script
python validate_paper_trading_setup.py

if errorlevel 1 (
    echo.
    echo ==========================================
    echo    ❌ SETUP VALIDATION FAILED
    echo ==========================================
    echo.
    echo Please fix the errors shown above and run
    echo this script again before attempting to
    echo launch paper trading.
    echo.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo    ✅ SETUP VALIDATION SUCCESSFUL
echo ==========================================
echo.
echo Your paper trading environment is properly
echo configured and ready to use.
echo.
echo Next steps:
echo 1. Run LAUNCH_PAPER_TRADING.bat to start
echo 2. Use CHECK_PAPER_STATUS.bat to monitor
echo 3. Check paper_trading_data/ for reports
echo.
echo For advanced monitoring, run:
echo python monitor_paper_trading.py --continuous
echo.
pause