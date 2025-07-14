#!/bin/bash
# Trading Bot Claude-Flow Initialization

echo "🤖 Initializing Crypto Trading Bot with Claude-Flow"

# Direct initialization commands
echo "1️⃣ Installing Claude-Flow Alpha..."
npm install -g claude-flow@alpha

echo "2️⃣ Creating project structure..."
mkdir -p src tests data config logs

echo "3️⃣ Initializing with trading bot configuration..."
npx claude-flow@alpha init --force --skip-mcp

echo "4️⃣ Setting up trading bot memory..."
npx claude-flow@alpha memory store "bot_name" "Profit Snowball Bot"
npx claude-flow@alpha memory store "exchange" "fee-free exchange"
npx claude-flow@alpha memory store "strategy" "scalping small profits"
npx claude-flow@alpha memory store "risk_management" "1% per trade max"

echo "✅ Ready to build trading bot!"
echo ""
echo "Next command to run:"
echo 'npx claude-flow@alpha hive-mind spawn "Build Python crypto trading bot" --agents 6'
