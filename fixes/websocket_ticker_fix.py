"""
WebSocket Ticker Parsing Fix for Kraken V2
Fixes the ticker data parsing to match Kraken's actual message format
"""

async def _handle_ticker_update_FIXED(self, data: Dict[str, Any]) -> None:
    """
    Fixed ticker update handler that correctly parses Kraken V2 ticker format.
    
    Kraken V2 sends ticker data as:
    {
        "channel": "ticker",
        "type": "snapshot" or "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "last": 30000.0,
                "bid": 29999.0,
                "ask": 30001.0,
                "volume": 1000.0,
                // ... other fields
            }
        ]
    }
    """
    try:
        # Get the data array - this is where Kraken puts the ticker info
        ticker_data = data.get("data", [])
        
        # Check if we have data
        if not ticker_data:
            logger.warning(f"[WEBSOCKET] No ticker data in message: {data}")
            return
            
        # Process each ticker in the data array
        for ticker_info in ticker_data:
            if not isinstance(ticker_info, dict):
                continue
                
            # Extract symbol and price data
            symbol = ticker_info.get("symbol")
            if not symbol:
                continue
                
            # Convert XBT back to BTC for internal consistency
            internal_symbol = symbol.replace("XBT/", "BTC/")
            
            # Extract all price data
            price_data = {
                'price': ticker_info.get('last', 0),
                'bid': ticker_info.get('bid', 0),
                'ask': ticker_info.get('ask', 0),
                'volume': ticker_info.get('volume', 0),
                'timestamp': time.time(),
                'spread': None,
                'raw_data': ticker_info
            }
            
            # Calculate spread if we have bid and ask
            if price_data['bid'] and price_data['ask']:
                price_data['spread'] = price_data['ask'] - price_data['bid']
            
            # Validate we have a valid price
            if price_data['price'] and price_data['price'] > 0:
                # Store the price update
                self.last_price_update[internal_symbol] = price_data
                self.last_heartbeat = time.time()
                self.parsing_successes += 1
                
                # Log first few updates for debugging
                if self.price_update_count < 10 or self.price_update_count % 100 == 0:
                    logger.info(
                        f"[WEBSOCKET] Ticker update #{self.price_update_count} "
                        f"for {internal_symbol}: ${price_data['price']:.2f} "
                        f"(bid: ${price_data['bid']:.2f}, ask: ${price_data['ask']:.2f})"
                    )
                
                # Pass to real-time data store if available
                if self.real_time_data_store and hasattr(self.real_time_data_store, 'update_ticker_optimized'):
                    await self.real_time_data_store.update_ticker_optimized(internal_symbol, ticker_info)
                    
                # Update price count
                self.price_update_count += 1
            else:
                logger.warning(f"[WEBSOCKET] Invalid price for {symbol}: {ticker_info}")
                self.parsing_failures += 1
                
    except Exception as e:
        logger.error(f"[WEBSOCKET] Ticker update error: {e}", exc_info=True)
        self.parsing_failures += 1


# Additional fix for OHLC parsing
async def _handle_ohlc_update_FIXED(self, data: Dict[str, Any]) -> None:
    """
    Fixed OHLC update handler for Kraken V2 format.
    
    Kraken V2 sends OHLC data as:
    {
        "channel": "ohlc", 
        "type": "snapshot" or "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "open": 29500.0,
                "high": 30500.0,
                "low": 29000.0,
                "close": 30000.0,
                "vwap": 29800.0,
                "trades": 150,
                "volume": 1000.0,
                "interval_begin": "2022-12-25T09:30:00.000000Z",
                "interval": 1
            }
        ]
    }
    """
    try:
        # Get the data array
        ohlc_data = data.get("data", [])
        
        if not ohlc_data:
            return
            
        # Process each OHLC candle
        for candle in ohlc_data:
            if not isinstance(candle, dict):
                continue
                
            symbol = candle.get("symbol")
            if not symbol:
                continue
                
            # Convert symbol for internal use
            internal_symbol = symbol.replace("XBT/", "BTC/")
            
            # Convert to standard format for strategy manager
            ohlc_dict = {
                'timestamp': candle.get('interval_begin', ''),
                'open': float(candle.get('open', 0)),
                'high': float(candle.get('high', 0)),
                'low': float(candle.get('low', 0)),
                'close': float(candle.get('close', 0)),
                'volume': float(candle.get('volume', 0)),
                'trades': candle.get('trades', 0),
                'vwap': float(candle.get('vwap', 0))
            }
            
            # Send to strategy manager if available
            if self.strategy_manager and hasattr(self.strategy_manager, 'update_ohlc_data'):
                await self.strategy_manager.update_ohlc_data(internal_symbol, ohlc_dict)
                
            # Store in real-time data store
            if self.real_time_data_store and hasattr(self.real_time_data_store, 'update_ohlc_optimized'):
                await self.real_time_data_store.update_ohlc_optimized(internal_symbol, [ohlc_dict])
                
            # Log first few updates
            if self.price_update_count < 10 or self.price_update_count % 50 == 0:
                logger.info(
                    f"[WEBSOCKET] OHLC update for {internal_symbol}: "
                    f"O:{ohlc_dict['open']:.2f} H:{ohlc_dict['high']:.2f} "
                    f"L:{ohlc_dict['low']:.2f} C:{ohlc_dict['close']:.2f}"
                )
                
    except Exception as e:
        logger.error(f"[WEBSOCKET] OHLC update error: {e}", exc_info=True)


# Export the fixes
WEBSOCKET_FIXES = {
    '_handle_ticker_update': _handle_ticker_update_FIXED,
    '_handle_ohlc_update': _handle_ohlc_update_FIXED
}
