@echo off
echo 🚀 STARTING KRAKEN TRADING BOT - 2025 OPTIMIZED EDITION
echo ============================================================

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo ✅ Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  No virtual environment found, using system Python
)

REM Set environment variables for 2025 optimization
set PYTHONPATH=%cd%;%cd%\src
set KRAKEN_OPTIMIZATION_2025=true
set TRADING_MODE=live
set LOG_LEVEL=INFO

echo ✅ Environment configured for 2025 trading
echo ✅ Python path: %PYTHONPATH%
echo ✅ Starting bot with ultra-low latency mode...

REM Start the bot with 2025 optimizations
python src\core\bot.py

echo.
echo Bot execution completed. Press any key to exit...
pause >nul
