"""
WebSocket V2 Data Explorer - See all real-time SHIB data
Shows ticker, trades, order book, and calculated metrics
"""

import asyncio
import websockets
import json
import time
from datetime import datetime
from collections import deque
from typing import Dict, List


class WebSocketDataExplorer:
    """Explore all WebSocket V2 data streams for SHIB/USDT"""
    
    def __init__(self):
        self.ws_url = "wss://ws.kraken.com/v2"
        self.pair = "SHIB/USDT"
        
        # Data storage
        self.last_ticker = {}
        self.recent_trades = deque(maxlen=20)
        self.order_book = {"bids": [], "asks": []}
        
        # Metrics
        self.trades_count = 0
        self.total_volume = 0
        self.buy_volume = 0
        self.sell_volume = 0
        
    async def connect_and_explore(self):
        """Connect and show all available data"""
        print(f"🔌 Connecting to Kraken WebSocket V2...")
        
        async with websockets.connect(self.ws_url) as ws:
            print(f"✅ Connected successfully!")
            print(f"📊 Exploring all data for {self.pair}")
            print("="*70)
            
            # Subscribe to all channels
            await self._subscribe_all(ws)
            
            # Process messages
            start_time = time.time()
            
            async for message in ws:
                data = json.loads(message)
                
                # Process based on channel
                if data.get("channel") == "ticker":
                    self._process_ticker(data)
                elif data.get("channel") == "trade":
                    self._process_trade(data)
                elif data.get("channel") == "book":
                    self._process_book(data)
                    
                # Display every 2 seconds
                if time.time() - start_time > 2:
                    self._display_all_data()
                    start_time = time.time()
                    
                # Run for 60 seconds
                if time.time() - start_time > 60:
                    print("\n✅ Data exploration complete!")
                    break
                    
    async def _subscribe_all(self, ws):
        """Subscribe to all data channels"""
        # 1. Ticker (best bid/ask/last)
        ticker_sub = {
            "method": "subscribe",
            "params": {
                "channel": "ticker",
                "symbol": [self.pair],
                "snapshot": True
            }
        }
        await ws.send(json.dumps(ticker_sub))
        print("✓ Subscribed to ticker data")
        
        # 2. Trades (all executed trades)
        trade_sub = {
            "method": "subscribe",
            "params": {
                "channel": "trade",
                "symbol": [self.pair],
                "snapshot": False
            }
        }
        await ws.send(json.dumps(trade_sub))
        print("✓ Subscribed to trade feed")
        
        # 3. Order Book (market depth)
        book_sub = {
            "method": "subscribe",
            "params": {
                "channel": "book",
                "symbol": [self.pair],
                "depth": 10,
                "snapshot": True
            }
        }
        await ws.send(json.dumps(book_sub))
        print("✓ Subscribed to order book")
        
        print("-"*70)
        
    def _process_ticker(self, data: Dict):
        """Process ticker updates"""
        if "data" in data:
            ticker = data["data"][0]
            self.last_ticker = {
                "bid": float(ticker.get("bid", 0)),
                "ask": float(ticker.get("ask", 0)),
                "last": float(ticker.get("last", 0)),
                "volume": float(ticker.get("volume", 0)),
                "vwap": float(ticker.get("vwap", 0)),
                "low": float(ticker.get("low", 0)),
                "high": float(ticker.get("high", 0)),
                "change": float(ticker.get("change", 0)),
                "change_pct": float(ticker.get("change_pct", 0))
            }
            
    def _process_trade(self, data: Dict):
        """Process trade feed"""
        if "data" in data:
            for trade in data["data"]:
                trade_info = {
                    "price": float(trade["price"]),
                    "volume": float(trade["qty"]),
                    "side": trade["side"],
                    "time": datetime.now().strftime("%H:%M:%S.%f")[:-3]
                }
                self.recent_trades.append(trade_info)
                
                # Update metrics
                self.trades_count += 1
                self.total_volume += trade_info["volume"]
                if trade_info["side"] == "buy":
                    self.buy_volume += trade_info["volume"]
                else:
                    self.sell_volume += trade_info["volume"]
                    
    def _process_book(self, data: Dict):
        """Process order book"""
        if "data" in data:
            book = data["data"][0]
            
            if "bids" in book:
                self.order_book["bids"] = [
                    {
                        "price": float(b["price"]),
                        "volume": float(b["qty"]),
                        "count": int(b.get("count", 1))
                    }
                    for b in book["bids"][:5]  # Top 5 levels
                ]
                
            if "asks" in book:
                self.order_book["asks"] = [
                    {
                        "price": float(a["price"]),
                        "volume": float(a["qty"]),
                        "count": int(a.get("count", 1))
                    }
                    for a in book["asks"][:5]  # Top 5 levels
                ]
                
    def _display_all_data(self):
        """Display all collected data"""
        # Clear screen for clean display
        print("\033[H\033[J", end="")  # ANSI escape to clear screen
        
        print("="*70)
        print(f"🔴 LIVE SHIB/USDT DATA - {datetime.now().strftime('%H:%M:%S')}")
        print("="*70)
        
        # 1. TICKER DATA
        if self.last_ticker:
            t = self.last_ticker
            spread = t["ask"] - t["bid"]
            spread_pct = (spread / t["last"] * 100) if t["last"] > 0 else 0
            
            print("\n📊 TICKER DATA:")
            print(f"  Last Price: ${t['last']:.8f}")
            print(f"  Bid/Ask:    ${t['bid']:.8f} / ${t['ask']:.8f}")
            print(f"  Spread:     ${spread:.8f} ({spread_pct:.3f}%)")
            print(f"  24h Change: {t['change_pct']:.2f}%")
            print(f"  24h Range:  ${t['low']:.8f} - ${t['high']:.8f}")
            print(f"  24h Volume: {t['volume']:,.0f} SHIB")
            
        # 2. ORDER BOOK
        if self.order_book["bids"] and self.order_book["asks"]:
            print("\n📗 ORDER BOOK (Top 5 Levels):")
            print("  BIDS (Buyers)               |  ASKS (Sellers)")
            print("  " + "-"*28 + "|" + "-"*28)
            
            for i in range(5):
                bid_str = ""
                ask_str = ""
                
                if i < len(self.order_book["bids"]):
                    b = self.order_book["bids"][i]
                    bid_str = f"  ${b['price']:.8f} | {b['volume']:>10,.0f}"
                    
                if i < len(self.order_book["asks"]):
                    a = self.order_book["asks"][i]
                    ask_str = f"${a['price']:.8f} | {a['volume']:>10,.0f}  "
                    
                print(f"{bid_str:<30}|{ask_str:>30}")
                
            # Book imbalance
            total_bid_vol = sum(b["volume"] for b in self.order_book["bids"])
            total_ask_vol = sum(a["volume"] for a in self.order_book["asks"])
            imbalance = (total_bid_vol - total_ask_vol) / (total_bid_vol + total_ask_vol) * 100
            print(f"\n  Book Imbalance: {imbalance:+.1f}% {'(More Buyers)' if imbalance > 0 else '(More Sellers)'}")
            
        # 3. RECENT TRADES
        if self.recent_trades:
            print("\n📈 RECENT TRADES:")
            print("  Time        | Price        | Volume      | Side")
            print("  " + "-"*50)
            
            for trade in list(self.recent_trades)[-10:]:  # Last 10 trades
                side_emoji = "🟢" if trade["side"] == "buy" else "🔴"
                print(f"  {trade['time']} | ${trade['price']:.8f} | "
                      f"{trade['volume']:>10,.0f} | {side_emoji} {trade['side'].upper()}")
                      
        # 4. TRADE FLOW METRICS
        if self.trades_count > 0:
            order_flow = ((self.buy_volume - self.sell_volume) / 
                         self.total_volume * 100) if self.total_volume > 0 else 0
            
            print(f"\n📊 TRADE FLOW ANALYSIS:")
            print(f"  Total Trades:  {self.trades_count}")
            print(f"  Total Volume:  {self.total_volume:,.0f} SHIB")
            print(f"  Buy Volume:    {self.buy_volume:,.0f} SHIB ({self.buy_volume/self.total_volume*100:.1f}%)")
            print(f"  Sell Volume:   {self.sell_volume:,.0f} SHIB ({self.sell_volume/self.total_volume*100:.1f}%)")
            print(f"  Order Flow:    {order_flow:+.1f}% {'(Bullish)' if order_flow > 0 else '(Bearish)'}")
            
        # 5. TRADING OPPORTUNITIES
        if self.last_ticker and self.trades_count > 10:
            print(f"\n💡 TRADING INSIGHTS:")
            
            # Spread opportunity
            if spread_pct < 0.1:
                print(f"  ✅ Tight spread ({spread_pct:.3f}%) - Good for scalping!")
            else:
                print(f"  ⚠️  Wide spread ({spread_pct:.3f}%) - Wait for better entry")
                
            # Order flow
            if order_flow > 20:
                print(f"  ✅ Strong buying pressure ({order_flow:+.1f}%)")
            elif order_flow < -20:
                print(f"  ⚠️  Strong selling pressure ({order_flow:+.1f}%)")
            else:
                print(f"  ➖ Neutral order flow ({order_flow:+.1f}%)")
                
            # Volume
            if self.trades_count > 50:
                print(f"  ✅ High activity ({self.trades_count} trades)")
            else:
                print(f"  ⚠️  Low activity ({self.trades_count} trades)")
                

async def main():
    """Run the data explorer"""
    print("🔍 WebSocket V2 Data Explorer for SHIB/USDT")
    print("This will show all available real-time data streams")
    print("Running for 60 seconds...\n")
    
    explorer = WebSocketDataExplorer()
    
    try:
        await explorer.connect_and_explore()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        

if __name__ == "__main__":
    asyncio.run(main())
