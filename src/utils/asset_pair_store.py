"""
Asset pair store and related utilities for the crypto trading bot.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class OrderVolumeTooLow(Exception):
    """Exception raised when order volume is too low for trading."""

    def __init__(self, symbol: str, volume: float, min_volume: float):
        self.symbol = symbol
        self.volume = volume
        self.min_volume = min_volume
        super().__init__(f"Order volume {volume} too low for {symbol}. Minimum: {min_volume}")


@dataclass
class AssetPairInfo:
    """Information about an asset trading pair."""
    symbol: str
    base_asset: str
    quote_asset: str
    min_order_size: float
    max_order_size: float
    price_precision: int
    volume_precision: int
    tick_size: float
    is_active: bool = True
    fees: dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class AssetPairStore:
    """
    Store and manage information about trading pairs and their properties.
    """

    def __init__(self):
        """Initialize the asset pair store."""
        self.pairs: dict[str, AssetPairInfo] = {}
        self.active_pairs: set[str] = set()
        self.base_assets: set[str] = set()
        self.quote_assets: set[str] = set()

        # Default configuration
        self.default_min_order_size = 10.0
        self.default_fees = {
            'maker': 0.0016,
            'taker': 0.0026
        }

        logger.info("AssetPairStore initialized")

    def add_pair(self, pair_info: AssetPairInfo) -> None:
        """
        Add a trading pair to the store.

        Args:
            pair_info: Information about the trading pair
        """
        symbol = pair_info.symbol
        self.pairs[symbol] = pair_info

        if pair_info.is_active:
            self.active_pairs.add(symbol)
            self.base_assets.add(pair_info.base_asset)
            self.quote_assets.add(pair_info.quote_asset)

        logger.debug(f"Added pair: {symbol}")

    def remove_pair(self, symbol: str) -> None:
        """
        Remove a trading pair from the store.

        Args:
            symbol: Symbol of the pair to remove
        """
        if symbol in self.pairs:
            del self.pairs[symbol]
            self.active_pairs.discard(symbol)
            logger.debug(f"Removed pair: {symbol}")

    def get_pair_info(self, symbol: str) -> Optional[AssetPairInfo]:
        """
        Get information about a trading pair.

        Args:
            symbol: Symbol of the trading pair

        Returns:
            AssetPairInfo if pair exists, None otherwise
        """
        return self.pairs.get(symbol)

    def is_pair_active(self, symbol: str) -> bool:
        """
        Check if a trading pair is active.

        Args:
            symbol: Symbol of the trading pair

        Returns:
            True if pair is active, False otherwise
        """
        return symbol in self.active_pairs

    def get_active_pairs(self) -> list[str]:
        """Get list of active trading pairs."""
        return list(self.active_pairs)

    def get_pairs_by_base_asset(self, base_asset: str) -> list[str]:
        """
        Get all pairs with a specific base asset.

        Args:
            base_asset: Base asset to filter by

        Returns:
            List of pair symbols
        """
        return [
            symbol for symbol, info in self.pairs.items()
            if info.base_asset == base_asset and info.is_active
        ]

    def get_pairs_by_quote_asset(self, quote_asset: str) -> list[str]:
        """
        Get all pairs with a specific quote asset.

        Args:
            quote_asset: Quote asset to filter by

        Returns:
            List of pair symbols
        """
        return [
            symbol for symbol, info in self.pairs.items()
            if info.quote_asset == quote_asset and info.is_active
        ]

    def validate_order_size(self, symbol: str, size: float) -> None:
        """
        Validate if order size meets minimum requirements.

        Args:
            symbol: Trading pair symbol
            size: Order size to validate

        Raises:
            OrderVolumeTooLow: If order size is too low
        """
        pair_info = self.get_pair_info(symbol)

        if pair_info is None:
            raise ValueError(f"Unknown trading pair: {symbol}")

        min_size = pair_info.min_order_size

        if size < min_size:
            raise OrderVolumeTooLow(symbol, size, min_size)

    def get_min_order_size(self, symbol: str) -> float:
        """
        Get minimum order size for a trading pair.

        Args:
            symbol: Trading pair symbol

        Returns:
            Minimum order size
        """
        pair_info = self.get_pair_info(symbol)

        if pair_info is None:
            return self.default_min_order_size

        return pair_info.min_order_size

    def get_trading_fees(self, symbol: str) -> dict[str, float]:
        """
        Get trading fees for a pair.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dictionary with maker and taker fees
        """
        pair_info = self.get_pair_info(symbol)

        if pair_info is None or not pair_info.fees:
            return self.default_fees

        return pair_info.fees

    def round_price(self, symbol: str, price: float) -> float:
        """
        Round price to appropriate precision for the pair.

        Args:
            symbol: Trading pair symbol
            price: Price to round

        Returns:
            Rounded price
        """
        pair_info = self.get_pair_info(symbol)

        if pair_info is None:
            return round(price, 8)  # Default precision

        return round(price, pair_info.price_precision)

    def round_volume(self, symbol: str, volume: float) -> float:
        """
        Round volume to appropriate precision for the pair.

        Args:
            symbol: Trading pair symbol
            volume: Volume to round

        Returns:
            Rounded volume
        """
        pair_info = self.get_pair_info(symbol)

        if pair_info is None:
            return round(volume, 8)  # Default precision

        return round(volume, pair_info.volume_precision)

    def get_tick_size(self, symbol: str) -> float:
        """
        Get tick size for a trading pair.

        Args:
            symbol: Trading pair symbol

        Returns:
            Tick size
        """
        pair_info = self.get_pair_info(symbol)

        if pair_info is None:
            return 0.01  # Default tick size

        return pair_info.tick_size

    def update_pair_status(self, symbol: str, is_active: bool) -> None:
        """
        Update the active status of a trading pair.

        Args:
            symbol: Trading pair symbol
            is_active: New active status
        """
        if symbol not in self.pairs:
            logger.warning(f"Attempt to update unknown pair: {symbol}")
            return

        self.pairs[symbol].is_active = is_active
        self.pairs[symbol].last_updated = datetime.now()

        if is_active:
            self.active_pairs.add(symbol)
            self.base_assets.add(self.pairs[symbol].base_asset)
            self.quote_assets.add(self.pairs[symbol].quote_asset)
        else:
            self.active_pairs.discard(symbol)

        logger.debug(f"Updated pair {symbol} active status to {is_active}")

    def get_all_base_assets(self) -> list[str]:
        """Get all unique base assets."""
        return list(self.base_assets)

    def get_all_quote_assets(self) -> list[str]:
        """Get all unique quote assets."""
        return list(self.quote_assets)

    def get_pair_statistics(self) -> dict[str, any]:
        """Get statistics about the pair store."""
        return {
            'total_pairs': len(self.pairs),
            'active_pairs': len(self.active_pairs),
            'base_assets': len(self.base_assets),
            'quote_assets': len(self.quote_assets),
            'pairs_by_base': {
                asset: len(self.get_pairs_by_base_asset(asset))
                for asset in self.base_assets
            },
            'pairs_by_quote': {
                asset: len(self.get_pairs_by_quote_asset(asset))
                for asset in self.quote_assets
            }
        }

    def load_from_exchange(self, exchange_info: dict[str, any]) -> None:
        """
        Load pair information from exchange data.

        Args:
            exchange_info: Exchange information dictionary
        """
        try:
            # Process exchange symbols
            for symbol, info in exchange_info.items():
                # Parse symbol parts
                if '/' in symbol:
                    base_asset, quote_asset = symbol.split('/')
                else:
                    # Handle other formats
                    continue

                # Extract trading limits
                min_order_size = float(info.get('limits', {}).get('amount', {}).get('min', self.default_min_order_size))
                max_order_size = float(info.get('limits', {}).get('amount', {}).get('max', float('inf')))

                # Extract precision
                price_precision = int(info.get('precision', {}).get('price', 8))
                volume_precision = int(info.get('precision', {}).get('amount', 8))

                # Extract fees
                fees = info.get('fees', self.default_fees)

                # Create pair info
                pair_info = AssetPairInfo(
                    symbol=symbol,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    min_order_size=min_order_size,
                    max_order_size=max_order_size,
                    price_precision=price_precision,
                    volume_precision=volume_precision,
                    tick_size=10 ** (-price_precision),
                    is_active=info.get('active', True),
                    fees=fees
                )

                self.add_pair(pair_info)

            logger.info(f"Loaded {len(self.pairs)} pairs from exchange")

        except Exception as e:
            logger.error(f"Error loading pairs from exchange: {e}")

    def save_to_file(self, filepath: str) -> None:
        """
        Save pair store to file.

        Args:
            filepath: Path to save file
        """
        try:
            # Convert to serializable format
            data = {
                'pairs': {
                    symbol: {
                        'symbol': info.symbol,
                        'base_asset': info.base_asset,
                        'quote_asset': info.quote_asset,
                        'min_order_size': info.min_order_size,
                        'max_order_size': info.max_order_size,
                        'price_precision': info.price_precision,
                        'volume_precision': info.volume_precision,
                        'tick_size': info.tick_size,
                        'is_active': info.is_active,
                        'fees': info.fees,
                        'last_updated': info.last_updated.isoformat()
                    }
                    for symbol, info in self.pairs.items()
                },
                'metadata': {
                    'total_pairs': len(self.pairs),
                    'active_pairs': len(self.active_pairs),
                    'saved_at': datetime.now().isoformat()
                }
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Pair store saved to {filepath}")

        except Exception as e:
            logger.error(f"Error saving pair store: {e}")

    def load_from_file(self, filepath: str) -> None:
        """
        Load pair store from file.

        Args:
            filepath: Path to load file
        """
        try:
            with open(filepath) as f:
                data = json.load(f)

            # Clear existing data
            self.pairs.clear()
            self.active_pairs.clear()
            self.base_assets.clear()
            self.quote_assets.clear()

            # Load pairs
            for _symbol, info_dict in data['pairs'].items():
                pair_info = AssetPairInfo(
                    symbol=info_dict['symbol'],
                    base_asset=info_dict['base_asset'],
                    quote_asset=info_dict['quote_asset'],
                    min_order_size=info_dict['min_order_size'],
                    max_order_size=info_dict['max_order_size'],
                    price_precision=info_dict['price_precision'],
                    volume_precision=info_dict['volume_precision'],
                    tick_size=info_dict['tick_size'],
                    is_active=info_dict['is_active'],
                    fees=info_dict['fees'],
                    last_updated=datetime.fromisoformat(info_dict['last_updated'])
                )

                self.add_pair(pair_info)

            logger.info(f"Pair store loaded from {filepath}")

        except Exception as e:
            logger.error(f"Error loading pair store: {e}")


# Global instance
asset_pair_store = AssetPairStore()
