"""In-memory LRU cache with ETag and TTL support for the SDK."""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    data: dict
    etag: str | None
    fetched_at: float


class PromptCache:
    """Thread-safe LRU cache with TTL and stale-while-revalidate support."""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> tuple[CacheEntry | None, bool]:
        """Get a cache entry. Returns (entry, is_fresh)."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None, False
            self._cache.move_to_end(key)
            is_fresh = (time.time() - entry.fetched_at) < self._ttl
            return entry, is_fresh

    def put(self, key: str, data: dict, etag: str | None = None) -> None:
        """Store an entry in the cache."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = CacheEntry(data=data, etag=etag, fetched_at=time.time())
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def refresh_ttl(self, key: str) -> None:
        """Reset the TTL for an entry (e.g., after 304 response)."""
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                entry.fetched_at = time.time()

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
