#!/bin/bash
# Install Claude-Flow dependencies

echo "📦 Installing required dependencies for Claude-Flow..."

# 1. Install unzip (needed for Deno)
echo "1️⃣ Installing unzip..."
sudo apt-get update
sudo apt-get install -y unzip

# 2. Install Deno
echo "2️⃣ Installing Deno..."
curl -fsSL https://deno.land/x/install/install.sh | sh

# 3. Add Deno to PATH
echo "3️⃣ Adding Deno to PATH..."
echo 'export DENO_INSTALL="$HOME/.deno"' >> ~/.bashrc
echo 'export PATH="$DENO_INSTALL/bin:$PATH"' >> ~/.bashrc
export DENO_INSTALL="$HOME/.deno"
export PATH="$DENO_INSTALL/bin:$PATH"

# 4. Install tsx globally
echo "4️⃣ Installing tsx..."
npm install -g tsx

# 5. Now install Claude-Flow
echo "5️⃣ Installing Claude-Flow..."
npm install -g claude-flow@alpha

# 6. Test installation
echo ""
echo "✅ Testing installation..."
claude-flow --version || npx claude-flow@alpha --version

echo ""
echo "🎯 Installation complete! Now you can use:"
echo "   claude-flow hive-mind spawn 'Help improve my trading bot'"
echo "   OR"
echo "   npx claude-flow@alpha hive-mind spawn 'Help improve my trading bot'"
