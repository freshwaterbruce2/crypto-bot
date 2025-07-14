@echo off
REM ULTIMATE BOT LAUNCHER - NO CACHE ISSUES
REM This script prevents ALL Python cache problems

echo ===============================================
echo KRAKEN TRADING BOT - CACHE-FREE LAUNCHER
echo ===============================================

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

REM Launch bot with cache disabled
echo [LAUNCH] Starting bot with cache disabled...
python -B scripts/live_launch.py

echo [DONE] Bot launcher finished
pause