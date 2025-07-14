@echo off
echo ========================================
echo Closing ALL Trading Bot Instances
echo ========================================
echo.

echo Killing all Python processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM python3.exe 2>nul
taskkill /F /IM pythonw.exe 2>nul

echo Killing specific bot processes...
taskkill /F /FI "WINDOWTITLE eq *kraken*" 2>nul
taskkill /F /FI "WINDOWTITLE eq *trading*" 2>nul
taskkill /F /FI "WINDOWTITLE eq *bot*" 2>nul

echo.
echo Checking for any remaining processes...
tasklist | findstr /I python

if errorlevel 1 (
    echo.
    echo ✓ All Python processes have been closed!
) else (
    echo.
    echo ⚠ Some Python processes may still be running.
    echo Try closing them manually in Task Manager.
)

echo.
echo ========================================
echo Cleanup Complete
echo ========================================
pause