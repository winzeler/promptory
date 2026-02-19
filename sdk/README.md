# promptory

Python SDK for [Promptory](https://github.com/futureself-app/promptory) — Git-native LLM prompt management.

Fetch, cache, and render LLM prompts from a Promptory server. Supports both sync and async clients with built-in LRU caching, ETag revalidation, and retry logic.

## Installation

```bash
pip install promptory
```

For async support with HTTP/2:

```bash
pip install "promptory[async]"
```

**Requirements:** Python 3.10+

## Quick Start

```python
from promptory import PromptClient

client = PromptClient(
    base_url="http://localhost:8000",
    api_key="pm_live_...",
)

# Fetch a prompt by UUID
prompt = client.get("550e8400-e29b-41d4-a716-446655440000")
print(prompt.name)   # "meditation_script_relax"
print(prompt.body)   # Raw Jinja2 template

# Fetch by fully qualified name
prompt = client.get_by_name("myorg", "myapp", "meditation_script_relax")

# Render with variables
rendered = prompt.render(variables={
    "user": {"display_name": "Alice", "elevenlabs_voice_id": "abc123"},
    "vision": {"identity_statement": "I am confident"},
})
# rendered is a string ready to send to an LLM

client.close()
```

### Context Manager

```python
with PromptClient(base_url="http://localhost:8000", api_key="pm_live_...") as client:
    prompt = client.get_by_name("myorg", "myapp", "greeting")
    print(prompt.render({"user_name": "Alice"}))
```

### Async Client

```python
import asyncio
from promptory import AsyncPromptClient

async def main():
    async with AsyncPromptClient(
        base_url="http://localhost:8000",
        api_key="pm_live_...",
    ) as client:
        prompt = await client.get_by_name("myorg", "myapp", "greeting")
        rendered = prompt.render(variables={"name": "Alice"})
        print(rendered)

asyncio.run(main())
```

The async client uses `httpx.AsyncClient` under the hood. All methods mirror the sync client but return coroutines.

## Client Options

Both `PromptClient` and `AsyncPromptClient` accept the same options:

```python
client = PromptClient(
    base_url="http://localhost:8000",  # Promptory server URL
    api_key="pm_live_...",              # API key (generate in Promptory web UI)
    cache_ttl=300,          # Cache TTL in seconds (default: 300)
    cache_max_size=1000,    # Max cached prompts (default: 1000)
    timeout=10.0,           # Request timeout in seconds (default: 10.0)
    retry_count=3,          # Retry attempts on transport failure (default: 3)
)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `base_url` | (required) | Promptory server URL |
| `api_key` | (required) | API key starting with `pm_live_` or `pm_test_` |
| `cache_ttl` | `300` | Seconds before a cached entry is considered stale |
| `cache_max_size` | `1000` | Max entries in LRU cache before eviction |
| `timeout` | `10.0` | HTTP request timeout in seconds |
| `retry_count` | `3` | Number of retries on transport errors |

## Fetching Prompts

### By UUID

```python
prompt = client.get("550e8400-e29b-41d4-a716-446655440000")
```

### By Qualified Name

```python
prompt = client.get_by_name("org_name", "app_name", "prompt_name")
```

### By Name with Environment Filter

```python
prompt = client.get_by_name(
    "myorg", "myapp", "greeting",
    environment="production"
)
```

Only returns prompts in the specified environment (`development`, `staging`, or `production`).

### Render Shortcut

```python
# Fetch + render in one call
rendered = client.render("550e8400-...", variables={"name": "Alice"})
```

## Prompt Object

`Prompt` is a dataclass returned by `get()` and `get_by_name()`:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | UUID |
| `name` | `str` | Prompt name (e.g., `meditation_script_relax`) |
| `version` | `str` | Semantic version from front-matter |
| `org` | `str` | Organization name |
| `app` | `str` | Application name |
| `domain` | `str \| None` | Domain category (e.g., `meditation`, `coaching`) |
| `description` | `str \| None` | Human-readable description |
| `type` | `str` | `chat`, `completion`, `tts`, `transcription` |
| `role` | `str \| None` | LLM message role: `system`, `user`, `assistant` |
| `model` | `dict` | Model config: `default`, `temperature`, `max_tokens`, `fallback`, `top_p` |
| `modality` | `dict \| None` | Input/output modality config |
| `tts` | `dict \| None` | TTS provider/voice/settings |
| `audio` | `dict \| None` | Audio generation config |
| `environment` | `str` | `development`, `staging`, or `production` |
| `active` | `bool` | Whether the prompt is active |
| `tags` | `list[str]` | Tags for filtering |
| `body` | `str` | Raw Jinja2 template body |
| `includes` | `list[str]` | Referenced prompt names for composition |
| `meta` | `dict` | Full API response as dict |
| `git_sha` | `str \| None` | Git commit SHA |
| `updated_at` | `str \| None` | Last update timestamp |

### Rendering

```python
# Render with Jinja2 (sandboxed environment)
rendered = prompt.render(variables={
    "user": {"display_name": "Alice"},
    "items": ["focus", "calm", "gratitude"],
})
```

The `render()` method uses Jinja2's `SandboxedEnvironment`, supporting:
- Variable substitution: `{{ user.display_name }}`
- Conditionals: `{% if formal %}Dear{% else %}Hey{% endif %}`
- Loops: `{% for item in items %}{{ item }}{% endfor %}`
- Filters: `{{ name | upper }}`, `{{ name | default('World') }}`

**Note:** Prompt composition (`{% include "other_prompt" %}`) requires server-side rendering via `client.render()`. Local `prompt.render()` does not resolve includes.

### Accessing Model Config

```python
model_name = prompt.model.get("default")         # "gemini-2.0-flash"
temperature = prompt.model.get("temperature", 0.7)
max_tokens = prompt.model.get("max_tokens", 4000)
fallbacks = prompt.model.get("fallback", [])
```

## Caching

The SDK includes an in-memory LRU cache with ETag-based revalidation:

```
Request flow:
  1. Check in-memory LRU cache (keyed by prompt ID or qualified name)
  2. If HIT and fresh (age < cache_ttl) → return immediately (no network call)
  3. If HIT and stale (age >= cache_ttl) → return stale, revalidate in background thread
  4. If MISS → fetch from API with If-None-Match header
  5. If API returns 304 Not Modified → refresh cache TTL, return cached
  6. If API returns 200 → update cache with new data
  7. If API unreachable → return stale cached (if available), log warning
```

The stale-while-revalidate pattern means your application never blocks on cache misses after the first fetch, even when the server is temporarily unavailable.

### Cache Management

```python
# View cache stats
stats = client.cache_stats()
# {
#   "total_entries": 42,
#   "fresh_entries": 38,
#   "stale_entries": 4,
#   "max_size": 1000,
#   "ttl": 300,
#   "oldest_age_seconds": 287.5
# }

# Invalidate entries matching a prompt name
removed = client.cache_invalidate("meditation_script_relax")

# Clear entire cache
removed = client.cache_invalidate_all()
```

## Error Handling

```python
from promptory import PromptoryError, NotFoundError, AuthenticationError
from promptory.exceptions import RateLimitError

try:
    prompt = client.get("missing-id")
except NotFoundError:
    print("Prompt not found")
except AuthenticationError:
    print("Invalid or expired API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except PromptoryError as e:
    print(f"API error (HTTP {e.status_code}): {e}")
```

### Exception Hierarchy

| Exception | HTTP Status | Attributes | Description |
|-----------|-------------|------------|-------------|
| `PromptoryError` | any | `status_code` | Base exception for all SDK errors |
| `NotFoundError` | 404 | `status_code` | Prompt or resource not found |
| `AuthenticationError` | 401 | `status_code` | Invalid or missing API key |
| `RateLimitError` | 429 | `status_code`, `retry_after` | Rate limit exceeded |

## Integration Example

Using Promptory with a generic LLM client:

```python
from promptory import AsyncPromptClient

prompt_client = AsyncPromptClient(
    base_url="https://prompts.example.com",
    api_key="pm_live_...",
    cache_ttl=300,
)

async def generate_meditation(user, vision):
    # Fetch prompt — cached after first call
    prompt = await prompt_client.get_by_name(
        "futureself", "meditate", "meditation_script_relax"
    )

    # Render Jinja2 template with user context
    rendered = prompt.render(variables={
        "user": {"display_name": user.name, "elevenlabs_voice_id": user.voice_id},
        "vision": {"identity_statement": vision.statement, "deep_why": vision.why},
        "duration_minutes": 10,
    })

    # Send to LLM with model config from prompt metadata
    response = await llm.chat(
        messages=[{"role": prompt.role or "system", "content": rendered}],
        model=prompt.model["default"],
        temperature=prompt.model.get("temperature", 0.7),
        max_tokens=prompt.model.get("max_tokens", 4000),
    )

    return response.text
```

## API Reference

### PromptClient (sync)

| Method | Returns | Description |
|--------|---------|-------------|
| `get(prompt_id)` | `Prompt` | Fetch by UUID |
| `get_by_name(org, app, name, environment?)` | `Prompt` | Fetch by qualified name |
| `render(prompt_id, variables)` | `str` | Fetch and render with Jinja2 |
| `cache_stats()` | `dict` | Cache statistics |
| `cache_invalidate(name)` | `int` | Invalidate by name/ID prefix |
| `cache_invalidate_all()` | `int` | Clear all cache entries |
| `close()` | `None` | Close HTTP client |

### AsyncPromptClient (async)

Same methods as `PromptClient`. All fetch/render methods are `async` and must be awaited. Use `async with` for automatic cleanup.

### Prompt

| Method/Property | Type | Description |
|-----------------|------|-------------|
| `render(variables)` | `str` | Render Jinja2 template locally |
| `id` | `str` | Prompt UUID |
| `name` | `str` | Prompt name |
| `body` | `str` | Raw template body |
| `model` | `dict` | Model configuration |
| `meta` | `dict` | Full response data |

## Dependencies

- [httpx](https://www.python-httpx.org/) — HTTP client (sync and async)
- [Jinja2](https://jinja.palletsprojects.com/) — Template rendering (sandboxed)

## License

MIT
