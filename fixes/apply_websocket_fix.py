"""
Apply WebSocket Ticker Fix for Kraken V2
This script patches the websocket_manager.py to fix ticker data parsing
"""

import os
import sys
import re

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def apply_websocket_fix():
    """Apply the WebSocket ticker parsing fix"""
    
    websocket_file = os.path.join(project_root, 'src', 'websocket_manager.py')
    
    print("🔧 Applying WebSocket ticker parsing fix...")
    
    # Read the current file
    with open(websocket_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if fix already applied
    if "_handle_ticker_update_FIXED" in content:
        print("✅ Fix already applied!")
        return
    
    # Find the _handle_ticker_update method
    ticker_pattern = r'async def _handle_ticker_update\(self,.*?\n(?=\s{0,4}async def|\s{0,4}def|\s{0,4}class|\Z)'
    
    # Replace with our fixed version
    fixed_ticker_method = '''async def _handle_ticker_update(self, data: Dict[str, Any]) -> None:
        """Handle ticker data updates with Kraken V2 format support."""
        try:
            # Get the data array - Kraken V2 puts ticker info here
            ticker_data = data.get("data", [])
            
            if not ticker_data:
                # Try legacy format
                ticker_data = data.get("ticker_data", [])
                if not ticker_data:
                    logger.warning(f"[WEBSOCKET] No ticker data found")
                    return
                    
            # Process each ticker in the data array
            for ticker_info in ticker_data:
                if not isinstance(ticker_info, dict):
                    continue
                    
                # Extract symbol
                symbol = ticker_info.get("symbol")
                if not symbol:
                    continue
                    
                # Convert XBT back to BTC for internal consistency
                internal_symbol = symbol.replace("XBT/", "BTC/")
                
                # Extract price data
                price = ticker_info.get('last', 0)
                bid = ticker_info.get('bid', 0)
                ask = ticker_info.get('ask', 0)
                volume = ticker_info.get('volume', 0)
                
                if price and price > 0:
                    # Store the price update
                    self.last_price_update[internal_symbol] = {
                        'price': price,
                        'bid': bid,
                        'ask': ask,
                        'volume': volume,
                        'timestamp': time.time(),
                        'spread': (ask - bid) if (ask and bid) else None,
                        'raw_data': ticker_info
                    }
                    
                    self.last_heartbeat = time.time()
                    self.parsing_successes += 1
                    
                    # Log first few updates
                    if self.price_update_count < 10 or self.price_update_count % 100 == 0:
                        logger.info(
                            f"[WEBSOCKET] Ticker #{self.price_update_count} "
                            f"{internal_symbol}: ${price:.2f}"
                        )
                    
                    # Pass to real-time data store
                    if self.real_time_data_store:
                        await self.real_time_data_store.update_ticker_optimized(internal_symbol, ticker_info)
                        
                    self.price_update_count += 1
                else:
                    self.parsing_failures += 1
                    
        except Exception as e:
            logger.error(f"[WEBSOCKET] Ticker update error: {e}")
            self.parsing_failures += 1
    '''
    
    # Apply the fix
    content = re.sub(ticker_pattern, fixed_ticker_method + '\n    ', content, flags=re.DOTALL)
    
    # Save the fixed file
    with open(websocket_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ WebSocket ticker parsing fix applied successfully!")
    print("🚀 The bot will now correctly parse Kraken V2 ticker data")
    
if __name__ == "__main__":
    apply_websocket_fix()
