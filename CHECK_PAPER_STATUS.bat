@echo off
REM ============================================================================
REM PAPER TRADING STATUS CHECKER
REM Quick status check for paper trading bot
REM ============================================================================

title Paper Trading Status Checker
color 0B

echo.
echo ==========================================
echo    📊 PAPER TRADING STATUS CHECK
echo ==========================================
echo.

REM Change to the project directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python not found
    pause
    exit /b 1
)

REM Run the monitoring script for a single check
echo Running status check...
echo.

python monitor_paper_trading.py

if errorlevel 1 (
    echo.
    echo ❌ Status check failed
    pause
    exit /b 1
)

echo.
echo ✅ Status check completed
echo.
echo For continuous monitoring, run:
echo python monitor_paper_trading.py --continuous
echo.
pause