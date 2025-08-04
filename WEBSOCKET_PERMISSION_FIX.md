# WebSocket Permission Fix Required

## 🚨 Issue Detected

The WebSocket API key is getting `EGeneral:Permission denied` when trying to obtain authentication tokens.

## 🔧 Solution

The **WebSocket API key** needs additional permissions to work with Kraken's WebSocket V2 API.

### Required Permissions for WebSocket API Key:

Go back to your WebSocket API key on Kraken and ensure it has:

#### ✅ **Required Permissions:**
- **Query Funds** ✅ (already have)
- **Query Open Orders & Trades** ✅ (already have)  
- **Query Closed Orders & Trades** ✅ (already have)
- **Query Ledger Entries** ✅ (already have)

#### 🚨 **Missing Permission (ADD THIS):**
- **Export Data** ✅ **← ADD THIS ONE**

## 🤔 Why Export Data is Needed

Kraken's WebSocket V2 API requires the "Export Data" permission to:
1. Generate WebSocket authentication tokens
2. Access real-time balance streams
3. Subscribe to private channels

This is different from REST API requirements.

## 🔄 Steps to Fix:

1. **Go to Kraken API Management**
2. **Edit your WebSocket API key** (`WebSocket-data` or similar)
3. **Enable "Export Data" permission**
4. **Save the changes**
5. **Test again**

## 🧪 After Fixing:

Run this test to verify:
```bash
python3 src/core/bot.py
```

You should see:
- ✅ No more "Permission denied" errors
- ✅ WebSocket authentication successful
- ✅ Balance streaming working
- ✅ Bot launching successfully

## 🔒 Security Note

"Export Data" for the WebSocket key is safe because:
- It's only used for real-time streaming
- No trading permissions on this key
- Separate from your REST trading key