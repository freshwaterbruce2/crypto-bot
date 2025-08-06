@echo off
REM ====================================================================
REM KRAKEN API CREDENTIALS SETUP FOR WINDOWS
REM ====================================================================
REM This script helps you set up your Kraken API credentials securely
REM on Windows for use with the crypto trading bot in WSL.

echo.
echo ====================================================================
echo KRAKEN API CREDENTIALS SETUP
echo ====================================================================
echo.
echo This script will help you set up your Kraken API credentials
echo as Windows system environment variables for secure access.
echo.
echo IMPORTANT: You need your Kraken API credentials ready!
echo Get them from: https://www.kraken.com/u/security/api
echo.
echo Required permissions for your API key:
echo - Query Funds
echo - Query Open/Closed Orders  
echo - Create/Modify/Cancel Orders
echo - Access WebSockets API
echo.
echo Press any key to continue or Ctrl+C to exit...
pause >nul

echo.
echo ====================================================================
echo STEP 1: ENTER YOUR KRAKEN API CREDENTIALS
echo ====================================================================
echo.

:GET_API_KEY
set /p "KRAKEN_KEY=Enter your Kraken API Key: "
if "%KRAKEN_KEY%"=="" (
    echo Error: API Key cannot be empty!
    echo.
    goto GET_API_KEY
)

:GET_API_SECRET
set /p "KRAKEN_SECRET=Enter your Kraken API Secret: "
if "%KRAKEN_SECRET%"=="" (
    echo Error: API Secret cannot be empty!
    echo.
    goto GET_API_SECRET
)

echo.
echo ====================================================================
echo STEP 2: SETTING WINDOWS SYSTEM ENVIRONMENT VARIABLES
echo ====================================================================
echo.

REM Set system-wide environment variables (requires admin)
echo Setting KRAKEN_KEY as system environment variable...
setx KRAKEN_KEY "%KRAKEN_KEY%" /M >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Warning: Failed to set system-wide variable. Setting user variable instead...
    setx KRAKEN_KEY "%KRAKEN_KEY%" >nul
    if %errorlevel% NEQ 0 (
        echo Error: Failed to set KRAKEN_KEY environment variable!
        pause
        exit /b 1
    )
    echo Successfully set KRAKEN_KEY as user environment variable
) else (
    echo Successfully set KRAKEN_KEY as system environment variable
)

echo Setting KRAKEN_SECRET as system environment variable...
setx KRAKEN_SECRET "%KRAKEN_SECRET%" /M >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Warning: Failed to set system-wide variable. Setting user variable instead...
    setx KRAKEN_SECRET "%KRAKEN_SECRET%" >nul
    if %errorlevel% NEQ 0 (
        echo Error: Failed to set KRAKEN_SECRET environment variable!
        pause
        exit /b 1
    )
    echo Successfully set KRAKEN_SECRET as user environment variable
) else (
    echo Successfully set KRAKEN_SECRET as system environment variable
)

echo.
echo ====================================================================
echo STEP 3: VERIFICATION
echo ====================================================================
echo.

echo Verifying environment variables...

REM Check if variables are set
echo Checking KRAKEN_KEY...
reg query "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v KRAKEN_KEY >nul 2>&1
if %errorlevel% EQU 0 (
    echo ✓ KRAKEN_KEY set as system variable
) else (
    reg query "HKEY_CURRENT_USER\Environment" /v KRAKEN_KEY >nul 2>&1
    if %errorlevel% EQU 0 (
        echo ✓ KRAKEN_KEY set as user variable
    ) else (
        echo ✗ KRAKEN_KEY not found in registry
    )
)

echo Checking KRAKEN_SECRET...
reg query "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v KRAKEN_SECRET >nul 2>&1
if %errorlevel% EQU 0 (
    echo ✓ KRAKEN_SECRET set as system variable
) else (
    reg query "HKEY_CURRENT_USER\Environment" /v KRAKEN_SECRET >nul 2>&1
    if %errorlevel% EQU 0 (
        echo ✓ KRAKEN_SECRET set as user variable
    ) else (
        echo ✗ KRAKEN_SECRET not found in registry
    )
)

echo.
echo ====================================================================
echo STEP 4: SECURITY RECOMMENDATIONS
echo ====================================================================
echo.
echo IMPORTANT SECURITY NOTES:
echo.
echo 1. API Key Permissions: Ensure your API key only has the required
echo    permissions listed above. Never give more permissions than needed.
echo.
echo 2. IP Restrictions: Consider restricting your API key to your current
echo    IP address in the Kraken security settings.
echo.
echo 3. Regular Rotation: Rotate your API keys periodically for security.
echo.
echo 4. Environment Variables: Your credentials are now stored as Windows
echo    environment variables and will be accessible to the trading bot
echo    running in WSL.
echo.
echo 5. Backup: Keep a secure backup of your credentials in case you need
echo    to reconfigure them later.
echo.

echo ====================================================================
echo SETUP COMPLETE!
echo ====================================================================
echo.
echo Your Kraken API credentials have been configured as Windows
echo environment variables. The trading bot will now be able to
echo access them securely.
echo.
echo NEXT STEPS:
echo 1. Restart any open terminals/WSL sessions
echo 2. Test the credentials with: python test_credentials_status.py
echo 3. Launch the bot with: python main.py
echo.
echo NOTE: You may need to restart your computer for system-wide
echo environment variables to take effect in all applications.
echo.

echo Press any key to exit...
pause >nul

REM Clear credentials from memory
set KRAKEN_KEY=
set KRAKEN_SECRET=