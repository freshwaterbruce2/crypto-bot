# Claude Code Built-in Tools & Optimization

## Built-in Tools (No MCP needed!)
Claude Code already has these tools built-in:
- File operations (read, write, edit)
- Command execution (bash, git, etc.)
- Directory navigation
- Git operations
- Code analysis
- Web fetching (can read URLs)

## MCP Servers (Optional)
While Claude Code CAN use MCP servers, you DON'T need them for your trading bot.
The built-in tools are sufficient.

## Optimization Commands for Trading Bot

### 1. Batch Operations Command
```bash
claude "1. Fix balance check in src/enhanced_trade_executor_with_assistants.py line 257 using portfolio intelligence. 2. Apply minimum order learning fix in same file. 3. Update config.json: take_profit_pct=0.5, stop_loss_pct=0.8. 4. Test with python scripts/simple_bot_launcher.py for 30 seconds. 5. If successful, commit all changes."
```

### 2. Use --dangerously-skip-permissions for Autonomous Work
```bash
claude --dangerously-skip-permissions "Fix all issues in the trading bot and get it running profitably"
```

### 3. Create Custom Commands for Repeated Tasks
In .claude/commands/full-fix.md:
```
Apply ALL fixes from project knowledge:
1. Portfolio Intelligence fix from 'Portfolio Intelligence Fix - Enhanced Trade Executor.txt'
2. Minimum learning from 'Kraken Minimum Learning & USDT Optimization Fix.txt'  
3. Config optimization: take_profit_pct=0.5, stop_loss_pct=0.8
4. Test and verify bot runs without errors
5. Commit with message "feat: complete trading bot optimization"
Do this autonomously without asking for permission.
```

### 4. Use Print Mode for Quick Checks
```bash
claude -p "Show current USDT balance and any errors in last 50 lines of logs/kraken_bot.log"
```

### 5. Direct Edit Without Analysis
```bash
claude "In config.json, ONLY change take_profit_pct to 0.5. Don't analyze anything else."
```