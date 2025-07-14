# Kraken SDK Migration Guide

## Overview
This guide documents the integration of the official `python-kraken-sdk` into the trading bot, as requested in CLAUDE.md.

## Current Implementation

### WebSocket (Already Using SDK)
- **File**: `src/exchange/websocket_manager_v2.py`
- **Status**: ✅ Already using `kraken.spot.SpotWSClient`
- **Features**:
  - Real-time ticker data
  - OHLC updates
  - Private channels (balances, orders)
  - Automatic reconnection

### REST API (Native Implementation)
- **File**: `src/exchange/native_kraken_exchange.py`
- **Status**: ⚠️ Using custom implementation
- **Features**:
  - Manual nonce handling
  - Custom rate limiting
  - Direct HTTP requests

## New SDK Implementation

### KrakenSDKExchange
- **File**: `src/exchange/kraken_sdk_exchange.py`
- **Status**: ✅ Created
- **Features**:
  - Uses official `kraken.spot.SpotClient`
  - Built-in error handling
  - SDK-managed authentication
  - Compatible with existing bot interface

## Benefits of SDK Migration

### 1. **Reliability**
- Official Kraken support
- Tested and maintained by Kraken team
- Automatic API updates

### 2. **Simplified Code**
- No manual nonce generation
- Built-in request signing
- Automatic retries

### 3. **Better Error Handling**
- Specific exception types
- Detailed error messages
- Automatic rate limit handling

### 4. **Future-Proof**
- API changes handled by SDK
- New features automatically available
- Security updates

## Migration Steps

### Option 1: Gradual Migration (Recommended)
1. Keep existing implementation as fallback
2. Add configuration option to use SDK
3. Test thoroughly in development
4. Switch production after validation

### Option 2: Full Migration
1. Replace `NativeKrakenExchange` with `KrakenSDKExchange`
2. Update all imports
3. Test all functionality
4. Deploy

## Configuration

Add to `config.json`:
```json
{
  "exchange_implementation": "sdk",  // or "native"
  "kraken": {
    "use_official_sdk": true,
    "sdk_version": "3.2.2"
  }
}
```

## Code Changes

### Bot Initialization
```python
# In src/core/bot.py
if self.config.get('kraken', {}).get('use_official_sdk', False):
    from src.exchange.kraken_sdk_exchange import KrakenSDKExchange
    self.exchange = KrakenSDKExchange(
        api_key=api_key,
        api_secret=api_secret,
        tier=self.config.get('kraken_api_tier', 'starter')
    )
else:
    # Use existing implementation
    from src.exchange.native_kraken_exchange import NativeKrakenExchange
    self.exchange = NativeKrakenExchange(...)
```

## SDK Features to Leverage

### 1. **Async/Await Support**
- All methods are async-ready
- Better performance
- Non-blocking operations

### 2. **WebSocket Integration**
- Unified authentication
- Shared token management
- Consistent data formats

### 3. **Built-in Types**
- Type hints for all methods
- Better IDE support
- Reduced errors

### 4. **Advanced Features**
- Batch operations
- Order amendments
- Conditional orders
- Staking operations

## Testing Checklist

- [ ] Balance fetching
- [ ] Order placement (market/limit)
- [ ] Order cancellation
- [ ] Order status queries
- [ ] WebSocket authentication
- [ ] Rate limit handling
- [ ] Error scenarios
- [ ] Stop loss orders

## Performance Comparison

### Native Implementation
- Direct HTTP calls
- Manual optimization
- Custom caching

### SDK Implementation
- Optimized by Kraken
- Connection pooling
- Automatic caching

## Monitoring

After migration, monitor:
1. API response times
2. Error rates
3. Rate limit usage
4. WebSocket stability

## Rollback Plan

If issues arise:
1. Switch config to use native implementation
2. No code changes needed
3. Instant rollback

## Next Steps

1. **Immediate**: Test SDK implementation in development
2. **Short-term**: Add SDK option to config
3. **Medium-term**: Migrate production after validation
4. **Long-term**: Deprecate native implementation

## Additional SDK Features

Consider implementing:
- Futures trading support
- Earn/Staking integration
- Advanced order types
- Account history exports

## Resources

- [SDK Documentation](https://python-kraken-sdk.readthedocs.io/)
- [GitHub Repository](https://github.com/btschwertfeger/python-kraken-sdk)
- [Kraken API Docs](https://docs.kraken.com/rest/)

## Conclusion

The Kraken SDK provides a more robust, maintainable solution for API interactions. The migration can be done gradually with minimal risk, allowing thorough testing before full adoption.