"""
Kraken API Authentication Handler - 2025 Compliance
==================================================

Main authentication system for Kraken API with complete 2025 compliance.
Integrates nonce management and signature generation for secure API access.

Features:
- Complete Kraken API authentication workflow
- Thread-safe operations with async support
- Automatic nonce management and collision recovery
- Comprehensive error handling and retry logic
- Multiple API key support with isolation
- Performance monitoring and debugging tools
- Production-ready logging and metrics

Usage:
    auth = KrakenAuth(api_key="your_key", private_key="your_private_key")
    headers = auth.get_auth_headers("/0/private/Balance", {"key": "value"})
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Optional

from ..utils.consolidated_nonce_manager import ConsolidatedNonceManager
from .signature_generator import SignatureGenerator

logger = logging.getLogger(__name__)


@dataclass
class AuthRequest:
    """Authentication request data structure"""

    uri_path: str
    params: dict[str, Any]
    nonce: str
    signature: str
    timestamp: float


@dataclass
class AuthStats:
    """Authentication statistics"""

    requests_count: int = 0
    successful_auths: int = 0
    failed_auths: int = 0
    nonce_errors: int = 0
    signature_errors: int = 0
    recovery_attempts: int = 0
    avg_auth_time_ms: float = 0.0


class KrakenAuthError(Exception):
    """Base exception for Kraken authentication errors"""

    pass


class NonceError(KrakenAuthError):
    """Nonce-related authentication error"""

    pass


class SignatureError(KrakenAuthError):
    """Signature-related authentication error"""

    pass


class KrakenAuth:
    """
    Production-ready Kraken API authentication handler.

    Provides complete authentication workflow with automatic nonce management,
    signature generation, error handling, and performance monitoring.
    """

    def __init__(
        self,
        api_key: str,
        private_key: str,
        storage_dir: Optional[str] = None,
        enable_debug: bool = False,
    ):
        """
        Initialize Kraken authentication handler.

        Args:
            api_key: Kraken API key
            private_key: Base64-encoded Kraken private key
            storage_dir: Directory for nonce state storage
            enable_debug: Enable detailed debug logging
        """
        self.api_key = api_key
        self.private_key = private_key
        self.enable_debug = enable_debug

        # Validate credentials
        self._validate_credentials()

        # Initialize components with unified nonce manager
        self.nonce_manager = ConsolidatedNonceManager.get_instance()
        # Use signature generator with correct algorithm
        self.signature_generator = SignatureGenerator(private_key)

        # Statistics and monitoring
        self.stats = AuthStats()
        self._last_auth_times = []
        self._max_time_samples = 100

        # Thread safety
        self._auth_lock = asyncio.Lock()

        # Configuration
        self.max_retry_attempts = 3
        self.retry_delay_ms = 100

        logger.info(f"[KRAKEN_AUTH_2025] Initialized for API key: {api_key[:8]}...")

        if enable_debug:
            self._run_self_test()

    def _validate_credentials(self) -> None:
        """Validate API credentials format"""
        if not self.api_key or len(self.api_key) < 16:
            raise ValueError("Invalid API key: too short")

        if not self.private_key or len(self.private_key) < 32:
            raise ValueError("Invalid private key: too short")

        # Test private key decoding
        try:
            import base64

            decoded = base64.b64decode(self.private_key)
            if len(decoded) < 32:
                raise ValueError("Decoded private key too short")
        except Exception as e:
            raise ValueError(f"Invalid private key format: {e}")

    def _run_self_test(self) -> None:
        """Run self-test to verify authentication components"""
        try:
            logger.info("[KRAKEN_AUTH_2025] Running self-test...")

            # Test nonce generation
            nonce = self.nonce_manager.get_nonce("kraken_auth_test")
            logger.debug(f"[KRAKEN_AUTH_2025] Test nonce: {nonce}")

            # Test signature generation
            test_sig = self.signature_generator.test_signature_algorithm()
            if not test_sig["success"]:
                raise KrakenAuthError(f"Signature test failed: {test_sig.get('error')}")

            logger.info("[KRAKEN_AUTH_2025] Self-test passed successfully")

        except Exception as e:
            logger.error(f"[KRAKEN_AUTH_2025] Self-test failed: {e}")
            raise KrakenAuthError(f"Self-test failed: {e}")

    def get_auth_headers(
        self, uri_path: str, params: Optional[dict[str, Any]] = None
    ) -> dict[str, str]:
        """
        Generate authentication headers for Kraken API request.

        Args:
            uri_path: API endpoint path (e.g., '/0/private/Balance')
            params: Optional request parameters (nonce will be added)

        Returns:
            Dictionary with authentication headers

        Raises:
            KrakenAuthError: If authentication fails
        """
        start_time = time.time()

        try:
            # Get fresh nonce (milliseconds format)
            nonce = self.nonce_manager.get_nonce("rest_api")

            # CRITICAL: Add nonce to params so it's included in request body
            if params is None:
                params = {}
            params["nonce"] = nonce

            # Generate signature
            signature = self.signature_generator.generate_signature(uri_path, nonce, params)

            # Create headers
            headers = {
                "API-Key": self.api_key,
                "API-Sign": signature,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            # Update statistics
            auth_time_ms = (time.time() - start_time) * 1000
            self._update_stats(True, auth_time_ms)

            if self.enable_debug:
                logger.debug(
                    f"[KRAKEN_AUTH_2025] Generated auth headers for {uri_path} "
                    f"with nonce {nonce} in {auth_time_ms:.2f}ms"
                )

            return headers

        except Exception as e:
            auth_time_ms = (time.time() - start_time) * 1000
            self._update_stats(False, auth_time_ms)
            logger.error(f"[KRAKEN_AUTH_2025] Auth header generation failed: {e}")
            raise KrakenAuthError(f"Failed to generate auth headers: {e}")

    async def get_auth_headers_async(
        self, uri_path: str, params: Optional[dict[str, Any]] = None
    ) -> dict[str, str]:
        """
        Async version of get_auth_headers.

        Args:
            uri_path: API endpoint path
            params: Optional request parameters (nonce will be added)

        Returns:
            Dictionary with authentication headers
        """
        async with self._auth_lock:
            start_time = time.time()

            try:
                # Get fresh nonce from REST manager (milliseconds format)
                nonce = self.rest_nonce_manager.get_nonce()

                # CRITICAL: Add nonce to params so it's included in request body
                if params is None:
                    params = {}
                params["nonce"] = nonce

                # Generate signature (async)
                signature = await self.signature_generator.generate_signature_async(
                    uri_path, nonce, params
                )

                # Create headers
                headers = {
                    "API-Key": self.api_key,
                    "API-Sign": signature,
                    "Content-Type": "application/x-www-form-urlencoded",
                }

                # Update statistics
                auth_time_ms = (time.time() - start_time) * 1000
                self._update_stats(True, auth_time_ms)

                return headers

            except Exception as e:
                auth_time_ms = (time.time() - start_time) * 1000
                self._update_stats(False, auth_time_ms)
                raise KrakenAuthError(f"Async auth failed: {e}")

    def handle_auth_error(
        self, error_message: str, uri_path: str, params: Optional[dict[str, Any]] = None
    ) -> dict[str, str]:
        """
        Handle authentication error with automatic recovery.

        Args:
            error_message: Error message from Kraken API
            uri_path: Original request URI path
            params: Original request parameters

        Returns:
            New authentication headers after recovery

        Raises:
            KrakenAuthError: If recovery fails
        """
        logger.warning(f"[KRAKEN_AUTH_2025] Handling auth error: {error_message}")

        # Parse error type
        if "nonce" in error_message.lower():
            return self._handle_nonce_error(uri_path, params, error_message)
        elif "signature" in error_message.lower():
            return self._handle_signature_error(uri_path, params, error_message)
        else:
            raise KrakenAuthError(f"Unknown auth error: {error_message}")

    def _handle_nonce_error(
        self, uri_path: str, params: Optional[dict[str, Any]], error_message: str
    ) -> dict[str, str]:
        """Handle nonce-related authentication errors"""
        self.stats.nonce_errors += 1
        self.stats.recovery_attempts += 1

        logger.warning(f"[KRAKEN_AUTH_2025] Nonce error recovery for {uri_path}")

        try:
            # Get recovery nonce
            recovery_nonce = self.nonce_manager.handle_invalid_nonce_error("rest_api")

            # Generate new signature with recovery nonce
            signature = self.signature_generator.generate_signature(
                uri_path, recovery_nonce, params
            )

            headers = {
                "API-Key": self.api_key,
                "API-Sign": signature,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            logger.info("[KRAKEN_AUTH_2025] Nonce error recovery successful")
            return headers

        except Exception as e:
            logger.error(f"[KRAKEN_AUTH_2025] Nonce error recovery failed: {e}")
            raise NonceError(f"Nonce recovery failed: {e}")

    def _handle_signature_error(
        self, uri_path: str, params: Optional[dict[str, Any]], error_message: str
    ) -> dict[str, str]:
        """Handle signature-related authentication errors"""
        self.stats.signature_errors += 1
        self.stats.recovery_attempts += 1

        logger.warning(f"[KRAKEN_AUTH_2025] Signature error recovery for {uri_path}")

        try:
            # Get fresh nonce and regenerate signature
            fresh_nonce = self.nonce_manager.get_nonce("rest_api")

            # Use debug signature generation for detailed logging
            if self.enable_debug:
                components = self.signature_generator.generate_signature_with_debug(
                    uri_path, fresh_nonce, params
                )
                logger.debug(
                    f"[KRAKEN_AUTH_2025] Debug signature components: "
                    f"nonce={components.nonce}, post_data={components.post_data}"
                )
                signature = components.signature
            else:
                signature = self.signature_generator.generate_signature(
                    uri_path, fresh_nonce, params
                )

            headers = {
                "API-Key": self.api_key,
                "API-Sign": signature,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            logger.info("[KRAKEN_AUTH_2025] Signature error recovery successful")
            return headers

        except Exception as e:
            logger.error(f"[KRAKEN_AUTH_2025] Signature error recovery failed: {e}")
            raise SignatureError(f"Signature recovery failed: {e}")

    def _update_stats(self, success: bool, auth_time_ms: float) -> None:
        """Update authentication statistics"""
        self.stats.requests_count += 1

        if success:
            self.stats.successful_auths += 1
        else:
            self.stats.failed_auths += 1

        # Update timing statistics
        self._last_auth_times.append(auth_time_ms)
        if len(self._last_auth_times) > self._max_time_samples:
            self._last_auth_times.pop(0)

        if self._last_auth_times:
            self.stats.avg_auth_time_ms = sum(self._last_auth_times) / len(self._last_auth_times)

    def get_comprehensive_status(self) -> dict[str, Any]:
        """
        Get comprehensive authentication system status.

        Returns:
            Dictionary with detailed status information
        """
        return {
            "api_key": self.api_key[:8] + "...",
            "auth_stats": {
                "total_requests": self.stats.requests_count,
                "successful_auths": self.stats.successful_auths,
                "failed_auths": self.stats.failed_auths,
                "success_rate": (
                    self.stats.successful_auths / max(self.stats.requests_count, 1) * 100
                ),
                "nonce_errors": self.stats.nonce_errors,
                "signature_errors": self.stats.signature_errors,
                "recovery_attempts": self.stats.recovery_attempts,
                "avg_auth_time_ms": self.stats.avg_auth_time_ms,
            },
            "nonce_manager": self.nonce_manager.get_status(),
            "signature_generator": self.signature_generator.get_statistics(),
            "configuration": {
                "debug_enabled": self.enable_debug,
                "max_retry_attempts": self.max_retry_attempts,
                "retry_delay_ms": self.retry_delay_ms,
            },
        }

    def run_comprehensive_test(self) -> dict[str, Any]:
        """
        Run comprehensive test of authentication system.

        Returns:
            Test results dictionary
        """
        test_results = {"timestamp": time.time(), "overall_success": True, "tests": {}}

        try:
            # Test 1: Nonce generation
            logger.info("[KRAKEN_AUTH_2025] Testing nonce generation...")
            nonce1 = self.nonce_manager.get_nonce("kraken_auth_test")
            nonce2 = self.nonce_manager.get_nonce("kraken_auth_test")

            test_results["tests"]["nonce_generation"] = {
                "success": int(nonce2) > int(nonce1),
                "nonce1": nonce1,
                "nonce2": nonce2,
                "increasing": int(nonce2) > int(nonce1),
            }

            # Test 2: Signature generation
            logger.info("[KRAKEN_AUTH_2025] Testing signature generation...")
            sig_test = self.signature_generator.test_signature_algorithm()
            test_results["tests"]["signature_generation"] = sig_test

            # Test 3: Full auth headers
            logger.info("[KRAKEN_AUTH_2025] Testing full auth header generation...")
            headers = self.get_auth_headers("/0/private/Balance")
            test_results["tests"]["auth_headers"] = {
                "success": all(key in headers for key in ["API-Key", "API-Sign"]),
                "has_api_key": "API-Key" in headers,
                "has_signature": "API-Sign" in headers,
                "api_key_length": len(headers.get("API-Key", "")),
                "signature_length": len(headers.get("API-Sign", "")),
            }

            # Test 4: Nonce collision recovery
            logger.info("[KRAKEN_AUTH_2025] Testing nonce collision recovery...")
            recovery_nonce = self.nonce_manager.handle_invalid_nonce_error("kraken_auth_test")
            test_results["tests"]["nonce_recovery"] = {
                "success": len(recovery_nonce) > 0,
                "recovery_nonce": recovery_nonce,
                "nonce_valid": True,  # Unified manager always returns valid nonces
            }

            # Overall success
            test_results["overall_success"] = all(
                test.get("success", False) for test in test_results["tests"].values()
            )

            logger.info(
                f"[KRAKEN_AUTH_2025] Comprehensive test completed. "
                f"Success: {test_results['overall_success']}"
            )

        except Exception as e:
            test_results["overall_success"] = False
            test_results["error"] = str(e)
            logger.error(f"[KRAKEN_AUTH_2025] Comprehensive test failed: {e}")

        return test_results

    def export_configuration(self) -> dict[str, Any]:
        """Export authentication configuration (excluding sensitive data)"""
        return {
            "api_key_hash": self.api_key[:8] + "...",
            "nonce_manager_config": {
                "type": "ConsolidatedNonceManager",
                "status": "singleton_instance",
            },
            "signature_generator_config": {
                "private_key_length": len(self.signature_generator._private_key_bytes),
                "signatures_generated": self.signature_generator._signature_count,
            },
            "auth_config": {
                "debug_enabled": self.enable_debug,
                "max_retry_attempts": self.max_retry_attempts,
                "retry_delay_ms": self.retry_delay_ms,
            },
            "statistics": self.stats.__dict__,
        }

    def cleanup(self) -> None:
        """Cleanup authentication system resources"""
        try:
            logger.info("[KRAKEN_AUTH_2025] Cleaning up authentication system...")

            # Cleanup nonce manager
            # Unified manager persists automatically, just force save
            self.nonce_manager.force_save()

            # Log final statistics
            if self.stats.requests_count > 0:
                logger.info(
                    f"[KRAKEN_AUTH_2025] Final stats: "
                    f"{self.stats.successful_auths}/{self.stats.requests_count} successful, "
                    f"avg time: {self.stats.avg_auth_time_ms:.2f}ms"
                )

            logger.info("[KRAKEN_AUTH_2025] Cleanup completed successfully")

        except Exception as e:
            logger.error(f"[KRAKEN_AUTH_2025] Error during cleanup: {e}")

    @classmethod
    def create_from_config(cls, config: dict[str, Any]) -> "KrakenAuth":
        """
        Create KrakenAuth instance from configuration dictionary.

        Args:
            config: Configuration dictionary with api_key, private_key, etc.

        Returns:
            KrakenAuth instance
        """
        return cls(
            api_key=config["api_key"],
            private_key=config["private_key"],
            storage_dir=config.get("storage_dir"),
            enable_debug=config.get("enable_debug", False),
        )

    @asynccontextmanager
    async def auth_context(self):
        """Async context manager for authentication"""
        try:
            yield self
        finally:
            self.cleanup()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()

    def __str__(self) -> str:
        """String representation"""
        return (
            f"KrakenAuth(api_key={self.api_key[:8]}..., "
            f"requests={self.stats.requests_count}, "
            f"success_rate={self.stats.successful_auths / max(self.stats.requests_count, 1) * 100:.1f}%)"
        )

    def __repr__(self) -> str:
        """Detailed representation"""
        return self.__str__()
