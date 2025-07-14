# Debug Trading Signals

Debug and analyze trading signal generation issues in the Kraken trading bot.

## Command Usage
`/debug-signals [symbol] [timeframe]`

## Action
Analyze the trading signal generation pipeline for the specified symbol and timeframe.

1. Check WebSocket data feed for $ARGUMENTS
2. Verify opportunity scanner is receiving ticker data
3. Examine signal thresholds and evaluation logic
4. Review recent signal generation logs
5. Test signal generation conditions manually
6. Provide detailed diagnostics and recommendations

Focus on:
- WebSocket V2 message flow
- Ticker data availability in last_price_update
- Signal confidence calculations
- Momentum and volatility thresholds
- Position detection accuracy

Output should include specific line numbers and values for debugging.