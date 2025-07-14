# Disk Space Analyzer - Find what's using all the space
# Quick analysis to identify space hogs

Write-Host "=== DISK SPACE ANALYZER ===" -ForegroundColor Cyan
Write-Host "Finding what's consuming disk space..." -ForegroundColor Yellow

# Current disk status
$drive = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
$usedGB = [math]::Round(($drive.Size - $drive.FreeSpace) / 1GB, 1)
$freeGB = [math]::Round($drive.FreeSpace / 1GB, 1)
$totalGB = [math]::Round($drive.Size / 1GB, 1)
$usagePercent = [math]::Round((($drive.Size - $drive.FreeSpace) / $drive.Size) * 100, 1)

Write-Host "`nCURRENT DISK STATUS:" -ForegroundColor White
Write-Host "Total: $totalGB GB" -ForegroundColor White
Write-Host "Used:  $usedGB GB" -ForegroundColor Red
Write-Host "Free:  $freeGB GB" -ForegroundColor $(if ($freeGB -lt 10) {"Red"} else {"Green"})
Write-Host "Usage: $usagePercent%" -ForegroundColor $(if ($usagePercent -gt 95) {"Red"} else {"Yellow"})

Write-Host "`nTOP SPACE CONSUMERS:" -ForegroundColor Yellow

# Quick directory analysis (top level only for speed)
$directories = @(
    @{Path="C:\Users"; Name="Users"},
    @{Path="C:\Program Files"; Name="Program Files"},
    @{Path="C:\Program Files (x86)"; Name="Program Files (x86)"},
    @{Path="C:\Windows"; Name="Windows"},
    @{Path="C:\ProgramData"; Name="ProgramData"},
    @{Path="C:\Temp"; Name="Temp"},
    @{Path="C:\Windows\Temp"; Name="Windows\Temp"},
    @{Path="C:\Windows\SoftwareDistribution"; Name="Windows\SoftwareDistribution"},
    @{Path="C:\Windows\Logs"; Name="Windows\Logs"},
    @{Path="C:\Windows\System32\winevt"; Name="Event Logs"}
)

$results = @()

foreach ($dir in $directories) {
    if (Test-Path $dir.Path) {
        try {
            Write-Host "Analyzing $($dir.Name)..." -ForegroundColor Gray
            $size = (Get-ChildItem $dir.Path -Recurse -File -ErrorAction SilentlyContinue | 
                    Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
            if ($size -gt 0) {
                $sizeGB = [math]::Round($size / 1GB, 2)
                $results += [PSCustomObject]@{
                    Directory = $dir.Name
                    SizeGB = $sizeGB
                    Path = $dir.Path
                }
            }
        } catch {
            Write-Host "  Could not analyze $($dir.Name)" -ForegroundColor Yellow
        }
    }
}

# Sort and display results
$results | Sort-Object SizeGB -Descending | ForEach-Object {
    $color = if ($_.SizeGB -gt 50) {"Red"} elseif ($_.SizeGB -gt 20) {"Yellow"} else {"Green"}
    Write-Host "  $($_.SizeGB) GB - $($_.Directory)" -ForegroundColor $color
}

# Quick file type analysis in common locations
Write-Host "`nLARGE FILE TYPES:" -ForegroundColor Yellow

$fileTypes = @{}
$searchPaths = @("C:\Users", "C:\Temp", "C:\Windows\Temp")

foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        try {
            Write-Host "Scanning $path for large files..." -ForegroundColor Gray
            Get-ChildItem $path -Recurse -File -ErrorAction SilentlyContinue | 
                Where-Object { $_.Length -gt 10MB } | 
                ForEach-Object {
                    $ext = $_.Extension.ToLower()
                    if (-not $fileTypes.ContainsKey($ext)) {
                        $fileTypes[$ext] = @{ Count = 0; Size = 0 }
                    }
                    $fileTypes[$ext].Count++
                    $fileTypes[$ext].Size += $_.Length
                }
        } catch {
            # Continue silently
        }
    }
}

# Display file type summary
$fileTypes.GetEnumerator() | 
    Where-Object { $_.Value.Size -gt 100MB } |
    Sort-Object { $_.Value.Size } -Descending |
    ForEach-Object {
        $sizeGB = [math]::Round($_.Value.Size / 1GB, 2)
        Write-Host "  $($_.Key): $sizeGB GB ($($_.Value.Count) files)" -ForegroundColor White
    }

# Specific recommendations
Write-Host "`nRECOMMENDATIONS:" -ForegroundColor Cyan

if ((Get-ChildItem "C:\Windows\SoftwareDistribution\Download" -ErrorAction SilentlyContinue).Count -gt 0) {
    Write-Host "• Clear Windows Update cache" -ForegroundColor Yellow
}

if (Test-Path "$env:LOCALAPPDATA\Temp") {
    $tempSize = (Get-ChildItem "$env:LOCALAPPDATA\Temp" -Recurse -ErrorAction SilentlyContinue | 
                Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
    if ($tempSize -gt 500MB) {
        Write-Host "• Clear user temp files: $([math]::Round($tempSize/1MB, 0)) MB" -ForegroundColor Yellow
    }
}

# Check for common space wasters
$spaceWasters = @(
    @{Path="C:\hiberfil.sys"; Name="Hibernate file"},
    @{Path="C:\pagefile.sys"; Name="Page file"},
    @{Path="C:\swapfile.sys"; Name="Swap file"}
)

foreach ($waster in $spaceWasters) {
    if (Test-Path $waster.Path) {
        try {
            $size = (Get-Item $waster.Path -Force).Length
            $sizeGB = [math]::Round($size / 1GB, 2)
            Write-Host "• $($waster.Name): $sizeGB GB" -ForegroundColor Cyan
        } catch {
            # File may be in use
        }
    }
}

Write-Host "`nRUN NEXT:" -ForegroundColor Green
Write-Host ".\AGGRESSIVE_DISK_CLEANUP.ps1 (as Administrator)" -ForegroundColor White
Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")