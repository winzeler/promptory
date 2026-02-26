"""Synchronous Promptdis client with caching."""

from __future__ import annotations

import logging
import random
import time
import threading

import httpx

from promptdis.cache import PromptCache
from promptdis.models import Prompt
from promptdis.exceptions import PromptdisError, NotFoundError, AuthenticationError

logger = logging.getLogger(__name__)


class PromptClient:
    """Synchronous client for fetching prompts from a Promptdis server.

    Usage:
        client = PromptClient(
            base_url="https://prompts.futureself.app",
            api_key="pm_live_...",
        )
        prompt = client.get("550e8400-e29b-41d4-a716-446655440000")
        rendered = prompt.render(variables={...})
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
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._retry_count = retry_count
        self._cache = PromptCache(max_size=cache_max_size, ttl=cache_ttl)
        self._http = httpx.Client(
            base_url=f"{self._base_url}/api/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def get(self, prompt_id: str) -> Prompt:
        """Fetch a prompt by UUID."""
        return self._fetch(f"id:{prompt_id}", f"/prompts/{prompt_id}")

    def get_by_name(
        self, org: str, app: str, name: str, environment: str | None = None
    ) -> Prompt:
        """Fetch a prompt by its fully qualified name (org/app/name)."""
        cache_key = f"name:{org}/{app}/{name}:{environment or 'any'}"
        params = {"environment": environment} if environment else {}
        return self._fetch(cache_key, f"/prompts/by-name/{org}/{app}/{name}", params=params)

    def render(self, prompt_id: str, variables: dict) -> str:
        """Fetch a prompt and render it with Jinja2 variables."""
        return self.get(prompt_id).render(variables)

    def _fetch(self, cache_key: str, path: str, params: dict | None = None) -> Prompt:
        entry, is_fresh = self._cache.get(cache_key)
        if entry and is_fresh:
            return Prompt.from_api_response(entry.data)

        if entry:
            self._revalidate_background(cache_key, path, params, entry.etag)
            return Prompt.from_api_response(entry.data)

        return self._fetch_from_api(cache_key, path, params, etag=entry.etag if entry else None)

    def _fetch_from_api(
        self, cache_key: str, path: str, params: dict | None, etag: str | None
    ) -> Prompt:
        headers = {"If-None-Match": etag} if etag else {}

        for attempt in range(self._retry_count):
            try:
                resp = self._http.get(path, params=params, headers=headers)
                break
            except httpx.TransportError:
                if attempt == self._retry_count - 1:
                    entry, _ = self._cache.get(cache_key)
                    if entry:
                        logger.warning("API unreachable, returning stale cache for %s", cache_key)
                        return Prompt.from_api_response(entry.data)
                    raise PromptdisError("Failed to connect to Promptdis server")
                # Exponential backoff with jitter: 0.5s, 1s, 2s base
                delay = (0.5 * (2 ** attempt)) + random.uniform(0, 0.25)
                logger.debug("Retry %d/%d after %.2fs", attempt + 1, self._retry_count, delay)
                time.sleep(delay)

        if resp.status_code == 304:
            self._cache.refresh_ttl(cache_key)
            entry, _ = self._cache.get(cache_key)
            return Prompt.from_api_response(entry.data)
        if resp.status_code == 401:
            raise AuthenticationError()
        if resp.status_code == 404:
            raise NotFoundError(f"Prompt not found: {path}")
        if resp.status_code >= 400:
            raise PromptdisError(f"API error: {resp.status_code}", status_code=resp.status_code)

        data = resp.json()
        self._cache.put(cache_key, data, resp.headers.get("etag"))
        return Prompt.from_api_response(data)

    def _revalidate_background(self, cache_key: str, path: str, params: dict | None, etag: str | None) -> None:
        def _work():
            try:
                self._fetch_from_api(cache_key, path, params, etag)
            except Exception as e:
                logger.debug("Background revalidation failed: %s", e)
        threading.Thread(target=_work, daemon=True).start()

    def cache_stats(self) -> dict:
        """Return SDK-side cache statistics."""
        return self._cache.stats()

    def cache_invalidate(self, prompt_name: str) -> int:
        """Invalidate cached entries for a specific prompt name. Returns count removed."""
        count = self._cache.invalidate_by_prefix(f"name:{prompt_name}")
        count += self._cache.invalidate_by_prefix(f"id:{prompt_name}")
        return count

    def cache_invalidate_all(self) -> int:
        """Invalidate all cached entries. Returns count removed."""
        stats = self._cache.stats()
        total = stats["total_entries"]
        self._cache.clear()
        return total

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
