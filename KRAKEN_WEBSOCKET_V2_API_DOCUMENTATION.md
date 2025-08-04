# Kraken WebSocket V2 API Comprehensive Documentation

Based on official Kraken documentation from https://docs.kraken.com/

## Overview

Kraken WebSocket V2 API provides a complete redesign of the WebSocket interface with significant improvements over V1:

- **Improved Format**: Pair symbols use readable "BTC/USD" format
- **Standard Timestamps**: RFC3339 format (e.g., `2021-05-11T19:47:09.896860Z`)
- **Numerical Precision**: Prices and quantities published as numbers with engine precision
- **FIX-like Design**: Industry standard communication protocol patterns
- **Normalized JSON**: Consistent object structure with predictable dictionary keys

## WebSocket Endpoints

- **Public Data**: `wss://ws.kraken.com/v2`
- **Private/Authenticated Data**: `wss://ws-auth.kraken.com/v2`

## Authentication

### Token Generation (Required for Private Channels)

**REST API Endpoint**: `POST https://api.kraken.com/0/private/GetWebSocketsToken`

**Requirements**:
- API Key with "WebSocket interface - On" permission
- Standard Kraken REST API authentication (API-Key, API-Sign headers)

**Token Characteristics**:
- Must be used within 15 minutes of creation
- Does not expire once successful WebSocket connection is established
- Required for all private channels (executions, balances, level3, order management)

## Message Format Structure

All messages use JSON format with consistent structure:

```json
{
  "method": "subscribe|unsubscribe|add_order|cancel_order|etc",
  "params": {
    // Method-specific parameters
  },
  "req_id": 1234567890  // Optional client request identifier
}
```

## Public Data Streams

### 1. Trade Channel

**Purpose**: Real-time trade execution data
**Endpoint**: `wss://ws.kraken.com/v2`

**Subscription Request**:
```json
{
  "method": "subscribe",
  "params": {
    "channel": "trade",
    "symbol": ["BTC/USD", "MATIC/USD"],
    "snapshot": true
  },
  "req_id": 1234567890
}
```

**Trade Data Format**:
```json
{
  "channel": "trade",
  "type": "update",
  "data": [{
    "symbol": "MATIC/USD",
    "side": "sell",
    "price": 0.5117,
    "qty": 40.0,
    "ord_type": "market",
    "trade_id": 4665906,
    "timestamp": "2023-09-25T07:49:37.708706Z"
  }]
}
```

### 2. Book Channel (Level 2)

**Purpose**: Aggregated order book data with price levels
**Endpoint**: `wss://ws.kraken.com/v2`

**Subscription Options**:
- **Depth**: 10, 25, 100, 500, or 1000 (default: 10)
- **Snapshot**: Initial order book state (default: true)
- **Multiple Symbols**: Supported in single subscription

**Subscription Request**:
```json
{
  "method": "subscribe",
  "params": {
    "channel": "book",
    "symbol": ["ALGO/USD", "MATIC/USD"],
    "depth": 10
  }
}
```

**Book Snapshot Format**:
```json
{
  "channel": "book",
  "type": "snapshot",
  "data": [{
    "symbol": "MATIC/USD",
    "bids": [
      {"price": 0.5666, "qty": 4831.75496356},
      {"price": 0.5665, "qty": 6658.22734739}
    ],
    "asks": [
      {"price": 0.5668, "qty": 4410.79769741},
      {"price": 0.5669, "qty": 4655.40412487}
    ],
    "checksum": 2439117997
  }]
}
```

**Key Features**:
- CRC32 checksum for top 10 bids/asks data validation
- Real-time price/quantity updates
- Batched updates possible

### 3. Instrument Channel

**Purpose**: Reference data for active assets and tradeable pairs
**Endpoint**: `wss://ws.kraken.com/v2`

**Subscription Request**:
```json
{
  "method": "subscribe",
  "params": {
    "channel": "instrument",
    "snapshot": true
  }
}
```

**Data Provided**:
- Asset information (status, precision, margin rates)
- Trading pair details (symbol, base/quote currencies, trading status)
- Price/quantity increments and minimum order requirements

## Private/Authenticated Data Streams

### 1. Executions Channel

**Purpose**: Real-time order status and trade execution updates
**Endpoint**: `wss://ws-auth.kraken.com/v2`
**Authentication**: Required (session token)

**Subscription Request**:
```json
{
  "method": "subscribe",
  "params": {
    "channel": "executions",
    "snap_trades": false,
    "snap_orders": true,
    "order_status": true,
    "token": "your_session_token"
  }
}
```

**Subscription Options**:
- `snap_trades`: Get last 50 order fills (default: false)
- `snap_orders`: Include open orders (default: true)
- `order_status`: Stream all status transitions (default: true)
- `users`: For master accounts, stream events from all subaccounts

**Execution Update Format**:
```json
{
  "channel": "executions",
  "type": "update",
  "data": [{
    "order_id": "OK4GJX-KSTLS-7DZZO5",
    "order_userref": 3,
    "symbol": "BTC/USD",
    "order_qty": 0.005,
    "cum_cost": 0.0,
    "time_in_force": "GTC",
    "exec_type": "pending_new",
    "side": "sell",
    "order_type": "limit",
    "limit_price_type": "static",
    "limit_price": 26500.0,
    "order_status": "pending_new",
    "timestamp": "2023-09-22T10:33:05.709950Z"
  }],
  "sequence": 8
}
```

**Event Types**: `pending_new`, `new`, `trade`, `filled`, `canceled`, etc.

### 2. Balances Channel

**Purpose**: Real-time account balance updates and transaction tracking
**Endpoint**: `wss://ws-auth.kraken.com/v2`
**Authentication**: Required (session token)

**Subscription Request**:
```json
{
  "method": "subscribe",
  "params": {
    "channel": "balances",
    "snapshot": true,
    "token": "your_session_token"
  }
}
```

**Update Types**:
- **Snapshot**: Initial full account balance state
- **Update**: Real-time balance changes from transactions

**Transaction Types Tracked**:
- Deposit, Withdrawal, Trade, Margin, Staking, Transfer

**Features**:
- Tracks asset changes across wallet types (spot, earn)
- Includes transaction metadata (asset, amount, type, timestamp)

### 3. Level 3 Orders Channel

**Purpose**: Granular view of individual orders in the order book
**Endpoint**: `wss://ws-auth.kraken.com/v2`
**Authentication**: Required (session token)

**Subscription Limits**:
- Max 200 symbols per connection
- Rate limits: Standard (200/second), Pro (500/second)

**Depth Options**: 10, 100, or 1000 orders

**Features**:
- Individual order visibility with order ID, price, quantity, timestamp
- Real-time order events: `add`, `modify`, `delete`
- CRC32 checksum for data validation
- Excludes in-flight, unmatched, and hidden orders

## Order Management via WebSocket

### 1. Add Order

**Method**: `add_order`
**Endpoint**: `wss://ws-auth.kraken.com/v2`
**Authentication**: Required (session token)

**Basic Request Format**:
```json
{
  "method": "add_order",
  "params": {
    "order_type": "limit",
    "side": "buy",
    "limit_price": 26500.4,
    "order_qty": 1.2,
    "symbol": "BTC/USD",
    "token": "your_session_token"
  },
  "req_id": 1234567890
}
```

**Required Parameters**:
- `order_type`: limit, market, stop-loss, take-profit, trailing-stop, iceberg, settle-position
- `side`: "buy" or "sell"
- `order_qty`: Order quantity in base asset
- `symbol`: Trading pair (e.g., "BTC/USD")
- `token`: Authentication session token

**Optional Parameters**:
- `limit_price`: Price restriction for limit orders
- `time_in_force`: "gtc" (Good Till Cancelled), "gtd" (Good Till Date), "ioc" (Immediate or Cancel)
- `margin`: Enable margin trading
- `post_only`: Passive order placement (maker-only)
- `reduce_only`: Position size management
- `conditional`: Secondary order configuration
- `cl_ord_id`: Custom client order identifier

**Advanced Order Example (Trailing Stop)**:
```json
{
  "method": "add_order",
  "params": {
    "order_type": "trailing-stop",
    "side": "buy",
    "order_qty": 100,
    "symbol": "MATIC/USD",
    "triggers": {
      "reference": "last",
      "price": 1.0,
      "price_type": "pct"
    },
    "token": "your_session_token"
  }
}
```

### 2. Cancel Order

**Method**: `cancel_order`
**Endpoint**: `wss://ws-auth.kraken.com/v2`
**Authentication**: Required (session token)

**Request Format**:
```json
{
  "method": "cancel_order",
  "params": {
    "order_id": [
      "OM5CRX-N2HAL-GFGWE9",
      "OLUMT4-UTEGU-ZYM7E9"
    ],
    "token": "your_session_token"
  },
  "req_id": 123456789
}
```

**Cancellation Options**:
- `order_id`: Array of Kraken order identifiers
- `cl_ord_id`: Array of client order identifiers
- `order_userref`: Array of client user reference integers

**Features**:
- Multiple orders can be cancelled in single request
- Cancelled order details streamed on executions channel

### 3. Amend Order (Modify)

**Method**: `amend_order`
**Endpoint**: `wss://ws-auth.kraken.com/v2`
**Authentication**: Required (session token)

**Purpose**: Modify order parameters in-place without cancelling/recreating
**Benefits**: 
- Maintains queue priority where possible
- Preserves original order and client identifiers
- Enhanced performance over cancel/replace

### 4. Edit Order (Alternative Modify)

**Method**: `edit_order`
**Endpoint**: `wss://ws-auth.kraken.com/v2`
**Authentication**: Required (session token)

**Note**: This method cancels the original order and creates a new one with adjusted parameters. New `order_id` will be assigned. The `amend_order` method is recommended for better performance.

## Message Flow Patterns

### Subscription Response Format
```json
{
  "method": "subscribe",
  "req_id": 1234567890,
  "result": {
    "channel": "book",
    "snapshot": false,
    "symbol": "BTC/USD"
  },
  "success": true,
  "time_in": "2022-06-13T08:09:10.123456Z",
  "time_out": "2022-06-13T08:09:10.7890123"
}
```

### Error Handling

All responses include:
- `success`: Boolean indicating operation success
- `time_in`/`time_out`: Request processing timestamps
- `req_id`: Matches client-provided request identifier
- Error details in case of failures

### Heartbeat/Connection Management

- WebSocket connections should implement reconnection logic
- Monitor connection status through ping/pong or message flow
- Authenticated connections require valid session tokens
- Token refresh may be needed for long-running connections

## Rate Limiting

- **Standard Accounts**: 200 requests/second
- **Pro Accounts**: 500 requests/second
- **Level 3 Orders**: Max 200 symbols per connection
- Limits apply per connection and API key

## Best Practices

1. **Connection Management**:
   - Implement automatic reconnection with exponential backoff
   - Monitor WebSocket connection health
   - Handle token expiration gracefully

2. **Data Integrity**:
   - Use CRC32 checksums for order book validation
   - Implement sequence number tracking for executions
   - Handle out-of-order message delivery

3. **Performance Optimization**:
   - Subscribe only to required symbols and channels
   - Use appropriate depth levels for order book data
   - Batch operations where supported (e.g., multiple order cancellations)

4. **Error Recovery**:
   - Implement comprehensive error handling for all message types
   - Log and monitor API errors and connection issues
   - Have fallback mechanisms for critical trading operations

## Comparison with V1

WebSocket V2 improvements over V1:
- Cleaner, more consistent JSON structure
- Better timestamp formatting (RFC3339)
- Numerical precision preservation
- Simplified subscription patterns
- Enhanced order management capabilities
- FIX protocol-inspired design

V1 will be maintained but new features will be developed in V2.