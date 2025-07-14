# Kraken Pro Micro-Profit Trading Bot - Autonomous Self-Evolving System

<!-- CLAUDE-note-overview: Fee-free micro-profit trading bot with self-learning, self-diagnosing, self-repairing capabilities -->
<!-- CLAUDE-note-architecture: Multi-assistant autonomous system with portfolio intelligence and adaptive learning -->
<!-- CLAUDE-note-critical: Rate limits and WebSocket v2 authentication are primary failure vectors -->

## System Architecture
```
tool-crypto-trading-bot-2025/
├── .claude/
│   ├── CLAUDE.md (this file)
│   ├── TRADE_EXECUTION_FLOW.md
│   ├── LEARNING_FLOW.md
│   ├── MANAGEMENT_FLOW.md
│   ├── SELF_DIAGNOSTIC_FLOW.md
│   ├── RATE_LIMIT_PROTECTION.md
│   └── WEBSOCKET_CONFIGURATION.md
├── src/
│   ├── bot.py (KrakenTradingBot)
│   ├── enhanced_trade_executor_with_assistants.py
│   ├── enhanced_balance_manager.py
│   ├── kraken_rate_limit_manager.py
│   ├── websocket_manager.py
│   ├── self_learning_error_resolver.py
│   └── unified_autonomous_system.py
└── scripts/
    ├── live_launch.py
    ├── emergency_stop.py
    └── rate_limit_recovery.py
```

## Core Strategy

- **Goal**: Realized profits through high-frequency micro-gains
- **Method**: Buy low, sell high, 0.5-1% profits per trade
- **Advantage**: Fee-free trading on Kraken Pro
- **Philosophy**: Snowball effect - 1000 trades × $0.10 = $100

## Essential Commands

```bash
# Launch autonomous trading
cd C:\projects050625\projects\active\tool-crypto-trading-bot-2025
python scripts/live_launch.py

# Emergency procedures
python scripts/emergency_stop.py
python scripts/rate_limit_recovery.py

# System diagnostics
python -m src.diagnostics.system_health_check
```

## Critical Warnings

⚠️ **NEVER exceed rate limits** - see @RATE_LIMIT_PROTECTION.md  
⚠️ **NEVER use XBT/USD** - always BTC/USD (WebSocket v2)  
⚠️ **NEVER report insufficient funds** without portfolio check  
⚠️ **ALWAYS verify WebSocket permissions** before connection  

## System Flows

📊 **Trade Execution**: @TRADE_EXECUTION_FLOW.md  
🧠 **Learning & Adaptation**: @LEARNING_FLOW.md  
💼 **Portfolio Management**: @MANAGEMENT_FLOW.md  
🔧 **Self-Diagnostics**: @SELF_DIAGNOSTIC_FLOW.md  
🚦 **Rate Limiting**: @RATE_LIMIT_PROTECTION.md  
🔌 **WebSocket Config**: @WEBSOCKET_CONFIGURATION.md  

## Development Principles

✅ Async-first architecture  
✅ Self-healing systems  
✅ Continuous learning  
✅ Fail-safe operations  
✅ Token-efficient documentation