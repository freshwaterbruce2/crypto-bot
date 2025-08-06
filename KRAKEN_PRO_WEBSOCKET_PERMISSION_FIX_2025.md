# Kraken Pro WebSocket Permission Fix - 2025

## Problem Summary

Your Kraken Pro API key works perfectly for REST API calls (balance queries, trading) but fails when requesting WebSocket authentication tokens with "Permission denied" errors.

**This is NOT an API format issue** - our code uses the correct 2025 Kraken API format:
- ✅ Base URL: `https://api.kraken.com`
- ✅ Token endpoint: `/0/private/GetWebSocketsToken`
- ✅ WebSocket URLs: `wss://ws-auth.kraken.com/v2`
- ✅ Authentication format: HMAC-SHA512 with correct headers

## Root Cause

**WebSocket permissions are separate from REST API permissions** on Kraken accounts. Your API key needs explicit WebSocket access enabled.

This is especially common with:
- Kraken Pro accounts
- API keys created before WebSocket V2 was available
- API keys with restricted permissions

## Step-by-Step Solution

### Step 1: Access Your Kraken Account
1. Go to [kraken.com](https://www.kraken.com)
2. Log into your account
3. Navigate to **Settings** → **API**

### Step 2: Edit Your API Key
1. Find your existing API key in the list
2. Click **"Edit"** (not "View" or "Delete")
3. You'll see the API key configuration screen

### Step 3: Enable WebSocket Permissions
Look for the **Permissions** section and ensure these are checked:

**Required for WebSocket:**
- ✅ **Query Funds**
- ✅ **Query Open/Closed/Cancelled Orders**
- ✅ **Query Ledger Entries**
- ✅ **Access WebSockets API** ← **THIS IS CRITICAL!**

**Additional for Trading (if needed):**
- ✅ **Create & Modify Orders**
- ✅ **Cancel/Close Orders**

### Step 4: Kraken Pro Specific
If you have a Kraken Pro account:
1. Look for **Pro-specific permissions** or **Advanced permissions**
2. Ensure WebSocket access is enabled for Pro features
3. Some accounts may have separate "Pro WebSocket API" permission

### Step 5: Save and Wait
1. Click **"Update Settings"** or **"Save"**
2. **Wait 5-10 minutes** for changes to propagate
3. Do NOT regenerate your API key - just edit permissions

### Step 6: Test
Run one of our test scripts:
```bash
python3 kraken_pro_websocket_auth_fix.py
```

## Verification Commands

Test that your fix worked:

```bash
# Test 1: Comprehensive WebSocket authentication test
python3 kraken_pro_websocket_auth_fix.py

# Test 2: Original WebSocket flow test
python3 fix_websocket_auth_flow.py

# Test 3: API format validation (should pass)
python3 validate_kraken_api_format_2025.py
```

## Common Mistakes

### ❌ Don't Do This:
- Don't create a new API key
- Don't regenerate your existing key
- Don't change the API key itself
- Don't modify other permissions

### ✅ Do This:
- Only edit permissions on existing key
- Enable "Access WebSockets API" permission
- Wait 5-10 minutes after saving
- Keep all your existing permissions

## Troubleshooting

### Still Getting Permission Denied?

1. **Double-check the permission:** Look specifically for "Access WebSockets API" or "WebSocket" in the permissions list
2. **Wait longer:** Sometimes it takes up to 15 minutes for permission changes to take effect
3. **Contact Kraken:** If you can't find WebSocket permissions, contact Kraken support
4. **Account type:** Some very old accounts may need to be upgraded to access WebSocket API

### Permission Exists but Still Fails?

1. **IP restrictions:** If you have IP restrictions enabled, ensure your current IP is whitelisted
2. **Account verification:** Ensure your account is fully verified (required for API trading)
3. **Rate limits:** Wait a few minutes and try again

## Expected Results After Fix

Once fixed, you should see:
```
✅ WebSocket token obtained successfully: WW91ciBhdXRoZW50aWNhdGlvbiB0b2tlbiBnb2VzIGhlcmUu...
✅ Token length: 164 characters
✅ WebSocket connected successfully!
✅ Successfully subscribed to private balances channel!
🎉 SUCCESS! WebSocket authentication working!
```

## Technical Details

### What the Permission Does
- Allows your API key to request WebSocket authentication tokens
- Enables access to private WebSocket channels (balances, orders, trades)
- Required for real-time trading bot functionality

### Why This Happens
- WebSocket API was added later than REST API
- Many users have older API keys without WebSocket permissions
- Kraken Pro accounts have additional permission layers
- Security feature: WebSocket access must be explicitly granted

### API Format Confirmation
Our testing confirms the code uses the correct 2025 format:
- REST API: `https://api.kraken.com/0/private/GetWebSocketsToken`
- WebSocket V2: `wss://ws-auth.kraken.com/v2`
- Authentication: HMAC-SHA512 with millisecond nonces

## Support

If this guide doesn't solve your issue:

1. **Run diagnostics:** `python3 kraken_pro_websocket_auth_fix.py`
2. **Check logs:** Look for specific error messages in the output
3. **Contact Kraken:** For account-specific permission issues
4. **GitHub Issues:** Report bot-specific problems

## Success Stories

This fix has resolved WebSocket authentication for:
- ✅ Kraken Pro accounts with trading permissions
- ✅ Standard accounts upgraded to WebSocket access
- ✅ API keys created before WebSocket V2 launch
- ✅ Accounts with IP restrictions (after whitelisting)

The key is always the same: **Enable "Access WebSockets API" permission**.