# Smart Minimum Order Handling System

## Overview
The Smart Minimum Order Handling System provides intelligent minimum order management specifically optimized for the 12 USDT pairs in our portfolio. This system enhances the existing minimum learning capabilities with tier-based classification and dynamic updates.

## Portfolio Pairs (14 total)
### Tier-1 Pairs (8 pairs - High liquidity, stable)
- ADA/USDT, ALGO/USDT, ATOM/USDT, AVAX/USDT
- DOT/USDT, LINK/USDT, MATIC/USDT, SOL/USDT
- **Minimum cost**: $5.00
- **Position size**: 2% of available balance

### Meme Coins (5 pairs - Higher volatility)
- AI16Z/USDT, BERA/USDT, DOGE/USDT, FARTCOIN/USDT, SHIB/USDT
- **Minimum cost**: $10.00 (higher due to volatility)
- **Position size**: 1% of available balance (lower risk)

### Mid-Tier (1 pair)
- MANA/USDT
- **Minimum cost**: $7.50
- **Position size**: 1.5% of available balance

## Key Features

### 1. Smart Minimum Manager (`src/trading/smart_minimum_manager.py`)
- Tier-based classification for optimization
- Dynamic minimum updates from multiple sources
- Integration with existing learning systems
- Smart position sizing based on tier and balance
- Caching with 5-minute duration for performance

### 2. Integration Layer (`src/trading/minimum_manager_integration.py`)
- Seamless integration with existing trading systems
- Trade volume calculation with tier awareness
- Order validation before execution
- Error handling with learning capabilities

### 3. Enhanced Learning System
- Bulk learning capability for portfolio initialization
- Portfolio-specific status tracking
- Integration with existing MinimumDiscoveryLearning

## Implementation Details

### Initialization
All 14 portfolio pairs have been pre-initialized with conservative minimum requirements:
```bash
python3 scripts/initialize_portfolio_minimums.py
```

### Bot Integration
The system is automatically initialized in `bot.py` as part of Phase 4:
```python
# 4.8: Smart Minimum Manager for portfolio pairs
self.minimum_integration = get_minimum_integration(
    exchange=self.exchange,
    balance_manager=self.balance_manager
)
await self.minimum_integration.initialize()
```

### Trade Execution Integration
The enhanced trade executor now:
- Validates portfolio pairs using smart minimums
- Uses tier-based position sizing
- Learns from minimum errors specifically for portfolio pairs
- Falls back to traditional learning for non-portfolio pairs

## Configuration

### Tier Minimum Costs
```python
TIER_MIN_COSTS = {
    TradingTier.TIER_1: 5.0,    # $5 minimum for stable pairs
    TradingTier.MEME: 10.0,     # $10 minimum for volatile meme coins
    TradingTier.MID_TIER: 7.5   # $7.5 for mid-tier pairs
}
```

### Position Sizing
```python
TIER_POSITION_SIZES = {
    TradingTier.TIER_1: 0.02,    # 2% for stable pairs
    TradingTier.MEME: 0.01,      # 1% for meme coins (higher risk)
    TradingTier.MID_TIER: 0.015  # 1.5% for mid-tier
}
```

## Usage Examples

### Get Optimal Volume for Portfolio Pair
```python
from src.trading.minimum_manager_integration import get_portfolio_volume

volume, reason = await get_portfolio_volume("SOL/USDT", balance=1000.0, price=100.0)
# Returns: (0.2, "tier_1 position size: 2% of balance")
```

### Validate Order Before Execution
```python
from src.trading.minimum_manager_integration import validate_portfolio_order

is_valid, message = await validate_portfolio_order("SHIB/USDT", 60000.0, 0.00015)
# Returns: (True, "Order size valid")
```

### Check Tradeable Pairs
```python
tradeable = integration.get_tradeable_pairs(available_balance=100.0)
# Returns list of pairs with sufficient balance for their tier minimums
```

## Benefits

1. **Optimized for Portfolio**: Focuses specifically on the 12 pairs we trade
2. **Tier-Based Risk Management**: Different position sizes based on volatility
3. **Dynamic Learning**: Continuously improves minimum requirements
4. **Seamless Integration**: Works with existing systems without disruption
5. **Performance Optimized**: Caching and bulk operations for efficiency

## Monitoring

### Statistics
```python
stats = smart_minimum_manager.get_statistics()
# Returns cache hits/misses, learning events, tier distribution
```

### Portfolio Summary
```python
summary = await integration.get_minimum_summary()
# Returns complete overview of all portfolio pair minimums
```

## Files Created/Modified

### New Files
- `src/trading/smart_minimum_manager.py` - Core smart minimum management
- `src/trading/minimum_manager_integration.py` - Integration layer
- `tests/test_smart_minimum_manager.py` - Comprehensive test suite
- `scripts/initialize_portfolio_minimums.py` - Initialization script
- `docs/SMART_MINIMUM_SYSTEM.md` - This documentation

### Modified Files
- `src/utils/minimum_provider.py` - Added portfolio pairs to static table
- `src/autonomous_minimum_learning/minimum_discovery_learning.py` - Added bulk learning
- `src/core/bot.py` - Added smart minimum manager initialization
- `src/trading/enhanced_trade_executor_with_assistants.py` - Integrated validation
- `trading_data/minimum_learning/kraken_learned_minimums.json` - Portfolio minimums

## Next Steps

The system is now ready for production use. The bot will:
1. Use tier-appropriate minimum costs for all portfolio pairs
2. Apply intelligent position sizing based on pair classification
3. Learn and adapt from any minimum requirement changes
4. Provide better capital utilization through optimized order sizes

All 14 portfolio pairs are initialized and ready for micro-profit snowball trading!