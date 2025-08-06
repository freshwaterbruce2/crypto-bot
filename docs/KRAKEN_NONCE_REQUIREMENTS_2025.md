# Kraken API Nonce Requirements - 2025 Documentation

## Overview
The nonce is a critical component of Kraken's API authentication system, ensuring request uniqueness and preventing replay attacks. This document provides comprehensive information about nonce requirements, implementation, and troubleshooting.

## Nonce Format Requirements

### Core Requirements
- **Type**: Always increasing, unsigned 64-bit integer
- **Format**: UNIX timestamp in milliseconds (recommended)
- **Resolution**: Milliseconds or higher for rapid API calls
- **Persistence**: Each API key maintains its own nonce value
- **No Reset**: Cannot reset nonce to a lower value

### Recommended Implementation
```python
import time

# Standard millisecond timestamp (RECOMMENDED)
nonce = str(int(time.time() * 1000))

# Higher resolution for rapid trading (10ths of milliseconds)
nonce = str(int(time.time() * 10000))
```

## Authentication Algorithm

### API Signature Generation
The Kraken API requires an HMAC-SHA512 signature calculated as follows:

```python
import hashlib
import hmac
import base64
import urllib.parse

def get_kraken_signature(urlpath, data, secret):
    """Generate Kraken API signature"""
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()
```

### Request Headers
```python
headers = {
    'API-Key': api_key,
    'API-Sign': signature,
    'Content-Type': 'application/x-www-form-urlencoded'
}
```

## Common "EAPI:Invalid nonce" Error Causes

### 1. Concurrent Requests
- **Problem**: Multiple simultaneous requests arrive out of order
- **Solution**: Use separate API keys for each process/bot/application

### 2. Insufficient Resolution
- **Problem**: Making more than one request per millisecond
- **Solution**: Increase nonce resolution to 10000 * time.time()

### 3. Clock Drift
- **Problem**: System clock changes or synchronization issues
- **Solution**: Implement nonce window tolerance (5000-10000ms)

### 4. Shared API Keys
- **Problem**: Multiple scripts using the same API key
- **Solution**: Create unique API key pairs for each application

### 5. Race Conditions
- **Problem**: Requests arrive at Kraken out of order
- **Solution**: Implement sequential request processing

## Best Practices

### 1. Thread-Safe Singleton Pattern
```python
import threading

class NonceManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._last_nonce = 0
                cls._instance._nonce_lock = threading.Lock()
            return cls._instance
    
    def get_nonce(self):
        with self._nonce_lock:
            current = int(time.time() * 1000)
            if current <= self._last_nonce:
                current = self._last_nonce + 1
            self._last_nonce = current
            return str(current)
```

### 2. Error Recovery
```python
def handle_nonce_error(self):
    """Jump ahead to recover from invalid nonce"""
    with self._nonce_lock:
        # Jump 60 seconds ahead
        self._last_nonce = int(time.time() * 1000) + 60000
        return str(self._last_nonce)
```

### 3. Sequential Request Queue
```python
import asyncio
from asyncio import Queue

class KrakenRequestQueue:
    def __init__(self):
        self.queue = Queue()
        self.processing = False
    
    async def add_request(self, request):
        await self.queue.put(request)
        if not self.processing:
            asyncio.create_task(self._process_queue())
    
    async def _process_queue(self):
        self.processing = True
        while not self.queue.empty():
            request = await self.queue.get()
            await self._execute_request(request)
            await asyncio.sleep(0.1)  # Rate limiting
        self.processing = False
```

## Platform-Specific Notes

### Spot Trading
- **Required**: Nonce is mandatory for all authenticated Spot REST API calls
- **Format**: Millisecond timestamp recommended

### Futures Trading
- **Optional**: Nonce is NOT required for Futures REST authentication
- **Note**: Can still use millisecond timestamp if desired

### WebSocket Authentication
- **Token Request**: Requires nonce for GetWebSocketsToken endpoint
- **Token Usage**: WebSocket connections use the token, not direct nonce

## Troubleshooting Guide

### Diagnostic Steps
1. **Check Current Nonce**: Log the exact nonce being sent
2. **Verify Timestamp**: Ensure system clock is synchronized
3. **Monitor Frequency**: Count requests per second
4. **Review API Keys**: Confirm unique keys per application
5. **Test Sequential**: Try single-threaded test first

### Common Solutions
| Error | Solution |
|-------|----------|
| Invalid nonce on first call | Delete nonce state file and restart |
| Intermittent failures | Increase nonce resolution to 10000 |
| Consistent failures | Check system clock synchronization |
| Parallel script errors | Use separate API keys |
| After system restart | Implement persistent nonce storage |

## Configuration Options

### Nonce Window
- **Purpose**: Tolerance for out-of-order requests
- **Setting**: Configure in Kraken account settings
- **Recommended**: 5000-10000ms for high-frequency trading

### API Key Permissions
- **Best Practice**: Create keys with minimal required permissions
- **Separate Keys**: Use different keys for different operations
- **Regular Rotation**: Rotate keys periodically for security

## References

### Official Documentation
- [Kraken Spot REST Authentication](https://docs.kraken.com/api/docs/guides/spot-rest-auth/)
- [What is a nonce?](https://support.kraken.com/hc/en-us/articles/360000906023)
- [Invalid nonce errors](https://support.kraken.com/hc/en-us/articles/360001148063)

### GitHub Libraries
- [ccxt/ccxt](https://github.com/ccxt/ccxt) - Unified crypto exchange library
- [veox/python3-krakenex](https://github.com/veox/python3-krakenex) - Low-level Python client
- [btschwertfeger/python-kraken-sdk](https://github.com/btschwertfeger/python-kraken-sdk) - High-level Python SDK

## Version History
- **2025-08-06**: Initial comprehensive documentation
- **Author**: Crypto Trading Bot Development Team