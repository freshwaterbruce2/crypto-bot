#!/bin/bash
# Simple Claude-Flow Setup as Development Tool

echo "🛠️ Setting up Claude-Flow as a development assistant"
echo ""

# Install Claude-Flow globally for development use
echo "📦 Installing Claude-Flow..."
npm install -g claude-flow@alpha

# Initialize Claude-Flow in your home directory (not in project)
cd ~
npx claude-flow@alpha init --force

# Store project context in Claude-Flow's memory
echo ""
echo "💾 Storing your trading bot project context..."
npx claude-flow@alpha memory store "current_project" "crypto-trading-bot"
npx claude-flow@alpha memory store "project_goal" "Python bot for fee-free crypto trading"
npx claude-flow@alpha memory store "strategy" "Buy low sell high, small profits, high volume"
npx claude-flow@alpha memory store "example_trade" "Buy DOGE at 1.00, sell at 1.10"
npx claude-flow@alpha memory store "project_path" "/mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025"

echo ""
echo "✅ Claude-Flow is ready to help you build!"
echo ""
echo "📋 Example commands to help with development:"
echo ""
echo "1. Get AI help planning your bot:"
echo '   npx claude-flow@alpha hive-mind spawn "Plan Python crypto trading bot architecture"'
echo ""
echo "2. Get code suggestions:"
echo '   npx claude-flow@alpha hive-mind spawn "Create CCXT integration for fee-free trading"'
echo ""
echo "3. Review your strategy:"
echo '   npx claude-flow@alpha cognitive analyze --behavior "scalping-strategy"'
