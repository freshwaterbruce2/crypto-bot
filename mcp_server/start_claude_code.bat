@echo off
REM Claude Code MCP Server Launcher for WSL

REM Try different ways to launch WSL
echo Attempting to start Claude Code MCP server in WSL...

REM Method 1: Direct wsl.exe path
C:\Windows\System32\wsl.exe --exec bash -lc "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && claude mcp serve" 2>nul
if %errorlevel% equ 0 goto :success

REM Method 2: Try wsl command if in PATH
wsl --exec bash -lc "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && claude mcp serve" 2>nul
if %errorlevel% equ 0 goto :success

REM Method 3: Try ubuntu.exe if installed from Microsoft Store
ubuntu.exe run "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && claude mcp serve" 2>nul
if %errorlevel% equ 0 goto :success

REM Method 4: Try with cmd /c
cmd /c "C:\Windows\System32\wsl.exe" --exec bash -lc "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && claude mcp serve" 2>nul
if %errorlevel% equ 0 goto :success

REM If all methods fail, show error
echo ERROR: Could not start Claude Code server in WSL
echo Please ensure:
echo 1. WSL is properly installed
echo 2. Ubuntu is installed in WSL
echo 3. Claude Code is installed in WSL (run: claude --version)
echo 4. You have proper permissions
exit /b 1

:success
echo Claude Code MCP server started successfully
