@echo off
REM ============================================================================
REM ORCHESTRATED MODE LAUNCHER - CRYPTO TRADING BOT
REM Launches the bot with full orchestration, monitoring, and diagnostics
REM ============================================================================

title Orchestrated Mode Bot Launcher
color 0E

echo.
echo ==========================================
echo    ORCHESTRATED MODE BOT LAUNCHER
echo ==========================================
echo.
echo This will launch the crypto trading bot in
echo ORCHESTRATED mode with full system monitoring
echo.
echo Features included:
echo   - Full system orchestration
echo   - Advanced health monitoring
echo   - Comprehensive diagnostics
echo   - Real-time performance tracking
echo   - WebSocket-first architecture
echo   - Interactive dashboard (optional)
echo   - Emergency response systems
echo.

REM Change to the project directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo ERROR: main.py not found
    echo Please ensure you're in the correct directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo Checking orchestrated mode availability...
python main.py --info | findstr "Orchestrated Mode"
if errorlevel 1 (
    echo WARNING: Orchestrated mode may not be available
    echo Check if main_orchestrated.py exists...
    if not exist "main_orchestrated.py" (
        echo ERROR: main_orchestrated.py not found
        echo Orchestrated mode is not available
        pause
        exit /b 1
    )
)

echo.
echo Ready to launch ORCHESTRATED MODE BOT
echo.
echo This will start the bot with:
echo - Full system orchestration
echo - Advanced health monitoring
echo - Comprehensive logging and diagnostics
echo - WebSocket-first initialization
echo - Real-time performance metrics
echo - Emergency response capabilities
echo.

set /p confirm="Launch orchestrated mode bot? (Y/N): "

if /i not "%confirm%"=="Y" (
    echo Launch cancelled by user
    pause
    exit /b 0
)

echo.
echo Launching Orchestrated Mode Bot...
echo ==========================================
echo Press Ctrl+C to stop the bot safely
echo Full diagnostics will be available
echo ==========================================
echo.

REM Launch the bot in orchestrated mode
python main.py --orchestrated

if errorlevel 1 (
    echo.
    echo Bot launch failed or stopped with error
    echo Check the logs for detailed error information
    echo Emergency diagnostics may have been exported
    pause
    exit /b 1
)

echo.
echo Orchestrated mode bot has stopped
echo Check logs in D:\trading_data\logs\ for details
echo Check for any exported diagnostic files
pause