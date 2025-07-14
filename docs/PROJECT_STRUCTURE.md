# Kraken Trading Bot Project Structure

## Core Files
- `config.json` - Main configuration (USDT pairs, $5 minimums)
- `requirements.txt` - Python dependencies
- `.env` - API keys (not in git)

## Launch Commands
- `launch_trading_bot.py` - Main launcher
- `START_TRADING_BOT.bat` - Windows quick start

## Source Code (/src)
- `bot.py` - Main bot class with infinity loop
- `native_kraken_exchange.py` - Kraken API integration
- `websocket_manager.py` - Real-time data feeds
- `opportunity_scanner.py` - Finds profitable trades
- `opportunity_execution_bridge.py` - Executes opportunities
- `enhanced_trade_executor_with_assistants.py` - Trade execution with assistants
- `functional_strategy_manager.py` - Strategy coordination
- `enhanced_balance_manager.py` - Balance and portfolio tracking
- `profit_harvester.py` - Profit taking logic

## Strategies (/src/strategies)
- `fast_start_strategy.py` - Quick profit strategy
- `mean_reversion_strategy.py` - Buy low, sell high
- `autonomous_sell_engine.py` - Automatic profit taking

## Data Storage
- `/logs` - Log files
- `D:/trading_bot_data/` - Historical data and learning

## Key Features
- Kraken WebSocket v2 compliant
- $5 minimum trades (Tier 1)
- USDT pairs only
- Fee-free trading optimization
- Autonomous operation with self-healing
