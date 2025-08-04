@echo off
REM Launch WSL and setup trading bot

echo ====================================
echo Kraken Trading Bot - WSL Setup
echo ====================================
echo.

REM Check if WSL is installed
wsl --status >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: WSL is not installed!
    echo.
    echo Please install WSL first:
    echo 1. Open PowerShell as Administrator
    echo 2. Run: wsl --install
    echo 3. Restart your computer
    echo 4. Run this script again
    echo.
    pause
    exit /b 1
)

echo Launching WSL to set up trading bot...
echo.

REM Create setup commands
echo Creating setup script in WSL...

REM Launch WSL and run setup
wsl -e bash -c "cd ~ && mkdir -p wsl-bot-setup && cd wsl-bot-setup && echo 'Downloading setup files...' && cp -r /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025/wsl-setup/* . 2>/dev/null || echo 'Please copy setup files manually' && ls -la && echo 'Run: bash quick_setup.sh' && echo 'To start setup in WSL' && bash"

echo.
echo WSL session ended.
pause
