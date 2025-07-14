# WebSocket Authentication and Balance Detection Fixes

## Summary of Issues Fixed

### 1. **WebSocket Authentication Token Issue** ✓
**Problem**: Bot couldn't authenticate to private WebSocket channels (balances, orders)
**Root Cause**: Missing "Access WebSockets API" permission on Kraken API key
**Solution**: 
- Added clear instructions about required API permission
- Enhanced error messages to guide users
- Created diagnostic tool to verify token generation

### 2. **Balance Detection Shows $0.00** ✓
**Problem**: Bot shows $0.00 despite having $18.85 USDT
**Root Cause**: Balance cache corruption when WebSocket fails
**Solution**:
- Added stale cache detection
- Track last known USDT balance
- Force refresh when cache incorrectly shows $0
- Multiple retry attempts during initialization

### 3. **Symbol Format Errors** ✓
**Problem**: "Unknown symbol" errors for ETH/USDT, XRP/USDT
**Root Cause**: Markets not loaded before symbol operations
**Solution**:
- Load markets early in initialization (Phase 1.1.5)
- Create symbol aliases (ETH/USDT → XETH/USDT)
- Add defensive market loading

### 4. **OHLC Data Not Reaching Strategies** ✓
**Problem**: Strategies not receiving OHLC candle data
**Root Cause**: WebSocket not subscribing to OHLC channel
**Solution**:
- Added OHLC subscription method
- Subscribe to 1-minute candles for all symbols

## Critical Requirements

### API Key Configuration
Your Kraken API key MUST have these permissions:
- ✅ Query Funds
- ✅ Query Open Orders & Trades
- ✅ Query Closed Orders & Trades
- ✅ Create & Modify Orders
- ✅ **Other → Access WebSockets API** (CRITICAL!)

Without "Access WebSockets API" permission, private channels will fail!

### How to Enable WebSocket Permission
1. Log in to Kraken.com
2. Go to Security → API
3. Click on your API key to edit
4. Enable "Other → Access WebSockets API"
5. Save changes

## Files Modified

### Core Bot (`src/core/bot.py`)
- Added early market loading in Phase 1.1.5
- Enhanced balance initialization with retries
- Better error handling and logging

### Exchange (`src/exchange/native_kraken_exchange.py`)
- Added symbol aliases for Kraken's internal naming
- Defensive market loading in all methods
- Better error messages for symbol lookup

### WebSocket Manager (`src/exchange/websocket_manager_v2.py`)
- Added OHLC subscription method
- Enhanced authentication error handling
- Get API credentials from environment

### Balance Manager (`src/trading/enhanced_balance_manager.py`)
- Stale cache detection
- Last known balance tracking
- Force refresh on $0 detection

## Diagnostic Tools Created

### 1. `scripts/fix_websocket_auth.py`
Comprehensive fix script that:
- Checks API permissions
- Fixes balance manager cache issues
- Creates diagnostic tool
- Updates WebSocket manager

### 2. `scripts/diagnose_websocket.py`
Diagnostic tool that tests:
- REST API connectivity
- WebSocket token generation
- Token refresh rate limits
- DNS resolution for WebSocket endpoints

### 3. `scripts/fix_balance_detection.py`
Tests balance detection at multiple levels:
- Direct exchange balance fetch
- Balance manager initialization
- Cache verification
- Multiple refresh attempts

## Running the Fixes

1. **First, enable WebSocket API permission on Kraken**

2. **Run the fix script**:
   ```bash
   python3 scripts/fix_websocket_auth.py
   ```

3. **Run diagnostics**:
   ```bash
   python3 scripts/diagnose_websocket.py
   ```

4. **Launch the bot**:
   ```bash
   python3 scripts/live_launch.py
   ```

## Expected Results

After applying fixes, the bot should:
- ✅ Generate WebSocket auth tokens successfully
- ✅ Show correct balance ($18.85 USDT + portfolio)
- ✅ Connect to private channels for real-time updates
- ✅ Receive OHLC data for strategy calculations
- ✅ Handle symbol lookups correctly

## Troubleshooting

### If token generation fails:
- Check API key has "Access WebSockets API" permission
- Verify API key and secret in .env file
- Run diagnostic tool to identify specific issue

### If balance still shows $0:
- Check logs/kraken_bot.log for cache issues
- Verify REST API returns correct balance
- Force clear cache and restart bot

### If WebSocket disconnects:
- Check network connectivity
- Verify DNS resolution works
- Check for rate limiting errors

## Architecture Notes

The bot uses WebSocket V2 directly (not SDK) for:
- Better control over connection handling
- Custom reconnection logic
- Direct token management
- Real-time data without caching

Private channels require separate authenticated connection to:
- `wss://ws-auth.kraken.com/v2`
- With token from `/0/private/GetWebSocketsToken`
- Token expires in 15 minutes
- Auto-refresh every 10 minutes