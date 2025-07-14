#\!/bin/bash
# MCP Server Setup for Trading Bot Project

echo "Setting up MCP servers for trading bot..."

# 1. Memory server for persistent trading context
echo "Adding memory server..."
claude mcp add memory npx -y @modelcontextprotocol/server-memory

# 2. File system server for better file operations
echo "Adding filesystem server for project directory..."
claude mcp add filesystem npx -y @modelcontextprotocol/server-filesystem /mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025

# 3. File system server for trading data
echo "Adding filesystem server for trading data..."
claude mcp add trading-data npx -y @modelcontextprotocol/server-filesystem D:/trading_data

# List configured servers
echo -e "\nConfigured MCP servers:"
claude mcp list

echo -e "\nSetup complete\! Run 'claude mcp serve' to start the MCP server."
