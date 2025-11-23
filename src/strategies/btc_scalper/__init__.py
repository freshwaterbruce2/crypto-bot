"""BTC scalper strategy package."""

from .runner import run_scalper
from .strategy import BTCScalper

__all__ = ["BTCScalper", "run_scalper"]
