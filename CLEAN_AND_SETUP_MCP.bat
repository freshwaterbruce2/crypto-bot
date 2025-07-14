@echo off
echo ========================================
echo MCP Configuration Cleanup and Setup
echo ========================================
echo.

echo Step 1: Backing up existing configurations...
echo ----------------------------------------

REM Backup old Claude Desktop config
if exist "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json" (
    echo Backing up old Claude Desktop config...
    copy "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json" "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json.old" >nul 2>&1
    echo [DONE] Backup created
)

REM Backup project MCP config
if exist ".mcp.json" (
    echo Backing up project .mcp.json...
    copy ".mcp.json" ".mcp.json.backup" >nul 2>&1
    echo [DONE] Project MCP config backed up
)

echo.
echo Step 2: Removing old configurations...
echo ----------------------------------------

REM Remove old Claude Desktop config
if exist "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json" (
    del "C:\Users\fresh_zxae3v6\AppData\Roaming\Claude\claude_desktop_config.json"
    echo [DONE] Removed old Claude Desktop config
)

REM Remove local .mcp.json (old Claude Code style)
if exist ".mcp.json" (
    del ".mcp.json"
    echo [DONE] Removed project .mcp.json
)

echo.
echo Step 3: Checking for global npm packages...
echo ----------------------------------------

where npm >nul 2>&1
if %errorlevel% equ 0 (
    echo Checking for MCP-related npm packages...
    npm list -g --depth=0 2>nul  < /dev/null |  findstr "@modelcontextprotocol @anthropic-ai/dxt"
    if %errorlevel% equ 0 (
        echo.
        echo [WARNING] Found global MCP packages
        echo To remove them manually, run:
        echo   npm uninstall -g @modelcontextprotocol/server-filesystem
        echo   npm uninstall -g @modelcontextprotocol/server-memory
        echo   npm uninstall -g @anthropic-ai/dxt
    ) else (
        echo [OK] No global MCP packages found
    )
)

echo.
echo ========================================
echo Cleanup Complete\!
echo ========================================
echo.
echo What's Next:
echo ------------
echo 1. RESTART Claude Desktop completely
echo 2. Go to Settings -^> Extensions
echo 3. Look for these extensions to install:
echo    - Filesystem MCP Server
echo    - Memory MCP Server
echo    - Any trading-related extensions
echo.
echo OR use the new .dxt extension format for one-click installs\!
echo.
echo Your old configs have been backed up:
echo - Claude Desktop: %%APPDATA%%\Claude\claude_desktop_config.json.old
echo - Project MCP: .mcp.json.backup
echo.
pause
