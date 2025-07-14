@echo off
cls
echo ===============================================
echo    KRAKEN TRADING BOT - WINDOWS LAUNCHER
echo ===============================================
echo.

REM Change to the correct directory
cd /d "C:\projects050625\projects\active\tool-crypto-trading-bot-2025"

REM Check if we're in the right directory by looking for the actual bot
if not exist "src\core\bot.py" (
    echo ERROR: Not in correct directory or bot files missing
    echo Expected: C:\projects050625\projects\active\tool-crypto-trading-bot-2025\
    echo Current: %CD%
    echo Looking for: src\core\bot.py
    dir src 2>nul
    pause
    exit /b 1
)

REM Additional verification
if not exist "launch_trading_bot.py" (
    echo ERROR: Main launcher not found
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo ✅ Bot files verified

echo Starting Kraken Trading Bot...
echo.

REM Run the smart launcher
python launch_trading_bot.py

echo.
echo Bot session ended.
pause
