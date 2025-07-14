# 🚫 CRITICAL MISTAKES TO AVOID - Updated June 24, 2025

## ⚡ **NEWLY IDENTIFIED: Precision Validation Errors**

### **❌ CRITICAL ERROR: Micro-Dust Order Execution**
```python
# CAUSES "volume minimum not met" errors
async def broken_sell_logic():
    amount = 0.00000001  # Too small for trading engine
    await exchange.create_order(amount=amount)  # FAILS!
```

### **✅ CORRECT: Precision Validation Before Orders**
```python
async def precision_validated_sell():
    if amount < 0.00000010:  # Prevent precision errors
        logger.warning(f"[PRECISION_SKIP] Amount {amount:.8f} too small")
        return False
    
    # Safe to execute - meets trading engine precision
    return await exchange.create_order(amount=round(amount, 8))
```

## 🔧 **KRAKEN SELL RULE CLARIFICATION**

### **❌ WRONG: Applying BUY Minimums to SELL Orders**
```python
# BLOCKS legitimate profit-taking
if sell_amount < KRAKEN_BUY_MINIMUMS[symbol]:
    return False  # Wrong! Kraken has NO sell minimums
```

### **✅ CORRECT: Kraken Sell Rules**
```python
# Kraken Rule: Can sell ANY amount you own (no minimums)
if amount > 0:
    return True  # Any owned amount can be sold
    
# Only validate precision for trading engine compatibility
if amount >= 0.00000010:
    return "SAFE_TO_EXECUTE"
else:
    return "PRECISION_TOO_SMALL"
```

## 📊 **API TIMEOUT HANDLING PATTERNS**

### **❌ DANGEROUS: No Timeout Protection**
```python
# Causes infinite hanging and circuit breakers
while True:
    balance = await exchange.fetch_balance()  # Can hang forever
```

### **✅ SAFE: Timeout with Fallback**
```python
async def safe_balance_fetch():
    try:
        return await asyncio.wait_for(
            exchange.fetch_balance(), 
            timeout=10.0
        )
    except asyncio.TimeoutError:
        logger.warning("[BALANCE] Fetch timeout - using cached data")
        return cached_balance
```

## 🎯 **UPDATED CRITICAL CHECKLIST**

Before ANY production deployment:

- [ ] **Precision validation:** Amount >= 0.00000010 for orders
- [ ] **Kraken rule compliance:** No sell minimums enforced  
- [ ] **Timeout protection:** All API calls have timeout limits
- [ ] **Circuit breaker awareness:** Systems recover from failures
- [ ] **Balance fetch fallbacks:** Cached data when API unavailable
- [ ] **Honest error reporting:** No fake success messages
- [ ] **Memory system updates:** Changes logged in context servers

## 🔍 **DIAGNOSTIC LOG PATTERNS**

### **✅ GOOD: Precision Fix Working**
```
[PRECISION_SKIP] BTC/USDT: Amount 0.00000000 too small for execution
[SELLABLE_POSITION] SOL/USDT: 0.00034819 ($0.0502) - Ready to sell
[FAST_PROFIT_READY] SOL: 0.00034819 ($0.0502) ready for immediate sale
```

### **❌ BAD: System Under Stress**
```
[CIRCUIT_BREAKER] BTC/USDT: Activated after 5 failures
[RETRY] ETH/USDT: Timeout on attempt 3, retrying in 4s
[BALANCE] Fetch timeout - using cached data
```

## 💡 **KEY LESSON: Precision vs Minimums**

**Critical Understanding:** 
- Kraken's "volume minimum not met" = Trading engine precision issue
- Solution: Validate amount >= 0.00000010, NOT enforce sell minimums
- Root cause: 0.00000001 amounts cause precision rounding errors

*Updated after successful precision validation deployment - June 24, 2025*