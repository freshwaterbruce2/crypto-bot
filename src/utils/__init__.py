# C:\projects050625\projects\active\tool-crypto-trading-bot-2025\src\utils\__init__.py

from .custom_logging import configure_logging, log_trade_opportunity, logger
try:
    from src.rate_limiting import KrakenRateLimiter2025 as KrakenRateLimiter
except Exception:
    KrakenRateLimiter = None  # type: ignore

__all__ = [
    "logger",
    "configure_logging",
    "log_trade_opportunity",
    "KrakenRateLimiter",
]
