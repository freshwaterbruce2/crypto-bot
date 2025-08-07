#!/bin/bash

# Auto-restart script for crypto trading bot
# Monitors the bot and automatically restarts it if it crashes

LOG_DIR="./logs"
LOG_FILE="$LOG_DIR/auto_restart.log"
PID_FILE="./bot.pid"
MAX_RETRIES=5
RETRY_COUNT=0
RESTART_DELAY=10

# Ensure log directory exists
mkdir -p "$LOG_DIR"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

start_bot() {
    log_message "Starting trading bot..."
    python3 main.py --simple > "$LOG_DIR/bot_output.log" 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > "$PID_FILE"
    log_message "Bot started with PID: $BOT_PID"
}

check_bot_health() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

cleanup() {
    log_message "Shutdown signal received. Stopping bot..."
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        kill $PID 2>/dev/null
        rm -f "$PID_FILE"
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

log_message "Auto-restart monitor started"
start_bot

while true; do
    sleep 30
    
    if ! check_bot_health; then
        log_message "Bot is not running! Attempting restart..."
        
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            log_message "ERROR: Maximum restart attempts ($MAX_RETRIES) reached. Manual intervention required."
            exit 1
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_message "Restart attempt $RETRY_COUNT of $MAX_RETRIES"
        
        # Wait before restarting
        sleep $RESTART_DELAY
        
        start_bot
    else
        # Reset retry count if bot is running successfully
        if [ $RETRY_COUNT -gt 0 ]; then
            log_message "Bot is running stable. Resetting retry counter."
            RETRY_COUNT=0
        fi
    fi
done