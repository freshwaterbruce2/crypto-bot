@echo off
echo ========================================
echo FULL DISK CLEANUP - Free 1.5GB+
echo ========================================
echo.
echo This will clean:
echo - C: drive bot logs (1.4GB)
echo - D: drive trading logs (53MB+)
echo - Python cache files
echo - Empty directories
echo.
pause

echo.
echo Step 1: Cleaning C: drive logs...
echo ========================================

cd /d "C:\projects050625\projects\active\tool-crypto-trading-bot-2025"

:: Delete the huge logs
if exist "kraken_infinity_bot.log" (
    echo Deleting kraken_infinity_bot.log (1.2GB)...
    del /f /q "kraken_infinity_bot.log"
)

if exist "bot_output.log" (
    echo Deleting bot_output.log (112MB)...
    del /f /q "bot_output.log"
)

if exist "bot_output_fixed.log" (
    echo Deleting bot_output_fixed.log (80MB)...
    del /f /q "bot_output_fixed.log"
)

:: Delete all .log files in root
del /f /q *.log 2>nul

echo.
echo Step 2: Cleaning D: drive logs...
echo ========================================

if exist "D:\trading_data\logs" (
    cd /d "D:\trading_data\logs"
    
    :: Archive old logs before deleting (optional)
    :: move *.log backups\ 2>nul
    
    :: Delete all log files
    echo Deleting D:\trading_data\logs\*.log files...
    del /f /q *.log 2>nul
    
    :: Clean backup directories if they're too large
    if exist "backups\*.log" (
        echo Cleaning old backups...
        del /f /q "backups\*.log" 2>nul
    )
    
    if exist "compressed\*.log" (
        del /f /q "compressed\*.log" 2>nul
    )
)

if exist "D:\trading_bot_data\logs" (
    cd /d "D:\trading_bot_data\logs"
    del /f /q *.log 2>nul
)

echo.
echo Step 3: Cleaning Python cache...
echo ========================================

cd /d "C:\projects050625\projects\active\tool-crypto-trading-bot-2025"

:: Delete all __pycache__ directories
for /d /r %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)

:: Delete all .pyc files
del /s /f /q *.pyc 2>nul

echo.
echo Step 4: Additional cleanup...
echo ========================================

:: Clean test outputs
if exist "tests\*.log" del /f /q "tests\*.log" 2>nul
if exist "tests\test_outputs\*" del /f /q "tests\test_outputs\*" 2>nul

:: Clean any .tmp files
del /s /f /q *.tmp 2>nul

:: Clean trading_data logs
if exist "trading_data\logs\*.log" del /f /q "trading_data\logs\*.log" 2>nul

echo.
echo ========================================
echo CLEANUP COMPLETE!
echo ========================================
echo.
echo Freed approximately 1.5GB+ of disk space!
echo.
echo Note: The bot will create new log files when it runs.
echo Consider setting up automatic log rotation to prevent
echo logs from growing too large in the future.
echo.
pause