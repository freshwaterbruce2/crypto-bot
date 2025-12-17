"""
Unit tests for safe BTC buying logic using a mocked ccxt client.
"""

from unittest.mock import MagicMock

import ccxt
import pytest


BUY_AMOUNT_USD = 20
PAIR = "BTC/USDT"


def place_small_btc_order(exchange):
    """
    Execute the small BTC buy flow using the provided exchange client.

    The exchange client must provide ``fetch_balance``, ``fetch_ticker``, and
    ``create_market_buy_order`` methods. No real network calls are made because
    the caller is expected to pass a mock.
    """

    balance = exchange.fetch_balance()
    usdt_available = balance.get("USDT", {}).get("free", 0)

    ticker = exchange.fetch_ticker(PAIR)
    btc_amount = round(BUY_AMOUNT_USD / ticker["last"], 6)

    if usdt_available >= BUY_AMOUNT_USD:
        return exchange.create_market_buy_order(PAIR, btc_amount)

    return None


def test_buy_places_order_with_sufficient_balance(monkeypatch):
    """Ensure the buy logic uses the mocked exchange and places the order."""

    # Explicitly prevent accidental instantiation of a real client.
    monkeypatch.setattr(
        ccxt,
        "kraken",
        lambda *_, **__: pytest.fail("Real ccxt client must not be used"),
    )

    mock_exchange = MagicMock()
    mock_exchange.fetch_balance.return_value = {"USDT": {"free": 25}}
    mock_exchange.fetch_ticker.return_value = {"last": 40_000}
    mock_exchange.create_market_buy_order.return_value = {"id": "mock-order"}

    order = place_small_btc_order(mock_exchange)

    expected_amount = round(BUY_AMOUNT_USD / 40_000, 6)
    mock_exchange.fetch_balance.assert_called_once_with()
    mock_exchange.fetch_ticker.assert_called_once_with(PAIR)
    mock_exchange.create_market_buy_order.assert_called_once_with(
        PAIR, pytest.approx(expected_amount)
    )
    assert order == {"id": "mock-order"}


def test_buy_skips_order_with_insufficient_balance(monkeypatch):
    """Verify no order is placed when the USDT balance is too low."""

    # Explicitly prevent accidental instantiation of a real client.
    monkeypatch.setattr(
        ccxt,
        "kraken",
        lambda *_, **__: pytest.fail("Real ccxt client must not be used"),
    )

    mock_exchange = MagicMock()
    mock_exchange.fetch_balance.return_value = {"USDT": {"free": 5}}
    mock_exchange.fetch_ticker.return_value = {"last": 30_000}

    order = place_small_btc_order(mock_exchange)

    mock_exchange.fetch_balance.assert_called_once_with()
    mock_exchange.fetch_ticker.assert_called_once_with(PAIR)
    mock_exchange.create_market_buy_order.assert_not_called()
    assert order is None
