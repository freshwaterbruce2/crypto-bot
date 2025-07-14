# PowerShell script to make Python and shell scripts executable in WSL

Write-Host "[INFO] Making scripts executable in WSL" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

$wslPath = "C:\Windows\System32\wsl.exe"
$projectPath = "$PSScriptRoot"

# Check if WSL is available
if (-not (Test-Path $wslPath)) {
    Write-Host "[ERROR] WSL executable not found at $wslPath" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Making Python scripts executable..." -ForegroundColor Yellow
& $wslPath -e bash -c "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && chmod +x *.py"

Write-Host "[INFO] Making shell scripts executable..." -ForegroundColor Yellow
& $wslPath -e bash -c "cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025 && chmod +x *.sh"

Write-Host "[SUCCESS] Scripts are now executable in WSL" -ForegroundColor Green 