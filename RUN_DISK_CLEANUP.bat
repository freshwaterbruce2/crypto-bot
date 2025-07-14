@echo off
echo === DISK SPACE EMERGENCY CLEANUP ===
echo.
echo This will run disk space analysis and cleanup scripts
echo Make sure you are running as Administrator!
echo.
pause

cd /d "C:\projects050625\projects\active\tool-crypto-trading-bot-2025"

echo.
echo === STEP 1: ANALYZING DISK SPACE ===
echo.
powershell -ExecutionPolicy Bypass -File "DISK_SPACE_ANALYZER.ps1"

echo.
echo === STEP 2: RUNNING AGGRESSIVE CLEANUP ===
echo.
powershell -ExecutionPolicy Bypass -File "AGGRESSIVE_DISK_CLEANUP.ps1"

echo.
echo === CLEANUP COMPLETE ===
echo.
pause