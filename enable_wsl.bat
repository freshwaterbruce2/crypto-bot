@echo off
echo ===================================
echo WSL and Claude Code Installer
echo ===================================
echo.
echo This script will enable WSL and install Ubuntu.
echo Please run this as Administrator!
echo.

REM Enable WSL and Virtual Machine Platform
echo Step 1: Enabling Windows Subsystem for Linux...
powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList 'Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart'"

echo.
echo Step 2: Enabling Virtual Machine Platform...
powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList 'Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart'"

echo.
echo Step 3: Downloading and installing WSL2 Linux kernel...
echo Please wait...
curl -L -o wsl_update_x64.msi https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi
msiexec /i wsl_update_x64.msi /quiet
del wsl_update_x64.msi

echo.
echo Step 4: Setting WSL 2 as default...
wsl --set-default-version 2 2>nul

echo.
echo ===================================
echo IMPORTANT: RESTART REQUIRED!
echo ===================================
echo.
echo 1. Restart your computer now
echo 2. After restart, run this command in PowerShell as Admin:
echo    wsl --install -d Ubuntu
echo 3. Then follow the Ubuntu setup steps in the guide
echo.
echo ===================================
pause
