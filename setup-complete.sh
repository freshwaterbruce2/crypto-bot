#!/bin/bash
# Complete setup for claude-flow

echo "🔧 Installing all dependencies for claude-flow..."

# 1. Install unzip (required for Deno)
echo "1️⃣ Installing unzip..."
sudo apt-get update
sudo apt-get install -y unzip

# 2. Install Deno
echo "2️⃣ Installing Deno..."
curl -fsSL https://deno.land/x/install/install.sh | sh

# 3. Add Deno to current session PATH
export DENO_INSTALL="$HOME/.deno"
export PATH="$DENO_INSTALL/bin:$PATH"

# 4. Verify Deno installation
echo "3️⃣ Verifying Deno..."
deno --version

# 5. Now install claude-flow
echo "4️⃣ Installing claude-flow globally..."
npm install -g claude-flow@alpha

# 6. Test it
echo "5️⃣ Testing claude-flow..."
claude-flow --version

echo ""
echo "✅ Setup complete! Now run:"
echo "   claude-flow hive-mind spawn 'Help improve my trading bot'"
