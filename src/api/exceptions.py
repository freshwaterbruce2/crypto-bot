"""
Kraken API Exception Classes
============================

Custom exception hierarchy for comprehensive error handling in the Kraken API client.
Maps Kraken API error codes to specific exception types for better error handling.

Exception Hierarchy:
- KrakenAPIError (base)
  ├── AuthenticationError (authentication failures)
  ├── RateLimitError (rate limit exceeded)
  ├── ValidationError (request validation failures)
  ├── NetworkError (network/connectivity issues)
  ├── InsufficientFundsError (insufficient balance)
  ├── OrderError (order-related errors)
  └── SystemError (Kraken system issues)

Usage:
    try:
        result = await client.add_order(...)
    except InsufficientFundsError as e:
        logger.error(f"Insufficient funds: {e}")
    except RateLimitError as e:
        await asyncio.sleep(e.retry_after)
    except KrakenAPIError as e:
        logger.error(f"API error: {e.error_code} - {e.message}")
"""

import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ErrorDetails:
    """
    Detailed error information from Kraken API.

    Attributes:
        error_code: Kraken error code
        message: Error message
        endpoint: API endpoint that failed
        request_data: Request data that caused the error
        response_data: Full response data
        timestamp: When the error occurred
        retry_after: Suggested retry delay in seconds
    """
    error_code: str
    message: str
    endpoint: Optional[str] = None
    request_data: Optional[dict[str, Any]] = None
    response_data: Optional[dict[str, Any]] = None
    timestamp: float = None
    retry_after: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class KrakenAPIError(Exception):
    """
    Base exception for all Kraken API errors.

    Provides common functionality for error handling, logging,
    and retry logic across all Kraken API error types.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        endpoint: Optional[str] = None,
        request_data: Optional[dict[str, Any]] = None,
        response_data: Optional[dict[str, Any]] = None,
        retry_after: Optional[float] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize Kraken API error.

        Args:
            message: Error message
            error_code: Kraken error code
            endpoint: API endpoint that failed
            request_data: Request data that caused the error
            response_data: Full response data
            retry_after: Suggested retry delay in seconds
            original_exception: Original exception that caused this error
        """
        super().__init__(message)

        self.details = ErrorDetails(
            error_code=error_code or "UNKNOWN",
            message=message,
            endpoint=endpoint,
            request_data=request_data,
            response_data=response_data,
            retry_after=retry_after
        )

        self.original_exception = original_exception

    @property
    def error_code(self) -> str:
        """Get error code."""
        return self.details.error_code

    @property
    def message(self) -> str:
        """Get error message."""
        return self.details.message

    @property
    def endpoint(self) -> Optional[str]:
        """Get endpoint that failed."""
        return self.details.endpoint

    @property
    def retry_after(self) -> Optional[float]:
        """Get suggested retry delay."""
        return self.details.retry_after

    def is_retryable(self) -> bool:
        """
        Check if this error is retryable.

        Returns:
            True if the error can be retried
        """
        return self.retry_after is not None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert error to dictionary format.

        Returns:
            Dictionary representation of the error
        """
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.details.error_code,
            'message': self.details.message,
            'endpoint': self.details.endpoint,
            'timestamp': self.details.timestamp,
            'retry_after': self.details.retry_after,
            'retryable': self.is_retryable()
        }

    def __str__(self) -> str:
        """String representation of the error."""
        parts = [f"{self.__class__.__name__}: {self.details.message}"]

        if self.details.error_code != "UNKNOWN":
            parts.append(f"(code: {self.details.error_code})")

        if self.details.endpoint:
            parts.append(f"[endpoint: {self.details.endpoint}]")

        return " ".join(parts)

    def __repr__(self) -> str:
        """Detailed representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.details.message}', "
            f"error_code='{self.details.error_code}', "
            f"endpoint='{self.details.endpoint}'"
            f")"
        )


class AuthenticationError(KrakenAPIError):
    """
    Authentication-related errors.

    Raised when API key, signature, or nonce issues occur.
    Common error codes: EAuth:Invalid, EAuth:Invalid key, EAuth:Invalid nonce
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)

        # Authentication errors are typically not retryable
        # unless it's a nonce issue
        if "nonce" in message.lower():
            self.details.retry_after = 1.0  # Quick retry for nonce issues

    def is_retryable(self) -> bool:
        """Authentication errors are retryable only for nonce issues."""
        return "nonce" in self.details.message.lower()


class RateLimitError(KrakenAPIError):
    """
    Rate limiting errors.

    Raised when API rate limits are exceeded.
    Common error codes: EGeneral:Temporary lockout, EAPI:Rate limit exceeded
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        **kwargs
    ):
        # Default retry delay for rate limit errors
        if retry_after is None:
            retry_after = 60.0  # Default to 1 minute

        super().__init__(message, retry_after=retry_after, **kwargs)

    def is_retryable(self) -> bool:
        """Rate limit errors are always retryable."""
        return True


class ValidationError(KrakenAPIError):
    """
    Request validation errors.

    Raised when request parameters are invalid or missing.
    Common error codes: EGeneral:Invalid arguments, EOrder:Invalid order
    """

    def __init__(self, message: str, validation_errors: Optional[list[str]] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []

    def is_retryable(self) -> bool:
        """Validation errors are typically not retryable."""
        return False


class NetworkError(KrakenAPIError):
    """
    Network and connectivity errors.

    Raised when network issues prevent API communication.
    Includes timeout, connection, and DNS resolution errors.
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        **kwargs
    ):
        # Network errors should be retried with exponential backoff
        if retry_after is None:
            retry_after = 5.0  # Default to 5 seconds

        super().__init__(message, retry_after=retry_after, **kwargs)

    def is_retryable(self) -> bool:
        """Network errors are retryable."""
        return True


class InsufficientFundsError(KrakenAPIError):
    """
    Insufficient funds errors.

    Raised when account doesn't have sufficient balance for the operation.
    Common error codes: EGeneral:Insufficient funds, EOrder:Insufficient funds
    """

    def __init__(
        self,
        message: str,
        required_amount: Optional[float] = None,
        available_amount: Optional[float] = None,
        currency: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.required_amount = required_amount
        self.available_amount = available_amount
        self.currency = currency

    def is_retryable(self) -> bool:
        """Insufficient funds errors are not retryable."""
        return False

    def to_dict(self) -> dict[str, Any]:
        """Include funding details in dictionary representation."""
        result = super().to_dict()
        result.update({
            'required_amount': self.required_amount,
            'available_amount': self.available_amount,
            'currency': self.currency
        })
        return result


class OrderError(KrakenAPIError):
    """
    Order-related errors.

    Raised when order operations fail due to order-specific issues.
    Common error codes: EOrder:Order minimum not met, EOrder:Invalid price
    """

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        order_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.order_id = order_id
        self.order_type = order_type

    def is_retryable(self) -> bool:
        """
        Order errors may be retryable depending on the specific error.

        Returns:
            True if the order error can be retried
        """
        # Some order errors are retryable (temporary issues)
        retryable_messages = [
            "service temporarily unavailable",
            "market in cancel_only mode",
            "market in post_only mode"
        ]

        return any(msg in self.details.message.lower() for msg in retryable_messages)

    def to_dict(self) -> dict[str, Any]:
        """Include order details in dictionary representation."""
        result = super().to_dict()
        result.update({
            'order_id': self.order_id,
            'order_type': self.order_type
        })
        return result


class SystemError(KrakenAPIError):
    """
    Kraken system errors.

    Raised when Kraken's systems are experiencing issues.
    Common error codes: EService:Unavailable, EGeneral:Internal error
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        **kwargs
    ):
        # System errors should be retried with longer delays
        if retry_after is None:
            retry_after = 30.0  # Default to 30 seconds

        super().__init__(message, retry_after=retry_after, **kwargs)

    def is_retryable(self) -> bool:
        """System errors are retryable."""
        return True


# Mapping of Kraken error codes to exception classes
KRAKEN_ERROR_MAPPING = {
    # Authentication errors
    'EAuth:Invalid': AuthenticationError,
    'EAuth:Invalid key': AuthenticationError,
    'EAuth:Invalid nonce': AuthenticationError,
    'EAuth:Invalid signature': AuthenticationError,

    # Rate limiting errors
    'EGeneral:Temporary lockout': RateLimitError,
    'EAPI:Rate limit exceeded': RateLimitError,
    'EGeneral:Too many requests': RateLimitError,

    # Validation errors
    'EGeneral:Invalid arguments': ValidationError,
    'EGeneral:Invalid request': ValidationError,
    'EOrder:Invalid order': ValidationError,
    'EOrder:Unknown position': ValidationError,

    # Insufficient funds errors
    'EGeneral:Insufficient funds': InsufficientFundsError,
    'EOrder:Insufficient funds': InsufficientFundsError,
    'EOrder:Insufficient margin': InsufficientFundsError,

    # Order errors
    'EOrder:Order minimum not met': OrderError,
    'EOrder:Invalid price': OrderError,
    'EOrder:Invalid volume': OrderError,
    'EOrder:Position limit exceeded': OrderError,
    'EOrder:Orders limit exceeded': OrderError,
    'EOrder:Unknown order': OrderError,
    'EOrder:Order not found': OrderError,

    # System errors
    'EService:Unavailable': SystemError,
    'EService:Market in cancel_only mode': SystemError,
    'EService:Market in post_only mode': SystemError,
    'EGeneral:Internal error': SystemError,
    'EGeneral:Service temporarily unavailable': SystemError,
}


def create_exception_from_error(
    error_code: str,
    message: str,
    endpoint: Optional[str] = None,
    request_data: Optional[dict[str, Any]] = None,
    response_data: Optional[dict[str, Any]] = None
) -> KrakenAPIError:
    """
    Create appropriate exception based on Kraken error code.

    Args:
        error_code: Kraken error code
        message: Error message
        endpoint: API endpoint that failed
        request_data: Request data that caused the error
        response_data: Full response data

    Returns:
        Appropriate KrakenAPIError subclass instance
    """
    exception_class = KRAKEN_ERROR_MAPPING.get(error_code, KrakenAPIError)

    return exception_class(
        message=message,
        error_code=error_code,
        endpoint=endpoint,
        request_data=request_data,
        response_data=response_data
    )


def parse_kraken_errors(
    response_data: dict[str, Any],
    endpoint: Optional[str] = None,
    request_data: Optional[dict[str, Any]] = None
) -> list[KrakenAPIError]:
    """
    Parse Kraken API response and create appropriate exceptions.

    Args:
        response_data: Kraken API response data
        endpoint: API endpoint that was called
        request_data: Request data that was sent

    Returns:
        List of KrakenAPIError instances
    """
    errors = []

    # Kraken errors are in the 'error' field as a list
    error_list = response_data.get('error', [])

    for error_msg in error_list:
        # Try to extract error code from message
        error_code = "UNKNOWN"
        if ':' in error_msg:
            potential_code = error_msg.split(':')[0] + ':' + error_msg.split(':')[1]
            if potential_code in KRAKEN_ERROR_MAPPING:
                error_code = potential_code

        error = create_exception_from_error(
            error_code=error_code,
            message=error_msg,
            endpoint=endpoint,
            request_data=request_data,
            response_data=response_data
        )

        errors.append(error)

    return errors


def raise_for_kraken_errors(
    response_data: dict[str, Any],
    endpoint: Optional[str] = None,
    request_data: Optional[dict[str, Any]] = None
) -> None:
    """
    Check Kraken API response for errors and raise appropriate exceptions.

    Args:
        response_data: Kraken API response data
        endpoint: API endpoint that was called
        request_data: Request data that was sent

    Raises:
        KrakenAPIError: If the response contains errors
    """
    if not response_data.get('error'):
        return  # No errors

    errors = parse_kraken_errors(response_data, endpoint, request_data)

    if len(errors) == 1:
        raise errors[0]
    elif len(errors) > 1:
        # Multiple errors - raise the first one with details about all
        primary_error = errors[0]
        all_messages = [error.message for error in errors]
        primary_error.details.message = f"Multiple errors: {'; '.join(all_messages)}"
        raise primary_error
