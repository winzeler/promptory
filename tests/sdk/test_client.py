"""Tests for PromptClient and AsyncPromptClient.

Uses httpx mock transport to simulate server responses without real HTTP calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the SDK package is importable
sdk_src = str(Path(__file__).resolve().parent.parent.parent / "sdk" / "src")
if sdk_src not in sys.path:
    sys.path.insert(0, sdk_src)

import json
import time
from unittest.mock import patch

import httpx
import pytest

from promptory.client import PromptClient
from promptory.async_client import AsyncPromptClient
from promptory.exceptions import PromptoryError, NotFoundError, AuthenticationError, RateLimitError


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_PROMPT = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "greeting",
    "version": "1.0.0",
    "org": "testorg",
    "app": "testapp",
    "domain": "test",
    "description": "A greeting prompt",
    "type": "chat",
    "role": "system",
    "body": "Hello {{ name }}, welcome to {{ place }}.",
    "environment": "production",
    "active": True,
    "tags": ["greeting"],
    "git_sha": "abc123",
    "updated_at": "2026-01-01T00:00:00",
}


def _mock_transport(responses: list[tuple[int, dict | None, dict | None]]):
    """Create a mock httpx transport that returns pre-configured responses.

    Each item in responses is (status_code, json_body, headers).
    Responses are consumed in order; last one repeats forever.
    """
    call_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        status, body, headers = responses[idx]
        return httpx.Response(
            status,
            json=body,
            headers=headers or {},
        )

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Sync client tests
# ---------------------------------------------------------------------------

class TestPromptClient:
    def test_get_prompt(self):
        transport = _mock_transport([(200, SAMPLE_PROMPT, {"etag": '"v1"'})])
        client = PromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        prompt = client.get(SAMPLE_PROMPT["id"])
        assert prompt.name == "greeting"
        assert prompt.body == "Hello {{ name }}, welcome to {{ place }}."
        client.close()

    def test_get_by_name(self):
        transport = _mock_transport([(200, SAMPLE_PROMPT, {"etag": '"v1"'})])
        client = PromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        prompt = client.get_by_name("testorg", "testapp", "greeting")
        assert prompt.name == "greeting"
        client.close()

    def test_render(self):
        transport = _mock_transport([(200, SAMPLE_PROMPT, {"etag": '"v1"'})])
        client = PromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        result = client.render(SAMPLE_PROMPT["id"], {"name": "Alice", "place": "Wonderland"})
        assert "Alice" in result
        assert "Wonderland" in result
        client.close()

    def test_404_raises_not_found(self):
        transport = _mock_transport([(404, {"error": "not found"}, None)])
        client = PromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        with pytest.raises(NotFoundError):
            client.get("nonexistent")
        client.close()

    def test_401_raises_auth_error(self):
        transport = _mock_transport([(401, {"error": "unauthorized"}, None)])
        client = PromptClient(base_url="http://test", api_key="bad-key")
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        with pytest.raises(AuthenticationError):
            client.get("some-id")
        client.close()

    def test_500_raises_promptory_error(self):
        transport = _mock_transport([(500, {"error": "server error"}, None)])
        client = PromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        with pytest.raises(PromptoryError) as exc_info:
            client.get("some-id")
        assert exc_info.value.status_code == 500
        client.close()

    def test_cache_hit(self):
        """Second request for same prompt should hit cache."""
        call_count = [0]

        def handler(request: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            return httpx.Response(200, json=SAMPLE_PROMPT, headers={"etag": '"v1"'})

        transport = httpx.MockTransport(handler)
        client = PromptClient(base_url="http://test", api_key="test-key", cache_ttl=300)
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        p1 = client.get(SAMPLE_PROMPT["id"])
        p2 = client.get(SAMPLE_PROMPT["id"])
        assert p1.name == p2.name
        # Only 1 HTTP call — second was a cache hit
        assert call_count[0] == 1
        client.close()

    def test_stale_cache_returns_prompt(self):
        """Stale cache entries are returned while background revalidation happens."""
        transport = _mock_transport([(200, SAMPLE_PROMPT, {"etag": '"v1"'})])
        client = PromptClient(base_url="http://test", api_key="test-key", cache_ttl=300)
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        # Fetch once — puts in cache
        p1 = client.get(SAMPLE_PROMPT["id"])
        assert p1.name == "greeting"

        # Manually mark as stale by setting fetched_at to 0
        cache_key = f"id:{SAMPLE_PROMPT['id']}"
        client._cache._cache[cache_key].fetched_at = 0

        # Second fetch returns stale entry immediately
        p2 = client.get(SAMPLE_PROMPT["id"])
        assert p2.name == "greeting"
        client.close()

    def test_cache_stats(self):
        transport = _mock_transport([(200, SAMPLE_PROMPT, {"etag": '"v1"'})])
        client = PromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        client.get(SAMPLE_PROMPT["id"])
        stats = client.cache_stats()
        assert stats["total_entries"] == 1
        assert stats["max_size"] == 1000
        client.close()

    def test_cache_invalidate(self):
        transport = _mock_transport([(200, SAMPLE_PROMPT, {"etag": '"v1"'})])
        client = PromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        client.get(SAMPLE_PROMPT["id"])
        assert client.cache_stats()["total_entries"] == 1

        count = client.cache_invalidate_all()
        assert count == 1
        assert client.cache_stats()["total_entries"] == 0
        client.close()

    def test_context_manager(self):
        transport = _mock_transport([(200, SAMPLE_PROMPT, {"etag": '"v1"'})])
        with PromptClient(base_url="http://test", api_key="test-key") as client:
            client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")
            prompt = client.get(SAMPLE_PROMPT["id"])
            assert prompt.name == "greeting"

    def test_transport_error_no_cache_raises(self):
        """Transport error with no cached entry raises PromptoryError."""
        transport = httpx.MockTransport(
            lambda req: (_ for _ in ()).throw(httpx.ConnectError("refused"))
        )
        client = PromptClient(base_url="http://test", api_key="test-key", retry_count=1)
        client._http = httpx.Client(transport=transport, base_url="http://test/api/v1")

        with pytest.raises(PromptoryError, match="Failed to connect"):
            client.get("some-id")
        client.close()


# ---------------------------------------------------------------------------
# Async client tests
# ---------------------------------------------------------------------------

class TestAsyncPromptClient:
    @pytest.mark.asyncio
    async def test_get_prompt(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=SAMPLE_PROMPT, headers={"etag": '"v1"'})
        )
        client = AsyncPromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test/api/v1")

        prompt = await client.get(SAMPLE_PROMPT["id"])
        assert prompt.name == "greeting"
        await client.close()

    @pytest.mark.asyncio
    async def test_get_by_name(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=SAMPLE_PROMPT, headers={"etag": '"v1"'})
        )
        client = AsyncPromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test/api/v1")

        prompt = await client.get_by_name("testorg", "testapp", "greeting")
        assert prompt.name == "greeting"
        await client.close()

    @pytest.mark.asyncio
    async def test_render(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=SAMPLE_PROMPT, headers={"etag": '"v1"'})
        )
        client = AsyncPromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test/api/v1")

        result = await client.render(SAMPLE_PROMPT["id"], {"name": "Alice", "place": "Wonderland"})
        assert "Alice" in result
        await client.close()

    @pytest.mark.asyncio
    async def test_404_raises_not_found(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(404, json={"error": "not found"})
        )
        client = AsyncPromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test/api/v1")

        with pytest.raises(NotFoundError):
            await client.get("nonexistent")
        await client.close()

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(401, json={"error": "unauthorized"})
        )
        client = AsyncPromptClient(base_url="http://test", api_key="bad-key")
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test/api/v1")

        with pytest.raises(AuthenticationError):
            await client.get("some-id")
        await client.close()

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        call_count = [0]

        def handler(request: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            return httpx.Response(200, json=SAMPLE_PROMPT, headers={"etag": '"v1"'})

        transport = httpx.MockTransport(handler)
        client = AsyncPromptClient(base_url="http://test", api_key="test-key", cache_ttl=300)
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test/api/v1")

        await client.get(SAMPLE_PROMPT["id"])
        await client.get(SAMPLE_PROMPT["id"])
        assert call_count[0] == 1  # Only 1 HTTP call
        await client.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=SAMPLE_PROMPT, headers={"etag": '"v1"'})
        )
        async with AsyncPromptClient(base_url="http://test", api_key="test-key") as client:
            client._http = httpx.AsyncClient(transport=transport, base_url="http://test/api/v1")
            prompt = await client.get(SAMPLE_PROMPT["id"])
            assert prompt.name == "greeting"

    @pytest.mark.asyncio
    async def test_cache_invalidate_all(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=SAMPLE_PROMPT, headers={"etag": '"v1"'})
        )
        client = AsyncPromptClient(base_url="http://test", api_key="test-key")
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test/api/v1")

        await client.get(SAMPLE_PROMPT["id"])
        assert client.cache_stats()["total_entries"] == 1

        count = client.cache_invalidate_all()
        assert count == 1
        assert client.cache_stats()["total_entries"] == 0
        await client.close()
