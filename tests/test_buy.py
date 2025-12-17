"""Safe unit tests for buy logic using a mocked ccxt-like client."""

from unittest.mock import MagicMock

import pytest


def buy_btc(exchange, spend_usd: float = 20) -> dict:
    """Execute a BTC/USDT market buy using the provided exchange client.

    The function mirrors the previous test script's behavior but relies on the
    supplied client for all exchange interactions. The caller is responsible
    for providing a mock so tests never hit real network endpoints.
    """

    balance = exchange.fetch_balance()
    usdt = balance.get("USDT", {}).get("free", 0)
    ticker = exchange.fetch_ticker("BTC/USDT")
    btc_amount = round(spend_usd / ticker["last"], 6)

    if usdt < spend_usd:
        raise ValueError("Not enough USDT to place order")

    return exchange.create_market_buy_order("BTC/USDT", btc_amount)


def test_buy_places_order_with_sufficient_balance():
    mock_exchange = MagicMock()
    mock_exchange.fetch_balance.return_value = {"USDT": {"free": 50}}
    mock_exchange.fetch_ticker.return_value = {"last": 25_000}
    mock_exchange.create_market_buy_order.return_value = {"id": "mock-order-id"}

    order = buy_btc(mock_exchange)

    expected_amount = round(20 / 25_000, 6)
    assert order == {"id": "mock-order-id"}
    mock_exchange.fetch_balance.assert_called_once_with()
    mock_exchange.fetch_ticker.assert_called_once_with("BTC/USDT")
    mock_exchange.create_market_buy_order.assert_called_once_with(
        "BTC/USDT", expected_amount
    )


def test_buy_rejects_when_balance_is_too_low():
    mock_exchange = MagicMock()
    mock_exchange.fetch_balance.return_value = {"USDT": {"free": 5}}
    mock_exchange.fetch_ticker.return_value = {"last": 20_000}

    with pytest.raises(ValueError, match="Not enough USDT"):
        buy_btc(mock_exchange)

    mock_exchange.create_market_buy_order.assert_not_called()
