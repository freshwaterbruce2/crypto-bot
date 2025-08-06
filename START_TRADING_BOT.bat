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
echo ✅ Unified launcher ready

echo.
echo Available launch modes:
echo   - Interactive mode selection (default)
echo   - Simple mode: python main.py --simple
echo   - Orchestrated mode: python main.py --orchestrated
echo   - Paper trading: python main.py --paper
echo   - Component tests: python main.py --test
echo   - Status check: python main.py --status
echo.

echo Starting unified launcher...
echo Press Ctrl+C to interrupt at any time
echo.

REM Run the unified launcher in interactive mode
python main.py

echo.
echo Launcher session ended.
echo Check logs in D:\trading_data\logs\ for details
pause
