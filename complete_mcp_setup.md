# Complete MCP Setup for Trading Bot

## Essential MCP Extensions

### 1. Memory Server 🧠
- **Purpose**: Persistent context and learning from past trades
- **Command**: `claude mcp add memory "npx" "@modelcontextprotocol/server-memory"`

### 2. SQLite Database 📊
- **Purpose**: Store trading history and performance metrics
- **Command**: `claude mcp add sqlite "npx" "@modelcontextprotocol/server-sqlite" "D:/trading_data/trading_bot.db"`

### 3. Time/Scheduler ⏰
- **Purpose**: Schedule tasks and time-based operations
- **Command**: `claude mcp add time "npx" "@modelcontextprotocol/server-time"`

### 4. Puppeteer 🌐
- **Purpose**: Web scraping, browser automation, monitoring exchange websites
- **Command**: `claude mcp add puppeteer "npx" "@modelcontextprotocol/server-puppeteer"`

## Claude Code Setup Commands

```bash
# Add all servers
claude mcp add memory "npx" "@modelcontextprotocol/server-memory"
claude mcp add sqlite "npx" "@modelcontextprotocol/server-sqlite" "D:/trading_data/trading_bot.db"
claude mcp add time "npx" "@modelcontextprotocol/server-time"
claude mcp add puppeteer "npx" "@modelcontextprotocol/server-puppeteer"

# List configured servers
claude mcp list

# Start MCP server
claude mcp serve
```

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
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
      "args": ["-y", "@modelcontextprotocol/server-time"]
    },
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    },
    "filesystem-project": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "C:/projects050625/projects/active/tool-crypto-trading-bot-2025"
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
```

## Puppeteer Use Cases for Trading Bot

1. **Exchange Monitoring**
   - Monitor Kraken status page for outages
   - Check for announcements and updates
   - Screenshot trading positions

2. **Price Alerts**
   - Monitor prices across multiple exchanges
   - Capture market sentiment from news sites
   - Track social media trends

3. **Automated Testing**
   - Test your trading dashboard
   - Verify UI elements are working
   - Automated screenshots for logs

4. **Data Collection**
   - Scrape additional market data
   - Collect trading volume statistics
   - Monitor competitor bots

