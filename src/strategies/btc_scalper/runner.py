"""Execution loop for the BTC scalper."""

from __future__ import annotations

import time
from datetime import datetime

from src.strategies.btc_scalper.strategy import BTCScalper


def run_scalper(bot: BTCScalper) -> None:
    bot.log_startup()
    bot.initialize()
    usdt, btc, data, starting_balance = bot.start_balances()
    loop_count = 0

    while True:
        try:
            loop_count += 1
            data = bot.get_market_data()
            usdt, btc = bot.get_balance()
            current_value = usdt + (btc * data["price"])
            if loop_count % 2 == 1:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
                print(
                    f"BTC: ${data['price']:,.2f} | Range: {data['range_position']:.1%} | Spread: {data['spread']:.4%}"
                )
                pct = ((current_value / starting_balance) - 1) * 100
                print(
                    f"Balance: ${usdt:.2f} + {btc:.6f} BTC = ${current_value:.2f} ({pct:+.2f}%)"
                )
            if not bot.position:
                should_buy, reason = bot.should_buy(data, usdt)
                if should_buy:
                    print(f"\n\ud83c\udfaf BUY: {reason}")
                    bot.place_buy_order(data)
                elif loop_count % 4 == 1:
                    print(f"\u23f3 Wait: {reason}")
            else:
                should_sell, reason = bot.should_sell(data)
                if should_sell:
                    print(f"\n\ud83c\udfaf SELL: {reason}")
                    bot.place_sell_order(data)
                elif loop_count % 2 == 1:
                    profit = (data["bid"] - bot.position["price"]) / bot.position["price"]
                    hold_time = (time.time() - bot.position["time"]) / 60
                    print(f"\u23f3 Holding: {profit:.4%} profit, {hold_time:.0f}min")
            time.sleep(8)
        except KeyboardInterrupt:
            print("\n\nStopping BTC scalper...")
            break
        except Exception as exc:  # pragma: no cover - runtime guard
            print(f"\nError: {exc}")
            time.sleep(20)

    usdt, btc = bot.get_balance()
    data = bot.get_market_data()
    final_value = usdt + (btc * data["price"])
    print("\n" + "=" * 70)
    print("BTC SCALPING RESULTS")
    print("=" * 70)
    print(f"Starting: ${starting_balance:.2f}")
    print(f"Final: ${final_value:.2f}")
    print(f"Net P&L: ${final_value - starting_balance:.2f} ({((final_value / starting_balance) - 1) * 100:+.2f}%)")
    print(f"Trades: {bot.successful_trades}/{bot.trades_today}")
    print(f"Est. Trading Profit: ${bot.total_profit:.2f}")
    if bot.trades_today > 0:
        success_rate = (bot.successful_trades / bot.trades_today) * 100
        avg_profit = bot.total_profit / bot.trades_today
        print(f"Success Rate: {success_rate:.0f}%")
        print(f"Avg per Trade: ${avg_profit:.2f}")
