# WSL Installation Script - Run as Administrator
# This script properly enables WSL on Windows 11

Write-Host "WSL and Claude Code Setup - Phase 1" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    Write-Host "This script MUST be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click on PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Checking current Windows features..." -ForegroundColor Yellow

# Enable Windows Subsystem for Linux
Write-Host "`nStep 1: Enabling Windows Subsystem for Linux..." -ForegroundColor Cyan
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine Platform
Write-Host "`nStep 2: Enabling Virtual Machine Platform..." -ForegroundColor Cyan
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Download and install WSL2 kernel update
Write-Host "`nStep 3: Downloading WSL2 Linux kernel update..." -ForegroundColor Cyan
$kernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
$kernelPath = "$env:TEMP\wsl_update_x64.msi"

try {
    Invoke-WebRequest -Uri $kernelUrl -OutFile $kernelPath -UseBasicParsing
    Write-Host "Installing WSL2 kernel update..." -ForegroundColor Yellow
    Start-Process msiexec.exe -ArgumentList "/i", $kernelPath, "/quiet" -Wait
    Remove-Item $kernelPath
    Write-Host "WSL2 kernel update installed successfully!" -ForegroundColor Green
} catch {
    Write-Host "Could not download/install WSL2 kernel. You may need to install it manually." -ForegroundColor Yellow
}

Write-Host "`n====================================" -ForegroundColor Green
Write-Host "RESTART REQUIRED!" -ForegroundColor Red
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. RESTART your computer" -ForegroundColor White
Write-Host "2. After restart, open PowerShell as Administrator again" -ForegroundColor White
Write-Host "3. Run: wsl --install -d Ubuntu" -ForegroundColor White
Write-Host "4. Follow the Ubuntu setup prompts" -ForegroundColor White
Write-Host "5. Use the setup_claude_ubuntu.sh script to install Claude Code" -ForegroundColor White
Write-Host ""
Write-Host "====================================" -ForegroundColor Green
Read-Host "Press Enter to exit (then restart your computer)"
