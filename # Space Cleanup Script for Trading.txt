# Space Cleanup Script for Trading Bot
Write-Host "=== SPACE CLEANUP SCRIPT ===" -ForegroundColor Cyan
Write-Host "Current free space: $([Math]::Round((Get-PSDrive C).Free/1GB,2)) GB" -ForegroundColor Yellow

# 1. Disable Hibernation (saves ~16GB)
Write-Host "`nDisabling hibernation..." -ForegroundColor Green
powercfg /hibernate off

# 2. Show large installed programs
Write-Host "`n=== PROGRAMS OVER 1GB ===" -ForegroundColor Cyan
$programs = @()
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*,HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -and $_.EstimatedSize -gt 1048576 } |
    ForEach-Object {
        $programs += [PSCustomObject]@{
            Name = $_.DisplayName
            SizeGB = [Math]::Round($_.EstimatedSize/1048576,2)
            Publisher = $_.Publisher
        }
    }
$programs | Sort-Object SizeGB -Descending | Format-Table -AutoSize

# 3. Check for games
Write-Host "`n=== CHECKING FOR GAMES ===" -ForegroundColor Cyan
$totalGameSize = 0

# Steam
if (Test-Path "C:\Program Files (x86)\Steam\steamapps\common") {
    Write-Host "Steam Games Found:" -ForegroundColor Yellow
    Get-ChildItem "C:\Program Files (x86)\Steam\steamapps\common" -Directory | ForEach-Object {
        $size = (Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1GB
        if ($size -gt 1) {
            Write-Host "  - $($_.Name): $([Math]::Round($size,2)) GB"
            $totalGameSize += $size
        }
    }
}

# Epic Games
if (Test-Path "C:\Program Files\Epic Games") {
    $epicSize = (Get-ChildItem "C:\Program Files\Epic Games" -Recurse -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1GB
    Write-Host "Epic Games: $([Math]::Round($epicSize,2)) GB" -ForegroundColor Yellow
    $totalGameSize += $epicSize
}

Write-Host "`nTotal games size: $([Math]::Round($totalGameSize,2)) GB" -ForegroundColor Red

# 4. Check Downloads
Write-Host "`n=== LARGE FILES IN DOWNLOADS ===" -ForegroundColor Cyan
$downloadSize = 0
Get-ChildItem "$env:USERPROFILE\Downloads" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Length -gt 100MB } |
    ForEach-Object {
        Write-Host "$($_.Name) - $([Math]::Round($_.Length/1MB,2)) MB"
        $downloadSize += $_.Length
    }
Write-Host "Total in Downloads: $([Math]::Round($downloadSize/1GB,2)) GB" -ForegroundColor Yellow

# 5. Clean temp files
Write-Host "`n=== CLEANING TEMP FILES ===" -ForegroundColor Cyan
$tempSize = (Get-ChildItem $env:TEMP -Recurse -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1GB
Write-Host "Temp folder size: $([Math]::Round($tempSize,2)) GB" -ForegroundColor Yellow
Remove-Item "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue

# 6. Empty Recycle Bin
Write-Host "`nEmptying Recycle Bin..." -ForegroundColor Green
Clear-RecycleBin -Force -ErrorAction SilentlyContinue

# Final space check
Start-Sleep -Seconds 2
$newFree = [Math]::Round((Get-PSDrive C).Free/1GB,2)
$gained = $newFree - $initialFree
Write-Host "`n=== RESULTS ===" -ForegroundColor Green
Write-Host "New free space: $newFree GB" -ForegroundColor Green
Write-Host "Space gained so far: $([Math]::Round($gained,2)) GB" -ForegroundColor Green

Write-Host "`n=== RECOMMENDATIONS ===" -ForegroundColor Cyan
Write-Host "1. Uninstall games you don't play (found $([Math]::Round($totalGameSize,2)) GB)"
Write-Host "2. Clear your Downloads folder (found $([Math]::Round($downloadSize/1GB,2)) GB)"
Write-Host "3. Run Disk Cleanup: cleanmgr /sagerun:99"
Write-Host "4. Consider uninstalling large programs listed above"