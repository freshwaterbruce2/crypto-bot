#!/bin/bash
# Simple claude-flow wrapper

# Set up environment
export NODE_ENV=production
cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025

# Try different execution methods
echo "🚀 Attempting to run claude-flow..."

# Method 1: Force npx with cache bypass
echo "1. Trying npx with cache bypass..."
npx --no-install --yes claude-flow@alpha hive-mind spawn "Help improve my trading bot" 2>/dev/null

# Method 2: Direct node execution
if [ $? -ne 0 ]; then
  echo "2. Trying direct node execution..."
  NODE_PATH=./node_modules node ./node_modules/claude-flow/bin/claude-flow hive-mind spawn "Help improve my trading bot" 2>/dev/null
fi

# Method 3: Use the package directly
if [ $? -ne 0 ]; then
  echo "3. Installing globally as fallback..."
  npm install -g claude-flow@alpha --force
  claude-flow hive-mind spawn "Help improve my trading bot"
fi
