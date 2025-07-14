# Fix WebSocket Issues

Diagnose and fix WebSocket connectivity and data flow issues.

## Command Usage
`/fix-websocket [connection|data|auth]`

## Action
Analyze and fix WebSocket V2 issues in the Kraken trading bot.

**For connection issues:**
- Check python-kraken-sdk installation and version
- Verify WebSocket manager initialization
- Test connection establishment and reconnection logic

**For data flow issues:**
- Verify callback registration and message handling
- Check ticker data storage in last_price_update
- Analyze message processing pipeline

**For auth issues:**
- Verify API credentials and WebSocket token generation
- Check private channel subscriptions
- Test balance and order updates

$ARGUMENTS

Provide specific fixes with file paths and line numbers. Test solutions and verify they resolve the issue.