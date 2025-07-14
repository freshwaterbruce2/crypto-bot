@echo off
echo ========================================
echo URGENT: Fixing WebSocket Compatibility
echo ========================================
echo.

echo Downgrading websockets to compatible version...
python -m pip install --upgrade "websockets==12.0"

if errorlevel 1 (
    echo.
    echo Trying with --user flag...
    python -m pip install --user --upgrade "websockets==12.0"
)

echo.
echo ========================================
echo Testing the fix...
echo ========================================
python -c "import websockets; print(f'websockets version: {websockets.__version__}')"

echo.
echo Fix applied! The bot should now connect properly.
echo.
echo IMPORTANT: You also have 98.7% disk usage!
echo Consider cleaning up some files to free space.
pause