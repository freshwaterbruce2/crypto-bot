# Signal Format Fix Summary

## Problem Identified
The bot was generating signals but collecting 0 signals because of field name mismatches:

1. **Strategies generate signals with:**
   - `symbol` (e.g., "BTC/USDT")
   - `type` (e.g., "buy")
   - `confidence` (e.g., 0.60)

2. **Signal formatter expected:**
   - `pair` (not `symbol`)
   - `side` (not `type`)
   - `confidence` ✓

## Fix Applied
Updated `_format_signal_for_kraken` in `functional_strategy_manager.py` to:
1. Accept both `symbol` and `pair` - converts `symbol` to `pair`
2. Accept both `type` and `side` - converts `type` to `side`
3. Added debug logging to track signal flow

## Expected Behavior
With these fixes:
- Signals with confidence 0.50-0.60 will be formatted correctly
- The bot will collect signals (not 0)
- Signals will be validated and queued for execution
- Trades should execute if balance is available

## Next Steps
1. Monitor logs for:
   - `[STRATEGY] XXX/USDT: Raw signal:` - Shows signal structure
   - `[SIGNAL_ACCEPTED]` - Confirms signal passed validation
   - `[BOT] Total signals collected: X` - Should be > 0
   - `[BOT] Signal passed validation` - Ready for execution

2. If signals are still not collected, check for:
   - Rate limiting blocking signals
   - Additional validation failures
   - Strategy status not "Ready"