#\!/bin/bash
echo "========================================="
echo "Removing MCP-related directories"
echo "========================================="
echo ""

# Check for mcp_server directory
if [ -d "mcp_server" ]; then
    echo "Found mcp_server/ directory"
    echo "Removing..."
    rm -rf mcp_server/
    echo "[DONE] Removed mcp_server/"
fi

# Check for .mcp directory
if [ -d ".mcp" ]; then
    echo "Found .mcp/ directory"
    echo "Removing..."
    rm -rf .mcp/
    echo "[DONE] Removed .mcp/"
fi

# Check for any node_modules with MCP packages
if [ -d "node_modules/@modelcontextprotocol" ]; then
    echo "Found MCP packages in node_modules"
    echo "Removing..."
    rm -rf node_modules/@modelcontextprotocol
    echo "[DONE] Removed MCP packages from node_modules"
fi

# Check home directory for .claude MCP configs
if [ -d ~/.claude/mcp ]; then
    echo "Found ~/.claude/mcp directory"
    echo "Backing up..."
    mv ~/.claude/mcp ~/.claude/mcp.backup
    echo "[DONE] Moved to ~/.claude/mcp.backup"
fi

echo ""
echo "========================================="
echo "Cleanup complete\!"
echo "========================================="
