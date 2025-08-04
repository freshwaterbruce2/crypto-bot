@echo off
REM ============================================================================
REM SECURE PAPER TRADING LAUNCHER FOR CRYPTO TRADING BOT
REM This script launches the bot in SAFE paper trading mode only
REM NO REAL FUNDS AT RISK - ALL TRADING IS SIMULATED
REM ============================================================================

title Paper Trading Bot Launcher
color 0A

echo.
echo ==========================================
echo    🧪 PAPER TRADING BOT LAUNCHER
echo ==========================================
echo.
echo This will launch the crypto trading bot in
echo SAFE paper trading mode with NO REAL MONEY
echo.
echo ✅ Paper trading mode ENABLED
echo ✅ Live trading DISABLED  
echo ✅ All trades are SIMULATED
echo ✅ Starting balance: $150 USD
echo ✅ Maximum loss limit: $20 USD
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

REM Check if validation script exists
if not exist "validate_paper_trading_setup.py" (
    echo ❌ ERROR: Validation script not found
    echo Please ensure you're in the correct directory
    pause
    exit /b 1
)

echo 🔍 Step 1: Validating paper trading setup...
echo.
python validate_paper_trading_setup.py
if errorlevel 1 (
    echo ❌ VALIDATION FAILED
    echo Please fix the errors above before launching
    pause
    exit /b 1
)

echo.
echo ✅ VALIDATION PASSED
echo.

REM Ask for confirmation
echo ==========================================
echo Ready to launch PAPER TRADING BOT
echo ==========================================
echo.
echo This will start the bot in paper trading mode with:
echo • Virtual starting balance: $150 USDT
echo • Trading pair: SHIB/USDT  
echo • Position size: $5-10 per trade
echo • Maximum 3 concurrent positions
echo • Daily loss limit: $20
echo • Circuit breaker at $30 loss
echo.
set /p confirm="🚀 Launch paper trading bot? (Y/N): "

if /i not "%confirm%"=="Y" (
    echo Launch cancelled by user
    pause
    exit /b 0
)

echo.
echo 🧪 Launching Paper Trading Bot...
echo ==========================================
echo Press Ctrl+C to stop the bot safely
echo ==========================================
echo.

REM Set environment variables for paper trading
set PAPER_TRADING_ENABLED=true
set LIVE_TRADING_DISABLED=true
set TRADING_MODE=paper
set FORCE_PAPER_MODE=true

REM Launch the paper trading bot
python launch_paper_trading.py

if errorlevel 1 (
    echo.
    echo ❌ Bot launch failed
    echo Check the logs for error details
    pause
    exit /b 1
)

echo.
echo 🛑 Paper trading bot has stopped
echo Check paper_trading_data/reports/ for performance reports
pause