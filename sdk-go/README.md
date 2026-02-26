# Promptdis Go SDK

Go client for the [Promptdis](https://github.com/futureself-app/promptdis) prompt management API. Zero external dependencies — uses only the Go standard library.

## Installation

```bash
go get github.com/futureself-app/promptdis-go
```

**Requirements:** Go 1.21+

## Quick Start

```go
package main

import (
    "context"
    "fmt"
    "log"

    promptdis "github.com/futureself-app/promptdis-go"
)

func main() {
    client, err := promptdis.NewClient(promptdis.ClientOptions{
        BaseURL: "https://prompts.futureself.app",
        APIKey:  "pm_live_...",
    })
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    ctx := context.Background()

    // Fetch by fully qualified name
    prompt, err := client.GetByName(ctx, "futureself", "meditate", "meditation_script_relax")
    if err != nil {
        log.Fatal(err)
    }

    // Local rendering (basic {{var}} substitution)
    rendered := client.RenderLocal(prompt.Body, map[string]string{
        "name": "Alice",
    })
    fmt.Println(rendered)

    // Model config helpers
    fmt.Println(prompt.ModelDefault("gemini-2.0-flash"))
    fmt.Println(prompt.ModelTemperature(0.7))
    fmt.Println(prompt.ModelMaxTokens(4000))
}
```

## Client Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `BaseURL` | `string` | *required* | Promptdis server URL |
| `APIKey` | `string` | *required* | API key (`pm_live_...` or `pm_test_...`) |
| `CacheMaxSize` | `int` | `100` | Maximum cached prompts (LRU eviction) |
| `CacheTTL` | `time.Duration` | `60s` | Cache time-to-live |
| `MaxRetries` | `int` | `3` | Retry attempts on 429/5xx |
| `Timeout` | `time.Duration` | `10s` | HTTP request timeout |
| `HTTPClient` | `*http.Client` | `nil` | Custom HTTP client (overrides Timeout) |

## Fetching Prompts

### By UUID

```go
prompt, err := client.Get(ctx, "550e8400-e29b-41d4-a716-446655440000")
```

### By Fully Qualified Name

```go
prompt, err := client.GetByName(ctx, "futureself", "meditate", "meditation_script_relax")
```

### With Environment Filter

```go
prompt, err := client.GetByName(ctx, "futureself", "meditate", "meditation_script_relax",
    promptdis.WithEnvironment("production"),
)
```

## Rendering

### Server-Side (Full Jinja2)

```go
result, err := client.Render(ctx, promptID, map[string]interface{}{
    "user":   map[string]interface{}{"display_name": "Loren"},
    "vision": map[string]interface{}{"identity_statement": "I am a confident leader"},
})
fmt.Println(result.RenderedBody)
```

### Local (Basic `{{var}}` Substitution)

```go
rendered := client.RenderLocal(prompt.Body, map[string]string{
    "name":  "Alice",
    "place": "Wonderland",
})
```

Local rendering supports `{{variable}}` substitution only. For conditionals, loops, filters, and includes, use `client.Render()` which delegates to the server's Jinja2 engine.

## Prompt Struct

| Field | Type | Description |
|-------|------|-------------|
| `ID` | `string` | UUID |
| `Name` | `string` | Prompt name (e.g., `meditation_script_relax`) |
| `Version` | `string` | Semver (e.g., `1.0.0`) |
| `Org` | `string` | Organization slug |
| `App` | `string` | Application slug |
| `Domain` | `*string` | Logical grouping (e.g., `meditation`) |
| `Description` | `*string` | Human-readable description |
| `Type` | `string` | `chat`, `completion`, `tts`, `transcription` |
| `Role` | `*string` | `system`, `user`, `assistant` |
| `Model` | `map[string]interface{}` | Model configuration |
| `Modality` | `map[string]interface{}` | Input/output modality |
| `TTS` | `map[string]interface{}` | Text-to-speech config |
| `Audio` | `map[string]interface{}` | Audio generation config |
| `Environment` | `string` | `development`, `staging`, `production` |
| `Active` | `bool` | Whether prompt is active |
| `Tags` | `[]string` | Tags for filtering |
| `Body` | `string` | Raw template body |
| `Includes` | `[]string` | Referenced prompt names |
| `GitSHA` | `*string` | Git commit SHA |
| `UpdatedAt` | `*string` | ISO 8601 timestamp |

### Model Config Helpers

```go
prompt.ModelDefault("gemini-2.0-flash")  // returns model name or fallback
prompt.ModelTemperature(0.7)             // returns temperature or fallback
prompt.ModelMaxTokens(4000)              // returns max_tokens or fallback
```

These safely extract values from the `Model` map with type assertions and fallbacks.

## Caching

The client maintains a thread-safe (goroutine-safe) LRU cache with TTL and ETag support:

```
Request flow:
  1. Check LRU cache (keyed by prompt ID or qualified name)
  2. If HIT and fresh (age < CacheTTL) → return immediately
  3. If HIT and stale → send request with If-None-Match: <etag>
  4. If server returns 304 → refresh TTL, return cached
  5. If server returns 200 → update cache, return fresh
  6. If server unreachable → return stale cached (if available)
  7. If MISS and server unreachable → return error
```

### Cache Management

```go
stats := client.CacheStats()
fmt.Printf("Size: %d / %d, TTL: %v\n", stats.Size, stats.MaxSize, stats.TTL)

client.CacheInvalidate("id:550e8400-...")  // remove specific entry
client.CacheClear()                        // clear all entries
```

## Error Handling

The SDK provides typed errors for common HTTP status codes:

```go
import "errors"

prompt, err := client.Get(ctx, "missing-id")

if errors.Is(err, promptdis.ErrNotFound) {
    // 404 — prompt not found
}

if errors.Is(err, promptdis.ErrAuthentication) {
    // 401 — invalid API key
}

if errors.Is(err, promptdis.ErrRateLimit) {
    // 429 — rate limit exceeded
    var rle *promptdis.RateLimitError
    if errors.As(err, &rle) {
        fmt.Printf("Retry after %d seconds\n", rle.RetryAfter)
    }
}

var pe *promptdis.PromptdisError
if errors.As(err, &pe) {
    fmt.Printf("Status %d: %s\n", pe.StatusCode, pe.Message)
}
```

| Error | Status | Description |
|-------|--------|-------------|
| `ErrNotFound` | 404 | Prompt not found |
| `ErrAuthentication` | 401 | Invalid or missing API key |
| `ErrRateLimit` | 429 | Rate limit exceeded |
| `PromptdisError` | any | Base error with `StatusCode` and `Message` |
| `RateLimitError` | 429 | Extends `PromptdisError` with `RetryAfter` field |

## Retry Logic

The client automatically retries on transient failures:

- **Retried status codes:** 429 (rate limit) and 5xx (server errors)
- **Exponential backoff:** 1s, 2s, 4s, ... capped at 10s
- **Retry-After header:** Respected on 429 responses
- **Network errors:** Also trigger retries
- **Stale fallback:** If all retries exhausted and a stale cache entry exists, it's returned instead of an error

## Integration Example

```go
// Fetch prompt and use with any LLM client
prompt, err := client.GetByName(ctx, "futureself", "meditate", taskName)
if err != nil {
    return fmt.Errorf("fetch prompt: %w", err)
}

rendered := client.RenderLocal(prompt.Body, map[string]string{
    "name":  user.DisplayName,
    "vision": vision.IdentityStatement,
})

// Use prompt metadata to configure LLM call
model := prompt.ModelDefault("gemini-2.0-flash")
temp := prompt.ModelTemperature(0.7)
maxTokens := prompt.ModelMaxTokens(4000)

role := "system"
if prompt.Role != nil {
    role = *prompt.Role
}

response, err := llmClient.Chat(ctx, ChatRequest{
    Model:       model,
    Temperature: temp,
    MaxTokens:   maxTokens,
    Messages:    []Message{{Role: role, Content: rendered}},
})
```

## Differences from Python/TS SDKs

| Feature | Python | TypeScript | Go |
|---------|--------|------------|----|
| HTTP client | `httpx` | Native `fetch` | `net/http` (stdlib) |
| External deps | httpx + jinja2 | Zero | Zero |
| Local render | Full Jinja2 (sandboxed) | Basic `{{var}}` regex | Basic `{{var}}` regex |
| Cache impl | `OrderedDict` + `threading.Lock` | `Map` insertion order | Linked list + map + `sync.RWMutex` |
| Async | Separate `AsyncPromptClient` | All methods async | `context.Context` (goroutine-safe) |
| Cache TTL | Seconds (`int`) | Milliseconds (`number`) | `time.Duration` |
| Error handling | Exception hierarchy | Exception hierarchy | Sentinel errors + `errors.Is/As` |
| Options | Constructor kwargs | Options interface | Struct + functional options |
| Background revalidation | Daemon thread | No | No (stale fallback) |

## API Reference

| Method | Signature | Description |
|--------|-----------|-------------|
| `NewClient` | `NewClient(opts ClientOptions) (*Client, error)` | Create a new client |
| `Get` | `Get(ctx, promptID) (*Prompt, error)` | Fetch by UUID |
| `GetByName` | `GetByName(ctx, org, app, name, ...GetOption) (*Prompt, error)` | Fetch by qualified name |
| `Render` | `Render(ctx, promptID, variables) (*RenderResult, error)` | Server-side Jinja2 render |
| `RenderLocal` | `RenderLocal(body, variables) string` | Local `{{var}}` substitution |
| `CacheStats` | `CacheStats() CacheStats` | Cache statistics |
| `CacheInvalidate` | `CacheInvalidate(key) bool` | Remove cache entry |
| `CacheClear` | `CacheClear()` | Clear all cache entries |
| `Close` | `Close()` | Release resources |

| Function | Signature | Description |
|----------|-----------|-------------|
| `RenderLocal` | `RenderLocal(body, variables) string` | Package-level local render |
| `WithEnvironment` | `WithEnvironment(env) GetOption` | Environment filter option |

## License

MIT
