#!/bin/bash
# Claude-Flow Installation Script for Trading Bot

echo "🚀 Installing Claude-Flow v2.0.0 Alpha for Trading Bot..."
echo ""

# Step 1: Initialize Claude Flow with force flag
echo "1️⃣ Initializing Claude Flow with enhanced MCP setup..."
npx --y claude-flow@alpha init --force

# Step 2: Check installation
echo ""
echo "2️⃣ Checking Claude Flow installation..."
npx --y claude-flow@alpha --version

# Step 3: Set up MCP configuration for trading bot
echo ""
echo "3️⃣ Setting up MCP configuration..."
mkdir -p .claude
cat > .claude/settings.json << 'EOF'
{
  "hooks": {
    "preEditHook": {
      "command": "npx",
      "args": ["claude-flow", "hooks", "pre-edit", "--file", "${file}", "--auto-assign-agents", "true"],
      "alwaysRun": false
    },
    "postEditHook": {
      "command": "npx", 
      "args": ["claude-flow", "hooks", "post-edit", "--file", "${file}", "--format", "true"],
      "alwaysRun": true
    },
    "sessionEndHook": {
      "command": "npx",
      "args": ["claude-flow", "hooks", "session-end", "--generate-summary", "true"],
      "alwaysRun": true
    }
  },
  "permissions": {
    "allow": [
      "mcp__ruv-swarm",
      "mcp__claude-flow"
    ],
    "deny": []
  }
}
EOF

# Step 4: Initialize memory system for trading bot
echo ""
echo "4️⃣ Initializing memory system for trading strategies..."
npx --y claude-flow@alpha memory store "trading-bot" "Crypto trading bot with fee-free trading focus"
npx --y claude-flow@alpha memory store "strategy" "Buy low sell high, small profits, high volume"
npx --y claude-flow@alpha memory store "example" "Buy DOGE at $1.00, sell at $1.10, profit $0.10 per coin"

# Step 5: Test hive-mind
echo ""
echo "5️⃣ Testing hive-mind capabilities..."
npx --y claude-flow@alpha hive-mind test --agents 3 --coordination-test

echo ""
echo "✅ Claude-Flow installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Run: bash install-claude-flow.sh"
echo "2. Then: npx claude-flow@alpha hive-mind wizard"
echo "3. Start building: npx claude-flow@alpha hive-mind spawn 'build crypto trading bot' --claude"
