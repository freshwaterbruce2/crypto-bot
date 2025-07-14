#!/bin/bash

echo "============================================"
echo "Kraken Trading Bot - Production Launch"
echo "============================================"
echo

# Function to cleanup on exit
cleanup() {
    echo "Stopping all processes..."
    kill $MONITOR_PID 2>/dev/null
    kill $BOT_PID 2>/dev/null
    exit
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Start monitoring dashboard in background
echo "Starting monitoring dashboard..."
python monitor_live_trading.py &
MONITOR_PID=$!

# Wait for monitor to initialize
sleep 2

# Start trading bot in foreground
echo "Starting trading bot..."
python scripts/live_launch.py &
BOT_PID=$!

echo
echo "============================================"
echo "Bot is running. Press Ctrl+C to stop."
echo "============================================"

# Wait for bot process
wait $BOT_PID