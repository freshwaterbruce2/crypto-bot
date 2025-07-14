# AGGRESSIVE DISK CLEANUP - EMERGENCY MODE
# Run as Administrator when disk is critically full

Write-Host "=== AGGRESSIVE DISK CLEANUP - EMERGENCY MODE ===" -ForegroundColor Red -BackgroundColor Yellow
Write-Host "CRITICAL: Disk at 99% - Aggressive cleanup required!" -ForegroundColor Red

# Get initial space
$drive = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
$initialFree = [math]::Round($drive.FreeSpace / 1GB, 2)
Write-Host "Initial free space: $initialFree GB" -ForegroundColor Red

$totalFreed = 0

# Phase 1: Immediate Emergency Actions
Write-Host "`n=== PHASE 1: EMERGENCY ACTIONS ===" -ForegroundColor Red

# 1. Clear all temp files aggressively
Write-Host "Clearing ALL temporary files..." -ForegroundColor Yellow
$tempPaths = @(
    "$env:TEMP\*",
    "$env:LOCALAPPDATA\Temp\*", 
    "C:\Windows\Temp\*",
    "C:\Windows\Prefetch\*",
    "C:\Windows\SoftwareDistribution\Download\*",
    "C:\Windows\Logs\*",
    "C:\ProgramData\Microsoft\Windows\WER\*"
)

foreach ($path in $tempPaths) {
    try {
        $items = Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue
        if ($items) {
            $beforeSize = ($items | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
            Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  Cleared: $(Split-Path $path -Parent) - $([math]::Round($beforeSize/1MB, 2)) MB" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Could not clear: $path" -ForegroundColor Yellow
    }
}

# 2. Empty Recycle Bin forcefully
Write-Host "Emptying Recycle Bin..." -ForegroundColor Yellow
try {
    Clear-RecycleBin -Force -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "  Recycle Bin emptied" -ForegroundColor Green
} catch {
    # Alternative method
    try {
        $recycleBin = Get-ChildItem 'C:\$Recycle.Bin' -Force -Recurse -ErrorAction SilentlyContinue
        $recycleBin | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  Recycle Bin cleared (alternative method)" -ForegroundColor Green
    } catch {
        Write-Host "  Could not clear Recycle Bin" -ForegroundColor Yellow
    }
}

# 3. Clear Windows Update files
Write-Host "Clearing Windows Update files..." -ForegroundColor Yellow
try {
    Stop-Service wuauserv -Force -ErrorAction SilentlyContinue
    Remove-Item "C:\Windows\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
    Start-Service wuauserv -ErrorAction SilentlyContinue
    Write-Host "  Windows Update cache cleared" -ForegroundColor Green
} catch {
    Write-Host "  Could not clear Windows Update cache" -ForegroundColor Yellow
}

# Phase 2: Browser Data Cleanup
Write-Host "`n=== PHASE 2: BROWSER DATA CLEANUP ===" -ForegroundColor Yellow

$browserPaths = @(
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache\*",
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Code Cache\*",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache\*",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Code Cache\*",
    "$env:APPDATA\Mozilla\Firefox\Profiles\*\cache2\*"
)

foreach ($path in $browserPaths) {
    try {
        $items = Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue
        if ($items) {
            $beforeSize = ($items | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
            Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  Browser cache cleared: $([math]::Round($beforeSize/1MB, 2)) MB" -ForegroundColor Green
        }
    } catch {
        # Continue silently
    }
}

# Phase 3: System File Cleanup
Write-Host "`n=== PHASE 3: SYSTEM FILE CLEANUP ===" -ForegroundColor Yellow

# Clear event logs (non-critical ones)
try {
    $logs = Get-WinEvent -ListLog * -ErrorAction SilentlyContinue | Where-Object { 
        $_.RecordCount -gt 0 -and 
        $_.LogName -notmatch "Security|System|Application|Setup" 
    }
    foreach ($log in $logs) {
        try {
            $logSize = $log.FileSize
            Clear-EventLog -LogName $log.LogName -ErrorAction SilentlyContinue
            Write-Host "  Cleared log: $($log.LogName) - $([math]::Round($logSize/1MB, 2)) MB" -ForegroundColor Green
        } catch {
            # Continue silently
        }
    }
} catch {
    Write-Host "  Event log cleanup failed" -ForegroundColor Yellow
}

# Phase 4: Find Large Files
Write-Host "`n=== PHASE 4: LARGE FILE ANALYSIS ===" -ForegroundColor Yellow

Write-Host "Scanning for large files (>100MB)..." -ForegroundColor Cyan
try {
    $largeFiles = Get-ChildItem C:\ -Recurse -File -ErrorAction SilentlyContinue | 
                  Where-Object { $_.Length -gt 100MB } | 
                  Sort-Object Length -Descending | 
                  Select-Object -First 10 FullName, @{Name="SizeGB";Expression={[math]::Round($_.Length/1GB,2)}}
    
    if ($largeFiles) {
        Write-Host "Top 10 largest files found:" -ForegroundColor Cyan
        foreach ($file in $largeFiles) {
            Write-Host "  $($file.SizeGB) GB - $($file.FullName)" -ForegroundColor White
        }
        Write-Host "`nConsider manually removing large files you don't need" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not scan for large files" -ForegroundColor Yellow
}

# Phase 5: Directory Size Analysis
Write-Host "`n=== PHASE 5: DIRECTORY SIZE ANALYSIS ===" -ForegroundColor Yellow

Write-Host "Analyzing largest directories..." -ForegroundColor Cyan
try {
    $largeDirs = @(
        "C:\Users",
        "C:\Program Files", 
        "C:\Program Files (x86)",
        "C:\Windows",
        "C:\ProgramData"
    )
    
    foreach ($dir in $largeDirs) {
        if (Test-Path $dir) {
            try {
                $size = (Get-ChildItem $dir -Recurse -File -ErrorAction SilentlyContinue | 
                        Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
                $sizeGB = [math]::Round($size / 1GB, 2)
                Write-Host "  $dir : $sizeGB GB" -ForegroundColor White
            } catch {
                Write-Host "  $dir : Could not calculate" -ForegroundColor Yellow
            }
        }
    }
} catch {
    Write-Host "Could not analyze directories" -ForegroundColor Yellow
}

# Final Results
Write-Host "`n=== CLEANUP RESULTS ===" -ForegroundColor Green

$driveAfter = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
$finalFree = [math]::Round($driveAfter.FreeSpace / 1GB, 2)
$spaceFreed = $finalFree - $initialFree

Write-Host "Before cleanup: $initialFree GB free" -ForegroundColor White
Write-Host "After cleanup:  $finalFree GB free" -ForegroundColor White
Write-Host "Space freed:    $spaceFreed GB" -ForegroundColor Green

$usagePercent = [math]::Round((($driveAfter.Size - $driveAfter.FreeSpace) / $driveAfter.Size) * 100, 1)
Write-Host "Current usage:  $usagePercent%" -ForegroundColor $(if ($usagePercent -gt 95) {"Red"} elseif ($usagePercent -gt 85) {"Yellow"} else {"Green"})

if ($finalFree -gt 15) {
    Write-Host "`n✅ SUCCESS: Disk space recovered!" -ForegroundColor Green
} elseif ($spaceFreed -gt 2) {
    Write-Host "`n⚠️  PARTIAL SUCCESS: Some space freed, but still critical" -ForegroundColor Yellow
    Write-Host "Manual intervention may be required" -ForegroundColor Yellow
} else {
    Write-Host "`n❌ MINIMAL IMPACT: Very little space freed" -ForegroundColor Red
    Write-Host "URGENT: Manual cleanup of large files required!" -ForegroundColor Red
}

Write-Host "`nNEXT STEPS if still critical:" -ForegroundColor Cyan
Write-Host "1. Review large files listed above" -ForegroundColor White
Write-Host "2. Uninstall unused programs" -ForegroundColor White
Write-Host "3. Move files to external storage" -ForegroundColor White
Write-Host "4. Consider disk cleanup tools like CCleaner" -ForegroundColor White

Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")