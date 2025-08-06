"""
Network Utilities
Resilient request handling for API connections
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class RequestConfig:
    """Configuration for resilient requests"""
    timeout: float = 30.0
    max_retries: int = 3
    backoff_factor: float = 1.0
    retry_on_status: list = None

    def __post_init__(self):
        if self.retry_on_status is None:
            self.retry_on_status = [429, 500, 502, 503, 504]


class ResilientRequest:
    """Resilient HTTP request handler with retry logic"""

    def __init__(self, config: Optional[RequestConfig] = None):
        """Initialize resilient request handler"""
        self.config = config or RequestConfig()
        self.session = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def get(self, url: str, headers: Optional[Dict[str, str]] = None,
                  params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make resilient GET request"""
        return await self._make_request('GET', url, headers=headers, params=params)

    async def post(self, url: str, data: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None,
                   json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make resilient POST request"""
        return await self._make_request('POST', url, data=data, headers=headers, json=json_data)

    async def request(self, func, *args, retry_exceptions=None, context=None, **kwargs):
        """
        Generic request method that wraps any async function with retry logic.
        This is used by the exchange code to make resilient API calls.
        
        Args:
            func: The async function to call
            *args: Arguments to pass to the function
            retry_exceptions: Tuple of exception types to retry on
            context: Context string for logging
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function call
        """
        retry_exceptions = retry_exceptions or (Exception,)
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Call the function with its arguments
                result = await func(*args, **kwargs)
                return result

            except retry_exceptions as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    wait_time = self.config.backoff_factor * (2 ** attempt)
                    logger.warning(f"[NETWORK] {context or 'Request'} failed: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{self.config.max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"[NETWORK] {context or 'Request'} failed after {self.config.max_retries} retries: {e}")
                    break
            except Exception as e:
                # Don't retry on non-specified exceptions
                logger.error(f"[NETWORK] {context or 'Request'} failed with non-retryable error: {e}")
                raise e

        # If we get here, all retries failed
        raise last_exception or Exception("Request failed after all retries")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the resilient request handler"""
        return {
            'max_retries': self.config.max_retries,
            'timeout': self.config.timeout,
            'backoff_factor': self.config.backoff_factor,
            'retry_on_status': self.config.retry_on_status
        }

    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make resilient HTTP request with retry logic"""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                    )

                async with self.session.request(method, url, **kwargs) as response:
                    # Check if we should retry based on status code
                    if response.status in self.config.retry_on_status and attempt < self.config.max_retries:
                        wait_time = self.config.backoff_factor * (2 ** attempt)
                        logger.warning(f"[NETWORK] Request failed with status {response.status}, retrying in {wait_time}s (attempt {attempt + 1}/{self.config.max_retries})")
                        await asyncio.sleep(wait_time)
                        continue

                    # Raise for other HTTP errors
                    response.raise_for_status()

                    # Try to parse JSON response
                    try:
                        return await response.json()
                    except Exception:
                        # If not JSON, return text
                        text = await response.text()
                        return {'text': text, 'status': response.status}

            except asyncio.TimeoutError as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    wait_time = self.config.backoff_factor * (2 ** attempt)
                    logger.warning(f"[NETWORK] Request timeout, retrying in {wait_time}s (attempt {attempt + 1}/{self.config.max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"[NETWORK] Request failed after {self.config.max_retries} retries due to timeout")
                    break

            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    wait_time = self.config.backoff_factor * (2 ** attempt)
                    logger.warning(f"[NETWORK] Request failed with error: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{self.config.max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"[NETWORK] Request failed after {self.config.max_retries} retries: {e}")
                    break

        # If we get here, all retries failed
        raise last_exception or Exception("Request failed after all retries")


# Convenience function for one-off requests
async def resilient_get(url: str, headers: Optional[Dict[str, str]] = None,
                       params: Optional[Dict[str, Any]] = None,
                       config: Optional[RequestConfig] = None) -> Dict[str, Any]:
    """Make a resilient GET request"""
    async with ResilientRequest(config) as client:
        return await client.get(url, headers=headers, params=params)


async def resilient_post(url: str, data: Optional[Dict[str, Any]] = None,
                        headers: Optional[Dict[str, str]] = None,
                        json_data: Optional[Dict[str, Any]] = None,
                        config: Optional[RequestConfig] = None) -> Dict[str, Any]:
    """Make a resilient POST request"""
    async with ResilientRequest(config) as client:
        return await client.post(url, data=data, headers=headers, json_data=json_data)


# Simple network health check
async def check_connectivity(url: str = "https://api.kraken.com/0/public/Time") -> bool:
    """Check network connectivity"""
    try:
        config = RequestConfig(timeout=10.0, max_retries=1)
        result = await resilient_get(url, config=config)
        return bool(result)
    except Exception as e:
        logger.error(f"[NETWORK] Connectivity check failed: {e}")
        return False
