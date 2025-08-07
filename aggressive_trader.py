#!/usr/bin/env python3
"""
AGGRESSIVE TRADER - ALWAYS TRADING
===================================
Simplified bot that trades frequently
"""

import json
import os
import time
from datetime import datetime

import ccxt
from dotenv import load_dotenv

load_dotenv()

class AggressiveTrader:
    def __init__(self):
        self.exchange = None
        self.symbol = 'SHIB/USDT'
        self.position_file = 'aggressive_position.json'
        self.position = None

        # VERY AGGRESSIVE PARAMETERS
        self.min_profit = 0.002  # 0.2% minimum
        self.target_profit = 0.003  # 0.3% target
        self.stop_loss = -0.01  # -1% stop

        # Track trades
        self.trades_today = 0
        self.profit_today = 0
        self.last_buy_price = 0

        self.load_position()

    def load_position(self):
        """Load saved position"""
        if os.path.exists(self.position_file):
            try:
                with open(self.position_file) as f:
                    self.position = json.load(f)
                    print(f"📂 Loaded position: {self.position['amount']:,.0f} SHIB @ ${self.position['price']:.8f}")
            except Exception:
                pass

    def save_position(self):
        """Save position"""
        if self.position:
            with open(self.position_file, 'w') as f:
                json.dump(self.position, f)
        elif os.path.exists(self.position_file):
            os.remove(self.position_file)

    def initialize(self):
        """Initialize exchange"""
        self.exchange = ccxt.kraken({
            'apiKey': os.getenv('KRAKEN_KEY'),
            'secret': os.getenv('KRAKEN_SECRET'),
            'enableRateLimit': True
        })
        print("✅ Connected to Kraken")

    def get_market_data(self):
        """Get simple market data"""
        ticker = self.exchange.fetch_ticker(self.symbol)
        return {
            'price': ticker['last'],
            'bid': ticker['bid'],
            'ask': ticker['ask'],
            'high': ticker['high'],
            'low': ticker['low'],
            'change': ticker['percentage']
        }

    def should_buy(self, data, usdt_balance):
        """SIMPLE BUY LOGIC - Just buy if we have money and no position"""
        if self.position:
            return False

        if usdt_balance < 2.5:
            return False

        # Buy if price hasn't pumped too much today
        if data['change'] < 5:  # Not up more than 5%
            # Additional check: don't buy at daily high
            price_position = (data['price'] - data['low']) / (data['high'] - data['low']) if data['high'] > data['low'] else 0.5
            if price_position < 0.8:  # Not in top 20% of range
                return True

        return False

    def should_sell(self, data):
        """SIMPLE SELL LOGIC - Sell on any profit or stop loss"""
        if not self.position:
            return False

        profit = (data['price'] - self.position['price']) / self.position['price']
        hold_time = (time.time() - self.position['time']) / 60

        # Take ANY profit after 5 minutes
        if hold_time > 5 and profit > 0.001:  # 0.1% after 5 min
            return True, f"Quick exit: {profit:.2%}"

        # Target profits
        if profit >= self.min_profit:
            return True, f"Min profit: {profit:.2%}"

        if profit >= self.target_profit:
            return True, f"Target: {profit:.2%}"

        # Time-based exits
        if hold_time > 30 and profit > 0:  # Any profit after 30 min
            return True, f"Time exit: {profit:.2%}"

        # Stop loss
        if profit <= self.stop_loss:
            return True, f"Stop loss: {profit:.2%}"

        return False, f"Hold: {profit:.3%}"

    def place_buy(self, amount, price):
        """Place buy order"""
        try:
            shib_amount = int((amount * 0.997) / price)

            # Market order for instant fill
            self.exchange.create_market_buy_order(self.symbol, shib_amount)

            self.position = {
                'amount': shib_amount,
                'price': price,
                'time': time.time()
            }
            self.save_position()
            self.last_buy_price = price

            print(f"\n🟢 BOUGHT: {shib_amount:,.0f} SHIB @ ${price:.8f}")
            print(f"   Cost: ${amount:.2f}")

            return True
        except Exception as e:
            print(f"❌ Buy error: {e}")
            return False

    def place_sell(self, price):
        """Place sell order"""
        try:
            self.exchange.create_market_sell_order(self.symbol, self.position['amount'])

            # Calculate profit
            profit = (price - self.position['price']) / self.position['price']
            profit_usdt = self.position['amount'] * (price - self.position['price'])
            hold_time = (time.time() - self.position['time']) / 60

            self.trades_today += 1
            self.profit_today += profit_usdt

            print(f"\n🔴 SOLD: {self.position['amount']:,.0f} SHIB @ ${price:.8f}")
            print(f"   Profit: {profit:.2%} = ${profit_usdt:.3f}")
            print(f"   Hold time: {hold_time:.1f} minutes")
            print(f"   Today: {self.trades_today} trades, Total: ${self.profit_today:.2f}")

            self.position = None
            self.save_position()

            return True
        except Exception as e:
            print(f"❌ Sell error: {e}")
            return False

    def run(self):
        """Main trading loop"""
        print("=" * 70)
        print("AGGRESSIVE TRADER - FREQUENT TRADES")
        print("=" * 70)
        print("Strategy: Trade frequently with 0.2-0.3% targets")
        print("=" * 70)

        self.initialize()

        # Get initial balance
        balance = self.exchange.fetch_balance()
        usdt = balance.get('USDT', {}).get('total', 0)
        shib = balance.get('SHIB', {}).get('total', 0)

        print(f"💰 Starting: ${usdt:.2f} USDT + {shib:,.0f} SHIB")

        # Detect existing SHIB
        if shib > 50000 and not self.position:
            data = self.get_market_data()
            self.position = {
                'amount': shib,
                'price': data['price'] * 0.995,
                'time': time.time() - 600
            }
            print(f"📂 Detected {shib:,.0f} SHIB position")
            self.save_position()

        loop_count = 0
        last_action_time = 0

        while True:
            try:
                loop_count += 1

                # Get data
                data = self.get_market_data()
                balance = self.exchange.fetch_balance()
                usdt = balance.get('USDT', {}).get('total', 0)
                shib = balance.get('SHIB', {}).get('total', 0)

                # Calculate position in range
                if data['high'] > data['low']:
                    price_position = (data['price'] - data['low']) / (data['high'] - data['low'])
                else:
                    price_position = 0.5

                # Display status every 3 loops
                if loop_count % 3 == 1:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                          f"SHIB: ${data['price']:.8f} | "
                          f"Range: {price_position:.1%} | "
                          f"24h: {data['change']:+.1f}%")
                    print(f"Balance: ${usdt:.2f} + {shib:,.0f} SHIB")

                # TRADING LOGIC
                if not self.position:
                    # Try to buy
                    if self.should_buy(data, usdt):
                        # Wait at least 1 minute between trades
                        if time.time() - last_action_time > 60:
                            print("🎯 BUY SIGNAL: Good entry point")
                            if self.place_buy(usdt, data['price']):
                                last_action_time = time.time()
                        else:
                            wait = 60 - (time.time() - last_action_time)
                            if loop_count % 3 == 1:
                                print(f"⏳ Cooldown: {wait:.0f}s")
                    elif loop_count % 3 == 1:
                        if price_position > 0.8:
                            print(f"⏳ Price too high: {price_position:.1%} of range")
                        else:
                            print("⏳ Waiting for entry")
                else:
                    # Try to sell
                    should_sell, reason = self.should_sell(data)
                    if should_sell:
                        print(f"🎯 SELL SIGNAL: {reason}")
                        if self.place_sell(data['price']):
                            last_action_time = time.time()
                    elif loop_count % 3 == 1:
                        profit = (data['price'] - self.position['price']) / self.position['price']
                        hold_time = (time.time() - self.position['time']) / 60
                        print(f"⏳ Holding: {profit:.3%} profit, {hold_time:.0f}min")

                # Sleep
                if self.position:
                    time.sleep(5)  # Check often when in position
                else:
                    time.sleep(10)  # Less often when waiting

            except KeyboardInterrupt:
                print("\n\nStopping bot...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(30)

        # Final report
        print("\n" + "=" * 70)
        print("FINAL REPORT")
        print("=" * 70)
        print(f"Trades completed: {self.trades_today}")
        print(f"Total profit: ${self.profit_today:.2f}")

        balance = self.exchange.fetch_balance()
        usdt = balance.get('USDT', {}).get('total', 0)
        shib = balance.get('SHIB', {}).get('total', 0)
        final_value = usdt + (shib * data['price'])
        print(f"Final value: ${final_value:.2f}")

if __name__ == "__main__":
    bot = AggressiveTrader()
    bot.run()
