# PowerShell script to run Claude Code with our trading bot fixes prompt
# This script helps you use Claude Code with the prepared prompt

Write-Host "[INFO] Claude Code Trading Bot Fix Assistant" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

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

# Check if prompt files exist
$promptFiles = @(
    @{
        Name = "General Fixes Prompt";
        Path = Join-Path $projectPath "claude_prompt_trading_bot_fixes.md";
    },
    @{
        Name = "Trading Rules Prompt";
        Path = Join-Path $projectPath "claude_code_trading_rules_prompt.md";
    },
    @{
        Name = "Claude Code Rules";
        Path = Join-Path $projectPath "CLAUDE_CODE_RULES.md";
    }
)

foreach ($promptFile in $promptFiles) {
    if (-not (Test-Path $promptFile.Path)) {
        Write-Host "[ERROR] Prompt file not found at $($promptFile.Path)" -ForegroundColor Red
        exit 1
    }
    Write-Host "[INFO] Found prompt file: $($promptFile.Name)" -ForegroundColor Green
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
    Write-Host "1. Run Claude Code with general trading bot fixes prompt" -ForegroundColor White
    Write-Host "2. Run Claude Code with trading rules implementation prompt" -ForegroundColor White
    Write-Host "3. Run Claude Code with both prompts (comprehensive fix)" -ForegroundColor White
    Write-Host "4. View Claude Code Rules for crypto trading" -ForegroundColor White
    Write-Host "5. Start Claude Code in interactive mode" -ForegroundColor White
    Write-Host "6. Run Claude Code with specific file analysis" -ForegroundColor White
    Write-Host "7. Exit" -ForegroundColor White
    
    $choice = Read-Host "`nEnter your choice (1-7)"
    
    switch ($choice) {
        "1" {
            Write-Host "[ACTION] Running Claude Code with general trading bot fixes prompt..." -ForegroundColor Green
            Invoke-WSLCommand "cat claude_prompt_trading_bot_fixes.md | claude"
        }
        "2" {
            Write-Host "[ACTION] Running Claude Code with trading rules implementation prompt..." -ForegroundColor Green
            Invoke-WSLCommand "cat claude_code_trading_rules_prompt.md | claude"
        }
        "3" {
            Write-Host "[ACTION] Running Claude Code with comprehensive fix approach..." -ForegroundColor Green
            Invoke-WSLCommand "cat CLAUDE_CODE_RULES.md claude_prompt_trading_bot_fixes.md claude_code_trading_rules_prompt.md | claude"
        }
        "4" {
            Write-Host "[ACTION] Viewing Claude Code Rules..." -ForegroundColor Green
            Get-Content -Path (Join-Path $projectPath "CLAUDE_CODE_RULES.md") | Out-Host
            Write-Host "`nPress any key to continue..." -ForegroundColor Yellow
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        "5" {
            Write-Host "[ACTION] Starting Claude Code in interactive mode..." -ForegroundColor Green
            Invoke-WSLCommand "claude"
        }
        "6" {
            $filePath = Read-Host "Enter path to file to analyze (relative to project root)"
            if ([string]::IsNullOrWhiteSpace($filePath)) {
                Write-Host "[ERROR] File path cannot be empty" -ForegroundColor Red
                break
            }
            
            Write-Host "[ACTION] Running Claude Code to analyze $filePath..." -ForegroundColor Green
            Invoke-WSLCommand "echo 'Analyze this file and suggest improvements to make it more robust and handle errors better according to the rules in CLAUDE_CODE_RULES.md: $filePath' | claude"
        }
        "7" {
            Write-Host "[INFO] Exiting..." -ForegroundColor Yellow
            exit 0
        }
        default {
            Write-Host "[ERROR] Invalid choice. Please try again." -ForegroundColor Red
        }
    }
    
    # Return to menu after command completes
    Show-Menu
}

# Start the menu
Show-Menu 