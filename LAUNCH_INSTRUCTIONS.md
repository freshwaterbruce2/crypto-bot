# Launch Instructions - Trading Bot Ready!

## Pre-Launch Checklist

### 1. Verify API Credentials
- Check `.env` file has:
  ```
  KRAKEN_API_KEY=your_actual_key
  KRAKEN_API_SECRET=your_actual_secret
  ```
- Ensure these are for the account with $161.39 USDT

### 2. Run Diagnostic Test
```bash
python scripts/diagnose_balance.py
```

Should show:
- Connected to Kraken API ✓
- USDT Balance: $161.39
- Portfolio includes ALGO and AI16Z

### 3. Launch the Bot
```bash
python scripts/live_launch.py
```

## What to Expect

### Initial Startup (First 30 seconds)
```
[INIT] Using API key: abcd1234... (tier: starter)
[INIT] Exchange connected successfully
[EBM] Cleared all caches on initialization
[BALANCE_DEBUG] Fetching fresh balance from Kraken API
[BALANCE_DEBUG] Found USDT: 161.39
[INIT] Found 11 USDT pairs
```

### Signal Generation (Every second)
```
[STRATEGY] ADA/USDT: Raw signal: {'type': 'buy', ...}
[SIGNAL_COLLECTED] ADA/USDT: buy signal with confidence=0.60
[BOT] Total signals collected: 6
```

### Trade Execution
```
[BOT] Signal passed validation: ADA/USDT buy
[BALANCE_DEBUG] Using USDT balance: 161.39
[EXECUTE] Trade executed: ADA/USDT buy
✓ Order placed: Buy 8.44 ADA @ $0.592
```

## Monitoring Success

### Good Signs
- `Total signals collected: 6` (not 0!)
- `Using USDT balance: 161.39` (not $1.97!)
- `Trade executed` messages
- New trades in Kraken account

### Warning Signs
- `Portfolio: $1.97` - Balance not detected
- `Total signals collected: 0` - Signal format issue
- `Insufficient funds` - Balance detection issue

## Troubleshooting

### If Balance Shows $1.97
1. Stop the bot (Ctrl+C)
2. Run diagnostic: `python scripts/diagnose_balance.py`
3. Check output for actual balance format
4. Verify API credentials are correct

### If No Signals Collected
- Check WebSocket connection
- Ensure market data is flowing
- Look for `[SIGNAL_REJECTED]` messages

### If Trades Don't Execute
- Check for rate limiting
- Verify minimum order sizes
- Look for Kraken API errors

## Success Metrics

After 5 minutes, you should see:
- Multiple executed trades
- Profits accumulating (0.5% targets)
- Portfolio value increasing
- No repeated errors

## Stop the Bot
Press `Ctrl+C` to gracefully shutdown

## Next Steps
Once trading successfully:
1. Monitor profit accumulation
2. Check logs for any warnings
3. Let the snowball effect build profits!

The bot is now ready to trade with your $161.39 USDT!