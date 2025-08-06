@echo off
REM ============================================================================
REM SIMPLE MODE LAUNCHER - CRYPTO TRADING BOT
REM Launches the bot in simple mode with core functionality only
REM ============================================================================

title Simple Mode Bot Launcher
color 0B

echo.
echo ==========================================
echo    SIMPLE MODE BOT LAUNCHER
echo ==========================================
echo.
echo This will launch the crypto trading bot in
echo SIMPLE mode with core functionality only
echo.
echo Features:
echo   - Core trading engine
echo   - Basic monitoring
echo   - Standard logging
echo   - Essential safety checks
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

echo Checking simple mode availability...
python main.py --info | findstr "Simple Mode"
if errorlevel 1 (
    echo WARNING: Simple mode status unclear
    echo Proceeding with launch attempt...
)

echo.
echo Ready to launch SIMPLE MODE BOT
echo.
echo This will start the bot with:
echo - Core trading functionality
echo - Basic error handling
echo - Standard position management
echo - Essential logging
echo.

set /p confirm="Launch simple mode bot? (Y/N): "

if /i not "%confirm%"=="Y" (
    echo Launch cancelled by user
    pause
    exit /b 0
)

echo.
echo Launching Simple Mode Bot...
echo ==========================================
echo Press Ctrl+C to stop the bot safely
echo ==========================================
echo.

REM Launch the bot in simple mode
python main.py --simple

if errorlevel 1 (
    echo.
    echo Bot launch failed or stopped with error
    echo Check the logs for error details
    pause
    exit /b 1
)

echo.
echo Simple mode bot has stopped
echo Check logs in D:\trading_data\logs\ for details
pause