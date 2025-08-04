# Dual API Key Setup Guide

## Why Separate API Keys?

The nonce collision issue occurs because both REST API and WebSocket V2 authentication try to use the same nonce sequence. By using separate API keys, each maintains its own independent nonce counter on Kraken's servers.

## Step 1: Create API Keys on Kraken

### REST API Key (Primary Trading)
**Name:** `Trading Bot REST API`
**Permissions:**
- ✅ Query Funds  
- ✅ Query Open/Closed Orders
- ✅ Create & Cancel Orders
- ✅ Query Ledger Entries

### WebSocket API Key (Data Streaming)
**Name:** `Trading Bot WebSocket`
**Permissions:**
- ✅ Query Funds
- ✅ Query Open/Closed Orders  
- ✅ Query Ledger Entries
- ❌ Create & Cancel Orders (not needed for WebSocket)

## Step 2: Update Configuration

1. **Copy your current config:**
   ```bash
   cp config.json config.json.backup
   ```

2. **Use the new dual API template:**
   ```bash
   cp dual_api_config_template.json config.json
   ```

3. **Add your API keys to config.json:**
   ```json
   {
     "api_configuration": {
       "dual_key_setup": true,
       "rest_api": {
         "api_key": "YOUR_REST_API_KEY_HERE",
         "api_secret": "YOUR_REST_API_SECRET_HERE"
       },
       "websocket_api": {
         "api_key": "YOUR_WEBSOCKET_API_KEY_HERE",
         "api_secret": "YOUR_WEBSOCKET_API_SECRET_HERE"
       }
     }
   }
   ```

## Step 3: Update Environment Variables (Alternative)

Instead of config.json, you can use .env file:

```bash
# REST API Credentials
KRAKEN_REST_API_KEY=your_rest_api_key
KRAKEN_REST_API_SECRET=your_rest_api_secret

# WebSocket API Credentials  
KRAKEN_WEBSOCKET_API_KEY=your_websocket_api_key
KRAKEN_WEBSOCKET_API_SECRET=your_websocket_api_secret
```

## Step 4: Benefits

✅ **Eliminates Nonce Collisions** - Each key has independent nonce sequence
✅ **Better Security** - Separate permissions for different functions
✅ **Improved Reliability** - WebSocket issues don't affect trading
✅ **Better Monitoring** - Can track usage per connection type
✅ **Industry Standard** - Professional trading systems use this approach

## Step 5: Testing

After setup, test with:
```bash
python3 validate_bot_ready.py --quick
```

The validation should show:
- ✅ No more nonce collision errors
- ✅ WebSocket authentication successful  
- ✅ REST API trading operations work
- ✅ Both systems running in parallel

## Troubleshooting

**If you still see nonce errors:**
1. Verify API keys are different
2. Check permissions are correct
3. Wait 60 seconds between tests (nonce window)
4. Restart the bot completely

**WebSocket connection fails:**
1. Ensure WebSocket key has "Query Funds" permission
2. Check network connectivity
3. Verify API key is active

## Security Notes

- Store API secrets securely (use .env file, not config.json for production)
- Never commit API keys to version control
- Use IP restrictions on Kraken API keys if possible
- Monitor API usage regularly