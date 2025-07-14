@echo off
echo ====================================
echo Direct WSL Enabler for Windows 11
echo ====================================
echo.
echo IMPORTANT: This must be run as Administrator!
echo If you see "Access Denied" errors, please:
echo 1. Right-click this file
echo 2. Select "Run as administrator"
echo.
pause

echo.
echo Enabling Windows Subsystem for Linux...
C:\Windows\System32\dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

echo.
echo Enabling Virtual Machine Platform...
C:\Windows\System32\dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

echo.
echo ====================================
echo FEATURES ENABLED!
echo ====================================
echo.
echo NEXT STEPS:
echo 1. RESTART your computer NOW
echo 2. After restart, open Command Prompt as Admin
echo 3. Run: wsl --install -d Ubuntu
echo 4. Follow Ubuntu setup
echo 5. Use setup_claude_ubuntu.sh for Claude Code
echo.
echo ====================================
pause
