@echo off
echo ========================================
echo Installing python-kraken-sdk
echo ========================================
echo.

REM Check if pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not installed or not in PATH
    pause
    exit /b 1
)

REM Install python-kraken-sdk
echo Installing python-kraken-sdk...
python -m pip install python-kraken-sdk

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install python-kraken-sdk
    echo Please try running this command manually:
    echo python -m pip install python-kraken-sdk
    echo.
    echo If you get an "externally-managed-environment" error, try:
    echo python -m pip install --user python-kraken-sdk
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo You can now run the trading bot.
pause