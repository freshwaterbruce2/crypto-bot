#!/usr/bin/env python3
"""CLI entry for the BTC/USDT micro-profit scalper."""

from src.strategies.btc_scalper.runner import run_scalper
from src.strategies.btc_scalper.strategy import BTCScalper


def main() -> None:
    bot = BTCScalper()
    run_scalper(bot)


if __name__ == "__main__":
    main()
