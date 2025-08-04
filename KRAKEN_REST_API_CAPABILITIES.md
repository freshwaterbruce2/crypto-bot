# Kraken Spot REST API Capabilities Documentation

Based on official Kraken documentation (https://docs.kraken.com/api/)

## API Base Structure

**Base URL:** `https://api.kraken.com`  
**API Version:** `/0/`  
**Endpoint Structure:**
- Public endpoints: `/0/public/`
- Private endpoints: `/0/private/`

## 1. Public Endpoints Available

### System Status and Server Time
- **System Status:** `GET /0/public/SystemStatus`
- **Server Time:** `GET /0/public/Time`

### Asset Information and Trading Pairs
- **Assets:** `GET /0/public/Assets`
  - Returns all available currencies with properties
  - Parameters: Optional asset list
  - Response: Currency metadata including decimals, display decimals

- **Asset Pairs:** `GET /0/public/AssetPairs`
  - Returns tradable asset pairs
  - Parameters: Optional pair list
  - Response: Trading pair information including fees, margins, ordermin

### Market Data Endpoints

#### Ticker Data
- **Endpoint:** `GET /0/public/Ticker`
- **Parameters:** 
  - `pair` (optional): Comma-delimited list of asset pairs
- **Example:** `https://api.kraken.com/0/public/Ticker?pair=XBTUSD`
- **Response:** Current ticker information including bid/ask prices, volumes, VWAP

#### OHLC Data (Candlestick)
- **Endpoint:** `GET /0/public/OHLC`
- **Parameters:**
  - `pair` (required): Asset pair
  - `interval` (optional): Time frame interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
  - `since` (optional): Return committed OHLC data since given ID
- **Response:** Array of OHLC data with timestamps

#### Order Book Data
- **Endpoint:** `GET /0/public/Depth`
- **Parameters:**
  - `pair` (required): Asset pair
  - `count` (optional): Maximum number of asks/bids (default: 100)
- **Example:** `https://api.kraken.com/0/public/Depth?pair=ETHUSD&count=5`
- **Response:** Arrays of bid/ask orders with price levels and volumes

#### Recent Trades
- **Endpoint:** `GET /0/public/Trades`
- **Parameters:**
  - `pair` (required): Asset pair
  - `since` (optional): Return trade data since given ID
- **Response:** Array of recent trades with price, volume, time, side

#### Spread Data
- **Endpoint:** `GET /0/public/Spread`
- **Parameters:**
  - `pair` (required): Asset pair
  - `since` (optional): Return spread data since given ID
- **Response:** Array of bid/ask spreads with timestamps

### Rate Limits and Requirements
- No authentication required for public endpoints
- No specific rate limits mentioned for public endpoints
- Can be accessed directly via web browser

## 2. Private/Authenticated Endpoints

### Account Balance and Trading Balance
- **Account Balance:** `POST /0/private/Balance`
  - **Required Permission:** Query Funds
  - **Response:** Array of asset names and balance amounts

- **Trade Balance:** `POST /0/private/TradeBalance`
  - **Required Permission:** Query Funds
  - **Parameters:** `asset` (optional, default: ZUSD)
  - **Response:** Account trade balance info including equity, margin, P&L

### Open Orders and Order History
- **Open Orders:** `POST /0/private/OpenOrders`
  - **Required Permission:** Query Open Orders & Trades
  - **Parameters:** `trades` (optional), `userref` (optional)
  - **Response:** Array of open order info

- **Closed Orders:** `POST /0/private/ClosedOrders`
  - **Required Permission:** Query Closed Orders & Trades
  - **Parameters:** 
    - `trades` (optional): Include trades in output
    - `userref` (optional): Restrict results to given user reference ID
    - `start` (optional): Starting unix timestamp
    - `end` (optional): Ending unix timestamp
    - `ofs` (optional): Result offset
    - `closetime` (optional): Which time to use (open, close, both)

- **Query Orders:** `POST /0/private/QueryOrders`
  - **Required Permission:** Query Open/Closed Orders & Trades
  - **Parameters:**
    - `trades` (optional): Include trades in output
    - `userref` (optional): Restrict results to given user reference ID
    - `txid` (required): Comma-delimited list of transaction IDs

### Trade History and Position Data
- **Trades History:** `POST /0/private/TradesHistory`
  - **Required Permission:** Query Closed Orders & Trades
  - **Parameters:**
    - `type` (optional): Type of trade (all, any position, closed position, closing position, no position)
    - `trades` (optional): Include trades related to position in output
    - `start` (optional): Starting unix timestamp
    - `end` (optional): Ending unix timestamp
    - `ofs` (optional): Result offset

- **Query Trades:** `POST /0/private/QueryTrades`
  - **Required Permission:** Query Closed Orders & Trades
  - **Parameters:**
    - `txid` (required): Comma-delimited list of transaction IDs
    - `trades` (optional): Include trades related to position in output

- **Open Positions:** `POST /0/private/OpenPositions`
  - **Required Permission:** Query Open Orders & Trades
  - **Parameters:**
    - `txid` (optional): Comma-delimited list of transaction IDs
    - `docalcs` (optional): Include profit/loss calculations

### Account Ledger and Transaction History
- **Ledgers:** `POST /0/private/Ledgers`
  - **Required Permission:** Query Ledger Entries
  - **Parameters:**
    - `asset` (optional): Comma-delimited list of assets to restrict output
    - `aclass` (optional): Asset class (currency)
    - `type` (optional): Type of ledger to retrieve
    - `start` (optional): Starting unix timestamp
    - `end` (optional): Ending unix timestamp
    - `ofs` (optional): Result offset

- **Query Ledgers:** `POST /0/private/QueryLedgers`
  - **Required Permission:** Query Ledger Entries
  - **Parameters:**
    - `id` (required): Comma-delimited list of ledger IDs

### Trading Volume
- **Trade Volume:** `POST /0/private/TradeVolume`
  - **Required Permission:** Query Funds
  - **Parameters:**
    - `pair` (optional): Comma-delimited list of asset pairs
  - **Response:** Currency volume discount and fee tier info

## 3. Order Management via REST

### Order Placement
- **Add Order:** `POST /0/private/AddOrder`
  - **Required Permission:** Create & Modify Orders
  - **Parameters:**
    - `ordertype` (required): market, limit, stop-loss, take-profit, stop-loss-limit, take-profit-limit, settle-position
    - `type` (required): buy or sell
    - `volume` (required): Order quantity in terms of the base asset
    - `pair` (required): Asset pair
    - `price` (optional): Price (required for limit orders)
    - `price2` (optional): Secondary price (for stop-loss orders)
    - `leverage` (optional): Amount of leverage desired
    - `oflags` (optional): Order flags (viqc, fcib, fciq, nompp, post)
    - `starttm` (optional): Scheduled start time
    - `expiretm` (optional): Expiration time
    - `userref` (optional): User reference ID
    - `validate` (optional): Validate inputs only, do not submit order
    - `close` (optional): Close position info
    - `timeinforce` (optional): Time in force (IOC, GTC)

- **Add Order Batch:** `POST /0/private/AddOrderBatch`
  - **Required Permission:** Create & Modify Orders
  - **Parameters:** Array of orders with same parameters as AddOrder

### Order Cancellation and Modification
- **Cancel Order:** `POST /0/private/CancelOrder`
  - **Required Permission:** Create & Modify Orders
  - **Parameters:**
    - `txid` (required): Transaction ID

- **Cancel All Orders:** `POST /0/private/CancelAll`
  - **Required Permission:** Create & Modify Orders

- **Cancel All Orders After:** `POST /0/private/CancelAllOrdersAfter`
  - **Required Permission:** Create & Modify Orders
  - **Parameters:**
    - `timeout` (required): Duration in seconds to cancel all orders

- **Edit Order:** `POST /0/private/EditOrder`
  - **Required Permission:** Create & Modify Orders
  - **Parameters:**
    - `txid` (required): Transaction ID
    - `volume` (optional): Order quantity in terms of the base asset
    - `price` (optional): Price
    - `price2` (optional): Secondary price
    - `oflags` (optional): Order flags
    - `newuserref` (optional): New user reference ID
    - `validate` (optional): Validate inputs only

### Batch Operations
- **Cancel Order Batch:** `POST /0/private/CancelOrderBatch`
  - **Required Permission:** Create & Modify Orders
  - **Parameters:**
    - `orders` (required): Array of transaction IDs

### Order Status Queries
- **Query Orders:** `POST /0/private/QueryOrders` (detailed above)
- **Open Orders:** `POST /0/private/OpenOrders` (detailed above)

## 4. Authentication Requirements

### API Key and Secret Setup
1. **Create API Key:** Generate via Kraken account settings
2. **Permissions Required:**
   - **Query Funds:** For balance and trade balance endpoints
   - **Query Open Orders & Trades:** For open orders and positions
   - **Query Closed Orders & Trades:** For order/trade history
   - **Query Ledger Entries:** For ledger access
   - **Create & Modify Orders:** For trading operations
   - **Deposit Funds:** For funding operations
   - **Withdraw Funds:** For withdrawal operations
   - **Export Data:** For data export

### Signature Generation Process
The API-Sign header value is generated using:
```
HMAC-SHA512 of (URI path + SHA256(nonce + POST data)) and base64 decoded secret API key
```

**Step-by-step process:**
1. Decode the API secret (private key) from base64
2. Calculate SHA256 hash of (nonce + POST data)
3. Concatenate URI path with the SHA256 hash
4. Calculate HMAC-SHA512 of the concatenated string using decoded secret as key
5. Encode the HMAC result to base64

### Required Headers
- **API-Key:** Your public API key
- **API-Sign:** Generated signature

### Required Parameters
- **nonce:** Always increasing unsigned 64-bit integer (typically millisecond timestamp)
- **otp:** One-time password (required only if 2FA is enabled for API)

### Nonce Requirements and Best Practices
- Must be unique and always increasing
- Recommended: Use current timestamp in milliseconds
- Must be string format, not integer
- Incorrect nonce handling can cause temporary API bans
- Each API key maintains separate nonce sequence

### Error Handling
Common authentication errors:
- `EAPI:Invalid key`
- `EAPI:Invalid signature`
- `EAPI:Invalid nonce`
- `EGeneral:Permission denied`

## 5. Request/Response Formats

### HTTP Methods
- **GET:** Public endpoints only
- **POST:** All private endpoints with form-encoded data

### Request Headers
```
Content-Type: application/x-www-form-urlencoded
API-Key: your_api_key
API-Sign: generated_signature
```

### Request Body Format
Private endpoints use form-encoded POST data:
```
nonce=1234567890&pair=XBTUSD&type=buy&ordertype=market&volume=0.1
```

### Response Data Structures
All responses follow this format:
```json
{
  "error": [],
  "result": {
    // Endpoint-specific data
  }
}
```

**Success Response:**
- `error`: Empty array
- `result`: Contains response data

**Error Response:**
- `error`: Array of error messages
- `result`: Empty or null

### Common Response Fields
- **Timestamps:** Unix timestamps (some in nanoseconds)
- **Prices/Volumes:** String format to preserve precision
- **Asset Names:** Kraken's internal naming (e.g., XBTUSD for BTC/USD)

## 6. Rate Limiting

### Rate Limit Tiers
**Starter Tier:**
- Max API Counter: 15
- Counter Decay: -0.33/second

**Intermediate Tier:**
- Max API Counter: 20
- Counter Decay: -0.5/second

**Pro Tier:**
- Max API Counter: 20
- Counter Decay: -1/second

### Counter Mechanics
- Each API key has separate counter
- Counter starts at 0
- Most API calls increase counter by 1
- Ledger/trade history calls increase counter by 2
- Counter decreases over time based on tier
- When counter exceeds maximum, calls are rate limited

### Special Rate Limits
**AddOrder and CancelOrder:**
- Operate on separate rate limiter
- Different rules than general API counter

### Rate Limit Errors
- `EAPI:Rate limit exceeded`: REST API counter exceeded
- `EService: Throttled: [UNIX timestamp]`: Too many concurrent requests

### Best Practices
1. Monitor your API counter usage
2. Implement exponential backoff for rate limit errors
3. Use WebSocket API for real-time data to reduce REST calls
4. Batch operations when possible
5. Cache frequently accessed static data (assets, pairs)
6. Respect the decay rates and plan API calls accordingly

## Example Implementation Considerations

### Authentication Example (Python)
```python
import hashlib
import hmac
import base64
import time

def get_kraken_signature(urlpath, data, secret):
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()
```

### Common Error Handling
- Implement retry logic for transient errors
- Handle nonce synchronization issues
- Monitor for permission-related errors
- Log all API interactions for debugging

### Performance Optimization
- Use connection pooling for HTTP requests
- Implement request queuing to respect rate limits
- Cache static data (assets, trading pairs)
- Use appropriate timeouts for requests
- Consider using WebSocket API for real-time data

This documentation provides comprehensive coverage of Kraken's Spot REST API capabilities based on official sources as of 2025.