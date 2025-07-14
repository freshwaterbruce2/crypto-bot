@echo off
echo ============================================
echo Kraken Trading Bot - Production Launch
echo ============================================
echo.

REM Start the monitoring dashboard in a new window
echo Starting monitoring dashboard...
start "Trading Monitor" cmd /k python monitor_live_trading.py

REM Wait a moment for monitor to initialize
timeout /t 2 /nobreak > nul

REM Start the trading bot
echo Starting trading bot...
python scripts/live_launch.py

echo.
echo ============================================
echo Bot stopped. Press any key to exit...
pause > nul