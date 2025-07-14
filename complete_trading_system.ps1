# PowerShell script to complete the trading system using Claude Code
# This script provides a direct interface to Claude Code for completing the trading system

# Define colors for output
$colors = @{
    Info = "Cyan"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Prompt = "White"
}

function Write-ColorOutput {
    param (
        [string]$Message,
        [string]$Type = "Info"
    )
    
    $prefix = switch ($Type) {
        "Info"    { "[INFO] " }
        "Success" { "[SUCCESS] " }
        "Warning" { "[WARNING] " }
        "Error"   { "[ERROR] " }
        "Task"    { "[TASK] " }
        default   { "" }
    }
    
    Write-Host "$prefix$Message" -ForegroundColor $colors[$Type]
}

Write-ColorOutput "Claude Code Trading System Completion Tool" "Info"
Write-ColorOutput "=========================================" "Info"

# Check if WSL is available
$wslPath = "C:\Windows\System32\wsl.exe"
if (-not (Test-Path $wslPath)) {
    Write-ColorOutput "WSL executable not found at $wslPath" "Error"
    exit 1
}
Write-ColorOutput "WSL found at $wslPath" "Success"

# Define the project directory
$projectPath = "$PSScriptRoot"
Write-ColorOutput "Project path: $projectPath" "Info"

# Define completion tasks
$tasks = @(
    "Analyze the current state of the trading system and identify what components need to be completed for full automation",
    "Complete the balance_manager.py to track account balances and handle API rate limits properly",
    "Implement error handling and recovery mechanisms in the trading bot",
    "Create a proper startup script that initializes all necessary components",
    "Implement a proper shutdown procedure to safely close positions and save state",
    "Add comprehensive logging for all trading activities",
    "Implement a monitoring system to alert on issues",
    "Create a configuration system for easy parameter adjustment",
    "Add unit tests for critical components",
    "Implement a dashboard for real-time monitoring"
)

# Function to run Claude Code with a specific task
function Invoke-ClaudeTask {
    param (
        [string]$Task
    )
    
    $taskFile = "claude_task_$([System.IO.Path]::GetRandomFileName()).txt"
    $taskFilePath = Join-Path $projectPath $taskFile
    
    Write-ColorOutput "Task: $Task" "Task"
    Write-ColorOutput "Creating task file..." "Info"
    
    # Create the task file
    @"
$Task

Please analyze the existing code in this directory and provide:
1. A detailed assessment of what exists and what's missing
2. Code implementations for the missing components
3. Instructions on how to integrate the new code with the existing system
4. Tests to verify the implementation works correctly

Focus on making the trading system fully automated, robust, and error-resistant.
"@ | Out-File -FilePath $taskFilePath -Encoding utf8
    
    Write-ColorOutput "Running Claude Code with task..." "Success"
    Write-ColorOutput "----------------------------------------" "Info"
    
    # Run Claude Code with the task
    try {
        & $wslPath -e bash -c "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && cat $(($taskFilePath -replace '\\', '/') -replace 'C:', '/mnt/c') | claude"
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "Claude command exited with code $LASTEXITCODE" "Warning"
        }
    } catch {
        Write-ColorOutput "Error running Claude Code: $_" "Error"
    }
    
    Write-ColorOutput "----------------------------------------" "Info"
    Write-ColorOutput "Task completed." "Success"
    
    # Clean up the task file
    Remove-Item -Path $taskFilePath -ErrorAction SilentlyContinue
}

# Display available tasks
Write-ColorOutput "Available tasks:" "Info"
for ($i = 0; $i -lt $tasks.Count; $i++) {
    Write-Host "$($i+1). $($tasks[$i])" -ForegroundColor $colors["Prompt"]
}

# Ask how to proceed
Write-Host "`n" -NoNewline
Write-ColorOutput "How do you want to proceed?" "Info"
Write-Host "1. Run all tasks sequentially" -ForegroundColor $colors["Prompt"]
Write-Host "2. Select a specific task" -ForegroundColor $colors["Prompt"]
Write-Host "3. Enter a custom task" -ForegroundColor $colors["Prompt"]
Write-Host "4. Exit" -ForegroundColor $colors["Prompt"]

$choice = Read-Host "`nEnter your choice (1-4)"

switch ($choice) {
    "1" {
        Write-ColorOutput "Running all tasks sequentially..." "Success"
        foreach ($task in $tasks) {
            Invoke-ClaudeTask -Task $task
            Write-ColorOutput "Waiting 5 seconds before next task..." "Info"
            Start-Sleep -Seconds 5
        }
    }
    "2" {
        $taskNum = [int](Read-Host "Enter task number (1-$($tasks.Count))")
        if ($taskNum -ge 1 -and $taskNum -le $tasks.Count) {
            Invoke-ClaudeTask -Task $tasks[$taskNum-1]
        } else {
            Write-ColorOutput "Invalid task number" "Error"
            exit 1
        }
    }
    "3" {
        Write-ColorOutput "Enter your custom task:" "Info"
        $customTask = Read-Host
        Invoke-ClaudeTask -Task $customTask
    }
    "4" {
        Write-ColorOutput "Exiting..." "Info"
        exit 0
    }
    default {
        Write-ColorOutput "Invalid choice" "Error"
        exit 1
    }
}

Write-ColorOutput "All tasks completed. Your trading system should now be closer to completion." "Success"
Write-ColorOutput "Don't forget to test thoroughly before deploying to production!" "Warning" 