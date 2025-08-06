#!/usr/bin/env python3
"""
Kraken API Nonce Implementation Examples
=========================================

Working examples of nonce generation and authentication for Kraken API.
Based on official documentation and successful GitHub implementations.

Author: Crypto Trading Bot Team
Date: 2025-08-06
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import aiohttp
import requests

logger = logging.getLogger(__name__)


# =============================================================================
# BASIC NONCE GENERATION
# =============================================================================

def generate_nonce_milliseconds() -> str:
    """
    Standard millisecond-based nonce generation.
    Recommended for most use cases.
    """
    return str(int(time.time() * 1000))


def generate_nonce_high_resolution() -> str:
    """
    High-resolution nonce for rapid trading.
    Uses 10ths of milliseconds for more granularity.
    """
    return str(int(time.time() * 10000))


def generate_nonce_microseconds() -> str:
    """
    Microsecond-based nonce for ultra-high frequency.
    Maximum resolution for extreme cases.
    """
    return str(int(time.time() * 1000000))


# =============================================================================
# THREAD-SAFE NONCE MANAGER
# =============================================================================

class ThreadSafeNonceManager:
    """
    Thread-safe singleton nonce manager.
    Ensures nonces always increase even with concurrent access.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._nonce_lock = threading.Lock()
        self._last_nonce = 0
        self._state_file = Path("nonce_state.json")
        self._load_state()
        self._initialized = True

        logger.info(f"Nonce manager initialized with last nonce: {self._last_nonce}")

    def get_nonce(self) -> str:
        """Get next valid nonce, guaranteed to be increasing."""
        with self._nonce_lock:
            # Use milliseconds
            current = int(time.time() * 1000)

            # Ensure always increasing
            if current <= self._last_nonce:
                current = self._last_nonce + 1

            self._last_nonce = current
            self._save_state()

            return str(current)

    def recover_from_error(self) -> str:
        """Recover from invalid nonce error by jumping ahead."""
        with self._nonce_lock:
            # Jump 60 seconds ahead
            self._last_nonce = int(time.time() * 1000) + 60000
            self._save_state()

            logger.warning(f"Nonce recovery: jumped to {self._last_nonce}")
            return str(self._last_nonce)

    def _load_state(self):
        """Load persisted nonce state."""
        try:
            if self._state_file.exists():
                with open(self._state_file) as f:
                    data = json.load(f)
                    self._last_nonce = data.get('last_nonce', 0)
        except Exception as e:
            logger.error(f"Failed to load nonce state: {e}")

    def _save_state(self):
        """Persist nonce state to file."""
        try:
            with open(self._state_file, 'w') as f:
                json.dump({'last_nonce': self._last_nonce}, f)
        except Exception as e:
            logger.error(f"Failed to save nonce state: {e}")


# =============================================================================
# KRAKEN API AUTHENTICATION
# =============================================================================

class KrakenAuthenticator:
    """
    Complete Kraken API authentication implementation.
    Handles signature generation and request signing.
    """

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.nonce_manager = ThreadSafeNonceManager()
        self.base_url = "https://api.kraken.com"

    def get_kraken_signature(self, urlpath: str, data: dict[str, Any]) -> str:
        """
        Generate Kraken API signature.

        Algorithm: HMAC-SHA512 of (URI path + SHA256(nonce + POST data))
        """
        postdata = urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        sigdigest = base64.b64encode(mac.digest())

        return sigdigest.decode()

    def prepare_request(self, endpoint: str, params: dict[str, Any] = None) -> tuple:
        """
        Prepare authenticated request with headers and data.

        Returns:
            tuple: (headers, data) for the request
        """
        if params is None:
            params = {}

        # Add nonce to parameters
        data = params.copy()
        data['nonce'] = self.nonce_manager.get_nonce()

        # Generate signature
        signature = self.get_kraken_signature(endpoint, data)

        # Prepare headers
        headers = {
            'API-Key': self.api_key,
            'API-Sign': signature,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        return headers, data

    def make_request(self, endpoint: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """
        Make synchronous authenticated request to Kraken API.
        """
        headers, data = self.prepare_request(endpoint, params)
        url = self.base_url + endpoint

        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            result = response.json()

            # Check for errors
            if 'error' in result and result['error']:
                errors = result['error']
                if any('nonce' in str(err).lower() for err in errors):
                    logger.error(f"Nonce error: {errors}")
                    # Could implement retry logic here
                raise Exception(f"API error: {errors}")

            return result

        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

    async def make_async_request(self, endpoint: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """
        Make asynchronous authenticated request to Kraken API.
        """
        headers, data = self.prepare_request(endpoint, params)
        url = self.base_url + endpoint

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url,
                    headers=headers,
                    data=urlencode(data),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    result = await response.json()

                    # Check for errors
                    if 'error' in result and result['error']:
                        errors = result['error']
                        if any('nonce' in str(err).lower() for err in errors):
                            logger.error(f"Nonce error: {errors}")
                            # Could implement retry logic here
                        raise Exception(f"API error: {errors}")

                    return result

            except Exception as e:
                logger.error(f"Async request failed: {e}")
                raise


# =============================================================================
# SEQUENTIAL REQUEST HANDLER
# =============================================================================

class SequentialRequestHandler:
    """
    Ensures requests are processed sequentially to avoid nonce conflicts.
    """

    def __init__(self, authenticator: KrakenAuthenticator):
        self.auth = authenticator
        self.queue = asyncio.Queue()
        self.processing = False

    async def add_request(self, endpoint: str, params: dict[str, Any] = None):
        """Add request to queue for sequential processing."""
        await self.queue.put((endpoint, params))

        if not self.processing:
            asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Process requests sequentially."""
        self.processing = True

        while not self.queue.empty():
            endpoint, params = await self.queue.get()

            try:
                await self.auth.make_async_request(endpoint, params)
                logger.info(f"Request successful: {endpoint}")

                # Rate limiting
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Request failed: {endpoint} - {e}")

        self.processing = False


# =============================================================================
# ERROR RECOVERY EXAMPLES
# =============================================================================

class RobustKrakenClient:
    """
    Robust Kraken client with automatic error recovery.
    """

    def __init__(self, api_key: str, api_secret: str):
        self.auth = KrakenAuthenticator(api_key, api_secret)
        self.max_retries = 3
        self.retry_delay = 1.0

    async def call_with_retry(self, endpoint: str, params: dict[str, Any] = None) -> dict[str, Any]:
        """
        Make API call with automatic retry on nonce errors.
        """
        for attempt in range(self.max_retries):
            try:
                result = await self.auth.make_async_request(endpoint, params)
                return result

            except Exception as e:
                error_str = str(e).lower()

                if 'invalid nonce' in error_str:
                    logger.warning(f"Nonce error on attempt {attempt + 1}, recovering...")

                    # Recover nonce
                    self.auth.nonce_manager.recover_from_error()

                    # Exponential backoff
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))

                    if attempt == self.max_retries - 1:
                        raise
                else:
                    # Non-nonce error, don't retry
                    raise

        raise Exception(f"Failed after {self.max_retries} attempts")


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

async def example_basic_usage():
    """Basic usage example."""
    # Initialize with your credentials
    api_key = "your_api_key"
    api_secret = "your_api_secret"

    # Create authenticator
    auth = KrakenAuthenticator(api_key, api_secret)

    # Get account balance
    try:
        result = await auth.make_async_request('/0/private/Balance')
        print(f"Balance: {result}")
    except Exception as e:
        print(f"Error: {e}")


async def example_sequential_requests():
    """Sequential request processing example."""
    api_key = "your_api_key"
    api_secret = "your_api_secret"

    auth = KrakenAuthenticator(api_key, api_secret)
    handler = SequentialRequestHandler(auth)

    # Queue multiple requests
    await handler.add_request('/0/private/Balance')
    await handler.add_request('/0/private/TradeBalance')
    await handler.add_request('/0/private/OpenOrders')

    # Wait for processing
    await asyncio.sleep(5)


async def example_robust_client():
    """Robust client with error recovery example."""
    api_key = "your_api_key"
    api_secret = "your_api_secret"

    client = RobustKrakenClient(api_key, api_secret)

    try:
        # This will automatically retry on nonce errors
        result = await client.call_with_retry('/0/private/Balance')
        print(f"Balance retrieved: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")


def example_nonce_generation():
    """Demonstrate different nonce generation methods."""
    print("Nonce Generation Examples:")
    print("-" * 40)

    # Standard milliseconds
    print(f"Milliseconds: {generate_nonce_milliseconds()}")
    time.sleep(0.001)

    # High resolution
    print(f"High Resolution: {generate_nonce_high_resolution()}")
    time.sleep(0.001)

    # Microseconds
    print(f"Microseconds: {generate_nonce_microseconds()}")

    # Thread-safe manager
    manager = ThreadSafeNonceManager()
    print("\nThread-safe nonces:")
    for i in range(5):
        print(f"  {i+1}: {manager.get_nonce()}")
        time.sleep(0.001)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s'
    )

    # Run examples
    print("Kraken Nonce Implementation Examples")
    print("=" * 50)

    # Synchronous example
    example_nonce_generation()

    # Async examples (uncomment with valid credentials)
    # asyncio.run(example_basic_usage())
    # asyncio.run(example_sequential_requests())
    # asyncio.run(example_robust_client())

    print("\nExamples completed!")
