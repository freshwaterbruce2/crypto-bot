#!/usr/bin/env python3
"""
Simple Kraken REST Client with Working Authentication
Uses the exact signature format that works for both REST and WebSocket
"""

import base64
import hashlib
import hmac
import os
import time
import urllib.parse
from typing import Any, Dict, Optional

import aiohttp


class SimpleKrakenREST:
    """Simple Kraken REST client with correct authentication"""

    def __init__(self, api_key: Optional[str] = None, private_key: Optional[str] = None):
        # Load credentials from environment if not provided
        self.api_key = api_key or os.getenv('KRAKEN_KEY') or os.getenv('KRAKEN_API_KEY')
        self.private_key = private_key or os.getenv('KRAKEN_SECRET') or os.getenv('KRAKEN_API_SECRET')

        if not self.api_key or not self.private_key:
            raise ValueError("API credentials required")

        self.base_url = "https://api.kraken.com"

    def _generate_signature(self, urlpath: str, data: dict) -> str:
        """Generate Kraken signature using the CORRECT krakenex format"""
        # URL-encode the POST data
        postdata = urllib.parse.urlencode(data)

        # Create the message to sign (CORRECT FORMAT)
        encoded = (str(data['nonce']) + postdata).encode('utf-8')
        message = urlpath.encode('utf-8') + hashlib.sha256(encoded).digest()

        # Generate HMAC-SHA512 signature
        mac = hmac.new(
            base64.b64decode(self.private_key),
            message,
            hashlib.sha512
        )

        return base64.b64encode(mac.digest()).decode('utf-8')

    async def _make_request(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make authenticated request to Kraken API"""

        if data is None:
            data = {}

        # Add nonce
        data['nonce'] = str(int(time.time() * 1000))

        # Generate signature
        signature = self._generate_signature(endpoint, data)

        # Prepare headers
        headers = {
            'API-Key': self.api_key,
            'API-Sign': signature,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        # Make request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url + endpoint,
                headers=headers,
                data=urllib.parse.urlencode(data),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:

                result = await response.json()

                if result.get('error') and result['error']:
                    error_msg = result['error'][0] if isinstance(result['error'], list) else str(result['error'])
                    raise Exception(f"Kraken API Error: {error_msg}")

                return result.get('result', {})

    # Public methods matching KrakenRestClient interface
    async def get_account_balance(self) -> Dict[str, str]:
        """Get account balance"""
        return await self._make_request('/0/private/Balance')

    async def get_trade_balance(self) -> Dict[str, Any]:
        """Get trade balance"""
        return await self._make_request('/0/private/TradeBalance')

    async def add_order(self, pair: str, type: str, ordertype: str, volume: str, **kwargs) -> Dict[str, Any]:
        """Add order"""
        data = {
            'pair': pair,
            'type': type,
            'ordertype': ordertype,
            'volume': volume,
            **kwargs
        }
        return await self._make_request('/0/private/AddOrder', data)

    async def cancel_order(self, txid: str) -> Dict[str, Any]:
        """Cancel order"""
        data = {'txid': txid}
        return await self._make_request('/0/private/CancelOrder', data)

    async def get_open_orders(self) -> Dict[str, Any]:
        """Get open orders"""
        return await self._make_request('/0/private/OpenOrders')

    async def get_closed_orders(self) -> Dict[str, Any]:
        """Get closed orders"""
        return await self._make_request('/0/private/ClosedOrders')

    # Context manager support
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    # Compatibility methods
    async def close(self):
        """Close (compatibility)"""
        pass

# Alias for compatibility
KrakenRestClientFixed = SimpleKrakenREST
