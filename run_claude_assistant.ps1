# PowerShell script to run Claude Code assistant for the trading bot
# This script helps you interact with Claude Code in WSL

Write-Host "[INFO] Claude Code Trading Bot Assistant" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

$projectPath = "$PSScriptRoot"
Write-Host "[INFO] Project path: $projectPath" -ForegroundColor Yellow

# Check if WSL is available
try {
    $wslPath = "C:\Windows\System32\wsl.exe"
    if (-not (Test-Path $wslPath)) {
        Write-Host "[ERROR] WSL executable not found at $wslPath" -ForegroundColor Red
        exit 1
    }
    Write-Host "[INFO] WSL found at $wslPath" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Error checking WSL: $_" -ForegroundColor Red
    exit 1
}

# Function to run a command in WSL
function Invoke-WSLCommand {
    param (
        [string]$Command
    )
    
    try {
        Write-Host "[INFO] Running command in WSL..." -ForegroundColor Yellow
        & $wslPath -e bash -c "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && $Command"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[WARNING] Command exited with code $LASTEXITCODE" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[ERROR] Error running WSL command: $_" -ForegroundColor Red
    }
}

# Menu options
function Show-Menu {
    Write-Host "`n[MENU] Choose an option:" -ForegroundColor Cyan
    Write-Host "1. Run the trading system completion tool" -ForegroundColor White
    Write-Host "2. Start Claude Code in interactive mode" -ForegroundColor White
    Write-Host "3. Run a specific Claude Code command" -ForegroundColor White
    Write-Host "4. Check trading bot status" -ForegroundColor White
    Write-Host "5. Exit" -ForegroundColor White
    
    $choice = Read-Host "`nEnter your choice (1-5)"
    
    switch ($choice) {
        "1" {
            Write-Host "[ACTION] Running trading system completion tool..." -ForegroundColor Green
            Invoke-WSLCommand "./finish_trading_system.sh"
        }
        "2" {
            Write-Host "[ACTION] Starting Claude Code in interactive mode..." -ForegroundColor Green
            Invoke-WSLCommand "claude"
        }
        "3" {
            $claudeCommand = Read-Host "Enter Claude Code command"
            Write-Host "[ACTION] Running command: $claudeCommand" -ForegroundColor Green
            Invoke-WSLCommand "echo '$claudeCommand' | claude"
        }
        "4" {
            Write-Host "[ACTION] Checking trading bot status..." -ForegroundColor Green
            Invoke-WSLCommand "python -c \"import os; print('[INFO] Files in src directory:'); [print(f) for f in os.listdir('src') if os.path.isdir(os.path.join('src', f))]\" 2>/dev/null || echo '[ERROR] Python not available or directory not found'"
        }
        "5" {
            Write-Host "[INFO] Exiting..." -ForegroundColor Yellow
            exit 0
        }
        default {
            Write-Host "[ERROR] Invalid choice. Please try again." -ForegroundColor Red
            Show-Menu
        }
    }
    
    # Return to menu after command completes
    Show-Menu
}

# Start the menu
Show-Menu 