#!/bin/bash
# Fix claude-flow execution

echo "🔧 Setting up claude-flow to work properly..."

# Method 1: Use node directly with the compiled JS
echo "Method 1: Direct node execution..."
cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025
node node_modules/claude-flow/dist/cli/cli-core.js hive-mind spawn "Help improve my trading bot"

# If that doesn't work, let's check package.json for the correct entry point
echo ""
echo "Checking package.json for entry point..."
cat node_modules/claude-flow/package.json | grep -A 5 '"bin"'
