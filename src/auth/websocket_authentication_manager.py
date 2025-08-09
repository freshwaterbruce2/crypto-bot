from contextlib import contextmanager


class WebSocketAuthenticationError(Exception):
    pass


class TokenExpiredError(WebSocketAuthenticationError):
    pass


class NonceValidationError(WebSocketAuthenticationError):
    pass


class CircuitBreakerOpenError(WebSocketAuthenticationError):
    pass


class WebSocketAuthenticationManager:
    def __init__(self) -> None:
        self._token = None

    def get_token(self) -> str:
        return self._token or "stub-token"


def create_websocket_auth_manager() -> WebSocketAuthenticationManager:
    return WebSocketAuthenticationManager()


@contextmanager
def websocket_auth_context():
    manager = create_websocket_auth_manager()
    try:
        yield manager
    finally:
        pass