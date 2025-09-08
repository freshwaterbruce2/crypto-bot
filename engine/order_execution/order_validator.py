#!/usr/bin/env python3
"""
Order Validator for Kraken Trading System
Validates order parameters and ensures compliance with Kraken requirements
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OrderValidator:
    """
    Validates order parameters against Kraken's requirements
    Ensures orders are properly formatted and within exchange limits
    """

    # Kraken order type mappings
    KRAKEN_ORDER_TYPES = {
        "market": "market",
        "limit": "limit",
        "stop-loss": "stop-loss",
        "take-profit": "take-profit",
        "take-profit-limit": "take-profit-limit",
        "stop-loss-limit": "stop-loss-limit",
        "trailing-stop": "trailing-stop",
        "trailing-stop-limit": "trailing-stop-limit",
    }

    # Minimum order sizes for different assets (Kraken requirements)
    MINIMUM_ORDER_SIZES = {
        "XLM": Decimal("12"),  # Stellar minimum
        "BTC": Decimal("0.0001"),  # Bitcoin minimum
        "ETH": Decimal("0.001"),  # Ethereum minimum
        "ADA": Decimal("10"),  # Cardano minimum
        "DOT": Decimal("0.1"),  # Polkadot minimum
        "LINK": Decimal("0.1"),  # Chainlink minimum
        "LTC": Decimal("0.01"),  # Litecoin minimum
        "XRP": Decimal("1"),  # Ripple minimum
    }

    # Maximum order sizes (conservative limits)
    MAXIMUM_ORDER_SIZES = {
        "XLM": Decimal("100000"),  # 100k XLM max
        "BTC": Decimal("10"),  # 10 BTC max
        "ETH": Decimal("100"),  # 100 ETH max
        "ADA": Decimal("1000000"),  # 1M ADA max
        "DOT": Decimal("10000"),  # 10k DOT max
        "LINK": Decimal("10000"),  # 10k LINK max
        "LTC": Decimal("1000"),  # 1k LTC max
        "XRP": Decimal("100000"),  # 100k XRP max
    }

    # Price precision requirements
    PRICE_PRECISION = {
        "XLM/USD": 6,  # 0.000001 precision
        "BTC/USD": 1,  # 0.1 precision
        "ETH/USD": 2,  # 0.01 precision
        "ADA/USD": 6,  # 0.000001 precision
        "DOT/USD": 4,  # 0.0001 precision
        "LINK/USD": 3,  # 0.001 precision
        "LTC/USD": 4,  # 0.0001 precision
        "XRP/USD": 6,  # 0.000001 precision
    }

    # Volume precision requirements
    VOLUME_PRECISION = {
        "XLM/USD": 8,  # 0.00000001 precision
        "BTC/USD": 8,  # 0.00000001 precision
        "ETH/USD": 8,  # 0.00000001 precision
        "ADA/USD": 8,  # 0.00000001 precision
        "DOT/USD": 8,  # 0.00000001 precision
        "LINK/USD": 8,  # 0.00000001 precision
        "LTC/USD": 8,  # 0.00000001 precision
        "XRP/USD": 8,  # 0.00000001 precision
    }

    def __init__(self):
        self.validation_errors: List[str] = []

    def validate_order_parameters(
        self, order_params: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Comprehensive order parameter validation

        Args:
            order_params: Order parameters to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate required fields
        required_fields = ["symbol", "side", "type", "quantity"]
        for field in required_fields:
            if field not in order_params:
                errors.append(f"Missing required field: {field}")

        if errors:
            return False, errors

        # Validate symbol format
        symbol_errors = self._validate_symbol(order_params["symbol"])
        errors.extend(symbol_errors)

        # Validate order side
        side_errors = self._validate_side(order_params["side"])
        errors.extend(side_errors)

        # Validate order type
        type_errors = self._validate_order_type(order_params["type"])
        errors.extend(type_errors)

        # Validate quantity
        quantity_errors = self._validate_quantity(
            order_params["quantity"], order_params["symbol"]
        )
        errors.extend(quantity_errors)

        # Validate price (if present and not None)
        if "price" in order_params and order_params["price"] is not None:
            price_errors = self._validate_price(
                order_params["price"], order_params["symbol"]
            )
            errors.extend(price_errors)

        # Validate conditional order parameters
        if order_params["type"] in [
            "stop-loss",
            "take-profit",
            "stop-loss-limit",
            "take-profit-limit",
        ]:
            conditional_errors = self._validate_conditional_parameters(order_params)
            errors.extend(conditional_errors)

        # Validate trailing stop parameters
        if "trailing" in order_params["type"]:
            trailing_errors = self._validate_trailing_parameters(order_params)
            errors.extend(trailing_errors)

        is_valid = len(errors) == 0
        return is_valid, errors

    def _validate_symbol(self, symbol: str) -> List[str]:
        """Validate trading symbol format"""
        errors = []

        if not isinstance(symbol, str):
            errors.append("Symbol must be a string")
            return errors

        if "/" not in symbol:
            errors.append("Symbol must contain '/' separator (e.g., 'XLM/USD')")
            return errors

        base, quote = symbol.split("/", 1)

        # Check if base asset is supported
        if base not in self.MINIMUM_ORDER_SIZES:
            errors.append(f"Base asset '{base}' not supported by Kraken")

        # Check if quote asset is USD (most common)
        if quote != "USD":
            errors.append(f"Quote asset '{quote}' not supported (only USD supported)")

        return errors

    def _validate_side(self, side: str) -> List[str]:
        """Validate order side"""
        errors = []

        if not isinstance(side, str):
            errors.append("Side must be a string")
            return errors

        if side.lower() not in ["buy", "sell"]:
            errors.append(f"Invalid side: {side}. Must be 'buy' or 'sell'")

        return errors

    def _validate_order_type(self, order_type: str) -> List[str]:
        """Validate order type"""
        errors = []

        if not isinstance(order_type, str):
            errors.append("Order type must be a string")
            return errors

        if order_type not in self.KRAKEN_ORDER_TYPES:
            supported_types = ", ".join(self.KRAKEN_ORDER_TYPES.keys())
            errors.append(
                f"Invalid order type: {order_type}. Supported: {supported_types}"
            )

        return errors

    def _validate_quantity(self, quantity: Any, symbol: str) -> List[str]:
        """Validate order quantity"""
        errors = []

        try:
            if isinstance(quantity, str):
                decimal_quantity = Decimal(quantity)
            elif isinstance(quantity, (int, float)):
                decimal_quantity = Decimal(str(quantity))
            elif isinstance(quantity, Decimal):
                decimal_quantity = quantity
            else:
                errors.append(f"Invalid quantity type: {type(quantity)}")
                return errors

            if decimal_quantity <= 0:
                errors.append("Quantity must be positive")
                return errors

            # Get base asset for minimum size validation
            if "/" in symbol:
                base_asset = symbol.split("/")[0]

                # Check minimum order size
                min_size = self.MINIMUM_ORDER_SIZES.get(base_asset)
                if min_size and decimal_quantity < min_size:
                    errors.append(
                        f"Quantity {decimal_quantity} below minimum {min_size} for {base_asset}"
                    )

                # Check maximum order size
                max_size = self.MAXIMUM_ORDER_SIZES.get(base_asset)
                if max_size and decimal_quantity > max_size:
                    errors.append(
                        f"Quantity {decimal_quantity} above maximum {max_size} for {base_asset}"
                    )

        except (InvalidOperation, ValueError):
            errors.append(f"Invalid quantity format: {quantity}")

        return errors

    def _validate_price(self, price: Any, symbol: str) -> List[str]:
        """Validate order price"""
        errors = []

        try:
            if isinstance(price, str):
                decimal_price = Decimal(price)
            elif isinstance(price, (int, float)):
                decimal_price = Decimal(str(price))
            elif isinstance(price, Decimal):
                decimal_price = price
            else:
                errors.append(f"Invalid price type: {type(price)}")
                return errors

            if decimal_price <= 0:
                errors.append("Price must be positive")
                return errors

            # Check price precision
            precision = self.PRICE_PRECISION.get(symbol)
            if precision is not None:
                price_str = str(decimal_price)
                if "." in price_str:
                    decimal_places = len(price_str.split(".")[-1])
                    if decimal_places > precision:
                        errors.append(
                            f"Price precision {decimal_places} exceeds maximum {precision} for {symbol}"
                        )

        except (InvalidOperation, ValueError):
            errors.append(f"Invalid price format: {price}")

        return errors

    def _validate_conditional_parameters(
        self, order_params: Dict[str, Any]
    ) -> List[str]:
        """Validate conditional order parameters"""
        errors = []

        order_type = order_params["type"]

        if order_type in ["stop-loss", "stop-loss-limit"]:
            if "stop_price" not in order_params:
                errors.append("Stop-loss orders require 'stop_price' parameter")

        if order_type in ["take-profit", "take-profit-limit"]:
            if "trigger_price" not in order_params:
                errors.append("Take-profit orders require 'trigger_price' parameter")

        if order_type in ["stop-loss-limit", "take-profit-limit"]:
            if "price" not in order_params:
                errors.append("Limit conditional orders require 'price' parameter")

        # Validate stop price logic
        if "stop_price" in order_params and "side" in order_params:
            side = order_params["side"].lower()
            if "price" in order_params:
                entry_price = order_params["price"]
                stop_price = order_params["stop_price"]

                if side == "buy" and stop_price >= entry_price:
                    errors.append("Buy stop-loss price must be below entry price")
                elif side == "sell" and stop_price <= entry_price:
                    errors.append("Sell stop-loss price must be above entry price")

        return errors

    def _validate_trailing_parameters(self, order_params: Dict[str, Any]) -> List[str]:
        """Validate trailing stop parameters"""
        errors = []

        if "trailing_distance" not in order_params:
            errors.append("Trailing stop orders require 'trailing_distance' parameter")

        if "trailing_distance" in order_params:
            distance = order_params["trailing_distance"]
            try:
                decimal_distance = Decimal(str(distance))
                if decimal_distance <= 0:
                    errors.append("Trailing distance must be positive")
                elif decimal_distance > 1:  # More than 100%
                    errors.append("Trailing distance seems unreasonably high (>100%)")
            except (InvalidOperation, ValueError):
                errors.append(f"Invalid trailing distance format: {distance}")

        return errors

    def format_price_for_kraken(self, price: Decimal, symbol: str) -> str:
        """
        Format price according to Kraken's precision requirements

        Args:
            price: Price to format
            symbol: Trading symbol

        Returns:
            Formatted price string
        """
        precision = self.PRICE_PRECISION.get(symbol, 6)  # Default to 6 decimal places

        # Round to appropriate precision
        rounded_price = price.quantize(Decimal("1e-{}".format(precision)))

        # Remove trailing zeros for cleaner output
        return (
            str(rounded_price).rstrip("0").rstrip(".")
            if "." in str(rounded_price)
            else str(rounded_price)
        )

    def format_volume_for_kraken(self, volume: Decimal, symbol: str) -> str:
        """
        Format volume according to Kraken's precision requirements

        Args:
            volume: Volume to format
            symbol: Trading symbol

        Returns:
            Formatted volume string
        """
        precision = self.VOLUME_PRECISION.get(symbol, 8)  # Default to 8 decimal places

        # Round to appropriate precision
        rounded_volume = volume.quantize(Decimal("1e-{}".format(precision)))

        # Remove trailing zeros for cleaner output
        return (
            str(rounded_volume).rstrip("0").rstrip(".")
            if "." in str(rounded_volume)
            else str(rounded_volume)
        )

    def map_to_kraken_symbol(self, symbol: str) -> str:
        """
        Map WebSocket symbol format to Kraken REST API format

        Args:
            symbol: WebSocket format symbol (e.g., 'XLM/USD')

        Returns:
            Kraken REST format symbol (e.g., 'XXLMZUSD')
        """
        if "/" not in symbol:
            return symbol

        base, quote = symbol.split("/", 1)

        # Kraken's REST API format: X{BASENAME}Z{QUOTENAME}
        if quote == "USD":
            return f"X{base}ZUSD"
        elif quote == "EUR":
            return f"X{base}ZEUR"
        elif quote == "CAD":
            return f"X{base}ZCAD"
        elif quote == "GBP":
            return f"X{base}ZGBP"
        elif quote == "JPY":
            return f"X{base}ZJPY"
        else:
            return f"X{base}Z{quote}"

    def validate_order_size(self, quantity: Decimal, symbol: str) -> bool:
        """
        Validate order size against Kraken's minimum requirements

        Args:
            quantity: Order quantity
            symbol: Trading symbol

        Returns:
            True if valid, False otherwise
        """
        if "/" in symbol:
            base_asset = symbol.split("/")[0]
            min_size = self.MINIMUM_ORDER_SIZES.get(base_asset)

            if min_size and quantity >= min_size:
                return True

        return False

    def get_minimum_order_size(self, symbol: str) -> Optional[Decimal]:
        """
        Get minimum order size for a symbol

        Args:
            symbol: Trading symbol

        Returns:
            Minimum order size or None if unknown
        """
        if "/" in symbol:
            base_asset = symbol.split("/")[0]
            return self.MINIMUM_ORDER_SIZES.get(base_asset)

        return None

    def get_maximum_order_size(self, symbol: str) -> Optional[Decimal]:
        """
        Get maximum order size for a symbol

        Args:
            symbol: Trading symbol

        Returns:
            Maximum order size or None if unknown
        """
        if "/" in symbol:
            base_asset = symbol.split("/")[0]
            return self.MAXIMUM_ORDER_SIZES.get(base_asset)

        return None
