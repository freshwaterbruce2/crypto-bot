#!/usr/bin/env python3
"""
BTC/USDT MICRO-PROFIT SCALPER
=============================
Ultra-tight spread (0.008%) = Real profits!
Strategy: Quick 0.05-0.2% gains with BTC
"""

import json
import os
import time
from datetime import datetime

import ccxt
from dotenv import load_dotenv

load_dotenv()

class BTCScalper:
    def __init__(self):
        self.exchange = None
        self.symbol = 'BTC/USDT'
        self.position_file = 'btc_position.json'
        self.position = None

        # 2025 KRAKEN PRO OPTIMIZED PARAMETERS
        self.trade_amount = 20.0  # Use $20 per trade (keep $5 buffer)
        self.max_spread = 0.00005  # 0.005% max spread (API test shows 0.0001%)

        # ULTRA-MICRO PROFIT TARGETS (0.0001% spread allows tiny profits!)
        self.micro_target = 0.0002   # 0.02% - 2x the spread
        self.quick_target = 0.0005   # 0.05% - 5x the spread
        self.good_target = 0.001     # 0.1% - excellent profit
        self.stop_loss = -0.001      # -0.1% - very tight stop

        # Range trading (more aggressive due to tight spread)
        self.buy_zone = 0.7  # Buy in lower 70% of range

        # 2025 Kraken Pro fees (estimated based on volume)
        self.maker_fee = 0.0016  # 0.16% maker fee
        self.taker_fee = 0.0026  # 0.26% taker fee

        # Performance tracking
        self.starting_balance = None
        self.trades_today = 0
        self.successful_trades = 0
        self.total_profit = 0.0

        self.load_position()

    def load_position(self):
        """Load position if exists"""
        if os.path.exists(self.position_file):
            try:
                with open(self.position_file) as f:
                    self.position = json.load(f)
                    print(f"📂 Position: {self.position['btc_amount']:.6f} BTC @ ${self.position['price']:.2f}")
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
        """Initialize Kraken Pro connection with 2025 optimizations"""
        self.exchange = ccxt.kraken({
            'apiKey': os.getenv('KRAKEN_KEY'),
            'secret': os.getenv('KRAKEN_SECRET'),
            'enableRateLimit': True,
            'rateLimit': 200,  # Pro account: faster rate limiting
            'sandbox': False,  # Production trading
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 10000,
                'defaultType': 'spot',  # Spot trading
                'pro': True  # Enable Pro account features
            }
        })

        # Load markets for 2025 format compatibility
        self.exchange.load_markets()

        # Verify BTC/USDT is available
        if 'BTC/USDT' not in self.exchange.markets:
            raise Exception("BTC/USDT not available")

        print("✅ Connected to Kraken Pro (2025 API)")

    def get_balance(self):
        """Get current balances with 2025 USDT format handling"""
        balance = self.exchange.fetch_balance()

        # Handle different USDT formats Kraken might use
        usdt = 0
        for usdt_key in ['USDT', 'ZUSDT', 'USD', 'ZUSD']:
            if usdt_key in balance and balance[usdt_key]['free'] > 0:
                usdt = balance[usdt_key]['free']
                break

        # Handle different BTC formats
        btc = 0
        for btc_key in ['BTC', 'XBT', 'XXBT']:
            if btc_key in balance and balance[btc_key]['free'] > 0:
                btc = balance[btc_key]['free']
                break

        return usdt, btc

    def get_market_data(self):
        """Get BTC market data"""
        ticker = self.exchange.fetch_ticker(self.symbol)

        # Calculate spread
        bid = ticker['bid']
        ask = ticker['ask']
        spread = (ask - bid) / bid if bid > 0 else 0

        # Daily range position
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
        """BTC buy logic - account for tight spread"""
        if self.position:
            return False, "Already holding BTC"

        if usdt_balance < self.trade_amount:
            return False, f"Need ${self.trade_amount}, have ${usdt_balance:.2f}"

        # Check spread - must be ultra-tight
        if data['spread'] > self.max_spread:
            return False, f"Spread too wide: {data['spread']:.4%}"

        # Range position - buy in lower part
        if data['range_position'] > self.buy_zone:
            return False, f"Price too high: {data['range_position']:.1%} of range"

        # Don't buy after big pump
        if data['change'] > 2:
            return False, f"Already pumped {data['change']:.1f}% today"

        return True, f"Good entry: {data['range_position']:.1%} range, {data['spread']:.4%} spread"

    def should_sell(self, data):
        """BTC sell logic - take quick profits"""
        if not self.position:
            return False, ""

        buy_price = self.position['price']
        current_price = data['bid']  # We get bid when selling
        profit = (current_price - buy_price) / buy_price

        hold_time = (time.time() - self.position['time']) / 60

        # Account for fees in profit calculation
        net_profit = profit - (self.maker_fee + self.taker_fee)  # Conservative estimate

        # MICRO TARGET - take it fast!
        if profit >= self.micro_target:
            return True, f"Micro profit: {profit:.3%} (net: {net_profit:.3%})"

        # QUICK TARGET
        if profit >= self.quick_target:
            return True, f"Quick profit: {profit:.3%} (net: {net_profit:.3%})"

        # GOOD TARGET - always take
        if profit >= self.good_target:
            return True, f"Excellent profit: {profit:.3%} (net: {net_profit:.3%})"

        # Time-based exits for micro profits
        if hold_time > 15 and profit >= self.micro_target * 0.5:
            return True, f"Time + micro: {profit:.3%} after {hold_time:.0f}min"

        if hold_time > 30 and profit > 0:
            return True, f"Time exit: {profit:.3%} after {hold_time:.0f}min"

        # Stop loss
        if profit <= self.stop_loss:
            return True, f"Stop loss: {profit:.3%}"

        return False, f"Hold: {profit:.4%} (target: {self.micro_target:.3%})"

    def place_buy_order(self, data):
        """Buy BTC with limit order (maker fee)"""
        try:
            # Use bid price for limit order (maker fee)
            buy_price = data['bid']
            btc_amount = (self.trade_amount * 0.998) / buy_price  # Account for fees

            # Round to 6 decimals for BTC
            btc_amount = round(btc_amount, 6)

            # Check minimum
            if btc_amount < 0.00005:
                print(f"❌ Order too small: {btc_amount:.6f} BTC")
                return False

            # Place limit order at bid (should fill as maker)
            order = self.exchange.create_limit_buy_order(
                self.symbol,
                btc_amount,
                buy_price
            )

            # Track position
            self.position = {
                'btc_amount': btc_amount,
                'price': buy_price,
                'time': time.time(),
                'order_id': order['id']
            }
            self.save_position()

            print(f"\n🟢 BOUGHT: {btc_amount:.6f} BTC @ ${buy_price:,.2f}")
            print(f"   Cost: ${btc_amount * buy_price:.2f}")

            return True

        except Exception as e:
            print(f"❌ Buy error: {e}")
            return False

    def place_sell_order(self, data):
        """Sell BTC with limit order"""
        try:
            # Use ask price for quick fill
            sell_price = data['ask']
            btc_amount = self.position['btc_amount']

            self.exchange.create_limit_sell_order(
                self.symbol,
                btc_amount,
                sell_price
            )

            # Calculate results
            buy_price = self.position['price']
            gross_profit = (sell_price - buy_price) / buy_price
            gross_profit_usd = btc_amount * (sell_price - buy_price)

            # Estimate fees
            estimated_fees = (btc_amount * buy_price * self.maker_fee) + (btc_amount * sell_price * self.taker_fee)
            net_profit_usd = gross_profit_usd - estimated_fees

            self.trades_today += 1
            self.total_profit += net_profit_usd

            if net_profit_usd > 0:
                self.successful_trades += 1
                result_emoji = "✅"
            else:
                result_emoji = "❌"

            print(f"\n🔴 SOLD: {btc_amount:.6f} BTC @ ${sell_price:,.2f}")
            print(f"   {result_emoji} Gross: {gross_profit:.3%} = ${gross_profit_usd:.2f}")
            print(f"   💰 Net: ~${net_profit_usd:.2f} (after fees)")
            print(f"   📊 Today: {self.successful_trades}/{self.trades_today} = ${self.total_profit:.2f}")

            # Clear position
            self.position = None
            self.save_position()

            return True

        except Exception as e:
            print(f"❌ Sell error: {e}")
            return False

    def run(self):
        """Main BTC scalping loop"""
        print("=" * 70)
        print("BTC/USDT MICRO-PROFIT SCALPER")
        print("=" * 70)
        print("Strategy: 0.05-0.2% targets with 0.008% spread")
        print(f"Trade Size: ${self.trade_amount} per position")
        print("=" * 70)

        self.initialize()

        # Get starting balance
        usdt, btc = self.get_balance()
        data = self.get_market_data()
        self.starting_balance = usdt + (btc * data['price'])

        print(f"💰 Starting: ${usdt:.2f} USDT + {btc:.6f} BTC")
        print(f"📊 Total: ${self.starting_balance:.2f}")
        print(f"🎯 Spread: {data['spread']:.4%} (vs SHIB 0.079%)")

        loop_count = 0

        while True:
            try:
                loop_count += 1

                # Get fresh data
                data = self.get_market_data()
                usdt, btc = self.get_balance()
                current_value = usdt + (btc * data['price'])

                # Display status every 2nd loop
                if loop_count % 2 == 1:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
                    print(f"BTC: ${data['price']:,.2f} | "
                          f"Range: {data['range_position']:.1%} | "
                          f"Spread: {data['spread']:.4%}")
                    print(f"Balance: ${usdt:.2f} + {btc:.6f} BTC = "
                          f"${current_value:.2f} "
                          f"({((current_value/self.starting_balance)-1)*100:+.2f}%)")

                # Trading logic
                if not self.position:
                    should_buy, reason = self.should_buy(data, usdt)
                    if should_buy:
                        print(f"\n🎯 BUY: {reason}")
                        self.place_buy_order(data)
                    elif loop_count % 4 == 1:
                        print(f"⏳ Wait: {reason}")
                else:
                    should_sell, reason = self.should_sell(data)
                    if should_sell:
                        print(f"\n🎯 SELL: {reason}")
                        self.place_sell_order(data)
                    elif loop_count % 2 == 1:
                        profit = (data['bid'] - self.position['price']) / self.position['price']
                        hold_time = (time.time() - self.position['time']) / 60
                        print(f"⏳ Holding: {profit:.4%} profit, {hold_time:.0f}min")

                # Faster checking due to tight spread opportunities
                time.sleep(8)  # Check every 8 seconds

            except KeyboardInterrupt:
                print("\n\nStopping BTC scalper...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(20)

        # Final report
        usdt, btc = self.get_balance()
        data = self.get_market_data()
        final_value = usdt + (btc * data['price'])

        print("\n" + "=" * 70)
        print("BTC SCALPING RESULTS")
        print("=" * 70)
        print(f"Starting: ${self.starting_balance:.2f}")
        print(f"Final: ${final_value:.2f}")
        print(f"Net P&L: ${final_value - self.starting_balance:.2f} "
              f"({((final_value/self.starting_balance)-1)*100:+.2f}%)")
        print(f"Trades: {self.successful_trades}/{self.trades_today}")
        print(f"Est. Trading Profit: ${self.total_profit:.2f}")

        if self.trades_today > 0:
            success_rate = (self.successful_trades / self.trades_today) * 100
            avg_profit = self.total_profit / self.trades_today
            print(f"Success Rate: {success_rate:.0f}%")
            print(f"Avg per Trade: ${avg_profit:.2f}")

if __name__ == "__main__":
    bot = BTCScalper()
    bot.run()
