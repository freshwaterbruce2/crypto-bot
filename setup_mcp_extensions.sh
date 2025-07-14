#\!/bin/bash
echo "==========================================="
echo "Setting up MCP Extensions"
echo "==========================================="
echo ""

# Create directories for configuration
mkdir -p configs/claude_code
mkdir -p configs/claude_desktop

# 1. Claude Code Configuration (traditional method)
echo "Creating Claude Code MCP configuration..."
cat > configs/claude_code/mcp_setup_commands.txt << 'COMMANDS'
# Memory Server
claude mcp add memory "npx" "@modelcontextprotocol/server-memory"

# PostgreSQL Server (adjust connection string as needed)
claude mcp add postgres "npx" "@modelcontextprotocol/server-postgres" "postgresql://user:password@localhost:5432/trading_bot"

# Time/Scheduler Server (using cron-style scheduler)
claude mcp add scheduler "npx" "@modelcontextprotocol/server-cron"

# Alternative: SQLite for easier setup than PostgreSQL
claude mcp add sqlite "npx" "@modelcontextprotocol/server-sqlite" "trading_bot.db"

# List all servers
claude mcp list

# Start MCP server
claude mcp serve
COMMANDS

# 2. Claude Desktop Configuration (for manual setup if .dxt not available)
echo "Creating Claude Desktop configuration..."
cat > configs/claude_desktop/claude_desktop_config.json << 'JSON'
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-memory"
      ]
    },
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://localhost:5432/trading_bot"
      ],
      "env": {
        "PGUSER": "your_username",
        "PGPASSWORD": "your_password"
      }
    },
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "D:/trading_data/trading_bot.db"
      ]
    },
    "time": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-time"
      ]
    },
    "filesystem-project": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/mnt/c/projects050625/projects/active/tool-crypto-trading-bot-2025"
      ]
    },
    "filesystem-data": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "D:/trading_data"
      ]
    }
  }
}
JSON

echo ""
echo "==========================================="
echo "Setup Instructions"
echo "==========================================="
echo ""
echo "FOR CLAUDE CODE:"
echo "1. Run the commands in: configs/claude_code/mcp_setup_commands.txt"
echo "2. Or copy and paste them one by one"
echo ""
echo "FOR CLAUDE DESKTOP:"
echo "Option A - Using Extensions (Recommended):"
echo "1. Open Claude Desktop"
echo "2. Go to Settings → Extensions"
echo "3. Search and install:"
echo "   - Memory Extension"
echo "   - PostgreSQL Extension"
echo "   - SQLite Extension (easier than PostgreSQL)"
echo "   - Time/Scheduler Extension"
echo ""
echo "Option B - Manual Configuration:"
echo "1. Copy configs/claude_desktop/claude_desktop_config.json"
echo "2. To: %APPDATA%\Claude\claude_desktop_config.json"
echo "3. Restart Claude Desktop"
echo ""
echo "==========================================="
