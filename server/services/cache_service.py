"""In-memory prompt cache with ETag support for the public API."""

from __future__ import annotations

import hashlib
import logging
import time
import threading
from collections import OrderedDict

logger = logging.getLogger(__name__)


class PromptCache:
    """Thread-safe in-memory LRU cache with ETag support."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> tuple[dict | None, str | None, bool]:
        """Get a cached prompt. Returns (data, etag, is_fresh).

        Returns (None, None, False) on cache miss.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None, None, False

            # Move to end (most recently used)
            self._cache.move_to_end(key)

            is_fresh = (time.time() - entry.cached_at) < self._default_ttl
            return entry.data, entry.etag, is_fresh

    def put(self, key: str, data: dict, etag: str | None = None) -> None:
        """Store a prompt in cache."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = _CacheEntry(
                data=data,
                etag=etag or _generate_etag(data),
                cached_at=time.time(),
            )
            # Evict LRU if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_by_prefix(self, prefix: str) -> int:
        """Remove all keys matching a prefix. Returns count removed."""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class _CacheEntry:
    __slots__ = ("data", "etag", "cached_at")

    def __init__(self, data: dict, etag: str, cached_at: float):
        self.data = data
        self.etag = etag
        self.cached_at = cached_at


def _generate_etag(data: dict) -> str:
    """Generate an ETag from prompt data."""
    version = data.get("version", "")
    git_sha = data.get("git_sha", "")
    if version and git_sha:
        return f'"{version}-{git_sha[:8]}"'
    content = f"{data.get('id', '')}{data.get('updated_at', '')}"
    return f'"{hashlib.md5(content.encode()).hexdigest()[:16]}"'


# Global cache instance
prompt_cache = PromptCache()
