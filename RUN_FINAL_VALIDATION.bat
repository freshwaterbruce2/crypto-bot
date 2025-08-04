@echo off
echo ===============================================================================
echo CRYPTO TRADING BOT - FINAL VALIDATION AND PRODUCTION READINESS ASSESSMENT
echo ===============================================================================
echo.

:: Set console code page to UTF-8 for proper emoji display
chcp 65001 > nul

:: Check if Python is available
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

:: Check if we're in the correct directory
if not exist "src\" (
    echo ❌ ERROR: Please run this script from the crypto-trading-bot-2025 directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

:: Create validation results directory
if not exist "validation_results\" mkdir "validation_results"

echo 🚀 Starting comprehensive validation suite...
echo.
echo This will validate:
echo   ✅ Critical component functionality
echo   ✅ Security vulnerabilities  
echo   ✅ Performance benchmarks
echo   ✅ Memory usage and leaks
echo   ✅ Error recovery systems
echo   ✅ Production readiness
echo.

:: Prompt user for validation type
set /p choice="Choose validation type: [F]ull validation, [Q]uick validation, or [C]ancel: "

if /i "%choice%"=="C" (
    echo Validation cancelled by user
    pause
    exit /b 0
)

if /i "%choice%"=="Q" (
    echo 🏃 Running QUICK validation (validation + security, no benchmarks)...
    python run_final_validation.py --quick --html --verbose
) else (
    echo 🐌 Running FULL validation (all tests + benchmarks)...
    echo This may take 15-30 minutes...
    python run_final_validation.py --html --verbose
)

set validation_result=%errorlevel%

echo.
echo ===============================================================================

if %validation_result%==0 (
    echo ✅ VALIDATION COMPLETED SUCCESSFULLY
    echo 🚀 SYSTEM IS PRODUCTION READY
    echo.
    echo Next steps:
    echo   1. Review detailed reports in validation_results\ directory
    echo   2. Deploy to production environment
    echo   3. Monitor initial trading performance
) else (
    echo ❌ VALIDATION FAILED
    echo ⛔ SYSTEM IS NOT PRODUCTION READY
    echo.
    echo Required actions:
    echo   1. Review error details in validation logs
    echo   2. Fix all critical issues identified
    echo   3. Re-run validation until all tests pass
    echo   4. Verify fixes in staging environment
)

echo ===============================================================================
echo.

:: Show validation results directory
if exist "validation_results\" (
    echo 📁 Validation reports saved to: %CD%\validation_results\
    echo.
    echo Generated files:
    dir /b "validation_results\*.html" 2>nul | findstr .html >nul && (
        echo   📊 HTML Report: validation_results\test_report_*.html
    )
    dir /b "validation_results\*.json" 2>nul | findstr .json >nul && (
        echo   📋 JSON Report: validation_results\test_report_*.json
        echo   🏆 Certification: validation_results\production_certification_*.json
    )
    dir /b "*.log" 2>nul | findstr final_validation >nul && (
        echo   📝 Log File: final_validation_*.log
    )
    echo.
    
    :: Ask if user wants to open HTML report
    set /p open_report="Open HTML report in browser? [Y/N]: "
    if /i "%open_report%"=="Y" (
        for %%f in (validation_results\test_report_*.html) do (
            start "" "%%f"
            goto :opened_report
        )
        :opened_report
        echo 🌐 HTML report opened in default browser
    )
)

echo.
pause
exit /b %validation_result%