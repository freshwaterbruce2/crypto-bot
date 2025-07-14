# 🚫 MISTAKES TO AVOID - Quick Reference Guide# 🚫 MISTAKES TO AVOID - Critical Learning from Real Bugs

## 🚨 **CRITICAL SYSTEM-WIDE BUG: Sell Minimums Misapplication (June 24, 2025)**

**⚠️ THE DEADLY MISTAKE:**
```python
# WRONG - Applying BUY minimums to SELL decisions
if sell_amount < BUY_MINIMUM:
    skip_sale()  # BLOCKS ENTIRE FAST PROFITS STRATEGY!
```

**✅ THE CORRECT APPROACH:**
```python
# CORRECT - Kraken allows selling ANY amount you own
if sell_amount > 0:
    execute_sale()  # ENABLES FAST PROFITS!
```

### **What Happened:**
- **4 FILES** had the same bug: applying BUY order minimums to SELL decisions
- **IMPACT:** Prevented ALL fast small profit sales for weeks
- **SYMPTOM:** SOL 0.00034819 waiting for 20x growth instead of immediate sale
- **ROOT CAUSE:** Misunderstanding that exchange minimums are directional

### **Key Learning:**
**Exchange rules are directional! BUY ≠ SELL**
- **Kraken BUY orders:** Require minimums (prevent spam)  
- **Kraken SELL orders:** NO minimums (you own it, you can sell it)

### **Files That Had This Bug:**
- `autonomous_sell_engine_integration.py`
- `adaptive_selling_assistant.py` 
- `capital_reallocation_manager.py`
- `infinite_autonomous_loop.py`

---

## 🔥 PRODUCTION CODE KILLERS

### **❌ NEVER: Use Placeholder Values in Live Trading**
```python
# DEADLY MISTAKES
entry_price = 1.0              # Fake entry price
balance = 100.0               # Hardcoded balance  
min_order = 0.001             # Guessed minimum
```

### **✅ ALWAYS: Use Real Data Sources**
```python
# SAFE PATTERNS
entry_price = await get_actual_entry_price(order_id)
balance = await exchange.fetch_balance()['USDT']['free']
min_order = KRAKEN_MINIMUMS[symbol]  # From official docs
```

---

## 💰 EXCHANGE INTEGRATION TRAPS

### **❌ NEVER: Guess Exchange Requirements**
```python
# WRONG - Made up minimums cause order rejections
MIN_BTC = 0.00001    # Too small - Kraken rejects
MIN_ETH = 0.0005     # Too small - Kraken rejects
```

### **✅ ALWAYS: Use Official Documentation**
```python
# CORRECT - From Kraken official docs
KRAKEN_MINIMUMS = {
    'BTC/USDT': 0.0001,    # Official minimum
    'ETH/USDT': 0.01,      # Official minimum
    'ADA/USDT': 5.0,       # $1 USD equivalent
}
```

---

## 📊 LOGGING & SUCCESS REPORTING

### **❌ NEVER: Fake Success Reports**
```python
# LIES THAT HIDE PROBLEMS
if amount_too_small:
    logger.info("SUCCESS: Order executed!")  # LIE
    return True  # FAKE SUCCESS
```

### **✅ ALWAYS: Honest Status Reporting**
```python
# TRUTH THAT ENABLES DEBUGGING
if amount_too_small:
    logger.warning(f"SKIPPED: Amount {amount} below minimum")
    return False  # HONEST FAILURE
```

---

## 🎯 QUICK VALIDATION CHECKLIST

Before deploying ANY code change:

- [ ] **No hardcoded values** - All constants from config/environment
- [ ] **Exchange requirements verified** - Official documentation checked
- [ ] **Honest error reporting** - No fake success messages
- [ ] **Fresh data for trades** - Force refresh for critical operations
- [ ] **Connection validation** - Ensure systems ready before use
- [ ] **Comprehensive error handling** - Try/catch around all API calls

---

## 🚨 RED FLAGS IN LOGS

```
❌ "[SELL_SUCCESS]: Profit target reached: 10076750.00%"
❌ "[DUST_SKIP] followed by [SELL_SUCCESS]"  
❌ "INSUFFICIENT_FUNDS" when balance shows $196.99
❌ Any percentage over 100% profit on micro trades
```

---

*Keep this guide open while coding. When in doubt, choose the safer approach.*