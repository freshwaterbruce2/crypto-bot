# Balance Manager Conflict Resolution

## Problem
There are two `EnhancedBalanceManager` classes with the same name:
1. `src/trading/enhanced_balance_manager.py` - The correct one used by the bot
2. `src/utils/enhanced_balance_manager.py` - Old version with `get_available_balance` method

This is causing:
- Import confusion
- Method not found errors
- Unpredictable behavior

## Root Cause of the Error
The error `'EnhancedBalanceManager' object has no attribute 'get_available_balance'` happens because:
1. The bot correctly uses `src/trading/enhanced_balance_manager.py`
2. But something (likely portfolio_intelligence_system.py) expects the utils version
3. The trading version doesn't have `get_available_balance`, only `get_balance_for_asset`

## Solution

### Option 1: Rename the Utils Version (Recommended)
```python
# In src/utils/enhanced_balance_manager.py
class UtilsEnhancedBalanceManager:  # Renamed to avoid conflict
```

### Option 2: Remove the Utils Version
If it's not being used elsewhere, delete `src/utils/enhanced_balance_manager.py`

### Option 3: Add Compatibility Method
Add this to `src/trading/enhanced_balance_manager.py`:
```python
async def get_available_balance(self, currency: str = 'USDT', force_refresh: bool = False) -> float:
    """Compatibility wrapper for old method name"""
    return await self.get_balance_for_asset(currency, force_refresh)
```

## Immediate Fix
Since the bot is already running and we don't want to break it, Option 3 is the safest immediate fix.

## Files That May Need Updates
- `src/portfolio_intelligence_system.py` - Uses `get_available_balance`
- `src/assistants/sell_logic_assistant.py` - May use old balance manager
- `src/assistants/adaptive_selling_assistant.py` - May use old balance manager

## Testing
After implementing the fix:
1. Check that balance detection works
2. Verify no more `get_available_balance` errors
3. Ensure trades can execute