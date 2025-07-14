# Claude Code Installation Script for Windows 11 with WSL
# Run this script as Administrator

Write-Host "Claude Code Installation Script" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Step 1: Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))
{
    Write-Host "This script needs to be run as Administrator. Exiting..." -ForegroundColor Red
    exit 1
}

Write-Host "`nStep 1: Installing WSL..." -ForegroundColor Yellow

# Install WSL with Ubuntu
try {
    wsl --install -d Ubuntu
    Write-Host "WSL installation initiated. You may need to restart your computer." -ForegroundColor Green
} catch {
    Write-Host "WSL might already be installed or there was an error: $_" -ForegroundColor Yellow
}

# Check WSL status
Write-Host "`nChecking WSL status..." -ForegroundColor Yellow
wsl --status

Write-Host "`n================================" -ForegroundColor Green
Write-Host "IMPORTANT: After restart, complete the following steps:" -ForegroundColor Yellow
Write-Host "1. Open Ubuntu from Start Menu and create a username/password" -ForegroundColor White
Write-Host "2. Run the following commands in Ubuntu terminal:" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "   # Update packages" -ForegroundColor Cyan
Write-Host "   sudo apt update && sudo apt upgrade -y" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "   # Install Node.js via NodeSource (Node 20.x)" -ForegroundColor Cyan
Write-Host "   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -" -ForegroundColor Gray
Write-Host "   sudo apt-get install -y nodejs" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "   # Verify Node.js installation" -ForegroundColor Cyan
Write-Host "   node --version" -ForegroundColor Gray
Write-Host "   npm --version" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "   # Install Claude Code globally" -ForegroundColor Cyan
Write-Host "   sudo npm install -g @anthropic-ai/claude-code" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "   # Authenticate Claude Code" -ForegroundColor Cyan
Write-Host "   claude auth" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "   # Test Claude Code" -ForegroundColor Cyan
Write-Host "   claude" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "================================" -ForegroundColor Green

Read-Host "`nPress Enter to exit"
