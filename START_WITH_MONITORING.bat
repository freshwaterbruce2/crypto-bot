@echo off
REM =================================================================
REM Start Crypto Trading Bot with Production Monitoring
REM =================================================================
REM
REM This script launches the trading bot with comprehensive monitoring:
REM - Real-time health checks every 5 minutes
REM - Web dashboard on http://localhost:8000
REM - Alert system with configurable thresholds
REM - Emergency shutdown capabilities
REM
REM Usage: Double-click this file or run from command prompt
REM =================================================================

title Crypto Trading Bot - Production Monitor

echo.
echo =========================================================
echo    CRYPTO TRADING BOT - PRODUCTION MONITORING
echo =========================================================
echo.
echo Starting trading bot with comprehensive monitoring...
echo.
echo Features:
echo   * Real-time health checks every 5 minutes
echo   * Web dashboard: http://localhost:8000
echo   * Emergency shutdown capabilities
echo   * Performance tracking and alerts
echo.
echo Dashboard will be available at: http://localhost:8000
echo Press Ctrl+C to stop the bot safely
echo.
echo =========================================================
echo.

REM Change to project directory
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start bot with monitoring
python launch_with_monitoring.py --config production

REM Pause on error
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start bot with monitoring
    echo Check the logs above for details
    echo.
    pause
)

echo.
echo Bot stopped. Press any key to exit...
pause > nul