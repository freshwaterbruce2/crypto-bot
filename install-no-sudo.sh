#!/bin/bash
# Install claude-flow without sudo

echo "🔧 Installing without sudo requirements..."

# 1. Check if unzip exists
if ! command -v unzip &> /dev/null; then
    echo "❌ unzip is required but not installed."
    echo "Alternative: Download Deno manually from https://deno.land/"
    echo "Or use Option 3 below instead."
    exit 1
fi

# 2. Install Deno to user directory (no sudo needed)
echo "✅ Installing Deno to user directory..."
curl -fsSL https://deno.land/x/install/install.sh | sh

# 3. Set up PATH
echo 'export DENO_INSTALL="$HOME/.deno"' >> ~/.bashrc
echo 'export PATH="$DENO_INSTALL/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 4. Install claude-flow
echo "📦 Installing claude-flow..."
export DENO_INSTALL="$HOME/.deno"
export PATH="$DENO_INSTALL/bin:$PATH"
npm install -g claude-flow@alpha

echo "✅ Done! Now run: claude-flow hive-mind spawn 'Help improve my trading bot'"
