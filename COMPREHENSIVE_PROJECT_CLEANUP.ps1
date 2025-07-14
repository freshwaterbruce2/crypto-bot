# COMPREHENSIVE PROJECT CLEANUP SCRIPT
# Crypto Trading Bot Project - Space Recovery: 199MB -> 1.4MB
# PHASE APPROACH: Move files to archive first, then delete after review

param(
    [switch]$Phase1,           # Log file cleanup (198MB recovery)
    [switch]$Phase2,           # Duplicate file cleanup (15MB recovery) 
    [switch]$Phase3,           # Old script cleanup (10MB recovery)
    [switch]$Phase4,           # Documentation consolidation (5MB recovery)
    [switch]$All,              # Run all phases
    [switch]$FinalDelete,      # Actually delete archived files
    [switch]$DryRun            # Show what would be done
)

$ProjectRoot = "C:\projects050625\projects\active\tool-crypto-trading-bot-2025"
$ArchiveRoot = "$ProjectRoot\_CLEANUP_ARCHIVE"
$LogFile = "$ProjectRoot\cleanup_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

function Write-Log {
    param($Message, $Color = "White")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage -ForegroundColor $Color
    Add-Content -Path $LogFile -Value $LogMessage
}

function Get-FileSize {
    param($Path)
    if (Test-Path $Path) {
        $Size = (Get-Item $Path).Length
        if ($Size -gt 1MB) { return "{0:N2} MB" -f ($Size / 1MB) }
        elseif ($Size -gt 1KB) { return "{0:N2} KB" -f ($Size / 1KB) }
        else { return "$Size B" }
    }
    return "0 B"
}

function Move-ToArchive {
    param($SourcePath, $Category, $Reason)
    
    if (-not (Test-Path $SourcePath)) {
        Write-Log "SKIP: $SourcePath (not found)" "Yellow"
        return
    }
    
    $Size = Get-FileSize $SourcePath
    $RelativePath = $SourcePath.Replace($ProjectRoot, "").TrimStart('\')
    $ArchivePath = Join-Path $ArchiveRoot $Category
    $DestPath = Join-Path $ArchivePath $RelativePath
    
    if ($DryRun) {
        Write-Log "DRY-RUN: Would move $RelativePath ($Size) -> $Category ($Reason)" "Cyan"
        return
    }
    
    # Create archive directory if needed
    $DestDir = Split-Path $DestPath -Parent
    if (-not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    }
    
    try {
        Move-Item -Path $SourcePath -Destination $DestPath -Force
        Write-Log "MOVED: $RelativePath ($Size) -> $Category ($Reason)" "Green"
    }
    catch {
        Write-Log "ERROR: Failed to move $RelativePath - $($_.Exception.Message)" "Red"
    }
}

function Phase1-LogCleanup {
    Write-Log "=== PHASE 1: LOG FILE CLEANUP (198MB Recovery) ===" "Magenta"
    
    $LogFiles = @(
        "kraken_infinity_bot.log",
        "bot_live_output.log", 
        "bot_output.log",
        "test_bot.log",
        "fixed_launch.log",
        "test_launch.log", 
        "bot_test.log",
        "launch_output.log"
    )
    
    foreach ($LogFile in $LogFiles) {
        $FullPath = Join-Path $ProjectRoot $LogFile
        Move-ToArchive $FullPath "01_LOGS" "Large log file cleanup"
    }
}

function Phase2-DuplicateCleanup {
    Write-Log "=== PHASE 2: DUPLICATE FILE CLEANUP (15MB Recovery) ===" "Magenta"
    
    # WebSocket Manager Duplicates
    $WebSocketD