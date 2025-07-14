@echo off
echo ========================================
echo EMERGENCY DISK CLEANUP - Free 1.4GB
echo ========================================
echo.
echo Current disk usage: 98.7%% CRITICAL!
echo This will delete log files and cache to free up space.
echo.
pause

echo.
echo Step 1: Deleting large log files...
echo ----------------------------------------

:: Delete the huge 1.2GB log file
if exist "kraken_infinity_bot.log" (
    echo Deleting kraken_infinity_bot.log (1.2GB)...
    del /f /q "kraken_infinity_bot.log"
)

:: Delete other large logs
if exist "bot_output.log" (
    echo Deleting bot_output.log (112MB)...
    del /f /q "bot_output.log"
)

if exist "bot_output_fixed.log" (
    echo Deleting bot_output_fixed.log (80MB)...
    del /f /q "bot_output_fixed.log"
)

if exist "balance_manager_test.log" (
    echo Deleting balance_manager_test.log...
    del /f /q "balance_manager_test.log"
)

echo.
echo Step 2: Cleaning Python cache files...
echo ----------------------------------------

:: Delete all __pycache__ directories recursively
for /d /r %%d in (__pycache__) do (
    if exist "%%d" (
        echo Removing cache: %%d
        rmdir /s /q "%%d" 2>nul
    )
)

:: Delete all .pyc files
echo Removing compiled Python files...
for /r %%f in (*.pyc) do (
    if exist "%%f" del /f /q "%%f" 2>nul
)

echo.
echo Step 3: Cleaning old logs in subdirectories...
echo ----------------------------------------

:: Clean logs directory
if exist "logs\profiling\*.log" (
    echo Cleaning logs\profiling directory...
    del /f /q "logs\profiling\*.log" 2>nul
)

if exist "logs\*.log" (
    echo Cleaning logs directory...
    del /f /q "logs\*.log" 2>nul
)

:: Clean trading_data logs
if exist "trading_data\logs\*.log" (
    echo Cleaning trading_data\logs directory...
    del /f /q "trading_data\logs\*.log" 2>nul
)

echo.
echo ========================================
echo CLEANUP COMPLETE!
echo ========================================
echo.
echo Approximately 1.4GB of disk space freed!
echo.
echo The bot will recreate necessary log files when it runs.
echo Python cache files will be regenerated automatically.
echo.
pause