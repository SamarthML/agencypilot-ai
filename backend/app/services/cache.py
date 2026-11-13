"""A small in-process TTL cache shared by features that cache LLM results."""

import time
from collections.abc import Callable


class TtlCache[V]:
    """In-memory TTL cache with oldest-insert eviction. Per-process is fine for one API instance."""

    def __init__(
        self,
        ttl_seconds: float,
        max_entries: int = 256,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._entries: dict[str, tuple[float, V]] = {}

    def get(self, key: str) -> V | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._entries[key]
            return None
        return value

    def set(self, key: str, value: V) -> None:
        self._entries.pop(key, None)  # re-inserting moves the key to the newest position
        if len(self._entries) >= self._max_entries:
            self._entries.pop(next(iter(self._entries)))
        self._entries[key] = (self._clock() + self._ttl, value)

    def clear(self) -> None:
        self._entries.clear()
