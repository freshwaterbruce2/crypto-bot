@echo off
cls
echo ===============================================
echo    KRAKEN TRADING BOT - WINDOWS LAUNCHER
echo ===============================================
echo.

REM Change to the correct directory
cd /d "C:\dev\tools\crypto-trading-bot-2025"

REM Check if we're in the right directory by looking for main.py
if not exist "main.py" (
    echo ERROR: Not in correct directory or main.py missing
    echo Expected: C:\dev\tools\crypto-trading-bot-2025\
    echo Current: %CD%
    echo Looking for: main.py
    dir main.py 2>nul
    pause
    exit /b 1
)

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.9+ and add to PATH
    pause
    exit /b 1
)

echo ✅ Bot files verified
echo ✅ Python installation verified

echo Starting Kraken Trading Bot...
echo.

REM Run the main bot launcher
python main.py

echo.
echo Bot session ended.
pause
