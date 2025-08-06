@echo off
echo 🚀 STARTING KRAKEN TRADING BOT - MEMORY OPTIMIZED EDITION
echo ============================================================

REM Set memory optimization environment variables
set PYTHONHASHSEED=0
set PYTHONOPTIMIZE=1
set PYTHONDONTWRITEBYTECODE=1
set PYTHONUNBUFFERED=1

REM Disable pandas high memory features if available
set PANDAS_MAX_MEMORY_USAGE=100MB
set NUMBA_DISABLE_JIT=1

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo ✅ Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  No virtual environment found, using system Python
)

REM Set Python path
set PYTHONPATH=%cd%;%cd%\src

echo ✅ Memory optimization flags set
echo ✅ Python path: %PYTHONPATH%
echo ✅ Starting bot in memory-efficient mode...

REM Try orchestrated mode first, fall back to simple if memory issues
echo Attempting orchestrated mode...
python main.py --orchestrated

if errorlevel 1 (
    echo.
    echo ⚠️  Orchestrated mode failed, trying simple mode...
    python main.py --simple
)

echo.
echo Bot execution completed. Press any key to exit...
pause >nul