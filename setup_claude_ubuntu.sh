#!/bin/bash
# Claude Code Setup Script for Ubuntu/WSL
# Run this after WSL is installed and Ubuntu is set up

echo "====================================="
echo "Claude Code Setup Script for WSL"
echo "====================================="

# Update system
echo -e "\n[1/5] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required dependencies
echo -e "\n[2/5] Installing required dependencies..."
sudo apt install -y curl build-essential

# Install Node.js 20.x via NodeSource
echo -e "\n[3/5] Installing Node.js 20.x..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
echo -e "\n[4/5] Verifying installations..."
echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# Install Claude Code globally
echo -e "\n[5/5] Installing Claude Code..."
sudo npm install -g @anthropic-ai/claude-code

echo -e "\n====================================="
echo "Installation complete!"
echo "====================================="
echo ""
echo "Next steps:"
echo "1. Run: claude auth"
echo "2. Follow the authentication process"
echo "3. Test with: claude"
echo ""
echo "For VS Code integration:"
echo "- Open VS Code in WSL: code ."
echo "- Claude Code extension will be installed automatically"
echo ""
echo "====================================="
