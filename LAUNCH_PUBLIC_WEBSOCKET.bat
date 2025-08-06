@echo off
title Kraken Public WebSocket Demo
echo.
echo ========================================
echo   KRAKEN PUBLIC WEBSOCKET DEMO
echo ========================================
echo.
echo Starting live price feed...
echo No authentication required!
echo.
echo Press Ctrl+C to stop
echo.

cd /d C:\dev\tools\crypto-trading-bot-2025
python quick_public_websocket.py

echo.
echo Demo stopped.
pause