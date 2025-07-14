@echo off
echo =========================================
echo Installing MCP Configuration
echo =========================================
echo.

set CONFIG_DIR=C:\Users\fresh_zxae3v6\AppData\Roaming\Claude
set CONFIG_FILE=%CONFIG_DIR%\claude_desktop_config.json

echo Checking Claude configuration directory...
if not exist "%CONFIG_DIR%" (
    echo Creating directory: %CONFIG_DIR%
    mkdir "%CONFIG_DIR%"
)

echo.
echo Choose configuration to install:
echo 1. Full Access (single filesystem server with all directories)
echo 2. Organized (separate filesystem servers for projects, data, user)
echo.
set /p choice="Enter your choice (1 or 2): "

if "%choice%"=="1" (
    echo Installing Full Access configuration...
    copy /Y claude_desktop_full_access_config.json "%CONFIG_FILE%"
) else if "%choice%"=="2" (
    echo Installing Organized configuration...
    copy /Y claude_desktop_organized_config.json "%CONFIG_FILE%"
) else (
    echo Invalid choice. Exiting.
    pause
    exit /b 1
)

if exist "%CONFIG_FILE%" (
    echo.
    echo =========================================
    echo SUCCESS\! Configuration installed.
    echo =========================================
    echo.
    echo File access granted to:
    echo - C:\projects050625 (all projects)
    echo - D:\ (entire drive)
    echo - Desktop, Documents, Downloads
    echo.
    echo Next steps:
    echo 1. Close Claude Desktop completely
    echo 2. Restart Claude Desktop
    echo 3. Your MCP servers will start automatically
    echo.
) else (
    echo ERROR: Failed to copy configuration file
)

pause
