#!/bin/bash
# WSL Setup and Claude Code Installation Script

echo "=== WSL Claude Code Setup Script ==="
echo "Running from: $(pwd)"

# Update system packages
echo "1. Updating system packages..."
sudo apt update -y
sudo apt upgrade -y

# Install required dependencies
echo "2. Installing dependencies..."
sudo apt install -y curl git build-essential

# Install Node.js 20.x
echo "3. Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify Node installation
echo "4. Verifying Node.js installation..."
node --version
npm --version

# Clean npm cache
echo "5. Cleaning npm cache..."
sudo npm cache clean --force

# Install Claude Code globally
echo "6. Installing Claude Code..."
sudo npm install -g @anthropic-ai/claude-code --unsafe-perm=true --allow-root

# Create alias for easy access
echo "7. Setting up aliases..."
echo "alias claude='claude'" >> ~/.bashrc
echo "alias bot='cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025'" >> ~/.bashrc
source ~/.bashrc

# Navigate to project directory
echo "8. Navigating to project directory..."
cd /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025

# Test Claude Code
echo "9. Testing Claude Code installation..."
which claude
claude --version

echo "=== Setup Complete ==="
echo "You can now run 'claude' to start Claude Code CLI"
echo "Use 'bot' alias to quickly navigate to your project"