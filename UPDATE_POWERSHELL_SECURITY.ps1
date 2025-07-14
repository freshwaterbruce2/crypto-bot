# PowerShell 7.5.2 Security Update Script
# Addresses CVE-2025-21171 vulnerability
# Run as Administrator

Write-Host "=== PowerShell 7.5.2 Security Update ===" -ForegroundColor Cyan
Write-Host "Addressing CVE-2025-21171 vulnerability" -ForegroundColor Yellow

# Check current PowerShell version
$currentVersion = $PSVersionTable.PSVersion
Write-Host "Current PowerShell version: $currentVersion" -ForegroundColor White

# Check if update is needed
if ($currentVersion -lt [Version]"7.5.2") {
    Write-Host "Update needed: Current version $currentVersion < 7.5.2" -ForegroundColor Yellow
    
    # Method 1: Try winget (recommended for Windows Server 2025)
    try {
        Write-Host "`nAttempting update via winget..." -ForegroundColor Green
        winget install --id Microsoft.PowerShell --source winget --accept-package-agreements --accept-source-agreements
        Write-Host "PowerShell updated via winget" -ForegroundColor Green
        $updateSuccess = $true
    } catch {
        Write-Host "Winget update failed: $($_.Exception.Message)" -ForegroundColor Yellow
        $updateSuccess = $false
    }
    
    # Method 2: MSI installer fallback
    if (-not $updateSuccess) {
        Write-Host "`nAttempting MSI download and install..." -ForegroundColor Green
        
        $downloadUrl = "https://github.com/PowerShell/PowerShell/releases/download/v7.5.2/PowerShell-7.5.2-win-x64.msi"
        $downloadPath = "$env:TEMP\PowerShell-7.5.2-win-x64.msi"
        
        try {
            # Download MSI
            Write-Host "Downloading PowerShell 7.5.2 MSI..." -ForegroundColor Cyan
            Invoke-WebRequest -Uri $downloadUrl -OutFile $downloadPath -UseBasicParsing
            
            # Install MSI silently
            Write-Host "Installing PowerShell 7.5.2..." -ForegroundColor Cyan
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$downloadPath`" /quiet ADD_EXPLORER_CONTEXT_MENU_OPENPOWERSHELL=1 ADD_FILE_CONTEXT_MENU_RUNPOWERSHELL=1 ENABLE_PSREMOTING=1 REGISTER_MANIFEST=1 USE_MU=1 ENABLE_MU=1 ADD_PATH=1" -Wait
            
            # Cleanup
            Remove-Item $downloadPath -Force -ErrorAction SilentlyContinue
            
            Write-Host "PowerShell 7.5.2 installed successfully" -ForegroundColor Green
            $updateSuccess = $true
            
        } catch {
            Write-Host "MSI installation failed: $($_.Exception.Message)" -ForegroundColor Red
            $updateSuccess = $false
        }
    }
    
    # Verification
    if ($updateSuccess) {
        Write-Host "`n=== Update Complete ===" -ForegroundColor Green
        Write-Host "PowerShell has been updated to address CVE-2025-21171" -ForegroundColor Green
        Write-Host "Please restart your terminal to use the updated version" -ForegroundColor Yellow
        Write-Host "`nTo verify the update, run in a new terminal:" -ForegroundColor Cyan
        Write-Host '$PSVersionTable.PSVersion' -ForegroundColor Cyan
    } else {
        Write-Host "`n=== Update Failed ===" -ForegroundColor Red
        Write-Host "Manual installation may be required" -ForegroundColor Red
        Write-Host "Visit: https://github.com/PowerShell/PowerShell/releases/tag/v7.5.2" -ForegroundColor Cyan
    }
    
} else {
    Write-Host "PowerShell is already up to date (>= 7.5.2)" -ForegroundColor Green
    Write-Host "CVE-2025-21171 vulnerability is already patched" -ForegroundColor Green
}

Write-Host "`n=== Security Information ===" -ForegroundColor Cyan
Write-Host "CVE-2025-21171: .NET remote code execution vulnerability" -ForegroundColor White
Write-Host "Severity: Important" -ForegroundColor White
Write-Host "Impact: Attackers could exploit with specially crafted requests" -ForegroundColor White
Write-Host "Fix: PowerShell 7.5.2 includes the security patch" -ForegroundColor White

Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")