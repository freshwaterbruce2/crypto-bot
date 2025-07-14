# QUICK FIXES - IMMEDIATE IMPLEMENTATION

## 1. UPDATE ALL MINIMUM ORDER SIZES

### Step 1: Update imports in all files
Add this import to the top of each file that handles order sizes:
```python
from src.config.constants import MINIMUM_ORDER_SIZE_TIER1, calculate_minimum_cost
```

### Step 2: Replace hardcoded values

**File: src/core/bot.py (Line 94)**
```python
# OLD:
self.position_size_usd = max(2.0, base_position_size)

# NEW:
self.position_size_usd = min(base_position_size, tier_1_limit)
```

**File: src/trading/unified_risk_manager.py (Line 353)**
```python
# OLD:
min_order_size = self.config.get('min_order_size_usdt', 5.0)

# NEW:
from src.config.constants import MINIMUM_ORDER_SIZE_TIER1
min_order_size = self.config.get('min_order_size_usdt', MINIMUM_ORDER_SIZE_TIER1)
```

**File: src/trading/opportunity_execution_bridge.py (Line 120)**
```python
# OLD:
portfolio_min_cost = min(2.0, tier_1_limit)

# NEW:
from src.config.constants import MINIMUM_ORDER_SIZE_TIER1
portfolio_min_cost = MINIMUM_ORDER_SIZE_TIER1
```

## 2. INTEGRATE UNIFIED SELL COORDINATOR

### Step 1: Update opportunity_scanner.py
```python
# Add import
from src.trading.unified_sell_coordinator import UnifiedSellCoordinator

# In __init__:
self.sell_coordinator = UnifiedSellCoordinator(config)

# Replace sell signal generation with:
if holds_position:
    position_data = {
        'symbol': symbol,
        'entry_price': entry_price,
        'current_price': current_price,
        'pnl_percent': (current_price - entry_price) / entry_price,
        'entry_time': position_entry_time,
        'quantity': position_quantity
    }
    sell_decision = await self.sell_coordinator.evaluate_position(position_data)
    
    if sell_decision.should_sell:
        opportunity = {
            'symbol': symbol,
            'side': 'sell',
            'action': 'sell',
            'confidence': sell_decision.confidence,
            'reason': sell_decision.reason.value,
            'metadata': sell_decision.metadata
        }
```

### Step 2: Disable Autonomous Sell Engine
In `src/trading/functional_strategy_manager.py`:
```python
# Comment out or remove:
# from ..strategies.autonomous_sell_engine import AutonomousSellEngine

# In create_strategies method, skip sell engine creation:
# self.sell_engines[symbol] = None  # Unified coordinator handles sells
```

## 3. ASYNC COMPLIANCE FIXES

### Fix blocking sleep calls:
Search and replace in all files:
```python
# OLD:
time.sleep(5)

# NEW:
await asyncio.sleep(5)
```

### Fix synchronous file I/O:
```python
# OLD:
with open(file_path, 'r') as f:
    data = f.read()

# NEW:
import aiofiles
async with aiofiles.open(file_path, 'r') as f:
    data = await f.read()
```

## 4. IMMEDIATE CONFIG.JSON UPDATES

Update `config.json`:
```json
{
    "position_size_usdt": 2.0,
    "tier_1_trade_limit": 2.0,
    "min_order_size_usdt": 1.0,
    "kraken_api_tier": "starter",
    "emergency_min_trade_value": 2.0,
    "minimum_balance_threshold": 2.0
}
```

## 5. CRITICAL BOT.PY FIXES

Add to bot.py after line 88:
```python
# Import global constants
from src.config.constants import MINIMUM_ORDER_SIZE_TIER1, TRADING_CONSTANTS

# Validate position size
if self.position_size_usd < MINIMUM_ORDER_SIZE_TIER1:
    self.logger.warning(f"Position size ${self.position_size_usd} below minimum ${MINIMUM_ORDER_SIZE_TIER1}, adjusting...")
    self.position_size_usd = MINIMUM_ORDER_SIZE_TIER1
```

## 6. TEST COMMANDS

After implementing fixes, test with:
```bash
# Test initialization
python -c "from src.config.constants import MINIMUM_ORDER_SIZE_TIER1; print(f'Min order: ${MINIMUM_ORDER_SIZE_TIER1}')"

# Test sell coordinator
python -c "from src.trading.unified_sell_coordinator import UnifiedSellCoordinator; print('Sell coordinator imported successfully')"

# Test bot startup (dry run)
python scripts/live_launch.py --test-mode
```

## 7. VALIDATION CHECKLIST

Before running live:
- [ ] All files import from constants.py
- [ ] No hardcoded $5, $2.50 values remain
- [ ] Unified sell coordinator integrated
- [ ] Autonomous sell engine disabled
- [ ] Config.json updated
- [ ] Test imports work
- [ ] Bot initializes without errors

## 8. EMERGENCY ROLLBACK

If issues occur:
1. Restore original config.json
2. Comment out unified sell coordinator
3. Re-enable autonomous sell engine
4. Remove constants imports

Keep original files backed up before making changes!