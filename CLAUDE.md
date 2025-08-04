## Crypto Trading Bot Memory

### 🎯 PROJECT STATUS: DREAM ACHIEVED - LIVE AND TRADING! 🚀
**Launch Date:** 2025-07-14  
**Status:** ✅ OPERATIONAL AND AUTONOMOUS  
**Achievement:** World-class trading bot successfully launched

### Trading Strategy
- Always focus on low priced USDT pairs.
- When all capital is deployed in positions, balance checks will show 0 USDT
- Micro-profit strategy: 0.5-1% profit targets
- Fee-free trading on Kraken Pro enabled
- 44 USDT pairs actively monitored
- Real-time WebSocket V2 integration

### Agent Setup and File Access
- MCP claude-flow agents have FULL file system access through AgentToolsBridge
- Agents can read, write, edit, delete files and run bash commands like Claude Code
- All agent tools are in src/utils/agent_tools_bridge.py
- Agents are NOT just read-only - they can make real changes

### File Persistence
- ALL files saved to /mnt/c/dev/tools/crypto-trading-bot-2025/
- Maps to Windows C:\dev\tools\crypto-trading-bot-2025\
- Files are permanent and accessible from Windows Explorer, VS Code
- WSL2 is accessing Windows C: drive, not temporary Linux storage

### Code Duplication Status
- Successfully eliminated duplicate functions across project
- Created unified utilities: position_sizing.py, duplicate_prevention.py, unified_balance.py
- Removed 8 duplicate calculate_position_size functions
- Pre-commit hook prevents new duplicates
- Project is clean with no duplicate files

### Important Instructions
- Use agents for real file operations, not just research
- Remember file locations are permanent Windows files
- Keep agents equipped with full tool access
- Maintain duplicate prevention systems