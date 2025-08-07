#!/usr/bin/env python3
"""
PATIENT PROFIT BOT
==================
Strategy: Wait for REAL profits after spread
No more micro-scalping losses!
"""

import json
import os
import time
from datetime import datetime

import ccxt
from dotenv import load_dotenv

load_dotenv()

class PatientProfitBot:
    def __init__(self):
        self.exchange = None
        self.symbol = 'SHIB/USDT'
        self.position_file = 'patient_position.json'
        self.position = None

        # PATIENT STRATEGY - Account for spread!
        self.spread_buffer = 0.001  # 0.1% buffer above spread
        self.min_profit_target = 0.005  # 0.5% minimum (covers 0.08% spread + profit)
        self.good_profit_target = 0.01  # 1% is excellent
        self.stop_loss = -0.02  # -2% stop loss

        # Range trading parameters
        self.buy_zone = 0.25  # Only buy in bottom 25% of daily range
        self.sell_zone = 0.75  # Only sell in top 25% of daily range

        # Performance tracking
        self.starting_value = None
        self.trades_completed = 0
        self.total_profit = 0

        self.load_position()

    def load_position(self):
        """Load saved position if exists"""
        if os.path.exists(self.position_file):
            try:
                with open(self.position_file) as f:
                    self.position = json.load(f)
                    print(f"📂 Loaded position: {self.position['amount']:,.0f} SHIB @ ${self.position['price']:.8f}")
            except:
                pass

    def save_position(self):
        """Save position to file"""
        if self.position:
            with open(self.position_file, 'w') as f:
                json.dump(self.position, f)
        elif os.path.exists(self.position_file):
            os.remove(self.position_file)

    def initialize(self):
        """Initialize exchange connection"""
        self.exchange = ccxt.kraken({
            'apiKey': os.getenv('KRAKEN_KEY'),
            'secret': os.getenv('KRAKEN_SECRET'),
            'enableRateLimit': True
        })
        print("✅ Connected to Kraken")

    def get_balance(self):
        """Get current balances"""
        balance = self.exchange.fetch_balance()
        usdt = balance.get('USDT', {}).get('free', 0)
        shib = balance.get('SHIB', {}).get('free', 0)
        return usdt, shib

    def get_market_data(self):
        """Get comprehensive market data"""
        ticker = self.exchange.fetch_ticker(self.symbol)

        # Calculate spread
        bid = ticker['bid']
        ask = ticker['ask']
        spread = (ask - bid) / bid if bid > 0 else 0

        # Calculate position in daily range
        high = ticker['high']
        low = ticker['low']
        price = ticker['last']

        if high > low:
            range_position = (price - low) / (high - low)
        else:
            range_position = 0.5

        return {
            'price': price,
            'bid': bid,
            'ask': ask,
            'spread': spread,
            'high': high,
            'low': low,
            'range_position': range_position,
            'change': ticker['percentage']
        }

    def should_buy(self, data, usdt_balance):
        """Only buy at good prices with spread consideration"""
        if self.position:
            return False, "Already in position"

        if usdt_balance < 2.5:
            return False, "Insufficient balance"

        # Check if spread is reasonable
        if data['spread'] > 0.002:  # More than 0.2%
            return False, f"Spread too wide: {data['spread']:.3%}"

        # Only buy in lower part of daily range
        if data['range_position'] > self.buy_zone:
            return False, f"Price too high: {data['range_position']:.1%} of range"

        # Don't buy if already pumped today
        if data['change'] > 3:
            return False, f"Already up {data['change']:.1%} today"

        return True, f"Good entry: {data['range_position']:.1%} of range"

    def should_sell(self, data):
        """Only sell at profit accounting for spread"""
        if not self.position:
            return False, ""

        # Calculate REAL profit after spread
        buy_price = self.position['price']
        sell_price = data['bid']  # We'll get bid price when selling
        real_profit = (sell_price - buy_price) / buy_price

        hold_time = (time.time() - self.position['time']) / 60

        # Must cover spread + minimum profit
        spread_adjusted_target = data['spread'] + self.spread_buffer

        # Profit targets
        if real_profit >= self.good_profit_target:
            return True, f"Great profit: {real_profit:.2%}"

        if real_profit >= self.min_profit_target:
            # Only sell if in upper range or held long enough
            if data['range_position'] > self.sell_zone:
                return True, f"Target + high range: {real_profit:.2%}"
            if hold_time > 60:
                return True, f"Target + time: {real_profit:.2%} after {hold_time:.0f}min"

        # Patient exit - wait for real profit
        if hold_time > 120 and real_profit > spread_adjusted_target:
            return True, f"Patient exit: {real_profit:.2%} after {hold_time:.0f}min"

        # Stop loss
        if real_profit <= self.stop_loss:
            return True, f"Stop loss: {real_profit:.2%}"

        # Don't sell at a loss unless stop loss
        if real_profit < spread_adjusted_target:
            return False, f"Wait: {real_profit:.3%} (need {spread_adjusted_target:.3%})"

        return False, f"Hold: {real_profit:.3%}"

    def place_buy(self, amount, data):
        """Place buy order accounting for fees"""
        try:
            # Use ask price for immediate fill
            price = data['ask']
            shib_amount = int((amount * 0.997) / price)

            # Check minimum order size
            if shib_amount < 160000:  # Kraken minimum
                print(f"❌ Order too small: {shib_amount:,} SHIB")
                return False

            order = self.exchange.create_market_buy_order(self.symbol, shib_amount)

            # Track actual buy price
            self.position = {
                'amount': shib_amount,
                'price': price,  # Track ask price we paid
                'time': time.time()
            }
            self.save_position()

            print(f"\n🟢 BOUGHT: {shib_amount:,.0f} SHIB @ ${price:.8f}")
            print(f"   Cost: ${amount:.2f} (including spread)")

            return True

        except Exception as e:
            print(f"❌ Buy error: {e}")
            return False

    def place_sell(self, data):
        """Place sell order"""
        try:
            # Will get bid price
            price = data['bid']

            order = self.exchange.create_market_sell_order(
                self.symbol,
                self.position['amount']
            )

            # Calculate REAL profit
            real_profit = (price - self.position['price']) / self.position['price']
            profit_usdt = self.position['amount'] * (price - self.position['price'])
            hold_time = (time.time() - self.position['time']) / 60

            self.trades_completed += 1
            self.total_profit += profit_usdt

            print(f"\n🔴 SOLD: {self.position['amount']:,.0f} SHIB @ ${price:.8f}")
            print(f"   Real Profit: {real_profit:.2%} = ${profit_usdt:.3f}")
            print(f"   Hold time: {hold_time:.1f} minutes")
            print(f"   Total: {self.trades_completed} trades = ${self.total_profit:.2f}")

            self.position = None
            self.save_position()

            return True

        except Exception as e:
            print(f"❌ Sell error: {e}")
            return False

    def run(self):
        """Main trading loop"""
        print("=" * 70)
        print("PATIENT PROFIT BOT - REAL PROFITS AFTER SPREAD")
        print("=" * 70)
        print("Strategy: Wait for 0.5%+ profits, account for spread")
        print("=" * 70)

        self.initialize()

        # Get initial state
        usdt, shib = self.get_balance()
        data = self.get_market_data()
        self.starting_value = usdt + (shib * data['price'])

        print(f"💰 Starting: ${usdt:.2f} USDT + {shib:,.0f} SHIB")
        print(f"📊 Total Value: ${self.starting_value:.2f}")
        print(f"⚠️ Current Spread: {data['spread']:.3%}")

        # Detect existing SHIB position
        if shib > 160000 and not self.position:
            self.position = {
                'amount': shib,
                'price': data['price'],  # Use current price as estimate
                'time': time.time() - 3600  # Assume held for 1 hour
            }
            print(f"📂 Detected existing {shib:,.0f} SHIB position")
            self.save_position()

        loop_count = 0

        while True:
            try:
                loop_count += 1

                # Get fresh data
                data = self.get_market_data()
                usdt, shib = self.get_balance()
                current_value = usdt + (shib * data['price'])

                # Display every 3rd loop
                if loop_count % 3 == 1:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
                    print(f"Price: ${data['price']:.8f} | "
                          f"Range: {data['range_position']:.1%} | "
                          f"Spread: {data['spread']:.3%}")
                    print(f"Balance: ${usdt:.2f} + {shib:,.0f} SHIB = "
                          f"${current_value:.2f} ({((current_value/self.starting_value)-1)*100:+.2f}%)")

                # Trading logic
                if not self.position:
                    should_buy, reason = self.should_buy(data, usdt)
                    if should_buy:
                        print(f"\n🎯 BUY SIGNAL: {reason}")
                        self.place_buy(usdt, data)
                    elif loop_count % 6 == 1:  # Less frequent updates
                        print(f"⏳ Waiting: {reason}")
                else:
                    should_sell, reason = self.should_sell(data)
                    if should_sell:
                        print(f"\n🎯 SELL SIGNAL: {reason}")
                        self.place_sell(data)
                    elif loop_count % 3 == 1:
                        real_profit = (data['bid'] - self.position['price']) / self.position['price']
                        hold_time = (time.time() - self.position['time']) / 60
                        print(f"⏳ Holding: {real_profit:.3%} profit, {hold_time:.0f}min")
                        print(f"   {reason}")

                # Sleep based on position
                if self.position:
                    time.sleep(10)  # Check more often when holding
                else:
                    time.sleep(20)  # Less often when waiting

            except KeyboardInterrupt:
                print("\n\nStopping bot...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(30)

        # Final report
        usdt, shib = self.get_balance()
        data = self.get_market_data()
        final_value = usdt + (shib * data['price'])

        print("\n" + "=" * 70)
        print("FINAL REPORT")
        print("=" * 70)
        print(f"Starting Value: ${self.starting_value:.2f}")
        print(f"Final Value: ${final_value:.2f}")
        print(f"Net Result: ${final_value - self.starting_value:.2f} "
              f"({((final_value/self.starting_value)-1)*100:+.2f}%)")
        print(f"Trades Completed: {self.trades_completed}")
        print(f"Trading Profit: ${self.total_profit:.2f}")

if __name__ == "__main__":
    bot = PatientProfitBot()
    bot.run()
