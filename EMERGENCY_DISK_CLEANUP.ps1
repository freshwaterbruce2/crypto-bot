# EMERGENCY DISK CLEANUP SCRIPT
# Run this PowerShell script as Administrator to free up critical disk space
# System currently at 99% usage - IMMEDIATE ACTION REQUIRED

Write-Host "=== EMERGENCY DISK CLEANUP STARTING ===" -ForegroundColor Red
Write-Host "Current disk usage: 99% - Critical level!" -ForegroundColor Red

# Get initial disk space
$drive = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
$initialFreeSpace = [math]::Round($drive.FreeSpace / 1GB, 2)
Write-Host "Initial free space: $initialFreeSpace GB" -ForegroundColor Yellow

$totalFreed = 0

# Phase 1: Windows Built-in Cleanup
Write-Host "`n=== PHASE 1: Windows Built-in Cleanup ===" -ForegroundColor Green

# Clean Windows Update files
Write-Host "Cleaning Windows Update cache..."
try {
    $updateCleanup = Get-WindowsUpdateCache -ErrorAction SilentlyContinue
    if ($updateCleanup) {
        Clear-WindowsUpdateCache -Force -ErrorAction SilentlyContinue
        Write-Host "Windows Update cache cleaned" -ForegroundColor Green
    }
} catch {
    Write-Host "Windows Update cleanup not available on this system" -ForegroundColor Yellow
}

# Phase 2: Temporary Files Cleanup
Write-Host "`n=== PHASE 2: Temporary Files Cleanup ===" -ForegroundColor Green

$tempPaths = @(
    "$env:TEMP",
    "$env:LOCALAPPDATA\Temp",
    "C:\Windows\Temp",
    "C:\Windows\Prefetch",
    "C:\Windows\SoftwareDistribution\Download"
)

foreach ($path in $tempPaths) {
    if (Test-Path $path) {
        Write-Host "Cleaning: $path"
        try {
            $beforeSize = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | 
                Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            $afterSize = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
            $freed = [math]::Round(($beforeSize - $afterSize) / 1MB, 2)
            if ($freed -gt 0) {
                Write-Host "  Freed: $freed MB" -ForegroundColor Green
                $totalFreed += $freed
            }
        } catch {
            Write-Host "  Unable to clean $path" -ForegroundColor Yellow
        }
    }
}

# Phase 3: Event Logs Cleanup
Write-Host "`n=== PHASE 3: Event Logs Cleanup ===" -ForegroundColor Green

try {
    $eventLogs = Get-WinEvent -ListLog * -ErrorAction SilentlyContinue | Where-Object { $_.RecordCount -gt 0 }
    foreach ($log in $eventLogs) {
        if ($log.LogName -notmatch "Security|System|Application") {
            try {
                $beforeSize = $log.FileSize
                Clear-EventLog -LogName $log.LogName -ErrorAction SilentlyContinue
                $freed = [math]::Round($beforeSize / 1MB, 2)
                if ($freed -gt 0) {
                    Write-Host "  Cleared $($log.LogName): $freed MB" -ForegroundColor Green
                    $totalFreed += $freed
                }
            } catch {
                # Silently continue for logs that can't be cleared
            }
        }
    }
} catch {
    Write-Host "Event log cleanup not available" -ForegroundColor Yellow
}

# Phase 4: Browser Cache Cleanup
Write-Host "`n=== PHASE 4: Browser Cache Cleanup ===" -ForegroundColor Green

$browserPaths = @(
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache",
    "$env:LOCALAPPDATA\Mozilla\Firefox\Profiles\*.default*\cache2"
)

foreach ($browserPath in $browserPaths) {
    $expandedPaths = Get-ChildItem $browserPath -ErrorAction SilentlyContinue
    foreach ($path in $expandedPaths) {
        if (Test-Path $path) {
            try {
                $beforeSize = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
                Remove-Item "$path\*" -Recurse -Force -ErrorAction SilentlyContinue
                $freed = [math]::Round($beforeSize / 1MB, 2)
                if ($freed -gt 0) {
                    Write-Host "  Browser cache freed: $freed MB" -ForegroundColor Green
                    $totalFreed += $freed
                }
            } catch {
                # Silently continue
            }
        }
    }
}

# Phase 5: Recycle Bin
Write-Host "`n=== PHASE 5: Recycle Bin Cleanup ===" -ForegroundColor Green

try {
    $shell = New-Object -comObject Shell.Application
    $recycleBin = $shell.Namespace(0xA)
    $beforeSize = ($recycleBin.Items() | Measure-Object -Property Size -Sum).Sum
    Clear-RecycleBin -Force -ErrorAction SilentlyContinue
    $freed = [math]::Round($beforeSize / 1MB, 2)
    if ($freed -gt 0) {
        Write-Host "  Recycle Bin freed: $freed MB" -ForegroundColor Green
        $totalFreed += $freed
    }
} catch {
    Write-Host "Recycle Bin cleanup failed" -ForegroundColor Yellow
}

# Phase 6: Enable Storage Sense
Write-Host "`n=== PHASE 6: Enable Storage Sense ===" -ForegroundColor Green

try {
    # Enable Storage Sense
    $regPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy"
    if (!(Test-Path $regPath)) {
        New-Item -Path $regPath -Force | Out-Null
    }
    Set-ItemProperty -Path $regPath -Name "01" -Value 1
    Set-ItemProperty -Path $regPath -Name "StoragePolicydefault" -Value 1
    Write-Host "Storage Sense enabled for automatic cleanup" -ForegroundColor Green
} catch {
    Write-Host "Could not enable Storage Sense" -ForegroundColor Yellow
}

# Final Results
Write-Host "`n=== CLEANUP COMPLETE ===" -ForegroundColor Green

$driveAfter = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
$finalFreeSpace = [math]::Round($driveAfter.FreeSpace / 1GB, 2)
$spaceFreed = $finalFreeSpace - $initialFreeSpace

Write-Host "Initial free space: $initialFreeSpace GB" -ForegroundColor White
Write-Host "Final free space: $finalFreeSpace GB" -ForegroundColor Green
Write-Host "Total space freed: $spaceFreed GB" -ForegroundColor Green
Write-Host "Disk usage reduced from 99% to $(100 - [math]::Round(($driveAfter.FreeSpace / $driveAfter.Size) * 100, 1))%" -ForegroundColor Green

if ($finalFreeSpace -gt 10) {
    Write-Host "`nDISK CLEANUP SUCCESSFUL!" -ForegroundColor Green
    Write-Host "System is now stable for continued operation" -ForegroundColor Green
} else {
    Write-Host "`nWARNING: Disk space still critically low!" -ForegroundColor Red
    Write-Host "Consider moving large files to external storage" -ForegroundColor Yellow
    Write-Host "Or uninstalling unused applications" -ForegroundColor Yellow
}

Write-Host "`nTo run this script, execute in PowerShell as Administrator:" -ForegroundColor Cyan
Write-Host "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Cyan
Write-Host ".\EMERGENCY_DISK_CLEANUP.ps1" -ForegroundColor Cyan