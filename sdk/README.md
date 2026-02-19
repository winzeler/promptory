# promptory

Python SDK for [Promptory](https://github.com/futureself/prompt-mgmt) — Git-native LLM prompt management.

## Installation

```bash
pip install promptory
```

For async support with HTTP/2:

```bash
pip install "promptory[async]"
```

## Quick Start

```python
from promptory import PromptClient

client = PromptClient(
    base_url="http://localhost:8000",
    api_key="pm_live_your_api_key_here",
)

# Fetch a prompt by name
prompt = client.get_by_name("my-org", "my-app", "welcome_message")

# Render with variables
output = prompt.render({"user_name": "Alice", "topic": "meditation"})
print(output)

client.close()
```

### Context Manager

```python
with PromptClient(base_url="http://localhost:8000", api_key="pm_live_...") as client:
    prompt = client.get_by_name("my-org", "my-app", "welcome_message")
    print(prompt.render({"user_name": "Alice"}))
```

### Async Client

```python
import asyncio
from promptory import AsyncPromptClient

async def main():
    async with AsyncPromptClient(base_url="http://localhost:8000", api_key="pm_live_...") as client:
        prompt = await client.get_by_name("my-org", "my-app", "welcome_message")
        print(prompt.render({"user_name": "Alice"}))

asyncio.run(main())
```

## API

### `PromptClient` / `AsyncPromptClient`

```python
client = PromptClient(
    base_url="http://localhost:8000",  # Promptory server URL
    api_key="pm_live_...",             # API key from admin dashboard
    cache_ttl=300,                     # Cache TTL in seconds (default: 300)
    cache_max_size=1000,               # Max cached prompts (default: 1000)
    timeout=10.0,                      # Request timeout in seconds (default: 10)
    retry_count=3,                     # Retries on transport errors (default: 3)
)
```

**Methods:**

| Method | Description |
|--------|-------------|
| `get(prompt_id)` | Fetch prompt by UUID |
| `get_by_name(org, app, name, environment=None)` | Fetch by qualified name |
| `render(prompt_id, variables)` | Server-side render with variables |
| `cache_stats()` | Cache hit/miss statistics |
| `cache_invalidate(name)` | Invalidate cached prompt by name |
| `cache_invalidate_all()` | Clear entire cache |
| `close()` | Close HTTP connection |

### `Prompt`

Returned by `get()` and `get_by_name()`.

```python
prompt.name          # "welcome_message"
prompt.body          # Raw Jinja2 template
prompt.version       # "1.0.0"
prompt.domain        # "messaging"
prompt.model         # {"default": "gemini-2.0-flash", ...}
prompt.tags          # ["onboarding", "greeting"]
prompt.render(vars)  # Render template with variables
```

### Exceptions

```python
from promptory import PromptoryError, NotFoundError, AuthenticationError
from promptory.exceptions import RateLimitError

try:
    prompt = client.get_by_name("org", "app", "missing")
except NotFoundError:
    print("Prompt not found")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except PromptoryError as e:
    print(f"Error {e.status_code}: {e.message}")
```

## Caching

The SDK includes an LRU cache with ETag support:

- Prompts are cached locally for `cache_ttl` seconds
- Subsequent requests use `If-None-Match` headers for conditional fetches
- On 304 responses, the cached version is refreshed without re-downloading
- If the server is unreachable, stale cached prompts are returned as a fallback
- Retries use exponential backoff with jitter

```python
stats = client.cache_stats()
# {"total": 5, "fresh": 3, "stale": 2, "max_size": 1000, "ttl": 300}
```

## License

MIT
