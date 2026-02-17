"""Asynchronous Promptory client with caching."""

from __future__ import annotations

import logging

import httpx

from promptory.cache import PromptCache
from promptory.models import Prompt
from promptory.exceptions import PromptoryError, NotFoundError, AuthenticationError

logger = logging.getLogger(__name__)


class AsyncPromptClient:
    """Async client for fetching prompts from a Promptory server.

    Usage:
        async with AsyncPromptClient(base_url="...", api_key="...") as client:
            prompt = await client.get("550e8400-...")
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        cache_ttl: int = 300,
        cache_max_size: int = 1000,
        timeout: float = 10.0,
        retry_count: int = 3,
    ):
        self._retry_count = retry_count
        self._cache = PromptCache(max_size=cache_max_size, ttl=cache_ttl)
        self._http = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/api/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def get(self, prompt_id: str) -> Prompt:
        return await self._fetch(f"id:{prompt_id}", f"/prompts/{prompt_id}")

    async def get_by_name(
        self, org: str, app: str, name: str, environment: str | None = None
    ) -> Prompt:
        cache_key = f"name:{org}/{app}/{name}:{environment or 'any'}"
        params = {"environment": environment} if environment else {}
        return await self._fetch(cache_key, f"/prompts/by-name/{org}/{app}/{name}", params=params)

    async def render(self, prompt_id: str, variables: dict) -> str:
        return (await self.get(prompt_id)).render(variables)

    async def _fetch(self, cache_key: str, path: str, params: dict | None = None) -> Prompt:
        entry, is_fresh = self._cache.get(cache_key)
        if entry and is_fresh:
            return Prompt.from_api_response(entry.data)

        etag = entry.etag if entry else None
        headers = {"If-None-Match": etag} if etag else {}

        for attempt in range(self._retry_count):
            try:
                resp = await self._http.get(path, params=params, headers=headers)
                break
            except httpx.TransportError:
                if attempt == self._retry_count - 1:
                    if entry:
                        return Prompt.from_api_response(entry.data)
                    raise PromptoryError("Failed to connect to Promptory server")

        if resp.status_code == 304:
            self._cache.refresh_ttl(cache_key)
            return Prompt.from_api_response(entry.data)
        if resp.status_code == 401:
            raise AuthenticationError()
        if resp.status_code == 404:
            raise NotFoundError(f"Prompt not found: {path}")
        if resp.status_code >= 400:
            raise PromptoryError(f"API error: {resp.status_code}", status_code=resp.status_code)

        data = resp.json()
        self._cache.put(cache_key, data, resp.headers.get("etag"))
        return Prompt.from_api_response(data)

    async def close(self):
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
