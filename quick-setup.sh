#!/bin/bash
# Quick Claude-Flow Setup for Trading Bot

echo "🚀 Quick Setup for Claude-Flow Trading Bot Integration"
echo ""

# First, ensure we're in the right directory
cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025

# Install claude-flow globally
echo "📦 Installing Claude-Flow globally..."
npm install -g claude-flow@alpha

# Initialize with force flag
echo "🔧 Initializing Claude-Flow..."
claude-flow init --force

# Create trading bot specific configuration
echo "💾 Setting up trading bot memory..."
claude-flow memory store "project_type" "crypto-trading-bot"
claude-flow memory store "trading_strategy" "high-volume-small-profits"
claude-flow memory store "fee_structure" "fee-free-trading"

# Test the setup
echo "✅ Testing setup..."
claude-flow --version
claude-flow memory stats

echo ""
echo "🎯 Setup complete! You can now use claude-flow commands."
echo "Try: claude-flow hive-mind wizard"
