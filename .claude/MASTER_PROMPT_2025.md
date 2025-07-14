# Kraken Trading Bot - Master Prompt (2025)

## Project Context
You are working with a **production-ready Kraken cryptocurrency trading bot** that has been fully completed and optimized as of July 7, 2025. This is a high-performance, fee-free micro-scalping system built with Python 3.12+ and asyncio.

## 🎯 Current Status: PRODUCTION READY
- **Completion Level**: 100% - All critical systems operational
- **Last Major Update**: July 7, 2025 - WebSocket V2 fixes and optimization
- **Trading Mode**: Live production (no paper trading)
- **Performance**: Optimized for 0.5-1% profit targets with high frequency

## 🔧 Core Architecture
- **Exchange**: Kraken (leveraging fee-free trading advantage)
- **Real-Time Data**: WebSocket V2 with proper callback handling
- **Signal Generation**: Optimized thresholds (0.1% momentum, 0.6 confidence)
- **Balance Management**: Real-time WebSocket updates, no caching delays
- **Risk Management**: Multi-layer protection with 0.8% max stop-loss
- **Learning System**: Universal learning manager with event bus integration

## 📁 Critical File Locations
```
src/core/bot.py                              # Main bot orchestration
src/exchange/websocket_manager_v2.py         # WebSocket V2 real-time data
src/trading/opportunity_scanner.py           # Signal generation engine
src/trading/unified_balance_manager.py       # Balance management
src/learning/universal_learning_manager.py   # AI learning system
scripts/live_launch.py                       # Production launcher
config.json                                  # Bot configuration
requirements.txt                             # Python dependencies
```

## 🚀 Launch Commands
```bash
# Production Launch
python scripts/live_launch.py

# Alternative Windows Launch
./START_BOT_OPTIMIZED.bat

# Development Testing
python scripts/quick_check.py
```

## ⚠️ Safety Rules (CRITICAL)
1. **NO EMOJI POLICY**: Never use emojis in code, logs, or Python files
2. **FEE-FREE PROTECTION**: Never disable fee-free trading advantage
3. **STOP-LOSS LIMITS**: Never exceed 0.8% stop-loss per trade
4. **CAPITAL PROTECTION**: Max 2% position size, 5% daily loss limit
5. **API COMPLIANCE**: Respect Kraken rate limits (15 calls/second)

## 🔍 Debugging Workflow
When investigating issues:
1. Check recent logs: `tail -100 kraken_infinity_bot.log`
2. Verify WebSocket connectivity and message flow
3. Examine signal generation thresholds and evaluation
4. Test balance manager real-time updates
5. Validate component initialization order

## 🛠️ Custom Commands Available
- `/debug-signals` - Analyze signal generation issues
- `/fix-websocket` - Diagnose WebSocket connectivity problems  
- `/analyze-performance` - Review bot performance metrics
- `/launch-bot` - Safe production launch with pre-flight checks
- `/optimize-strategy` - Tune trading parameters for better performance

## 📊 Key Performance Indicators
- **Signal Frequency**: Minimum 1 signal per 10 iterations
- **Profit Target**: 0.5% per trade (range: 0.1% - 1%)
- **Success Rate**: Target 80%+ profitable trades
- **Execution Speed**: Sub-second trade execution
- **Uptime**: 99.9% availability target

## 🔧 Recent Fixes Applied (July 7, 2025)
1. ✅ **WebSocket V2 Callback Registration** - Fixed message handling
2. ✅ **Signal Optimization** - Lowered momentum threshold to 0.1%
3. ✅ **Debug Enhancement** - Added comprehensive logging
4. ✅ **Project Cleanup** - Removed old/incomplete files
5. ✅ **Dependency Management** - Added python-kraken-sdk to requirements
6. ✅ **Import Resolution** - Fixed all syntax and import errors

## 🎮 Development Guidelines
- **Test-Driven Development**: All changes require comprehensive testing
- **Real-Time Priority**: WebSocket V2 data always preferred over REST
- **Error Recovery**: Implement graceful degradation and auto-restart
- **Memory Management**: Keep project memory clean, no duplicates
- **Performance Focus**: Optimize for speed and reliability
- **Security First**: Protect API credentials and implement safe defaults

## 🌟 Competitive Advantages
1. **Fee-Free Trading**: Significant cost advantage over competitors
2. **Real-Time Data**: No latency from cached data, instant market response
3. **AI Learning**: Adaptive system that improves performance over time
4. **Risk Management**: Advanced multi-layer protection systems
5. **High Frequency**: Capable of rapid micro-scalping opportunities

## 🔄 Maintenance Workflow
- Monitor logs for performance patterns and optimization opportunities
- Regularly review and adjust signal generation thresholds
- Validate WebSocket connectivity and data flow integrity  
- Test emergency stops and risk management systems
- Update learning patterns based on market conditions

## 📈 Success Metrics
The bot is considered successful when:
- Generating consistent 0.5% profits per trade
- Maintaining 80%+ trade success rate
- Operating with 99.9% uptime
- Responding to market opportunities within 1 second
- Learning and adapting to new market patterns

Remember: This is a **completed, production-ready system**. Focus on optimization, monitoring, and maintenance rather than fundamental architectural changes. All critical issues have been resolved and the bot is ready for live trading operations.