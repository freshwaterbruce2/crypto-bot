@echo off
echo ========================================
echo Upgrading python-kraken-sdk to latest version
echo ========================================
echo.

REM Uninstall old version
echo Uninstalling old version...
python -m pip uninstall -y python-kraken-sdk

REM Install latest version
echo.
echo Installing latest version (3.2.2)...
python -m pip install python-kraken-sdk==3.2.2

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install python-kraken-sdk
    echo Trying with --user flag...
    python -m pip install --user python-kraken-sdk==3.2.2
)

echo.
echo ========================================
echo Testing import...
echo ========================================
python -c "from kraken.spot import SpotWSClient; print('Success! SpotWSClient imported correctly')"

if errorlevel 1 (
    echo.
    echo ERROR: Import test failed
    echo Please run test_kraken_import.py for diagnostics
) else (
    echo.
    echo Installation successful!
)

pause