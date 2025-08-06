@echo off
echo ===============================================
echo 🚀 LAUNCHING TRADING BOT WITH NONCE FIX
echo ===============================================
echo.

echo ✅ Activating Python environment...
cd /d "%~dp0"

echo ✅ Checking for .env file...
if not exist .env (
    echo ❌ ERROR: .env file not found!
    echo Please create .env file with your Kraken API credentials:
    echo KRAKEN_REST_API_KEY=your_api_key_here
    echo KRAKEN_REST_API_SECRET=your_api_secret_here
    pause
    exit /b 1
)

echo ✅ .env file found

echo.
echo 🔧 Starting bot with nonce collision prevention...
echo.

python launch_fixed_bot.py

echo.
echo ===============================================
echo 🏁 Bot session ended
echo ===============================================
pause