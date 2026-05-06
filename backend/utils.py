from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, *, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self._value: T | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def get_or_set(self, factory: Callable[[], T]) -> T:
        with self._lock:
            if self._value is None or time.monotonic() >= self._expires_at:
                self._value = factory()
                self._expires_at = time.monotonic() + self.ttl_seconds
            return self._value

    def clear(self) -> None:
        with self._lock:
            self._value = None
            self._expires_at = 0.0
