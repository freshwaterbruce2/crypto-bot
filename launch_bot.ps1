# Crypto Trading Bot Launcher for Windows PowerShell
# Run this script in PowerShell on Windows 11

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "CRYPTO TRADING BOT LAUNCHER" -ForegroundColor Cyan  
Write-Host "======================================" -ForegroundColor Cyan

# Check Python installation
Write-Host "`nChecking Python installation..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found! Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

$pythonPath = $pythonCmd.Path
Write-Host "Python found at: $pythonPath" -ForegroundColor Green

# Navigate to bot directory
$botPath = "C:\dev\tools\crypto-trading-bot-2025"
if (-not (Test-Path $botPath)) {
    Write-Host "ERROR: Bot directory not found at $botPath" -ForegroundColor Red
    exit 1
}

Set-Location $botPath
Write-Host "Bot directory: $botPath" -ForegroundColor Green

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found! Please create one with your API keys" -ForegroundColor Red
    exit 1
}
Write-Host "Configuration file found" -ForegroundColor Green

# Launch the bot
Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "LAUNCHING TRADING BOT..." -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the bot" -ForegroundColor Yellow
Write-Host ""

# Run the bot with proper error handling
try {
    & python main.py --simple
} catch {
    Write-Host "`nBot stopped or encountered an error: $_" -ForegroundColor Red
}

Write-Host "`nBot has stopped." -ForegroundColor Yellow