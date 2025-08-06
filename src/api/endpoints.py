"""
Kraken API Endpoint Definitions
===============================

Comprehensive mapping of all Kraken REST API endpoints with their configurations,
parameters, and metadata for proper request handling and rate limiting.

Features:
- Complete endpoint definitions with HTTP methods and paths
- Parameter validation and type information
- Rate limiting weights and penalty points
- Endpoint categorization (public vs private)
- Request/response format specifications
- Integration with rate limiting system

Usage:
    from src.api.endpoints import get_endpoint_definition, KRAKEN_ENDPOINTS

    endpoint = get_endpoint_definition('Balance')
    print(f"Endpoint: {endpoint.path}, Method: {endpoint.method}")
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class HttpMethod(Enum):
    """HTTP methods for API requests."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class EndpointType(Enum):
    """Endpoint type classification for rate limiting."""
    PUBLIC = "public"
    PRIVATE = "private"
    WEBSOCKET = "websocket"


class ParameterType(Enum):
    """Parameter types for validation."""
    STRING = "string"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    LIST = "list"
    DICT = "dict"
    TIMESTAMP = "timestamp"
    CURRENCY = "currency"
    PAIR = "pair"


@dataclass
class ParameterDefinition:
    """
    Definition of an API parameter.

    Attributes:
        name: Parameter name
        param_type: Parameter type
        required: Whether parameter is required
        description: Parameter description
        default: Default value if any
        validation: Validation rules (regex, range, etc.)
        examples: Example values
    """
    name: str
    param_type: ParameterType
    required: bool = False
    description: str = ""
    default: Any = None
    validation: Optional[dict[str, Any]] = None
    examples: list[str] = field(default_factory=list)


@dataclass
class EndpointDefinition:
    """
    Complete definition of a Kraken API endpoint.

    Attributes:
        name: Endpoint name (used as identifier)
        path: API path (without base URL)
        method: HTTP method
        endpoint_type: Endpoint type (public/private)
        description: Endpoint description
        parameters: List of parameter definitions
        required_permissions: Required API key permissions
        rate_limit_weight: Weight for rate limiting (default 1)
        penalty_points: Penalty points for rate limiting
        has_age_penalty: Whether endpoint has age-based penalties
        response_format: Expected response format
        examples: Usage examples
        deprecated: Whether endpoint is deprecated
        version: API version
    """
    name: str
    path: str
    method: HttpMethod
    endpoint_type: EndpointType
    description: str = ""
    parameters: list[ParameterDefinition] = field(default_factory=list)
    required_permissions: set[str] = field(default_factory=set)
    rate_limit_weight: int = 1
    penalty_points: int = 1
    has_age_penalty: bool = False
    response_format: str = "json"
    examples: list[dict[str, Any]] = field(default_factory=list)
    deprecated: bool = False
    version: str = "0"

    def get_full_path(self, base_url: str = "https://api.kraken.com") -> str:
        """Get full URL path for this endpoint."""
        return f"{base_url.rstrip('/')}/{self.version}/{self.path.lstrip('/')}"

    def get_required_parameters(self) -> list[ParameterDefinition]:
        """Get list of required parameters."""
        return [param for param in self.parameters if param.required]

    def get_optional_parameters(self) -> list[ParameterDefinition]:
        """Get list of optional parameters."""
        return [param for param in self.parameters if not param.required]

    def validate_parameters(self, params: dict[str, Any]) -> list[str]:
        """
        Validate parameters against endpoint definition.

        Args:
            params: Parameters to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Check required parameters
        required_params = {param.name for param in self.get_required_parameters()}
        missing_params = required_params - set(params.keys())

        for missing in missing_params:
            errors.append(f"Missing required parameter: {missing}")

        # Validate parameter types and values
        param_definitions = {param.name: param for param in self.parameters}

        for param_name, param_value in params.items():
            if param_name not in param_definitions:
                errors.append(f"Unknown parameter: {param_name}")
                continue

            param_def = param_definitions[param_name]
            validation_error = self._validate_parameter_value(param_def, param_value)
            if validation_error:
                errors.append(f"Parameter '{param_name}': {validation_error}")

        return errors

    def _validate_parameter_value(self, param_def: ParameterDefinition, value: Any) -> Optional[str]:
        """
        Validate a single parameter value.

        Args:
            param_def: Parameter definition
            value: Value to validate

        Returns:
            Error message if validation fails, None otherwise
        """
        if value is None and param_def.required:
            return "Required parameter cannot be None"

        if value is None:
            return None  # Optional parameter can be None

        # Type validation
        if param_def.param_type == ParameterType.STRING and not isinstance(value, str):
            return f"Expected string, got {type(value).__name__}"
        elif param_def.param_type == ParameterType.INTEGER and not isinstance(value, int):
            return f"Expected integer, got {type(value).__name__}"
        elif param_def.param_type == ParameterType.FLOAT and not isinstance(value, (int, float)):
            return f"Expected float, got {type(value).__name__}"
        elif param_def.param_type == ParameterType.BOOLEAN and not isinstance(value, bool):
            return f"Expected boolean, got {type(value).__name__}"
        elif param_def.param_type == ParameterType.LIST and not isinstance(value, list):
            return f"Expected list, got {type(value).__name__}"
        elif param_def.param_type == ParameterType.DICT and not isinstance(value, dict):
            return f"Expected dict, got {type(value).__name__}"

        # Custom validation rules
        if param_def.validation:
            validation_rules = param_def.validation

            # String length validation
            if 'min_length' in validation_rules and isinstance(value, str):
                if len(value) < validation_rules['min_length']:
                    return f"String too short (min: {validation_rules['min_length']})"

            if 'max_length' in validation_rules and isinstance(value, str):
                if len(value) > validation_rules['max_length']:
                    return f"String too long (max: {validation_rules['max_length']})"

            # Numeric range validation
            if 'min_value' in validation_rules and isinstance(value, (int, float)):
                if value < validation_rules['min_value']:
                    return f"Value too small (min: {validation_rules['min_value']})"

            if 'max_value' in validation_rules and isinstance(value, (int, float)):
                if value > validation_rules['max_value']:
                    return f"Value too large (max: {validation_rules['max_value']})"

            # Allowed values validation
            if 'allowed_values' in validation_rules:
                if value not in validation_rules['allowed_values']:
                    return f"Invalid value. Allowed: {validation_rules['allowed_values']}"

        return None


# Define all Kraken API endpoints
KRAKEN_ENDPOINTS: dict[str, EndpointDefinition] = {

    # ====== PUBLIC ENDPOINTS ======

    "ServerTime": EndpointDefinition(
        name="ServerTime",
        path="public/Time",
        method=HttpMethod.GET,
        endpoint_type=EndpointType.PUBLIC,
        description="Get server time",
        rate_limit_weight=1,
        penalty_points=0,
        examples=[
            {"description": "Get current server time", "params": {}}
        ]
    ),

    "SystemStatus": EndpointDefinition(
        name="SystemStatus",
        path="public/SystemStatus",
        method=HttpMethod.GET,
        endpoint_type=EndpointType.PUBLIC,
        description="Get system status",
        rate_limit_weight=1,
        penalty_points=0,
        examples=[
            {"description": "Get system status", "params": {}}
        ]
    ),

    "AssetInfo": EndpointDefinition(
        name="AssetInfo",
        path="public/Assets",
        method=HttpMethod.GET,
        endpoint_type=EndpointType.PUBLIC,
        description="Get asset information",
        parameters=[
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                description="Comma delimited list of assets to get info on",
                examples=["XBT", "ETH", "XBT,ETH"]
            ),
            ParameterDefinition(
                name="aclass",
                param_type=ParameterType.STRING,
                description="Asset class",
                default="currency",
                validation={"allowed_values": ["currency"]}
            )
        ],
        rate_limit_weight=1,
        penalty_points=0
    ),

    "AssetPairs": EndpointDefinition(
        name="AssetPairs",
        path="public/AssetPairs",
        method=HttpMethod.GET,
        endpoint_type=EndpointType.PUBLIC,
        description="Get tradable asset pairs",
        parameters=[
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                description="Comma delimited list of asset pairs",
                examples=["XBTUSD", "ETHUSD", "XBTUSD,ETHUSD"]
            ),
            ParameterDefinition(
                name="info",
                param_type=ParameterType.STRING,
                description="Info to retrieve",
                default="info",
                validation={"allowed_values": ["info", "leverage", "fees", "margin"]}
            )
        ],
        rate_limit_weight=1,
        penalty_points=0
    ),

    "Ticker": EndpointDefinition(
        name="Ticker",
        path="public/Ticker",
        method=HttpMethod.GET,
        endpoint_type=EndpointType.PUBLIC,
        description="Get ticker information",
        parameters=[
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                required=True,
                description="Comma delimited list of asset pairs",
                examples=["XBTUSD", "ETHUSD"]
            )
        ],
        rate_limit_weight=1,
        penalty_points=0
    ),

    "OHLC": EndpointDefinition(
        name="OHLC",
        path="public/OHLC",
        method=HttpMethod.GET,
        endpoint_type=EndpointType.PUBLIC,
        description="Get OHLC data",
        parameters=[
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset pair",
                examples=["XBTUSD"]
            ),
            ParameterDefinition(
                name="interval",
                param_type=ParameterType.INTEGER,
                description="Time frame interval in minutes",
                default=1,
                validation={"allowed_values": [1, 5, 15, 30, 60, 240, 1440, 10080, 21600]}
            ),
            ParameterDefinition(
                name="since",
                param_type=ParameterType.INTEGER,
                description="Return committed OHLC data since given ID"
            )
        ],
        rate_limit_weight=1,
        penalty_points=0
    ),

    "OrderBook": EndpointDefinition(
        name="OrderBook",
        path="public/Depth",
        method=HttpMethod.GET,
        endpoint_type=EndpointType.PUBLIC,
        description="Get order book",
        parameters=[
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset pair",
                examples=["XBTUSD"]
            ),
            ParameterDefinition(
                name="count",
                param_type=ParameterType.INTEGER,
                description="Maximum number of asks/bids",
                default=100,
                validation={"min_value": 1, "max_value": 500}
            )
        ],
        rate_limit_weight=1,
        penalty_points=0
    ),

    "RecentTrades": EndpointDefinition(
        name="RecentTrades",
        path="public/Trades",
        method=HttpMethod.GET,
        endpoint_type=EndpointType.PUBLIC,
        description="Get recent trades",
        parameters=[
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset pair",
                examples=["XBTUSD"]
            ),
            ParameterDefinition(
                name="since",
                param_type=ParameterType.STRING,
                description="Return trade data since given ID"
            )
        ],
        rate_limit_weight=1,
        penalty_points=0
    ),

    "RecentSpreads": EndpointDefinition(
        name="RecentSpreads",
        path="public/Spread",
        method=HttpMethod.GET,
        endpoint_type=EndpointType.PUBLIC,
        description="Get recent spreads",
        parameters=[
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset pair",
                examples=["XBTUSD"]
            ),
            ParameterDefinition(
                name="since",
                param_type=ParameterType.INTEGER,
                description="Return spread data since given ID"
            )
        ],
        rate_limit_weight=1,
        penalty_points=0
    ),

    # ====== PRIVATE ENDPOINTS ======

    "Balance": EndpointDefinition(
        name="Balance",
        path="private/Balance",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get account balance",
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1,
        examples=[
            {"description": "Get account balance", "params": {}}
        ]
    ),

    "TradeBalance": EndpointDefinition(
        name="TradeBalance",
        path="private/TradeBalance",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get trade balance",
        parameters=[
            ParameterDefinition(
                name="aclass",
                param_type=ParameterType.STRING,
                description="Asset class",
                default="currency"
            ),
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                description="Base asset used to determine balance",
                default="ZUSD"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "OpenOrders": EndpointDefinition(
        name="OpenOrders",
        path="private/OpenOrders",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get open orders",
        parameters=[
            ParameterDefinition(
                name="trades",
                param_type=ParameterType.BOOLEAN,
                description="Whether or not to include trades related to position in output",
                default=False
            ),
            ParameterDefinition(
                name="userref",
                param_type=ParameterType.INTEGER,
                description="Restrict results to given user reference id"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "ClosedOrders": EndpointDefinition(
        name="ClosedOrders",
        path="private/ClosedOrders",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get closed orders",
        parameters=[
            ParameterDefinition(
                name="trades",
                param_type=ParameterType.BOOLEAN,
                description="Whether or not to include trades related to position in output",
                default=False
            ),
            ParameterDefinition(
                name="userref",
                param_type=ParameterType.INTEGER,
                description="Restrict results to given user reference id"
            ),
            ParameterDefinition(
                name="start",
                param_type=ParameterType.INTEGER,
                description="Starting unix timestamp or order tx ID of results (exclusive)"
            ),
            ParameterDefinition(
                name="end",
                param_type=ParameterType.INTEGER,
                description="Ending unix timestamp or order tx ID of results (inclusive)"
            ),
            ParameterDefinition(
                name="ofs",
                param_type=ParameterType.INTEGER,
                description="Result offset for pagination"
            ),
            ParameterDefinition(
                name="closetime",
                param_type=ParameterType.STRING,
                description="Which time to use to search",
                default="both",
                validation={"allowed_values": ["open", "close", "both"]}
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "QueryOrders": EndpointDefinition(
        name="QueryOrders",
        path="private/QueryOrders",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Query orders info",
        parameters=[
            ParameterDefinition(
                name="txid",
                param_type=ParameterType.STRING,
                required=True,
                description="Comma delimited list of transaction IDs to query info about"
            ),
            ParameterDefinition(
                name="trades",
                param_type=ParameterType.BOOLEAN,
                description="Whether or not to include trades related to position in output",
                default=False
            ),
            ParameterDefinition(
                name="userref",
                param_type=ParameterType.INTEGER,
                description="Restrict results to given user reference id"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "TradesHistory": EndpointDefinition(
        name="TradesHistory",
        path="private/TradesHistory",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get trades history",
        parameters=[
            ParameterDefinition(
                name="type",
                param_type=ParameterType.STRING,
                description="Type of trade",
                default="all",
                validation={"allowed_values": ["all", "any position", "closed position", "closing position", "no position"]}
            ),
            ParameterDefinition(
                name="trades",
                param_type=ParameterType.BOOLEAN,
                description="Whether or not to include trades related to position in output",
                default=False
            ),
            ParameterDefinition(
                name="start",
                param_type=ParameterType.INTEGER,
                description="Starting unix timestamp or trade tx ID of results (exclusive)"
            ),
            ParameterDefinition(
                name="end",
                param_type=ParameterType.INTEGER,
                description="Ending unix timestamp or trade tx ID of results (inclusive)"
            ),
            ParameterDefinition(
                name="ofs",
                param_type=ParameterType.INTEGER,
                description="Result offset for pagination"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=2,
        penalty_points=2
    ),

    "QueryTrades": EndpointDefinition(
        name="QueryTrades",
        path="private/QueryTrades",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Query trades info",
        parameters=[
            ParameterDefinition(
                name="txid",
                param_type=ParameterType.STRING,
                required=True,
                description="Comma delimited list of transaction IDs to query info about"
            ),
            ParameterDefinition(
                name="trades",
                param_type=ParameterType.BOOLEAN,
                description="Whether or not to include trades related to position in output",
                default=False
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "OpenPositions": EndpointDefinition(
        name="OpenPositions",
        path="private/OpenPositions",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get open positions",
        parameters=[
            ParameterDefinition(
                name="txid",
                param_type=ParameterType.STRING,
                description="Comma delimited list of txids to limit output to"
            ),
            ParameterDefinition(
                name="docalcs",
                param_type=ParameterType.BOOLEAN,
                description="Whether to include P&L calculations",
                default=False
            ),
            ParameterDefinition(
                name="consolidation",
                param_type=ParameterType.STRING,
                description="Consolidate positions by market/pair",
                default="market",
                validation={"allowed_values": ["market"]}
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "LedgersInfo": EndpointDefinition(
        name="LedgersInfo",
        path="private/Ledgers",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get ledgers info",
        parameters=[
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                description="Comma delimited list of assets to restrict output to",
                default="all"
            ),
            ParameterDefinition(
                name="aclass",
                param_type=ParameterType.STRING,
                description="Asset class",
                default="currency"
            ),
            ParameterDefinition(
                name="type",
                param_type=ParameterType.STRING,
                description="Type of ledger to retrieve",
                default="all",
                validation={"allowed_values": ["all", "deposit", "withdrawal", "trade", "margin"]}
            ),
            ParameterDefinition(
                name="start",
                param_type=ParameterType.INTEGER,
                description="Starting unix timestamp or ledger ID of results (exclusive)"
            ),
            ParameterDefinition(
                name="end",
                param_type=ParameterType.INTEGER,
                description="Ending unix timestamp or ledger ID of results (inclusive)"
            ),
            ParameterDefinition(
                name="ofs",
                param_type=ParameterType.INTEGER,
                description="Result offset for pagination"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=2,
        penalty_points=2
    ),

    "QueryLedgers": EndpointDefinition(
        name="QueryLedgers",
        path="private/QueryLedgers",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Query ledgers",
        parameters=[
            ParameterDefinition(
                name="id",
                param_type=ParameterType.STRING,
                required=True,
                description="Comma delimited list of ledger IDs to query info about"
            ),
            ParameterDefinition(
                name="trades",
                param_type=ParameterType.BOOLEAN,
                description="Whether or not to include trades related to position in output",
                default=False
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "TradeVolume": EndpointDefinition(
        name="TradeVolume",
        path="private/TradeVolume",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get trade volume",
        parameters=[
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                description="Comma delimited list of asset pairs to get fee info on"
            ),
            ParameterDefinition(
                name="fee-info",
                param_type=ParameterType.BOOLEAN,
                description="Whether or not to include fee info in results"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    # ====== TRADING ENDPOINTS ======

    "AddOrder": EndpointDefinition(
        name="AddOrder",
        path="private/AddOrder",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Add standard order",
        parameters=[
            ParameterDefinition(
                name="userref",
                param_type=ParameterType.INTEGER,
                description="User reference id (32-bit signed integer)"
            ),
            ParameterDefinition(
                name="ordertype",
                param_type=ParameterType.STRING,
                required=True,
                description="Order type",
                validation={"allowed_values": ["market", "limit", "stop-loss", "take-profit", "stop-loss-limit", "take-profit-limit", "settle-position"]}
            ),
            ParameterDefinition(
                name="type",
                param_type=ParameterType.STRING,
                required=True,
                description="Order direction",
                validation={"allowed_values": ["buy", "sell"]}
            ),
            ParameterDefinition(
                name="volume",
                param_type=ParameterType.STRING,
                required=True,
                description="Order quantity in terms of the base asset"
            ),
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset pair",
                examples=["XBTUSD", "ETHUSD"]
            ),
            ParameterDefinition(
                name="price",
                param_type=ParameterType.STRING,
                description="Price (optional, dependent upon ordertype)"
            ),
            ParameterDefinition(
                name="price2",
                param_type=ParameterType.STRING,
                description="Secondary price (optional, dependent upon ordertype)"
            ),
            ParameterDefinition(
                name="leverage",
                param_type=ParameterType.STRING,
                description="Amount of leverage desired (optional, default = none)"
            ),
            ParameterDefinition(
                name="oflags",
                param_type=ParameterType.STRING,
                description="Comma delimited list of order flags",
                validation={"allowed_values": ["post", "fcib", "fciq", "nompp", "viqc"]}
            ),
            ParameterDefinition(
                name="starttm",
                param_type=ParameterType.STRING,
                description="Scheduled start time (optional)"
            ),
            ParameterDefinition(
                name="expiretm",
                param_type=ParameterType.STRING,
                description="Expiration time (optional)"
            ),
            ParameterDefinition(
                name="validate",
                param_type=ParameterType.BOOLEAN,
                description="Validate inputs only, do not submit order"
            ),
            ParameterDefinition(
                name="close",
                param_type=ParameterType.DICT,
                description="Closing order to add to system when order gets filled"
            )
        ],
        required_permissions={"trade"},
        rate_limit_weight=1,
        penalty_points=1,
        has_age_penalty=False
    ),

    "AddOrderBatch": EndpointDefinition(
        name="AddOrderBatch",
        path="private/AddOrderBatch",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Add multiple orders",
        parameters=[
            ParameterDefinition(
                name="orders",
                param_type=ParameterType.LIST,
                required=True,
                description="List of order objects"
            ),
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset pair for all orders"
            ),
            ParameterDefinition(
                name="validate",
                param_type=ParameterType.BOOLEAN,
                description="Validate inputs only, do not submit orders"
            )
        ],
        required_permissions={"trade"},
        rate_limit_weight=5,
        penalty_points=5
    ),

    "EditOrder": EndpointDefinition(
        name="EditOrder",
        path="private/EditOrder",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Edit an order",
        parameters=[
            ParameterDefinition(
                name="txid",
                param_type=ParameterType.STRING,
                required=True,
                description="Transaction ID of order to edit"
            ),
            ParameterDefinition(
                name="userref",
                param_type=ParameterType.INTEGER,
                description="User reference id"
            ),
            ParameterDefinition(
                name="volume",
                param_type=ParameterType.STRING,
                description="Order quantity in terms of the base asset"
            ),
            ParameterDefinition(
                name="pair",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset pair"
            ),
            ParameterDefinition(
                name="price",
                param_type=ParameterType.STRING,
                description="Price"
            ),
            ParameterDefinition(
                name="price2",
                param_type=ParameterType.STRING,
                description="Secondary price"
            ),
            ParameterDefinition(
                name="oflags",
                param_type=ParameterType.STRING,
                description="Comma delimited list of order flags"
            ),
            ParameterDefinition(
                name="newuserref",
                param_type=ParameterType.INTEGER,
                description="New user reference id to replace current userref"
            ),
            ParameterDefinition(
                name="validate",
                param_type=ParameterType.BOOLEAN,
                description="Validate inputs only, do not submit order"
            )
        ],
        required_permissions={"trade"},
        rate_limit_weight=1,
        penalty_points=1,
        has_age_penalty=True
    ),

    "CancelOrder": EndpointDefinition(
        name="CancelOrder",
        path="private/CancelOrder",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Cancel open order",
        parameters=[
            ParameterDefinition(
                name="txid",
                param_type=ParameterType.STRING,
                required=True,
                description="Transaction ID of order to cancel"
            )
        ],
        required_permissions={"trade"},
        rate_limit_weight=1,
        penalty_points=1,
        has_age_penalty=True
    ),

    "CancelAllOrders": EndpointDefinition(
        name="CancelAllOrders",
        path="private/CancelAll",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Cancel all open orders",
        required_permissions={"trade"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "CancelAllOrdersAfter": EndpointDefinition(
        name="CancelAllOrdersAfter",
        path="private/CancelAllOrdersAfter",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Cancel all orders after X seconds",
        parameters=[
            ParameterDefinition(
                name="timeout",
                param_type=ParameterType.INTEGER,
                required=True,
                description="Duration (in seconds) to set/extend the timer by",
                validation={"min_value": 5, "max_value": 86400}
            )
        ],
        required_permissions={"trade"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "CancelOrderBatch": EndpointDefinition(
        name="CancelOrderBatch",
        path="private/CancelOrderBatch",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Cancel multiple orders",
        parameters=[
            ParameterDefinition(
                name="orders",
                param_type=ParameterType.LIST,
                required=True,
                description="List of order transaction IDs to cancel"
            )
        ],
        required_permissions={"trade"},
        rate_limit_weight=1,
        penalty_points=1,
        has_age_penalty=True
    ),

    # ====== FUNDING ENDPOINTS ======

    "DepositMethods": EndpointDefinition(
        name="DepositMethods",
        path="private/DepositMethods",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get deposit methods",
        parameters=[
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset being deposited"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "DepositAddresses": EndpointDefinition(
        name="DepositAddresses",
        path="private/DepositAddresses",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get deposit addresses",
        parameters=[
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset being deposited"
            ),
            ParameterDefinition(
                name="method",
                param_type=ParameterType.STRING,
                required=True,
                description="Name of the deposit method"
            ),
            ParameterDefinition(
                name="new",
                param_type=ParameterType.BOOLEAN,
                description="Whether to generate a new address",
                default=False
            )
        ],
        required_permissions={"query", "funding"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "DepositStatus": EndpointDefinition(
        name="DepositStatus",
        path="private/DepositStatus",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get status of recent deposits",
        parameters=[
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                description="Asset being deposited"
            ),
            ParameterDefinition(
                name="method",
                param_type=ParameterType.STRING,
                description="Name of the deposit method"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "WithdrawInfo": EndpointDefinition(
        name="WithdrawInfo",
        path="private/WithdrawInfo",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get withdrawal information",
        parameters=[
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset being withdrawn"
            ),
            ParameterDefinition(
                name="key",
                param_type=ParameterType.STRING,
                required=True,
                description="Withdrawal key name, as set up on your account"
            ),
            ParameterDefinition(
                name="amount",
                param_type=ParameterType.STRING,
                required=True,
                description="Amount to withdraw"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "Withdraw": EndpointDefinition(
        name="Withdraw",
        path="private/Withdraw",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Withdraw funds",
        parameters=[
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset being withdrawn"
            ),
            ParameterDefinition(
                name="key",
                param_type=ParameterType.STRING,
                required=True,
                description="Withdrawal key name, as set up on your account"
            ),
            ParameterDefinition(
                name="amount",
                param_type=ParameterType.STRING,
                required=True,
                description="Amount to withdraw"
            )
        ],
        required_permissions={"withdraw"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "WithdrawStatus": EndpointDefinition(
        name="WithdrawStatus",
        path="private/WithdrawStatus",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get status of recent withdrawals",
        parameters=[
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                description="Asset being withdrawn"
            ),
            ParameterDefinition(
                name="method",
                param_type=ParameterType.STRING,
                description="Name of the withdrawal method"
            )
        ],
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    "WithdrawCancel": EndpointDefinition(
        name="WithdrawCancel",
        path="private/WithdrawCancel",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Cancel withdrawal",
        parameters=[
            ParameterDefinition(
                name="asset",
                param_type=ParameterType.STRING,
                required=True,
                description="Asset being withdrawn"
            ),
            ParameterDefinition(
                name="refid",
                param_type=ParameterType.STRING,
                required=True,
                description="Withdrawal reference ID"
            )
        ],
        required_permissions={"withdraw"},
        rate_limit_weight=1,
        penalty_points=1
    ),

    # ====== WEBSOCKET TOKEN ENDPOINT ======

    "GetWebSocketsToken": EndpointDefinition(
        name="GetWebSocketsToken",
        path="private/GetWebSocketsToken",
        method=HttpMethod.POST,
        endpoint_type=EndpointType.PRIVATE,
        description="Get WebSocket authentication token",
        required_permissions={"query"},
        rate_limit_weight=1,
        penalty_points=1
    )
}


def get_endpoint_definition(endpoint_name: str) -> Optional[EndpointDefinition]:
    """
    Get endpoint definition by name.

    Args:
        endpoint_name: Name of the endpoint

    Returns:
        EndpointDefinition if found, None otherwise
    """
    return KRAKEN_ENDPOINTS.get(endpoint_name)


def get_public_endpoints() -> dict[str, EndpointDefinition]:
    """Get all public endpoints."""
    return {
        name: endpoint for name, endpoint in KRAKEN_ENDPOINTS.items()
        if endpoint.endpoint_type == EndpointType.PUBLIC
    }


def get_private_endpoints() -> dict[str, EndpointDefinition]:
    """Get all private endpoints."""
    return {
        name: endpoint for name, endpoint in KRAKEN_ENDPOINTS.items()
        if endpoint.endpoint_type == EndpointType.PRIVATE
    }


def get_trading_endpoints() -> dict[str, EndpointDefinition]:
    """Get trading-related endpoints."""
    trading_endpoint_names = {
        "AddOrder", "AddOrderBatch", "EditOrder", "CancelOrder",
        "CancelAllOrders", "CancelAllOrdersAfter", "CancelOrderBatch"
    }

    return {
        name: endpoint for name, endpoint in KRAKEN_ENDPOINTS.items()
        if name in trading_endpoint_names
    }


def get_endpoints_by_permission(permission: str) -> dict[str, EndpointDefinition]:
    """
    Get endpoints that require specific permission.

    Args:
        permission: Required permission (e.g., 'trade', 'query', 'withdraw')

    Returns:
        Dictionary of endpoints requiring the permission
    """
    return {
        name: endpoint for name, endpoint in KRAKEN_ENDPOINTS.items()
        if permission in endpoint.required_permissions
    }


def validate_endpoint_parameters(endpoint_name: str, params: dict[str, Any]) -> list[str]:
    """
    Validate parameters for a specific endpoint.

    Args:
        endpoint_name: Name of the endpoint
        params: Parameters to validate

    Returns:
        List of validation error messages
    """
    endpoint = get_endpoint_definition(endpoint_name)
    if not endpoint:
        return [f"Unknown endpoint: {endpoint_name}"]

    return endpoint.validate_parameters(params)


def get_endpoint_summary() -> dict[str, Any]:
    """
    Get summary statistics of all endpoints.

    Returns:
        Summary statistics dictionary
    """
    total_endpoints = len(KRAKEN_ENDPOINTS)
    public_count = len(get_public_endpoints())
    private_count = len(get_private_endpoints())
    trading_count = len(get_trading_endpoints())

    # Count by HTTP method
    method_counts = {}
    for endpoint in KRAKEN_ENDPOINTS.values():
        method = endpoint.method.value
        method_counts[method] = method_counts.get(method, 0) + 1

    # Count by permission
    permission_counts = {}
    for endpoint in KRAKEN_ENDPOINTS.values():
        for permission in endpoint.required_permissions:
            permission_counts[permission] = permission_counts.get(permission, 0) + 1

    return {
        'total_endpoints': total_endpoints,
        'public_endpoints': public_count,
        'private_endpoints': private_count,
        'trading_endpoints': trading_count,
        'method_distribution': method_counts,
        'permission_distribution': permission_counts,
        'deprecated_endpoints': sum(1 for ep in KRAKEN_ENDPOINTS.values() if ep.deprecated),
        'endpoints_with_age_penalty': sum(1 for ep in KRAKEN_ENDPOINTS.values() if ep.has_age_penalty)
    }
