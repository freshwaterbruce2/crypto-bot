@echo off
REM ULTIMATE BOT LAUNCHER - NO CACHE ISSUES
REM This script prevents ALL Python cache problems

echo ===============================================
echo KRAKEN TRADING BOT - CACHE-FREE LAUNCHER
echo ===============================================

REM Change to correct directory
cd /d "C:\dev\tools\crypto-trading-bot-2025"

REM Set environment to prevent cache creation
set PYTHONDONTWRITEBYTECODE=1
set PYTHONUNBUFFERED=1

REM Clean any existing cache
echo [CLEANUP] Removing any existing Python cache...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
del /s /q *cpython-313* 2>nul

echo [CACHE] Cache cleanup complete!

REM Check if main.py exists
if not exist "main.py" (
    echo [ERROR] main.py not found in current directory
    echo Current: %CD%
    pause
    exit /b 1
)

REM Launch bot with cache disabled using unified launcher
echo [LAUNCH] Starting unified launcher with cache disabled...
echo Available modes: --simple, --orchestrated, --paper, --test
echo.
python -B main.py --simple

echo [DONE] Bot launcher finished
pause