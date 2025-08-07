#!/usr/bin/env python3
"""
BTC ADAPTIVE SCALPER - TRADES ANY MARKET CONDITION
===================================================
Adapts to current range and takes advantage of ultra-tight spread
"""

import json
import os
import time
from datetime import datetime

import ccxt
from dotenv import load_dotenv

load_dotenv()

class BTCAdaptiveScalper:
    def __init__(self):
        self.exchange = None
        self.symbol = 'BTC/USDT'
        self.position_file = 'btc_adaptive_position.json'
        self.position = None

        # ADAPTIVE PARAMETERS - Works in any range
        self.trade_amount = 20.0  # $20 per trade

        # ULTRA-MICRO TARGETS (0.0001% spread means ANY move is profit!)
        self.scalp_target = 0.0001   # 0.01% - Ultra-quick scalp
        self.micro_target = 0.0003   # 0.03% - Micro profit
        self.quick_target = 0.0005   # 0.05% - Quick profit
        self.stop_loss = -0.0005     # -0.05% - Ultra-tight stop

        # ADAPTIVE RANGE TRADING
        # If price is high, wait for small dips
        # If price is low, buy immediately
        self.adaptive_buy = True

        # Track performance
        self.trades_completed = 0
        self.total_profit = 0
        self.last_trade_time = 0

        self.load_position()

    def load_position(self):
        """Load saved position"""
        if os.path.exists(self.position_file):
            try:
                with open(self.position_file) as f:
                    self.position = json.load(f)
                    print(f"📂 Position: {self.position['amount']:.6f} BTC")
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
        """Get market data with momentum"""
        ticker = self.exchange.fetch_ticker(self.symbol)

        # Get 5-minute candles for momentum
        candles = self.exchange.fetch_ohlcv(self.symbol, '1m', limit=5)

        # Calculate momentum
        if len(candles) >= 2:
            momentum = (candles[-1][4] - candles[-2][4]) / candles[-2][4]  # Close to close
        else:
            momentum = 0

        return {
            'price': ticker['last'],
            'bid': ticker['bid'],
            'ask': ticker['ask'],
            'spread': (ticker['ask'] - ticker['bid']) / ticker['bid'],
            'high': ticker['high'],
            'low': ticker['low'],
            'range_position': (ticker['last'] - ticker['low']) / (ticker['high'] - ticker['low']) if ticker['high'] > ticker['low'] else 0.5,
            'momentum': momentum,
            'volume': ticker['baseVolume']
        }

    def adaptive_buy_decision(self, data, usdt_balance):
        """Adaptive buy logic - works at any range position"""
        if self.position:
            return False, "Already in position"

        if usdt_balance < self.trade_amount:
            return False, "Insufficient balance"

        # Cooldown between trades
        if time.time() - self.last_trade_time < 60:
            return False, f"Cooldown {60 - (time.time() - self.last_trade_time):.0f}s"

        # ADAPTIVE LOGIC BASED ON RANGE POSITION
        range_pos = data['range_position']

        # HIGH RANGE (80-100%) - Wait for micro-dips
        if range_pos > 0.8:
            # Only buy on negative momentum (small pullback)
            if data['momentum'] < -0.0001:  # 0.01% pullback
                return True, f"High range micro-dip: {data['momentum']:.4%}"
            return False, f"High range ({range_pos:.1%}), waiting for dip"

        # MID-HIGH RANGE (60-80%) - Buy on any dip
        elif range_pos > 0.6:
            if data['momentum'] <= 0:
                return True, f"Mid-high range, momentum {data['momentum']:.4%}"
            return False, "Mid-high range, waiting for flat/negative momentum"

        # MID RANGE (40-60%) - Buy freely
        elif range_pos > 0.4:
            return True, f"Mid range {range_pos:.1%}, good entry"

        # LOW RANGE (0-40%) - ALWAYS BUY
        else:
            return True, f"LOW RANGE {range_pos:.1%} - GREAT ENTRY!"

    def should_sell(self, data):
        """Ultra-quick sell logic for micro-profits"""
        if not self.position:
            return False, ""

        buy_price = self.position['price']
        current_price = data['bid']
        profit = (current_price - buy_price) / buy_price
        hold_time = (time.time() - self.position['time']) / 60

        # SCALP TARGET - Take tiny profits instantly!
        if profit >= self.scalp_target:
            return True, f"Scalp: {profit:.4%}"

        # MICRO TARGET
        if profit >= self.micro_target:
            return True, f"Micro: {profit:.4%}"

        # QUICK TARGET
        if profit >= self.quick_target:
            return True, f"Quick: {profit:.4%}"

        # Time-based exits - even break-even after time
        if hold_time > 10 and profit >= 0:
            return True, f"Time exit: {profit:.4%} @ {hold_time:.0f}min"

        # Stop loss
        if profit <= self.stop_loss:
            return True, f"Stop: {profit:.4%}"

        return False, f"Hold: {profit:.4%}"

    def place_buy(self, data):
        """Place buy order"""
        try:
            price = data['bid']
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
            print(f"   Cost: ${btc_amount * price:.2f}")

            return True

        except Exception as e:
            print(f"❌ Buy error: {e}")
            return False

    def place_sell(self, data):
        """Place sell order"""
        try:
            price = data['ask']
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
            print(f"   {emoji} Profit: {profit:.4%} = ${profit_usd:.3f}")
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
        """Main adaptive trading loop"""
        print("=" * 70)
        print("BTC ADAPTIVE SCALPER - TRADES ANY RANGE")
        print("=" * 70)
        print("Strategy: Ultra-micro profits 0.01-0.05%")
        print("Adapts to range position - trades high or low")
        print("=" * 70)

        self.initialize()

        # Get starting balance
        usdt, btc = self.get_balance()
        data = self.get_market_data()
        starting_value = usdt + (btc * data['price'])

        print(f"💰 Balance: ${usdt:.2f} USDT")
        print(f"📊 BTC: ${data['price']:,.2f} @ {data['range_position']:.1%} of range")
        print(f"🎯 Spread: {data['spread']:.4%}")

        loop_count = 0

        while True:
            try:
                loop_count += 1

                # Get fresh data
                data = self.get_market_data()
                usdt, btc = self.get_balance()
                current_value = usdt + (btc * data['price'])

                # Display every 2nd loop
                if loop_count % 2 == 1:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
                    print(f"BTC: ${data['price']:,.2f} | "
                          f"Range: {data['range_position']:.1%} | "
                          f"Mom: {data['momentum']:.4%} | "
                          f"Spread: {data['spread']:.4%}")
                    print(f"Balance: ${current_value:.2f} "
                          f"({((current_value/starting_value)-1)*100:+.3f}%)")

                # Trading logic
                if not self.position:
                    should_buy, reason = self.adaptive_buy_decision(data, usdt)
                    if should_buy:
                        print(f"\n🎯 BUY SIGNAL: {reason}")
                        self.place_buy(data)
                    elif loop_count % 6 == 1:
                        print(f"⏳ {reason}")
                else:
                    should_sell, reason = self.should_sell(data)
                    if should_sell:
                        print(f"\n🎯 SELL SIGNAL: {reason}")
                        self.place_sell(data)
                    elif loop_count % 2 == 1:
                        profit = (data['bid'] - self.position['price']) / self.position['price']
                        print(f"⏳ Holding: {profit:.4%}")

                # Fast checking for scalping
                time.sleep(5)

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
    bot = BTCAdaptiveScalper()
    bot.run()
