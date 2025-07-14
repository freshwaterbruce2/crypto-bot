# FIX 1: WEBSOCKET CALLBACK MISMATCH

File: src/bot.py

Replace _handle_ticker_data and _handle_ohlc_data methods with:

```python
async def _handle_ticker_data(self, msg):
    """Handle ticker updates from WebSocket v2"""
    try:
        # Extract symbol and data from WebSocket v2 message
        if isinstance(msg, dict) and 'data' in msg:
            ticker_data = msg['data'][0] if msg['data'] else {}
            symbol = ticker_data.get('symbol', '')
            
            if symbol and symbol.endswith('/USDT'):
                price = ticker_data.get('last', 0)
                volume = ticker_data.get('volume', 0)
                
                # Update price tracking
                self.latest_prices[symbol] = {
                    'price': price,
                    'volume': volume,
                    'timestamp': time.time()
                }
                
                # Notify strategies
                for strategy in self.strategies.values():
                    if hasattr(strategy, 'on_price_update'):
                        await strategy.on_price_update(symbol, price)
                        
    except Exception as e:
        logger.error(f"[TICKER] Error handling ticker data: {e}")

async def _handle_ohlc_data(self, msg):
    """Handle OHLC updates from WebSocket v2"""
    try:
        if isinstance(msg, dict) and 'data' in msg:
            for candle in msg.get('data', []):
                symbol = candle.get('symbol', '')
                if symbol and symbol.endswith('/USDT'):
                    # Store OHLC data
                    if symbol not in self.ohlc_data:
                        self.ohlc_data[symbol] = []
                    
                    self.ohlc_data[symbol].append({
                        'time': candle.get('interval_begin'),
                        'open': candle.get('open'),
                        'high': candle.get('high'),
                        'low': candle.get('low'),
                        'close': candle.get('close'),
                        'volume': candle.get('volume')
                    })
                    
                    # Keep only last 100 candles
                    self.ohlc_data[symbol] = self.ohlc_data[symbol][-100:]
                    
    except Exception as e:
        logger.error(f"[OHLC] Error handling OHLC data: {e}")
```