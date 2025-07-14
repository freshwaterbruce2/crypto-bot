#!/bin/bash
# Direct installation method for Claude-Flow

echo "Installing Claude-Flow directly..."

# Method 1: Global install (recommended)
echo "Method 1: Installing globally..."
npm install -g claude-flow@alpha

# Check if installed
echo ""
echo "Checking installation..."
claude-flow --version

# If global didn't work, try local install
if [ $? -ne 0 ]; then
    echo "Global install failed, trying local install..."
    npm install claude-flow@alpha
    echo "Using local install with npx..."
fi

echo ""
echo "Testing Claude-Flow..."
# Try global command first
claude-flow hive-mind spawn "Help improve my trading bot" 2>/dev/null || \
# If that fails, use npx with local install
npx claude-flow hive-mind spawn "Help improve my trading bot"
