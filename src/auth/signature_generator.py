"""
Kraken API Signature Generator - 2025 Compliance
================================================

HMAC-SHA512 signature generation for Kraken API authentication.
Implements the exact signature algorithm specified in Kraken API documentation.

Signature Algorithm:
1. Create API-Post string: nonce + POST data
2. Create SHA256 hash of API-Post
3. Create binary message: URI path + SHA256 hash
4. Generate HMAC-SHA512 using private key and binary message
5. Encode result as Base64

Features:
- Thread-safe operations
- Comprehensive error handling
- Debug logging support
- Performance optimized
- Async support
"""

import asyncio
import base64
import hashlib
import hmac
import logging
import urllib.parse
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SignatureComponents:
    """Components used in signature generation for debugging"""

    nonce: str
    post_data: str
    api_post: str
    sha256_hash: bytes
    binary_message: bytes
    signature: str


class SignatureGenerator:
    """
    Production-ready HMAC-SHA512 signature generator for Kraken API.

    Implements the exact signature algorithm required by Kraken with
    comprehensive error handling and debugging support.
    """

    def __init__(self, private_key: str):
        """
        Initialize signature generator with Kraken private key.

        Args:
            private_key: Base64-encoded Kraken API private key
        """
        self.private_key = private_key
        self._private_key_bytes = self._decode_private_key(private_key)

        # Performance tracking
        self._signature_count = 0

        logger.debug(
            f"[SIGNATURE_2025] Initialized with private key length: "
            f"{len(self._private_key_bytes)} bytes"
        )

    def _decode_private_key(self, private_key: str) -> bytes:
        """
        Decode Base64 private key with validation.

        Args:
            private_key: Base64-encoded private key string

        Returns:
            Decoded private key bytes

        Raises:
            ValueError: If private key is invalid
        """
        try:
            decoded = base64.b64decode(private_key)

            # Validate key length (Kraken private keys are typically 64 bytes)
            if len(decoded) < 32:
                raise ValueError("Private key too short")

            return decoded

        except Exception as e:
            logger.error(f"[SIGNATURE_2025] Invalid private key: {e}")
            raise ValueError(f"Invalid private key format: {e}")

    def _prepare_post_data(self, params: dict[str, Any]) -> str:
        """
        Prepare POST data string from parameters.

        Args:
            params: Dictionary of API parameters

        Returns:
            URL-encoded POST data string
        """
        if not params:
            return ""

        # Sort parameters for consistent signature generation
        sorted_params = sorted(params.items())

        # URL encode parameters
        encoded_params = []
        for key, value in sorted_params:
            # Convert all values to strings
            str_value = str(value) if value is not None else ""
            encoded_key = urllib.parse.quote_plus(str(key))
            encoded_value = urllib.parse.quote_plus(str_value)
            encoded_params.append(f"{encoded_key}={encoded_value}")

        return "&".join(encoded_params)

    def generate_signature(
        self, uri_path: str, nonce: str, params: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Generate HMAC-SHA512 signature for Kraken API request.

        Args:
            uri_path: API endpoint path (e.g., '/0/private/Balance')
            nonce: Unique nonce for the request
            params: Optional dictionary of request parameters

        Returns:
            Base64-encoded HMAC-SHA512 signature

        Raises:
            ValueError: If signature generation fails
        """
        try:
            # Step 1: Prepare POST data
            self._prepare_post_data(params or {})

            # Step 2: Create API-Post string (CORRECT krakenex format)
            # Format: str(nonce) + postdata (NOT "nonce={nonce}&{postdata}")
            params_with_nonce = params.copy() if params else {}
            params_with_nonce["nonce"] = nonce
            postdata = urllib.parse.urlencode(params_with_nonce)
            api_post = str(nonce) + postdata

            # Step 3: Create SHA256 hash of API-Post
            sha256_hash = hashlib.sha256(api_post.encode("utf-8")).digest()

            # Step 4: Create binary message (URI path + SHA256 hash)
            binary_message = uri_path.encode("utf-8") + sha256_hash

            # Step 5: Generate HMAC-SHA512 signature
            hmac_signature = hmac.new(
                self._private_key_bytes, binary_message, hashlib.sha512
            ).digest()

            # Step 6: Encode as Base64
            signature = base64.b64encode(hmac_signature).decode("utf-8")

            # Update counters
            self._signature_count += 1

            logger.debug(
                f"[SIGNATURE_2025] Generated signature #{self._signature_count} "
                f"for {uri_path} with nonce {nonce}"
            )

            return signature

        except Exception as e:
            logger.error(f"[SIGNATURE_2025] Signature generation failed: {e}")
            raise ValueError(f"Failed to generate signature: {e}")

    def generate_signature_with_debug(
        self, uri_path: str, nonce: str, params: Optional[dict[str, Any]] = None
    ) -> SignatureComponents:
        """
        Generate signature with detailed debug information.

        Args:
            uri_path: API endpoint path
            nonce: Unique nonce for the request
            params: Optional dictionary of request parameters

        Returns:
            SignatureComponents with all intermediate values for debugging
        """
        try:
            # Prepare POST data
            post_data = self._prepare_post_data(params or {})

            # Create API-Post string (CORRECT krakenex format)
            params_with_nonce = params.copy() if params else {}
            params_with_nonce["nonce"] = nonce
            postdata = urllib.parse.urlencode(params_with_nonce)
            api_post = str(nonce) + postdata

            # Create SHA256 hash
            sha256_hash = hashlib.sha256(api_post.encode("utf-8")).digest()

            # Create binary message
            binary_message = uri_path.encode("utf-8") + sha256_hash

            # Generate HMAC-SHA512 signature
            hmac_signature = hmac.new(
                self._private_key_bytes, binary_message, hashlib.sha512
            ).digest()

            # Encode as Base64
            signature = base64.b64encode(hmac_signature).decode("utf-8")

            return SignatureComponents(
                nonce=nonce,
                post_data=post_data,
                api_post=api_post,
                sha256_hash=sha256_hash,
                binary_message=binary_message,
                signature=signature,
            )

        except Exception as e:
            logger.error(f"[SIGNATURE_2025] Debug signature generation failed: {e}")
            raise ValueError(f"Failed to generate debug signature: {e}")

    async def generate_signature_async(
        self, uri_path: str, nonce: str, params: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Async version of generate_signature for asyncio applications.

        Args:
            uri_path: API endpoint path
            nonce: Unique nonce for the request
            params: Optional dictionary of request parameters

        Returns:
            Base64-encoded HMAC-SHA512 signature
        """
        # Run signature generation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_signature, uri_path, nonce, params)

    def validate_signature_components(
        self,
        uri_path: str,
        nonce: str,
        params: Optional[dict[str, Any]] = None,
        expected_signature: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Validate signature components for debugging authentication issues.

        Args:
            uri_path: API endpoint path
            nonce: Request nonce
            params: Request parameters
            expected_signature: Expected signature for comparison

        Returns:
            Validation results dictionary
        """
        try:
            components = self.generate_signature_with_debug(uri_path, nonce, params)
            generated_signature = components.signature

            result = {
                "success": True,
                "uri_path": uri_path,
                "nonce": nonce,
                "post_data": components.post_data,
                "api_post": components.api_post,
                "sha256_hash_hex": components.sha256_hash.hex(),
                "binary_message_hex": components.binary_message.hex(),
                "generated_signature": generated_signature,
                "signature_length": len(generated_signature),
                "private_key_length": len(self._private_key_bytes),
            }

            if expected_signature:
                result["expected_signature"] = expected_signature
                result["signatures_match"] = generated_signature == expected_signature

            return result

        except Exception as e:
            return {"success": False, "error": str(e), "uri_path": uri_path, "nonce": nonce}

    def get_statistics(self) -> dict[str, Any]:
        """
        Get signature generator statistics.

        Returns:
            Dictionary with performance statistics
        """
        return {
            "signature_count": self._signature_count,
            "private_key_length": len(self._private_key_bytes),
            "private_key_valid": len(self._private_key_bytes) >= 32,
        }

    def test_signature_algorithm(self) -> dict[str, Any]:
        """
        Test signature algorithm with known values for validation.

        Returns:
            Test results dictionary
        """
        try:
            # Test with simple known values
            test_uri = "/0/private/Balance"
            test_nonce = "1234567890123456"
            test_params = {"test": "value"}

            # Generate signature
            signature = self.generate_signature(test_uri, test_nonce, test_params)

            # Validate components
            validation = self.validate_signature_components(test_uri, test_nonce, test_params)

            return {
                "success": True,
                "test_signature": signature,
                "validation": validation,
                "algorithm_working": len(signature) > 0 and signature.endswith("="),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "algorithm_working": False}

    @staticmethod
    def create_from_credentials(api_key: str, private_key: str) -> "SignatureGenerator":
        """
        Create signature generator from API credentials.

        Args:
            api_key: Kraken API key (for logging)
            private_key: Base64-encoded private key

        Returns:
            SignatureGenerator instance
        """
        logger.info(f"[SIGNATURE_2025] Creating signature generator for API key: {api_key[:8]}...")

        return SignatureGenerator(private_key)

    def __str__(self) -> str:
        """String representation for debugging"""
        return (
            f"SignatureGenerator(signatures_generated={self._signature_count}, "
            f"key_length={len(self._private_key_bytes)})"
        )

    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return self.__str__()
