#!/bin/bash
# ULTIMATE BOT LAUNCHER - NO CACHE ISSUES
# This script prevents ALL Python cache problems

echo "==============================================="
echo "KRAKEN TRADING BOT - CACHE-FREE LAUNCHER"  
echo "==============================================="

# Set environment to prevent cache creation
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Clean any existing cache aggressively
echo "[CLEANUP] Removing any existing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true  
find . -name "*cpython-313*" -delete 2>/dev/null || true
find . -name "*cpython-312*" -delete 2>/dev/null || true

echo "[CACHE] Cache cleanup complete!"

# Launch bot with cache completely disabled
echo "[LAUNCH] Starting bot with cache disabled..."
python3 -B scripts/live_launch.py

echo "[DONE] Bot launcher finished"