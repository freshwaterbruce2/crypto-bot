@echo off
REM CRYPTO TRADING BOT - IMMEDIATE CLEANUP EXECUTION
REM This script runs the Python cleanup implementation

echo ===============================================
echo CRYPTO TRADING BOT PROJECT CLEANUP
echo ===============================================
echo.
echo This will stage files for deletion (safely):
echo - Phase 1: Log files (198MB recovery)
echo - Phase 2: Duplicate files (15MB recovery)  
echo - Phase 3: Old scripts (10MB recovery)
echo - Phase 4: Documentation (5MB recovery)
echo.
echo FILES ARE STAGED FIRST - NOT IMMEDIATELY DELETED
echo You can review and restore if needed
echo.

set /p confirm="Continue with cleanup? (y/N): "
if /i not "%confirm%"=="y" (
    echo Cleanup cancelled
    pause
    exit /b
)

echo.
echo Starting Python cleanup implementation...
python PROJECT_CLEANUP_IMPLEMENTATION.py

echo.
echo ===============================================
echo CLEANUP COMPLETED
echo ===============================================
echo.
echo Next steps:
echo 1. Review the staging summary above
echo 2. Check _DELETION_STAGING folder to verify files
echo 3. If satisfied, run permanent deletion
echo 4. If not satisfied, run emergency recovery
echo.
echo Commands for next steps:
echo python -c "from PROJECT_CLEANUP_IMPLEMENTATION import main; cleanup=main(); print(cleanup.get_status())"
echo.
pause
