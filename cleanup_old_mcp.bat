@echo off
echo ========================================
echo Cleaning Up Old MCP Configuration
echo ========================================
echo.

REM Check if old config exists
if exist "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json" (
    echo Found old MCP config at:
    echo C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json
    echo.
    
    REM Backup the old config just in case
    echo Creating backup...
    copy "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json" "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json.backup" >nul 2>&1
    
    REM Remove the old config
    echo Removing old config...
    del "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json"
    
    if exist "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json" (
        echo [ERROR] Failed to remove old config file
    ) else (
        echo [SUCCESS] Old config removed
    )
) else (
    echo No old config file found - already clean\!
)

echo.
echo ========================================
echo Checking for other MCP-related files...
echo ========================================

REM Check for any MCP server installations in npm global
echo.
echo Checking npm global packages for MCP servers...
where npm >nul 2>&1
if %errorlevel% equ 0 (
    npm list -g --depth=0 2>nul  < /dev/null |  findstr "@modelcontextprotocol"
    if %errorlevel% equ 0 (
        echo.
        echo Found global MCP packages. To remove them, run:
        echo npm uninstall -g @modelcontextprotocol/server-filesystem
        echo npm uninstall -g @modelcontextprotocol/server-memory
        echo npm uninstall -g @anthropic-ai/dxt
    ) else (
        echo No global MCP packages found
    )
) else (
    echo npm not found - skipping global package check
)

echo.
echo ========================================
echo Cleanup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Restart Claude Desktop
echo 2. Go to Settings -^> Extensions
echo 3. Install MCP servers using the new .dxt extension format
echo.
pause
