@echo off
echo ====================================
echo KRAKEN TRADING BOT - OPTIMIZED START
echo ====================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate
    echo [OK] Virtual environment activated
)

REM Check API keys
if "%KRAKEN_API_KEY%"=="" (
    echo [WARNING] KRAKEN_API_KEY not set - loading from .env
)

echo.
echo Starting Kraken Trading Bot...
echo - USDT pairs only
echo - $5 minimum trades
echo - Fee-free profit optimization
echo - Buy low, sell high strategy
echo.

REM Launch bot with proper error handling
python launch_trading_bot.py

if errorlevel 1 (
    echo.
    echo [ERROR] Bot exited with error!
    echo Check logs in D:\trading_bot_data\logs\
    pause
)

echo.
echo Bot stopped.
pause
