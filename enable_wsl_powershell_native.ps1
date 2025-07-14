# WSL Setup using PowerShell Cmdlets
Write-Host "Enabling WSL Features..." -ForegroundColor Green

# Enable WSL
Write-Host "Enabling Windows Subsystem for Linux..." -ForegroundColor Yellow
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart

# Enable VM Platform
Write-Host "Enabling Virtual Machine Platform..." -ForegroundColor Yellow
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart

# Download WSL2 Kernel
Write-Host "Downloading WSL2 Kernel Update..." -ForegroundColor Yellow
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi -OutFile wsl_update.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I wsl_update.msi /quiet'
Remove-Item wsl_update.msi

Write-Host "`nDONE! Please RESTART your computer now!" -ForegroundColor Green
Write-Host "After restart, run: wsl --install -d Ubuntu" -ForegroundColor Yellow
