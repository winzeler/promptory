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

    def invalidate_by_prefix(self, prefix: str) -> int:
        """Invalidate all entries whose key starts with the given prefix. Returns count removed."""
        with self._lock:
            to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in to_remove:
                del self._cache[k]
            return len(to_remove)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def keys(self) -> list[str]:
        """Return a snapshot of all cache keys."""
        with self._lock:
            return list(self._cache.keys())

    def stats(self) -> dict:
        """Return cache statistics: total entries, fresh/stale breakdown, TTL, max size, oldest entry age."""
        now = time.time()
        with self._lock:
            total = len(self._cache)
            fresh = 0
            oldest_age = 0.0
            for entry in self._cache.values():
                age = now - entry.fetched_at
                if age < self._ttl:
                    fresh += 1
                if age > oldest_age:
                    oldest_age = age
            return {
                "total_entries": total,
                "fresh_entries": fresh,
                "stale_entries": total - fresh,
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
                "oldest_entry_age_seconds": round(oldest_age, 1) if total > 0 else 0,
            }
