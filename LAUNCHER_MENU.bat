@echo off
REM ============================================================================
REM CRYPTO TRADING BOT - LAUNCHER MENU
REM Comprehensive menu system for all launch options
REM ============================================================================

title Crypto Trading Bot - Launcher Menu
color 0A

:MAIN_MENU
cls
echo.
echo ============================================================
echo    CRYPTO TRADING BOT - UNIFIED LAUNCHER MENU
echo ============================================================
echo.
echo Select your launch option:
echo.
echo   1. Interactive Mode       - Guided mode selection
echo   2. Simple Mode            - Core functionality only  
echo   3. Orchestrated Mode      - Full monitoring system
echo   4. Paper Trading          - Safe simulation mode
echo   5. Component Tests        - Validate installation
echo   6. Status Check           - Check running status
echo   7. Environment Info       - System information
echo   8. Cache-Free Launch      - Launch without Python cache
echo.
echo   9. View Launch Options    - Show all command-line options
echo   0. Quick Documentation    - Usage examples
echo.
echo   Q. Quit                   - Exit launcher menu
echo.
echo ============================================================

set /p choice="Enter your choice [1-9, 0, Q]: "

if /i "%choice%"=="1" goto INTERACTIVE_MODE
if /i "%choice%"=="2" goto SIMPLE_MODE
if /i "%choice%"=="3" goto ORCHESTRATED_MODE
if /i "%choice%"=="4" goto PAPER_TRADING
if /i "%choice%"=="5" goto COMPONENT_TESTS
if /i "%choice%"=="6" goto STATUS_CHECK
if /i "%choice%"=="7" goto ENVIRONMENT_INFO
if /i "%choice%"=="8" goto CACHE_FREE_LAUNCH
if /i "%choice%"=="9" goto LAUNCH_OPTIONS
if /i "%choice%"=="0" goto DOCUMENTATION
if /i "%choice%"=="Q" goto QUIT

echo Invalid choice. Please try again.
pause
goto MAIN_MENU

:INTERACTIVE_MODE
cls
echo.
echo ==========================================
echo    INTERACTIVE MODE LAUNCH
echo ==========================================
echo.
echo This will start the unified launcher in interactive mode
echo where you can select options through a guided interface.
echo.
pause
python main.py
goto MAIN_MENU

:SIMPLE_MODE
cls
echo.
echo ==========================================
echo    SIMPLE MODE LAUNCH
echo ==========================================
echo.
echo This will start the bot in simple mode with:
echo - Core trading functionality
echo - Basic monitoring
echo - Essential error handling
echo.
pause
python main.py --simple
goto MAIN_MENU

:ORCHESTRATED_MODE
cls
echo.
echo ==========================================
echo    ORCHESTRATED MODE LAUNCH
echo ==========================================
echo.
echo This will start the bot with full orchestration:
echo - Advanced health monitoring
echo - Comprehensive diagnostics
echo - WebSocket-first architecture
echo - Real-time performance tracking
echo.
pause
python main.py --orchestrated
goto MAIN_MENU

:PAPER_TRADING
cls
echo.
echo ==========================================
echo    PAPER TRADING MODE LAUNCH
echo ==========================================
echo.
echo This will start the bot in SAFE paper trading mode:
echo - NO REAL MONEY AT RISK
echo - All trades are simulated
echo - Perfect for testing strategies
echo - Starting balance: $150 virtual USD
echo.
pause
python main.py --paper
goto MAIN_MENU

:COMPONENT_TESTS
cls
echo.
echo ==========================================
echo    COMPONENT TESTS
echo ==========================================
echo.
echo This will run comprehensive component tests to validate:
echo - Nonce system functionality
echo - Exchange connectivity
echo - Bot initialization
echo - Configuration validation
echo.
pause
python main.py --test
goto MAIN_MENU

:STATUS_CHECK
cls
echo.
echo ==========================================
echo    STATUS CHECK
echo ==========================================
echo.
echo Checking current bot status...
echo.
python main.py --status
echo.
pause
goto MAIN_MENU

:ENVIRONMENT_INFO
cls
echo.
echo ==========================================
echo    ENVIRONMENT INFORMATION
echo ==========================================
echo.
echo Displaying system and environment information...
echo.
python main.py --info
echo.
pause
goto MAIN_MENU

:CACHE_FREE_LAUNCH
cls
echo.
echo ==========================================
echo    CACHE-FREE LAUNCH
echo ==========================================
echo.
echo This will launch the bot with Python cache disabled
echo to prevent any cache-related issues.
echo.
pause
call LAUNCH_BOT_NO_CACHE.bat
goto MAIN_MENU

:LAUNCH_OPTIONS
cls
echo.
echo ==========================================
echo    AVAILABLE LAUNCH OPTIONS
echo ==========================================
echo.
echo Command-line usage:
echo   python main.py [MODE] [OPTIONS]
echo.
echo Available modes:
echo   --simple           Simple bot mode
echo   --orchestrated     Orchestrated mode
echo   --paper            Paper trading mode
echo   --test             Component tests
echo   --status           Status check
echo   --info             Environment info
echo.
echo Available options:
echo   --config FILE      Use specific config file
echo   --verbose          Enable verbose logging
echo   --dry-run          Validate config only
echo   --help             Show help message
echo.
echo Batch file launchers:
echo   START_TRADING_BOT.bat         - Main launcher
echo   LAUNCH_SIMPLE_MODE.bat        - Simple mode
echo   LAUNCH_ORCHESTRATED_MODE.bat  - Orchestrated mode
echo   LAUNCH_PAPER_TRADING.bat      - Paper trading
echo   LAUNCH_BOT_NO_CACHE.bat       - Cache-free launch
echo   CHECK_BOT_STATUS.bat          - Status checker
echo.
echo Shell script (Linux/WSL):
echo   ./launch_bot.sh [MODE]        - Unix launcher
echo.
pause
goto MAIN_MENU

:DOCUMENTATION
cls
echo.
echo ==========================================
echo    QUICK DOCUMENTATION
echo ==========================================
echo.
echo USAGE EXAMPLES:
echo.
echo 1. First time setup:
echo    python main.py --test
echo    python main.py --info
echo.
echo 2. Safe testing:
echo    python main.py --paper
echo.
echo 3. Live trading:
echo    python main.py --simple        (basic)
echo    python main.py --orchestrated  (advanced)
echo.
echo 4. Troubleshooting:
echo    python main.py --status
echo    call LAUNCH_BOT_NO_CACHE.bat
echo.
echo IMPORTANT NOTES:
echo - Always test with paper trading first
echo - Check status before launching multiple instances
echo - Use cache-free launch if experiencing issues
echo - Logs are stored in D:\trading_data\logs\
echo.
echo FILES AND DIRECTORIES:
echo - main.py              : Unified launcher
echo - config.json          : Main configuration
echo - .env                 : Environment variables
echo - src/                 : Source code
echo - D:\trading_data\     : Data and logs (Windows)
echo.
pause
goto MAIN_MENU

:QUIT
cls
echo.
echo ==========================================
echo    EXITING LAUNCHER MENU
echo ==========================================
echo.
echo Thank you for using the Crypto Trading Bot!
echo.
echo For support:
echo - Check logs in D:\trading_data\logs\
echo - Run component tests if issues occur
echo - Use paper trading mode for safe testing
echo.
pause
exit /b 0