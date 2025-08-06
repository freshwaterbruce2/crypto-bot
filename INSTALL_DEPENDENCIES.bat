@echo off
cls
echo ===============================================
echo   INSTALL MISSING DEPENDENCIES - WINDOWS
echo ===============================================
echo.

echo Installing ALL MISSING DEPENDENCIES...
echo.

echo Installing CRITICAL database dependencies...
pip install aiosqlite>=0.19.0

echo Installing web framework dependencies...
pip install fastapi>=0.104.0
pip install pydantic>=2.5.0
pip install uvicorn>=0.24.0

echo Installing orchestrator dependencies...
pip install watchdog>=3.0.0
pip install rich>=13.0.0
pip install psutil>=5.9.0

echo Installing all requirements from requirements.txt...
pip install -r requirements.txt

echo.
echo ✅ All dependencies installed!
echo.
echo You can now run orchestrated mode:
echo   python main.py --orchestrated
echo   or
echo   START_TRADING_BOT.bat (select option 2)
echo.
pause