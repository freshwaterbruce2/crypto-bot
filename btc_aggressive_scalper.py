#!/usr/bin/env python3
"""
BTC AGGRESSIVE SCALPER - TRADES AT ANY RANGE
=============================================
Ultra-aggressive: Takes advantage of 0.0001% spread
Will trade even at 99% of range by using micro-dips
"""

import json
import os
import time
from datetime import datetime

import ccxt
from dotenv import load_dotenv

load_dotenv()

class BTCAggressiveScalper:
    def __init__(self):
        self.exchange = None
        self.symbol = 'BTC/USDT'
        self.position_file = 'btc_aggressive_position.json'
        self.position = None

        # ULTRA-AGGRESSIVE PARAMETERS
        self.trade_amount = 20.0  # $20 per trade

        # With 0.0001% spread, ANY movement is profit!
        self.instant_target = 0.00005  # 0.005% - Half the spread!
        self.micro_target = 0.0001    # 0.01% - Equal to spread
        self.quick_target = 0.0002    # 0.02% - Double the spread
        self.stop_loss = -0.0003      # -0.03% - Very tight stop

        # Track performance
        self.trades_completed = 0
        self.total_profit = 0
        self.last_trade_time = 0
        self.last_price = 0

        self.load_position()

    def load_position(self):
        """Load saved position"""
        if os.path.exists(self.position_file):
            try:
                with open(self.position_file) as f:
                    self.position = json.load(f)
                    print(f"📂 Position: {self.position['amount']:.6f} BTC @ ${self.position['price']:,.2f}")
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
        """Initialize Kraken Pro 2025"""
        self.exchange = ccxt.kraken({
            'apiKey': os.getenv('KRAKEN_KEY'),
            'secret': os.getenv('KRAKEN_SECRET'),
            'enableRateLimit': True,
            'rateLimit': 200
        })
        self.exchange.load_markets()
        print("✅ Connected to Kraken Pro")

    def get_balance(self):
        """Get balances"""
        balance = self.exchange.fetch_balance()
        usdt = balance.get('USDT', {}).get('free', 0)
        btc = balance.get('BTC', {}).get('free', 0)
        return usdt, btc

    def get_market_data(self):
        """Get market data with micro-movement tracking"""
        ticker = self.exchange.fetch_ticker(self.symbol)

        # Track micro price movements
        micro_movement = 0
        if self.last_price > 0:
            micro_movement = (ticker['last'] - self.last_price) / self.last_price

        self.last_price = ticker['last']

        return {
            'price': ticker['last'],
            'bid': ticker['bid'],
            'ask': ticker['ask'],
            'spread': (ticker['ask'] - ticker['bid']) / ticker['bid'],
            'high': ticker['high'],
            'low': ticker['low'],
            'range_position': (ticker['last'] - ticker['low']) / (ticker['high'] - ticker['low']) if ticker['high'] > ticker['low'] else 0.5,
            'micro_movement': micro_movement,
            'volume': ticker['baseVolume']
        }

    def aggressive_buy_decision(self, data, usdt_balance):
        """Ultra-aggressive buy logic - trades at ANY range"""
        if self.position:
            return False, "Already in position"

        if usdt_balance < self.trade_amount:
            return False, "Insufficient balance"

        # Minimal cooldown
        if time.time() - self.last_trade_time < 30:
            return False, f"Cooldown {30 - (time.time() - self.last_trade_time):.0f}s"

        range_pos = data['range_position']

        # ULTRA-HIGH RANGE (95-100%) - Buy on ANY micro-dip
        if range_pos > 0.95:
            # Even the tiniest pullback is an opportunity!
            if data['micro_movement'] < 0:  # ANY negative movement
                return True, f"MICRO-DIP at {range_pos:.1%}! Movement: {data['micro_movement']:.5%}"
            # Or if spread is super tight, just buy
            elif data['spread'] < 0.00015:  # 0.015% spread
                return True, f"ULTRA-TIGHT spread {data['spread']:.5%} at {range_pos:.1%}"
            return False, f"Waiting for micro-dip at {range_pos:.1%}"

        # HIGH RANGE (80-95%) - Buy on small dips
        elif range_pos > 0.8:
            if data['micro_movement'] <= 0:
                return True, f"High range dip: {data['micro_movement']:.5%}"
            return False, "High range, waiting for dip"

        # MID-HIGH (60-80%) - Buy freely
        elif range_pos > 0.6:
            return True, f"Mid-high range {range_pos:.1%}, good entry"

        # ANYTHING BELOW 60% - INSTANT BUY
        else:
            return True, f"EXCELLENT ENTRY at {range_pos:.1%}!"

    def should_sell(self, data):
        """Ultra-fast sell logic for instant profits"""
        if not self.position:
            return False, ""

        buy_price = self.position['price']
        current_price = data['bid']
        profit = (current_price - buy_price) / buy_price
        hold_time = (time.time() - self.position['time']) / 60

        # INSTANT TARGET - Take it immediately!
        if profit >= self.instant_target:
            return True, f"INSTANT: {profit:.5%}"

        # MICRO TARGET
        if profit >= self.micro_target:
            return True, f"MICRO: {profit:.5%}"

        # QUICK TARGET
        if profit >= self.quick_target:
            return True, f"QUICK: {profit:.5%}"

        # Break-even after 5 minutes
        if hold_time > 5 and profit >= 0:
            return True, f"Break-even @ {hold_time:.0f}min"

        # ANY profit after 10 minutes
        if hold_time > 10 and profit > -0.0001:
            return True, f"Time exit: {profit:.5%} @ {hold_time:.0f}min"

        # Stop loss
        if profit <= self.stop_loss:
            return True, f"Stop: {profit:.5%}"

        return False, f"Hold: {profit:.5%}"

    def place_buy(self, data):
        """Place market buy for instant fill"""
        try:
            price = data['ask']  # Use ask for market buy
            btc_amount = (self.trade_amount * 0.998) / price
            btc_amount = round(btc_amount, 6)

            if btc_amount < 0.00005:
                return False

            # Market order for instant fill
            self.exchange.create_market_buy_order(
                self.symbol,
                btc_amount
            )

            self.position = {
                'amount': btc_amount,
                'price': price,
                'time': time.time()
            }
            self.save_position()
            self.last_trade_time = time.time()

            print(f"\n🟢 BOUGHT: {btc_amount:.6f} BTC @ ${price:,.2f}")
            print(f"   Range: {data['range_position']:.1%}")

            return True

        except Exception as e:
            print(f"❌ Buy error: {e}")
            return False

    def place_sell(self, data):
        """Place market sell for instant fill"""
        try:
            price = data['bid']  # Use bid for market sell
            btc_amount = self.position['amount']

            self.exchange.create_market_sell_order(
                self.symbol,
                btc_amount
            )

            # Calculate profit
            buy_price = self.position['price']
            profit = (price - buy_price) / buy_price
            profit_usd = btc_amount * (price - buy_price)
            hold_time = (time.time() - self.position['time']) / 60

            self.trades_completed += 1
            self.total_profit += profit_usd

            emoji = "✅" if profit > 0 else "❌"

            print(f"\n🔴 SOLD: {btc_amount:.6f} BTC @ ${price:,.2f}")
            print(f"   {emoji} Profit: {profit:.5%} = ${profit_usd:.3f}")
            print(f"   ⏱️ Hold: {hold_time:.1f} minutes")
            print(f"   📊 Total: {self.trades_completed} trades = ${self.total_profit:.2f}")

            self.position = None
            self.save_position()
            self.last_trade_time = time.time()

            return True

        except Exception as e:
            print(f"❌ Sell error: {e}")
            return False

    def run(self):
        """Main aggressive trading loop"""
        print("=" * 70)
        print("BTC AGGRESSIVE SCALPER - TRADES AT 99% RANGE!")
        print("=" * 70)
        print("Strategy: Ultra-micro profits 0.005-0.02%")
        print("Will trade at ANY range using micro-dips")
        print("=" * 70)

        self.initialize()

        # Get starting balance
        usdt, btc = self.get_balance()
        data = self.get_market_data()
        starting_value = usdt + (btc * data['price'])

        print(f"💰 Balance: ${usdt:.2f} USDT")
        print(f"📊 BTC: ${data['price']:,.2f} @ {data['range_position']:.1%} of range")
        print(f"🎯 Spread: {data['spread']:.5%} (ULTRA-TIGHT!)")

        if data['range_position'] > 0.95:
            print("⚠️  WARNING: BTC at EXTREME HIGH!")
            print("   Strategy: Will buy on ANY micro-dip")

        loop_count = 0

        while True:
            try:
                loop_count += 1

                # Get fresh data
                data = self.get_market_data()
                usdt, btc = self.get_balance()
                current_value = usdt + (btc * data['price'])

                # Display every loop for aggressive monitoring
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}]", end=" ")
                print(f"${data['price']:,.2f} | {data['range_position']:.1%} | ", end="")
                print(f"Move: {data['micro_movement']:.5%} | ", end="")
                print(f"Value: ${current_value:.2f}")

                # Trading logic
                if not self.position:
                    should_buy, reason = self.aggressive_buy_decision(data, usdt)
                    if should_buy:
                        print(f"🎯 BUY SIGNAL: {reason}")
                        self.place_buy(data)
                    elif loop_count % 3 == 1:
                        print(f"   {reason}")
                else:
                    should_sell, reason = self.should_sell(data)
                    if should_sell:
                        print(f"🎯 SELL SIGNAL: {reason}")
                        self.place_sell(data)
                    else:
                        profit = (data['bid'] - self.position['price']) / self.position['price']
                        print(f"   Holding: {profit:.5%}")

                # Very fast checking for micro-movements
                time.sleep(3)

            except KeyboardInterrupt:
                print("\n\nStopping...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(10)

        # Final report
        usdt, btc = self.get_balance()
        final_value = usdt + (btc * data['price'])

        print("\n" + "=" * 70)
        print(f"Starting: ${starting_value:.2f}")
        print(f"Final: ${final_value:.2f}")
        print(f"Net: ${final_value - starting_value:.2f} "
              f"({((final_value/starting_value)-1)*100:+.3f}%)")
        print(f"Trades: {self.trades_completed}")
        print(f"Trading Profit: ${self.total_profit:.2f}")

if __name__ == "__main__":
    bot = BTCAggressiveScalper()
    bot.run()
