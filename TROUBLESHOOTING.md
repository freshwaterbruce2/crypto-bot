# TROUBLESHOOTING GUIDE - 2025 Production Fixes

**Comprehensive guide documenting all fixes applied for 2025 production deployment**

## Overview of Fixed Issues

This document provides detailed troubleshooting information for all major issues that were identified and resolved during the 2025 production preparation. All fixes have been tested and are currently deployed.

---

## 1. FORMAT STRING ERRORS (CRITICAL FIX)

### Problem Description
**Error:** `unsupported format string passed to dict.__format__`
**Impact:** Prevented trades from executing, caused bot crashes during order execution
**Files Affected:** `src/trading/enhanced_trade_executor_with_assistants.py`

### Root Cause
The bot was attempting to format dictionary objects as floats in f-string expressions, particularly when handling balance and price data from the Kraken API.

### Solution Applied
**Fixed in:** `enhanced_trade_executor_with_assistants.py:22-31`

```python
def _ensure_float(self, value, default=0.0):
    """Ensure value is a float for safe formatting"""
    if value is None:
        return default
    if isinstance(value, dict):
        return float(value.get('free', value.get('total', default)))
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
```

### Verification Steps
```bash
# Test trade execution without format errors
python3 -c "
from src.trading.enhanced_trade_executor_with_assistants import TradeExecutor
executor = TradeExecutor({})
test_value = {'free': 10.5}
result = executor._ensure_float(test_value)
assert result == 10.5
print('Format string fix verified')
"
```

### Prevention
- Always use `_ensure_float()` when formatting API response data
- Never directly format dict objects in f-strings
- Validate data types before string operations

---

## 2. INVALID NONCE ERRORS (CRITICAL FIX)

### Problem Description
**Error:** `EAPI:Invalid nonce`
**Impact:** All private API calls failing, no trading possible
**Files Affected:** `src/exchange/kraken_sdk_exchange.py`

### Root Cause
Nonce values were being reused or generated incorrectly, causing Kraken API to reject requests as potentially replayed attacks.

### Solution Applied
**Fixed in:** `kraken_sdk_exchange.py:576-578, 589-592`

```python
# Get fresh nonce for every request
nonce = self.nonce_manager.get_nonce("rest_api")
params["nonce"] = str(nonce)
```

### Key Implementation Details
- Fresh nonce generated for EVERY private API call
- Nonce manager ensures monotonic increase
- Separate nonce tracking for different API contexts

### Verification Steps
```bash
# Test nonce generation
python3 -c "
from src.utils.kraken_nonce_manager import KrakenNonceManager
nm = KrakenNonceManager()
nonce1 = nm.get_nonce('test')
nonce2 = nm.get_nonce('test')
assert nonce2 > nonce1
print('Nonce generation verified')
"
```

### Prevention
- Never reuse nonce values
- Always use `nonce_manager.get_nonce()` for private calls
- Monitor nonce sequence for any gaps or reversals

---

## 3. TYPE COMPARISON ERRORS (CRITICAL FIX)

### Problem Description
**Error:** `'>' not supported between instances of 'dict' and 'int'`
**Impact:** Position sizing and balance comparisons failing
**Files Affected:** Multiple trading modules

### Root Cause
The bot uses Decimal precision for all calculations, but some comparisons were mixing dict/float/int types.

### Solution Applied
**Fixed throughout codebase using:**

```python
from src.utils.decimal_precision_fix import safe_decimal, safe_float
# Convert all values to Decimal before comparison
price_decimal = safe_decimal(current_price)
balance_decimal = safe_decimal(asset_balance)
if balance_decimal > minimum_decimal:
    # Safe comparison
```

### Verification Steps
```bash
# Test decimal conversion
python3 -c "
from src.utils.decimal_precision_fix import safe_decimal
test_dict = {'free': '10.5'}
result = safe_decimal(test_dict)
assert str(result) == '10.5'
print('Decimal conversion verified')
"
```

### Prevention
- Always use `safe_decimal()` for financial calculations
- Never mix data types in comparisons
- Use Decimal type for all monetary values

---

## 4. WEBSOCKET CONNECTION ISSUES

### Problem Description
**Error:** WebSocket connections failing, display issues in WSL/PowerShell
**Impact:** No real-time price data, fallback to slower REST API
**Files Affected:** `src/exchange/websocket_manager_v2.py`

### Root Cause
- WebSocket v1 deprecation by Kraken
- Terminal encoding issues with emoji characters
- Connection stability problems

### Solution Applied
**Multi-source hybrid approach:**

1. **WebSocket v2 Implementation**
   ```python
   self.PUBLIC_WS_URL = "wss://ws.kraken.com/v2"
   ```

2. **Fallback Chain:**
   - Primary: WebSocket v2
   - Secondary: CoinGecko API
   - Tertiary: Kraken REST API

3. **Emoji Removal:**
   - All emoji characters removed for terminal compatibility
   - ASCII-only status indicators

### Verification Steps
```bash
# Test WebSocket connection
python3 -c "
import asyncio
from src.exchange.websocket_manager_v2 import WebSocketManagerV2
async def test():
    ws = WebSocketManagerV2()
    await ws.connect()
    print('WebSocket v2 connection verified')
asyncio.run(test())
"
```

### Prevention
- Monitor WebSocket connection status
- Ensure fallback data sources are configured
- Use ASCII-only characters in terminal output

---

## 5. RATE LIMITING AND API TIER MANAGEMENT

### Problem Description
**Error:** API rate limit exceeded, temporary bans
**Impact:** Trading halted during high-activity periods
**Files Affected:** `src/exchange/kraken_sdk_exchange.py`

### Root Cause
Insufficient rate limit tracking for different API tiers (Starter: 20, Intermediate: 60, Pro: 180 points)

### Solution Applied
**Enhanced rate limiting with exponential backoff:**

```python
# Tier-specific limits
if tier == "pro":
    self.max_api_counter = 180
    self.decay_rate = 3.75
elif tier == "intermediate":
    self.max_api_counter = 60
    self.decay_rate = 1.0
else:  # starter
    self.max_api_counter = 20
    self.decay_rate = 0.33

# Exponential backoff on rate limit hit
backoff_minutes = getattr(self, 'backoff_duration', 30) * (2 ** getattr(self, 'rate_limit_count', 0))
```

### Verification Steps
```bash
# Check rate limit status
python3 -c "
import asyncio
from src.exchange.kraken_sdk_exchange import KrakenSDKExchange
async def test():
    exchange = KrakenSDKExchange('', '', 'starter')
    status = await exchange.get_rate_limit_status()
    print(f'Rate limit status: {status}')
asyncio.run(test())
"
```

### Prevention
- Monitor API counter continuously
- Implement circuit breakers for protection
- Use appropriate API tier for trading volume

---

## 6. BALANCE AND POSITION TRACKING

### Problem Description
**Error:** Inconsistent balance reporting, position tracking mismatches
**Impact:** Incorrect available capital calculations
**Files Affected:** `src/trading/unified_balance_manager.py`

### Root Cause
- Multiple balance sources not synchronized
- Cache invalidation issues
- Asset name normalization problems

### Solution Applied
**Unified balance manager with smart caching:**

```python
# Real-time balance tracking
self.cache_duration = 5  # 5s cache for immediate accuracy
self.min_refresh_interval = 2  # 2s refresh for real-time trading
self.cache_invalidation_triggers = [
    'trade_complete', 'manual_refresh', 'position_change', 
    'sell_signal', 'balance_mismatch'
]
```

### Verification Steps
```bash
# Test balance synchronization
python3 -c "
import asyncio
from src.trading.unified_balance_manager import UnifiedBalanceManager
async def test():
    manager = UnifiedBalanceManager(None)
    await manager.initialize()
    print('Balance manager verified')
asyncio.run(test())
"
```

### Prevention
- Use unified balance manager for all balance queries
- Monitor cache invalidation triggers
- Validate balance consistency across sources

---

## 7. LOW-PRICED PAIR CONFIGURATION

### Problem Description
**Issue:** Bot trading expensive pairs (BTC/ETH) with small balance
**Impact:** Inefficient capital utilization, high minimum order requirements
**Files Affected:** `config.json`, trading strategies

### Root Cause
Default configuration included high-priced pairs that require large minimum orders.

### Solution Applied
**Low-priced pair prioritization:**

```json
{
  "prioritize_pairs": ["SHIB/USDT", "DOGE/USDT", "ADA/USDT", "ALGO/USDT", "MATIC/USDT", "XRP/USDT"],
  "position_size_usdt": 5.0,
  "avoid_expensive_pairs": ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
}
```

### Verification Steps
```bash
# Verify pair configuration
python3 -c "
import json
with open('config.json') as f:
    config = json.load(f)
assert 'SHIB/USDT' in config.get('prioritize_pairs', [])
print('Low-priced pair configuration verified')
"
```

### Prevention
- Regularly review pair profitability
- Monitor minimum order requirements
- Adjust pair selection based on account balance

---

## EMERGENCY PROCEDURES

### Bot Not Starting
1. **Check API credentials:**
   ```bash
   # Verify .env file
   cat .env | grep -E "KRAKEN_API_KEY|KRAKEN_API_SECRET"
   ```

2. **Test API connection:**
   ```bash
   python3 -c "
   import asyncio
   from src.exchange.kraken_sdk_exchange import KrakenSDKExchange
   async def test():
       exchange = KrakenSDKExchange('your_key', 'your_secret')
       connected = await exchange.connect()
       print(f'Connection: {connected}')
   asyncio.run(test())
   "
   ```

### No Trades Executing
1. **Check balance:**
   ```bash
   python3 check_balance.py
   ```

2. **Verify rate limits:**
   ```bash
   python3 -c "
   # Check if in rate limit backoff
   from src.exchange.kraken_sdk_exchange import KrakenSDKExchange
   # Check rate_limit_backoff status
   "
   ```

### Format String Errors Recurring
1. **Verify helper function usage:**
   ```bash
   grep -r "_ensure_float" src/
   ```

2. **Check for direct dict formatting:**
   ```bash
   grep -r "f.*{.*dict" src/
   ```

### Memory Usage Issues
1. **Monitor memory:**
   ```bash
   python3 monitor_bot.py --memory-only
   ```

2. **Clear cache:**
   ```bash
   python3 -c "
   from src.trading.unified_balance_manager import UnifiedBalanceManager
   # Clear balance cache
   "
   ```

---

## DIAGNOSTIC COMMANDS

### Quick Health Check
```bash
# Run comprehensive health check
python3 -c "
import asyncio
from src.core.bot import KrakenTradingBot

async def health_check():
    bot = KrakenTradingBot()
    await bot.initialize()
    print('✅ Bot initialization successful')
    
    # Test API connection
    connected = await bot.exchange.connect()
    print(f'✅ API Connection: {connected}')
    
    # Test balance fetch
    balance = await bot.exchange.fetch_balance()
    print(f'✅ Balance fetch: {len(balance)} assets')
    
    # Check rate limits
    status = await bot.exchange.get_rate_limit_status()
    print(f'✅ Rate limit: {status[\"percentage_used\"]:.1f}% used')

asyncio.run(health_check())
"
```

### Log Analysis
```bash
# Check for recent errors
tail -100 kraken_infinity_bot.log | grep -i error

# Monitor real-time logs
tail -f kraken_infinity_bot.log

# Check for rate limit issues
grep -i "rate limit" kraken_infinity_bot.log | tail -10
```

### Performance Monitoring
```bash
# Check trading performance
python3 -c "
from src.trading.portfolio_tracker import PortfolioTracker
tracker = PortfolioTracker()
stats = tracker.get_performance_stats()
print(f'Total trades: {stats.get(\"total_trades\", 0)}')
print(f'Success rate: {stats.get(\"success_rate\", 0):.1f}%')
"
```

---

## MAINTENANCE SCHEDULE

### Daily Checks
- Monitor log files for errors
- Verify trading activity
- Check rate limit usage
- Review balance changes

### Weekly Reviews
- Analyze trading performance
- Update pair configuration if needed
- Review error patterns
- Test emergency procedures

### Monthly Tasks
- Rotate API keys
- Update documentation
- Performance optimization
- Backup configuration

---

## GETTING HELP

### Log Locations
- Main log: `kraken_infinity_bot.log`
- Launch log: `bot_output.log`
- Historical logs: `D:/trading_data/logs/` (Windows)

### Key Configuration Files
- Main config: `config.json`
- Environment: `.env`
- Bot memory: `CLAUDE.md`

### Support Resources
- Technical issues: Check logs first
- Rate limit problems: Wait for backoff period
- API errors: Verify credentials and permissions
- Performance issues: Review configuration

---

**Remember: All fixes documented here have been tested and are currently deployed in production. Always check logs first when troubleshooting new issues.**