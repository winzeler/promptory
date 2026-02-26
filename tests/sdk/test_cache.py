"""Tests for SDK PromptCache."""

from __future__ import annotations

import sys
from pathlib import Path

# Add SDK source to path so we can import without installing the SDK package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sdk" / "src"))

from promptdis.cache import PromptCache  # noqa: E402


def test_get_set():
    cache = PromptCache(max_size=10, ttl=60)
    cache.put("k1", {"body": "hello"}, etag='"v1"')
    entry, is_fresh = cache.get("k1")
    assert entry is not None
    assert entry.data == {"body": "hello"}
    assert entry.etag == '"v1"'
    assert is_fresh is True


def test_ttl_expiry():
    cache = PromptCache(max_size=10, ttl=1)
    cache.put("k1", {"body": "hello"})
    entry, is_fresh = cache.get("k1")
    assert is_fresh is True

    # Manually age the entry
    entry.fetched_at -= 2
    _, is_fresh = cache.get("k1")
    assert is_fresh is False


def test_lru_eviction():
    cache = PromptCache(max_size=3, ttl=60)
    cache.put("a", {"v": 1})
    cache.put("b", {"v": 2})
    cache.put("c", {"v": 3})
    cache.put("d", {"v": 4})  # should evict "a"

    entry, _ = cache.get("a")
    assert entry is None

    entry, _ = cache.get("d")
    assert entry is not None
    assert entry.data == {"v": 4}


def test_stats():
    cache = PromptCache(max_size=100, ttl=60)
    cache.put("k1", {"v": 1})
    cache.put("k2", {"v": 2})

    stats = cache.stats()
    assert stats["total_entries"] == 2
    assert stats["fresh_entries"] == 2
    assert stats["stale_entries"] == 0
    assert stats["max_size"] == 100
    assert stats["ttl_seconds"] == 60


def test_invalidate():
    cache = PromptCache(max_size=10, ttl=60)
    cache.put("k1", {"v": 1})
    cache.invalidate("k1")
    entry, _ = cache.get("k1")
    assert entry is None


def test_invalidate_by_prefix():
    cache = PromptCache(max_size=10, ttl=60)
    cache.put("id:abc", {"v": 1})
    cache.put("id:def", {"v": 2})
    cache.put("name:xyz", {"v": 3})
    removed = cache.invalidate_by_prefix("id:")
    assert removed == 2
    assert cache.stats()["total_entries"] == 1
