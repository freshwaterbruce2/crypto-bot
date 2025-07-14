#!/usr/bin/env python3
"""
Fix for Enhanced Balance Manager API Call Tracking
Ensures accurate tracking and reporting of API calls in portfolio valuation
"""

import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def apply_api_tracking_fix():
    """Apply fix to enhanced_balance_manager.py for accurate API call tracking"""
    
    file_path = "C:/projects050625/projects/active/tool-crypto-trading-bot-2025/src/enhanced_balance_manager.py"
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Update the logging to show actual API budget and usage more clearly
    old_log = '''logger.info(
            f"[EBM_USDT] Portfolio: ${total_usd_value:.2f} "
            f"(used {api_calls_made}/{max_api_calls} API calls)"
        )'''
    
    new_log = '''# Show detailed API usage for transparency
        rate_status = self.rate_counter.get_status()
        logger.info(
            f"[EBM_USDT] Portfolio: ${total_usd_value:.2f} | "
            f"API calls: {api_calls_made} used, {max_api_calls} budgeted | "
            f"Rate counter: {rate_status['current_count']:.1f}/{rate_status['max_counter']} | "
            f"Available: {rate_status['available_calls']}"
        )'''
    
    # Fix 2: Ensure API calls are properly tracked when fetching tickers
    old_ticker_fetch = '''if api_calls_made < max_api_calls and await self._check_rate_limit(1):
                    try:
                        ticker_data = await self.exchange.fetch_ticker(ticker_symbol)
                        current_price = float(ticker_data.get('last', 0) or ticker_data.get('close', 0))
                        
                        if current_price > 0:
                            # Update cache
                            self.ticker_cache.update_ticker(ticker_symbol, ticker_data)
                            
                            value_in_usd = asset_amount * current_price
                            api_calls_made += 1'''
    
    new_ticker_fetch = '''if api_calls_made < max_api_calls and await self._check_rate_limit(1):
                    try:
                        # Track API call attempt
                        logger.debug(f"[EBM_API] Fetching ticker {ticker_symbol} (call {api_calls_made + 1}/{max_api_calls})")
                        
                        ticker_data = await self.exchange.fetch_ticker(ticker_symbol)
                        current_price = float(ticker_data.get('last', 0) or ticker_data.get('close', 0))
                        
                        if current_price > 0:
                            # Update cache
                            self.ticker_cache.update_ticker(ticker_symbol, ticker_data)
                            
                            value_in_usd = asset_amount * current_price
                            api_calls_made += 1
                            
                            # Successful API call - update rate counter tracking
                            self.rate_counter.reset_errors()'''
    
    # Fix 3: Add debug logging for cache hits
    old_cache_check = '''cached_price = self.ticker_cache.get_price(ticker_symbol, is_priority)
                if cached_price and cached_price > 0:
                    value_in_usd = asset_amount * cached_price
                    logger.debug(
                        f"[EBM_USDT] {currency_code}: {asset_amount:.4f}*${cached_price:.2f}"
                        f"(cached)=${value_in_usd:.2f}"
                    )
                    break'''
    
    new_cache_check = '''cached_price = self.ticker_cache.get_price(ticker_symbol, is_priority)
                if cached_price and cached_price > 0:
                    value_in_usd = asset_amount * cached_price
                    logger.debug(
                        f"[EBM_CACHE] {currency_code}: {asset_amount:.4f}*${cached_price:.2f}"
                        f"(cached)=${value_in_usd:.2f} - saved 1 API call"
                    )
                    break'''
    
    # Apply fixes
    content = content.replace(old_log, new_log)
    content = content.replace(old_ticker_fetch, new_ticker_fetch)
    content = content.replace(old_cache_check, new_cache_check)
    
    # Write back the fixed content
    with open(file_path, 'w') as f:
        f.write(content)
    
    logger.info("[FIX] Applied API tracking improvements to enhanced_balance_manager.py")
    
    return {
        'status': 'success',
        'fixes_applied': [
            'Enhanced API call logging with rate counter details',
            'Added debug logging for ticker API calls',
            'Added cache hit logging to show saved API calls',
            'Improved rate counter error reset on successful calls'
        ]
    }


async def verify_api_tracking():
    """Verify that API tracking is working correctly"""
    try:
        # Import the enhanced balance manager
        import sys
        sys.path.append("C:/projects050625/projects/active/tool-crypto-trading-bot-2025/src")
        from enhanced_balance_manager import get_enhanced_balance_manager
        
        ebm = get_enhanced_balance_manager()
        if ebm:
            # Get current rate counter status
            rate_status = ebm.rate_counter.get_status()
            cache_info = ebm.get_cache_info()
            
            logger.info("[VERIFY] Current API tracking status:")
            logger.info(f"  - Rate counter: {rate_status['current_count']:.1f}/{rate_status['max_counter']}")
            logger.info(f"  - Available calls: {rate_status['available_calls']}")
            logger.info(f"  - Tier: {rate_status['tier']}")
            logger.info(f"  - Cache status: {cache_info['ticker_cache']['cached_pairs']} pairs cached")
            
            return {
                'rate_counter': rate_status,
                'cache_info': cache_info,
                'tracking_active': True
            }
        else:
            logger.warning("[VERIFY] Balance manager not initialized")
            return {'tracking_active': False}
            
    except Exception as e:
        logger.error(f"[VERIFY] Error checking API tracking: {e}")
        return {'error': str(e)}


if __name__ == "__main__":
    # Apply the fix
    asyncio.run(apply_api_tracking_fix())
    
    # Verify the fix
    asyncio.run(verify_api_tracking())
