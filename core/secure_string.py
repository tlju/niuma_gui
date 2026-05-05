from __future__ import annotations

import threading
from typing import Optional


class SecureString:
    _lock = threading.Lock()

    def __init__(self, value: str = ""):
        self._data = bytearray(value.encode('utf-8')) if value else bytearray()
        self._consumed = False

    @property
    def value(self) -> str:
        if self._consumed:
            return ""
        return self._data.decode('utf-8', errors='ignore')

    def consume(self) -> str:
        with self._lock:
            if self._consumed:
                return ""
            result = self._data.decode('utf-8', errors='ignore')
            self._clear()
            return result

    def _clear(self):
        for i in range(len(self._data)):
            self._data[i] = 0
        self._data = bytearray()
        self._consumed = True

    def is_consumed(self) -> bool:
        return self._consumed

    def __del__(self):
        self._clear()

    def __repr__(self) -> str:
        return f"<SecureString(consumed={self._consumed})>"

    def __str__(self) -> str:
        return "***REDACTED***"

    def __bool__(self) -> bool:
        return not self._consumed and len(self._data) > 0
