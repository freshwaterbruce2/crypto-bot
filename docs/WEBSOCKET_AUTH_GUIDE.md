# Kraken WebSocket Authentication Guide

## Overview
This guide explains how to properly configure WebSocket authentication for the Kraken trading bot and resolve common issues.

## Key Requirements

### 1. API Key Permissions (CRITICAL)
Your Kraken API key MUST have the following permissions enabled:

- **Query Funds** - To check balances
- **Query Open Orders & Trades** - To monitor orders
- **Query Closed Orders & Trades** - To track completed trades
- **Other -> Access WebSockets API** ⚠️ **MOST IMPORTANT**

Without the "Access WebSockets API" permission, you cannot use private WebSocket channels.

### 2. How to Enable WebSocket Permission
1. Log in to Kraken
2. Go to Settings > API
3. Find your API key and click Edit
4. Scroll down to "Other" section
5. Check "Access WebSockets API"
6. Save changes

### 3. WebSocket Token Lifecycle
- Tokens are obtained via `/0/private/GetWebSocketsToken` REST endpoint
- Tokens expire after 15 minutes
- Must be used quickly after generation
- Bot automatically refreshes tokens every 10 minutes

## Common Issues and Solutions

### Issue 1: Balance Shows $0 After Initial Connection
**Symptoms:**
- Bot shows correct balance initially (e.g., $18.85)
- Balance suddenly shows as $0
- No balance updates received via WebSocket

**Solution:**
1. Run the fix script: `python scripts/fix_websocket_auth.py`
2. Ensure API key has WebSocket permission
3. Check that private channels are connected

### Issue 2: "EAPI:Invalid key" Error
**Cause:** API key doesn't have WebSocket permission

**Solution:**
1. Enable "Access WebSockets API" permission in Kraken
2. Wait 1-2 minutes for changes to propagate
3. Restart the bot

### Issue 3: Token Expires During Trading
**Symptoms:**
- Bot works for ~15 minutes then stops receiving updates
- Private channel disconnections

**Solution:**
- The bot should automatically refresh tokens every 10 minutes
- If not working, check the auth manager logs
- Ensure REST client is properly connected

## Architecture Overview

### WebSocket Connections
1. **Public WebSocket** (`wss://ws.kraken.com/v2`)
   - Ticker data
   - OHLC candles
   - Trade feed
   - No authentication required

2. **Private WebSocket** (`wss://ws-auth.kraken.com/v2`)
   - Balance updates (real-time)
   - Order executions
   - Requires authentication token

### Real-Time Balance System
- Uses WebSocket v2 `balances` channel
- Provides instant updates after trades
- No 5-minute cache delays
- Fallback to REST API if needed

## Testing WebSocket Authentication

### Quick Test Script
```bash
python scripts/test_websocket_auth.py
```

This will:
1. Test REST API connection
2. Get WebSocket token
3. Connect to public channels
4. Connect to private channels
5. Show current balances

### Fix Script
```bash
python scripts/fix_websocket_auth.py
```

This will:
1. Diagnose authentication issues
2. Apply automatic fixes
3. Verify balance updates
4. Show detailed diagnostics

## Troubleshooting Checklist

- [ ] API key has "Access WebSockets API" permission
- [ ] API key is not expired
- [ ] REST client can connect successfully
- [ ] WebSocket token can be obtained
- [ ] Private channels connect without errors
- [ ] Balance snapshot is received after connection
- [ ] Balance updates occur after trades

## Log Messages to Watch

### Success Indicators
```
[WEBSOCKET] Successfully retrieved new auth token
[WEBSOCKET] Connected to private channels
[WEBSOCKET] Subscribed to balances channel
[REALTIME_BALANCE] Snapshot received: X assets
```

### Error Indicators
```
[WEBSOCKET] Cannot get WebSocket token without valid token
[WEBSOCKET] Private channel connection failed
[AUTH_MANAGER] Token refresh failed
```

## Best Practices

1. **Always verify API permissions** before starting the bot
2. **Monitor token refresh logs** to ensure automatic renewal
3. **Use real-time balance manager** instead of cached balances
4. **Check WebSocket health** regularly via connection stats
5. **Implement proper error handling** for disconnections

## Integration with Bot

The bot automatically:
- Manages WebSocket connections
- Refreshes tokens before expiry
- Reconnects on disconnection
- Falls back to REST API if needed
- Provides real-time balance updates

No manual intervention required once properly configured!