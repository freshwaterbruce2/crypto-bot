"""Core BTC scalper strategy primitives."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import ccxt
from dotenv import load_dotenv

load_dotenv()


class BTCScalper:
    def __init__(self):
        self.exchange = None
        self.symbol = "BTC/USDT"
        self.position_file = Path("btc_position.json")
        self.position: dict[str, Any] | None = None

        self.trade_amount = 20.0
        self.max_spread = 0.00005

        self.micro_target = 0.0002
        self.quick_target = 0.0005
        self.good_target = 0.001
        self.stop_loss = -0.001

        self.buy_zone = 0.7

        self.maker_fee = 0.0016
        self.taker_fee = 0.0026

        self.starting_balance: float | None = None
        self.trades_today = 0
        self.successful_trades = 0
        self.total_profit = 0.0

        self.load_position()

    def load_position(self) -> None:
        if self.position_file.exists():
            try:
                with self.position_file.open() as position_handle:
                    self.position = json.load(position_handle)
                    print(
                        f"\ud83d\uddc2 Position: {self.position['btc_amount']:.6f} BTC @ ${self.position['price']:.2f}"
                    )
            except Exception:
                pass

    def save_position(self) -> None:
        if self.position:
            with self.position_file.open("w") as position_handle:
                json.dump(self.position, position_handle)
        elif self.position_file.exists():
            self.position_file.unlink()

    def initialize(self) -> None:
        self.exchange = ccxt.kraken(
            {
                "apiKey": os.getenv("KRAKEN_KEY"),
                "secret": os.getenv("KRAKEN_SECRET"),
                "enableRateLimit": True,
                "rateLimit": 200,
                "sandbox": False,
                "options": {
                    "adjustForTimeDifference": True,
                    "recvWindow": 10000,
                    "defaultType": "spot",
                    "pro": True,
                },
            }
        )
        self.exchange.load_markets()
        if "BTC/USDT" not in self.exchange.markets:
            raise Exception("BTC/USDT not available")
        print("\u2705 Connected to Kraken Pro (2025 API)")

    def get_balance(self) -> tuple[float, float]:
        balance = self.exchange.fetch_balance()
        usdt = 0.0
        for usdt_key in ["USDT", "ZUSDT", "USD", "ZUSD"]:
            if usdt_key in balance and balance[usdt_key]["free"] > 0:
                usdt = balance[usdt_key]["free"]
                break

        btc = 0.0
        for btc_key in ["BTC", "XBT", "XXBT"]:
            if btc_key in balance and balance[btc_key]["free"] > 0:
                btc = balance[btc_key]["free"]
                break
        return usdt, btc

    def get_market_data(self) -> dict[str, Any]:
        ticker = self.exchange.fetch_ticker(self.symbol)
        bid = ticker["bid"]
        ask = ticker["ask"]
        spread = (ask - bid) / bid if bid > 0 else 0
        high = ticker["high"]
        low = ticker["low"]
        price = ticker["last"]
        range_position = (price - low) / (high - low) if high > low else 0.5
        return {
            "price": price,
            "bid": bid,
            "ask": ask,
            "spread": spread,
            "high": high,
            "low": low,
            "range_position": range_position,
            "change": ticker["percentage"],
        }

    def should_buy(self, data: dict[str, Any], usdt_balance: float) -> tuple[bool, str]:
        if self.position:
            return False, "Already holding BTC"
        if usdt_balance < self.trade_amount:
            return False, f"Need ${self.trade_amount}, have ${usdt_balance:.2f}"
        if data["spread"] > self.max_spread:
            return False, f"Spread too wide: {data['spread']:.4%}"
        if data["range_position"] > self.buy_zone:
            return False, f"Price too high: {data['range_position']:.1%} of range"
        if data["change"] > 2:
            return False, f"Already pumped {data['change']:.1f}% today"
        return True, f"Good entry: {data['range_position']:.1%} range, {data['spread']:.4%} spread"

    def should_sell(self, data: dict[str, Any]) -> tuple[bool, str]:
        if not self.position:
            return False, ""
        buy_price = self.position["price"]
        current_price = data["bid"]
        profit = (current_price - buy_price) / buy_price
        hold_time = (time.time() - self.position["time"]) / 60
        net_profit = profit - (self.maker_fee + self.taker_fee)
        if profit >= self.micro_target:
            return True, f"Micro profit: {profit:.3%} (net: {net_profit:.3%})"
        if profit >= self.quick_target:
            return True, f"Quick profit: {profit:.3%} (net: {net_profit:.3%})"
        if profit >= self.good_target:
            return True, f"Excellent profit: {profit:.3%} (net: {net_profit:.3%})"
        if hold_time > 15 and profit >= self.micro_target * 0.5:
            return True, f"Time + micro: {profit:.3%} after {hold_time:.0f}min"
        if hold_time > 30 and profit > 0:
            return True, f"Time exit: {profit:.3%} after {hold_time:.0f}min"
        if profit <= self.stop_loss:
            return True, f"Stop loss: {profit:.3%}"
        return False, f"Hold: {profit:.4%} (target: {self.micro_target:.3%})"

    def place_buy_order(self, data: dict[str, Any]) -> bool:
        try:
            buy_price = data["bid"]
            btc_amount = (self.trade_amount * 0.998) / buy_price
            btc_amount = round(btc_amount, 6)
            if btc_amount < 0.00005:
                print(f"\u274c Order too small: {btc_amount:.6f} BTC")
                return False
            order = self.exchange.create_limit_buy_order(self.symbol, btc_amount, buy_price)
            self.position = {
                "btc_amount": btc_amount,
                "price": buy_price,
                "time": time.time(),
                "order_id": order["id"],
            }
            self.save_position()
            print(f"\n\ud83d\udfe2 BOUGHT: {btc_amount:.6f} BTC @ ${buy_price:,.2f}")
            print(f"   Cost: ${btc_amount * buy_price:.2f}")
            return True
        except Exception as exc:  # pragma: no cover - API call
            print(f"\u274c Buy error: {exc}")
            return False

    def place_sell_order(self, data: dict[str, Any]) -> bool:
        try:
            sell_price = data["ask"]
            btc_amount = self.position["btc_amount"]
            self.exchange.create_limit_sell_order(self.symbol, btc_amount, sell_price)
            buy_price = self.position["price"]
            gross_profit = (sell_price - buy_price) / buy_price
            gross_profit_usd = btc_amount * (sell_price - buy_price)
            estimated_fees = (btc_amount * buy_price * self.maker_fee) + (btc_amount * sell_price * self.taker_fee)
            net_profit_usd = gross_profit_usd - estimated_fees
            self.trades_today += 1
            self.total_profit += net_profit_usd
            result_emoji = "\u2705" if net_profit_usd > 0 else "\u274c"
            print(f"\n\ud83d\udd34 SOLD: {btc_amount:.6f} BTC @ ${sell_price:,.2f}")
            print(f"   {result_emoji} Gross: {gross_profit:.3%} = ${gross_profit_usd:.2f}")
            print(f"   \ud83d\udcb0 Net: ~${net_profit_usd:.2f} (after fees)")
            print(
                f"   \ud83d\udccb Today: {self.successful_trades}/{self.trades_today} = ${self.total_profit:.2f}"
            )
            self.position = None
            self.save_position()
            return True
        except Exception as exc:  # pragma: no cover - API call
            print(f"\u274c Sell error: {exc}")
            return False

    def log_startup(self) -> None:
        print("=" * 70)
        print("BTC/USDT MICRO-PROFIT SCALPER")
        print("=" * 70)
        print("Strategy: 0.05-0.2% targets with 0.008% spread")
        print(f"Trade Size: ${self.trade_amount} per position")
        print("=" * 70)

    def start_balances(self) -> tuple[float, float, dict[str, Any], float]:
        usdt, btc = self.get_balance()
        data = self.get_market_data()
        starting_balance = usdt + (btc * data["price"])
        print(f"\ud83d\udcb0 Starting: ${usdt:.2f} USDT + {btc:.6f} BTC")
        print(f"\ud83d\udcc8 Total: ${starting_balance:.2f}")
        print(f"\ud83c\udfaf Spread: {data['spread']:.4%} (vs SHIB 0.079%)")
        self.starting_balance = starting_balance
        return usdt, btc, data, starting_balance
