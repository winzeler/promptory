# @promptdis/client-js

JavaScript SDK for [Promptdis](https://github.com/futureself-app/promptdis) — Git-native LLM prompt management.

Fetch, cache, and render LLM prompts from a Promptdis server. Zero dependencies — uses native `fetch`. Built-in LRU cache with ETag revalidation and retry with exponential backoff.

**No TypeScript required.** For TypeScript type safety, use [`@promptdis/client`](../sdk-ts/README.md) instead.

## Installation

```bash
npm install @promptdis/client-js
# or
yarn add @promptdis/client-js
# or
pnpm add @promptdis/client-js
```

**Requirements:** Node.js 18+ (or any runtime with global `fetch`)

## Quick Start

### ESM (recommended)

```js
import { PromptClient } from "@promptdis/client-js";

const client = new PromptClient({
  baseUrl: "http://localhost:8000",
  apiKey: "pm_live_...",
});

// Fetch by UUID
const prompt = await client.get("550e8400-e29b-41d4-a716-446655440000");
console.log(prompt.name); // "meditation_script_relax"
console.log(prompt.body); // Raw Jinja2 template

// Fetch by fully qualified name
const greeting = await client.getByName("myorg", "myapp", "greeting");

// Server-side render with Jinja2 variables
const { rendered_body } = await client.render(prompt.id, {
  user: { display_name: "Alice" },
  vision: { identity_statement: "I am confident" },
});

// Local render (basic {{var}} substitution only)
const local = client.renderLocal(prompt.body, { name: "Alice" });
```

### CommonJS

The CJS entry point returns a promise (dynamic `import()` under the hood):

```js
const { PromptClient } = await require("@promptdis/client-js");

const client = new PromptClient({
  baseUrl: "http://localhost:8000",
  apiKey: "pm_live_...",
});
```

## Client Options

```js
const client = new PromptClient({
  baseUrl: "http://localhost:8000",  // Promptdis server URL
  apiKey: "pm_live_...",              // API key from Promptdis web UI
  cacheMaxSize: 100,    // Max LRU cache entries (default: 100)
  cacheTtlMs: 60_000,   // Cache TTL in milliseconds (default: 60000)
  maxRetries: 3,         // Retry attempts on 429/5xx (default: 3)
});
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `baseUrl` | `string` | (required) | Promptdis server URL |
| `apiKey` | `string` | (required) | API key starting with `pm_live_` or `pm_test_` |
| `cacheMaxSize` | `number` | `100` | Max entries in LRU cache before eviction |
| `cacheTtlMs` | `number` | `60000` | Milliseconds before a cache entry expires |
| `maxRetries` | `number` | `3` | Max retries on 429 (rate limit) or 5xx errors |

## Fetching Prompts

### By UUID

```js
const prompt = await client.get("550e8400-e29b-41d4-a716-446655440000");
```

### By Qualified Name

```js
const prompt = await client.getByName("org_name", "app_name", "prompt_name");
```

### By Name with Environment Filter

```js
const prompt = await client.getByName(
  "myorg", "myapp", "greeting", "production"
);
```

Only returns prompts in the specified environment (`development`, `staging`, or `production`).

## Rendering

### Server-Side (Full Jinja2)

Use `client.render()` for full Jinja2 rendering on the server, including conditionals, loops, filters, and `{% include %}` composition:

```js
const { rendered_body, meta } = await client.render("prompt-id", {
  user: { display_name: "Alice" },
  items: ["focus", "calm", "gratitude"],
  formal: true,
});
```

### Local (Basic Substitution)

Use `client.renderLocal()` for fast `{{variable}}` substitution without a server round-trip:

```js
const result = client.renderLocal(
  "Hello {{name}}, welcome to {{app}}!",
  { name: "Alice", app: "Promptdis" }
);
// "Hello Alice, welcome to Promptdis!"
```

Local rendering only supports simple `{{ variable }}` placeholders. For conditionals, loops, filters, or includes, use `client.render()`.

## Prompt Object Shape

```js
// All fields returned by the API:
{
  id: "550e8400-...",
  name: "meditation_script_relax",
  version: "1.0.0",
  org: "myorg",
  app: "myapp",
  domain: null,             // optional grouping
  description: "A relaxation meditation script",
  type: "chat",             // "chat", "completion", "tts", etc.
  role: "system",           // "system", "user", "assistant"
  model: {                  // model config from front-matter
    default: "gemini-2.0-flash",
    temperature: 0.7,
    max_tokens: 4000,
  },
  environment: "production", // "development", "staging", "production"
  active: true,
  tags: ["meditation", "wellness"],
  body: "...",              // Raw Jinja2 template
  includes: [],             // Referenced prompt names
  git_sha: "abc123",
  updated_at: "2025-01-15T10:30:00Z",
}
```

### Accessing Model Config

```js
const modelName = prompt.model.default;       // "gemini-2.0-flash"
const temperature = prompt.model.temperature ?? 0.7;
const maxTokens = prompt.model.max_tokens ?? 4000;
```

## Caching

The SDK includes a built-in LRU cache with ETag-based revalidation:

- Prompts are cached in memory with a configurable TTL
- Subsequent requests send `If-None-Match` headers for conditional fetches
- On `304 Not Modified`, the cached version is returned without downloading
- On network errors, stale cached prompts are returned as a fallback
- Cache keys are derived from prompt ID or qualified name + environment

### Cache Management

```js
// View cache stats
const stats = client.cacheStats();
// { size: 42, maxSize: 100 }

// Invalidate a specific cache entry
const removed = client.cacheInvalidate("id:550e8400-...");

// Clear entire cache
client.cacheClear();
```

## Error Handling

```js
import {
  PromptClient,
  PromptdisError,
  NotFoundError,
  AuthenticationError,
  RateLimitError,
} from "@promptdis/client-js";

try {
  const prompt = await client.get("missing-id");
} catch (e) {
  if (e instanceof NotFoundError) {
    console.log("Prompt not found");
  } else if (e instanceof AuthenticationError) {
    console.log("Invalid API key");
  } else if (e instanceof RateLimitError) {
    console.log(`Rate limited. Retry after ${e.retryAfter}s`);
  } else if (e instanceof PromptdisError) {
    console.log(`API error: ${e.message}`);
  }
}
```

### Error Classes

| Class | HTTP Status | Properties | Description |
|-------|-------------|------------|-------------|
| `PromptdisError` | any | `message` | Base error for all SDK errors |
| `NotFoundError` | 404 | `message` | Prompt or resource not found |
| `AuthenticationError` | 401 | `message` | Invalid or missing API key |
| `ForbiddenError` | 403 | `message` | Insufficient permissions |
| `RateLimitError` | 429 | `message`, `retryAfter` | Rate limit exceeded |

## Retry Logic

The client automatically retries on `429` (rate limit) and `5xx` (server error) responses:

- Retries up to `maxRetries` times (default: 3)
- Uses exponential backoff: 1s, 2s, 4s (capped at 10s)
- Respects `Retry-After` header from 429 responses
- Network errors also trigger retries with the same backoff

## Integration Example

Using Promptdis with the Anthropic SDK:

```js
import { PromptClient } from "@promptdis/client-js";
import Anthropic from "@anthropic-ai/sdk";

const prompts = new PromptClient({
  baseUrl: "http://localhost:8000",
  apiKey: "pm_live_...",
});

const anthropic = new Anthropic();

async function generateResponse(userMessage) {
  // Fetch system prompt (cached after first call)
  const prompt = await prompts.getByName(
    "myorg", "myapp", "chat_system", "production"
  );

  // Server-side render with full Jinja2 support
  const { rendered_body } = await prompts.render(prompt.id, {
    context: { topic: "productivity" },
  });

  // Use model config from prompt metadata
  const response = await anthropic.messages.create({
    model: prompt.model.default,
    max_tokens: prompt.model.max_tokens ?? 4000,
    system: rendered_body,
    messages: [{ role: "user", content: userMessage }],
  });

  return response.content[0].text;
}
```

## API Reference

### PromptClient

| Method | Returns | Description |
|--------|---------|-------------|
| `get(promptId)` | `Promise<Prompt>` | Fetch by UUID |
| `getByName(org, app, name, env?)` | `Promise<Prompt>` | Fetch by qualified name |
| `render(promptId, variables)` | `Promise<{ rendered_body, meta }>` | Server-side Jinja2 render |
| `renderLocal(body, variables)` | `string` | Local `{{var}}` substitution |
| `cacheStats()` | `{ size, maxSize }` | Cache statistics |
| `cacheInvalidate(key)` | `boolean` | Invalidate a cache entry |
| `cacheClear()` | `void` | Clear all cache entries |

### Exports

```js
// Classes
import { PromptClient } from "@promptdis/client-js";
import { LRUCache } from "@promptdis/client-js";

// Errors
import {
  PromptdisError,
  NotFoundError,
  AuthenticationError,
  ForbiddenError,
  RateLimitError,
} from "@promptdis/client-js";

// Utilities
import { renderLocal } from "@promptdis/client-js";
```

## Differences from TypeScript / Python SDKs

| Feature | JS SDK | TypeScript SDK | Python SDK |
|---------|--------|----------------|-----------|
| Package | `@promptdis/client-js` | `@promptdis/client` | `promptdis` |
| Build step | None | `tsc` required | None |
| Type safety | JSDoc annotations | Full TypeScript types | Type hints |
| HTTP client | Native `fetch` | Native `fetch` | `httpx` |
| Local render | Basic `{{var}}` | Basic `{{var}}` | Full Jinja2 (sandboxed) |
| Module format | ESM + CJS wrapper | ESM only | N/A |
| Async | All methods async | All methods async | Separate `AsyncPromptClient` |

For full Jinja2 rendering (conditionals, loops, filters, includes), use `client.render()` which delegates to the server.

## Development

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run tests in watch mode
npm run test:watch
```

## License

MIT
