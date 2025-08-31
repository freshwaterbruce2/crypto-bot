import threading
import time
from typing import Dict


class ConsolidatedNonceManager:
    """Simple microsecond-precision, per-key monotonic nonce manager."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_nonce_by_key: Dict[str, int] = {}

    def get_nonce(self, key: str) -> int:
        now_us = time.time_ns() // 1_000  # microseconds
        with self._lock:
            last = self._last_nonce_by_key.get(key, 0)
            nonce = now_us if now_us > last else last + 1
            self._last_nonce_by_key[key] = nonce
            return nonce


_singleton: ConsolidatedNonceManager | None = None


def get_unified_nonce_manager() -> ConsolidatedNonceManager:
    global _singleton
    if _singleton is None:
        _singleton = ConsolidatedNonceManager()
    return _singleton