@echo off
echo ========================================
echo Full SDK Upgrade Process
echo ========================================
echo.

echo Step 1: Uninstalling old version...
python -m pip uninstall -y python-kraken-sdk

echo.
echo Step 2: Installing latest version (3.2.2)...
python -m pip install python-kraken-sdk==3.2.2

if errorlevel 1 (
    echo.
    echo Trying with --user flag...
    python -m pip install --user python-kraken-sdk==3.2.2
)

echo.
echo Step 3: Fixing websockets compatibility...
python -m pip install --upgrade "websockets<13.0"

if errorlevel 1 (
    python -m pip install --user --upgrade "websockets<13.0"
)

echo.
echo ========================================
echo Testing the upgrade...
echo ========================================
python -c "from kraken.spot import SpotWSClient; print('SUCCESS! SpotWSClient imported correctly')"

if errorlevel 1 (
    echo.
    echo Testing alternative import...
    python -c "import kraken; print(f'Kraken SDK version info: {dir(kraken)}')"
)

echo.
echo ========================================
echo Checking versions...
echo ========================================
python -m pip show python-kraken-sdk
python -m pip show websockets

echo.
echo Upgrade complete! The bot should now work with the latest SDK.
pause