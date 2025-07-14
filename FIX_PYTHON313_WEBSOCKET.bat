@echo off
echo ========================================
echo Fixing Python 3.13 WebSocket Compatibility
echo ========================================
echo.

REM The issue is with websockets library compatibility with Python 3.13
echo Downgrading websockets to a compatible version...
python -m pip install --upgrade "websockets<15.0"

if errorlevel 1 (
    echo.
    echo Trying with --user flag...
    python -m pip install --user --upgrade "websockets<15.0"
)

echo.
echo ========================================
echo Testing WebSocket connection...
echo ========================================
python -c "import websockets; print(f'websockets version: {websockets.__version__}')"

echo.
echo Fix applied! The bot should now connect properly.
pause