# Jinja2 Rendering in Promptdis

A comprehensive guide to the template rendering pipeline — how `.md` prompt files are transformed into final prompt text for LLMs.

---

## Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [Prompt File Anatomy](#2-prompt-file-anatomy)
3. [Template Syntax Reference](#3-template-syntax-reference)
4. [Prompt Composition (Includes)](#4-prompt-composition-includes)
5. [Rendering Paths (Server vs Client)](#5-rendering-paths-server-vs-client)
6. [SDK Usage Examples](#6-sdk-usage-examples)
7. [API Reference](#7-api-reference)
8. [Security Model](#8-security-model)
9. [Error Handling](#9-error-handling)
10. [Testing](#10-testing)
11. [Internals / Source Files](#11-internals--source-files)

---

## 1. Overview & Architecture

Promptdis stores prompts as Markdown files with YAML front-matter in GitHub repos. When a prompt is fetched via the API or SDK, its Jinja2 template body can be rendered with variables to produce final prompt text for an LLM.

### Pipeline

```
 GitHub Repo          Server                    Client / LLM
 ───────────          ──────                    ─────────────

 prompts/
 ├─ greeting.md ──► GitHub webhook ──► SQLite index
 └─ safety.md        (push event)      (front_matter JSON)
                                            │
                          ┌─────────────────┘
                          ▼
                    API fetch (/api/v1/prompts/...)
                          │
                          ├──► Server render ──► Jinja2 engine ──► rendered_body
                          │    (POST /render)     (includes,        returned in
                          │                        conditionals,    JSON response
                          │                        loops, filters)
                          │
                          └──► Client fetch ──► SDK local render ──► LLM
                               (GET prompt)     (Jinja2 or regex)
```

### Two Rendering Paths

| Function | What it does |
|----------|-------------|
| `render_prompt(body, variables)` | Simple Jinja2 render — no includes, no DB access |
| `render_prompt_with_includes(body, variables, db, app_id)` | Resolves `{% include %}` directives from the DB, then renders |

The server automatically picks the right path based on the prompt's `includes` front-matter field.

### Security

All rendering uses Jinja2's `SandboxedEnvironment`, which prevents template injection attacks by blocking access to dangerous Python attributes and methods.

---

## 2. Prompt File Anatomy

A prompt file has three zones separated by `---` delimiters:

```markdown
---
name: meditation_guide
version: "1.2"
description: Guided meditation script
type: chat
role: system
model:
  default: claude-sonnet-4-5-20250514
tags:
  - meditation
  - wellness
includes:
  - safety_disclaimer
active: true
---
{% include "safety_disclaimer" %}

You are a meditation guide for {{ user_name }}.

{% if session_type == "morning" %}
Focus on energizing breathwork and intention setting.
{% elif session_type == "evening" %}
Focus on relaxation and releasing the day's tension.
{% else %}
Provide a balanced, general-purpose meditation.
{% endif %}

Session duration: {{ duration | default("10") }} minutes.
```

### Zone breakdown

| Zone | Content |
|------|---------|
| **YAML front-matter** | Metadata: name, version, model config, tags, includes list |
| **`---` delimiter** | Separates front-matter from template body |
| **Jinja2 body** | The template text with variables, conditionals, loops, includes |

### How the body is stored

When synced from GitHub, the body is stored in the SQLite `prompts.front_matter` JSON column under the `_body` key:

```json
{
  "name": "meditation_guide",
  "version": "1.2",
  "_body": "{% include \"safety_disclaimer\" %}\n\nYou are a meditation guide for {{ user_name }}.\n..."
}
```

---

## 3. Template Syntax Reference

### Variables

Simple substitution with double curly braces:

```jinja
Hello {{ name }}!
```

**Nested access:**
```jinja
Model: {{ model.default }}
```

**Missing variables render as empty strings** (not an error):
```jinja
Hello {{ name }}!
{# If name is not provided, renders as: "Hello !" #}
```

### Filters

Transform variable values with the `|` pipe operator:

| Filter | Input | Output |
|--------|-------|--------|
| `upper` | `{{ "alice" \| upper }}` | `ALICE` |
| `lower` | `{{ "HELLO" \| lower }}` | `hello` |
| `title` | `{{ "hello world" \| title }}` | `Hello World` |
| `default` | `{{ name \| default("World") }}` | `World` (when `name` is undefined) |
| `join` | `{{ items \| join(", ") }}` | `a, b, c` |
| `trim` | `{{ text \| trim }}` | Removes leading/trailing whitespace |
| `replace` | `{{ text \| replace("old", "new") }}` | String replacement |
| `length` | `{{ items \| length }}` | `3` |

**Example:**
```jinja
Welcome, {{ name | default("friend") | title }}!
```
- With `{"name": "alice"}` → `Welcome, Alice!`
- With `{}` → `Welcome, Friend!`

### Conditionals

```jinja
{% if formal %}
Dear {{ name }},
{% elif casual %}
Hey {{ name }}!
{% else %}
Hello {{ name }}.
{% endif %}
```

**Truthiness:** Empty strings, `None`, `0`, `false`, `[]`, and `{}` are all falsy.

### Loops

```jinja
{% for item in items %}
- {{ item }}
{% endfor %}
```

**Loop variables:**

| Variable | Description |
|----------|-------------|
| `loop.index` | Current iteration (1-indexed) |
| `loop.index0` | Current iteration (0-indexed) |
| `loop.first` | `true` on first iteration |
| `loop.last` | `true` on last iteration |
| `loop.length` | Total number of items |

**Example:**
```jinja
{% for step in steps %}
Step {{ loop.index }}: {{ step }}{% if not loop.last %}
{% endif %}
{% endfor %}
```

### Whitespace Control

Use `-` to trim whitespace around block tags:

```jinja
{%- if condition -%}
    Content with no extra whitespace
{%- endif -%}
```

Without `-`, Jinja2 preserves the whitespace around block tags.

### Comments

```jinja
{# This comment will not appear in the rendered output #}
```

### Trailing Newlines

Promptdis preserves trailing newlines (`keep_trailing_newline=True`). A template ending with `\n` will produce output ending with `\n`.

---

## 4. Prompt Composition (Includes)

### Syntax

```jinja
{% include "prompt_name" %}
```

Include another prompt by its `name` field (not filename, not ID). The included prompt must:
- Belong to the **same application** (`app_id`)
- Have `active: true`
- Exist in the database

### How It Works

```
 Main template                  _resolve_includes()            Jinja2 DictLoader
 ─────────────                  ───────────────────            ─────────────────

 '{% include "safety" %}        1. Regex scan for              DictLoader({
  You are a {{ role }}.'           {% include "..." %}           "safety": "Always be...",
        │                       2. DB lookup by name             "preamble": "You are..."
        │                          within same app_id          })
        ├──► "safety" ─────────►3. Get _body from                     │
        │                          front_matter JSON                  │
        └──► render ◄──────────────────────────────────────── Jinja2 render
                                                               with DictLoader
```

1. **Regex scan** — `_INCLUDE_RE` finds all `{% include "name" %}` directives
2. **DB lookup** — Queries `prompts` table: `WHERE app_id = ? AND name = ? AND active = 1`
3. **Recursive resolution** — If the included prompt itself has includes, resolve those too
4. **DictLoader** — All resolved bodies are loaded into a `DictLoader`, then Jinja2 renders

### The `includes` Front-Matter Field

Declare dependencies explicitly in front-matter:

```yaml
---
name: meditation_guide
includes:
  - safety_disclaimer
  - meditation_preamble
---
```

The server uses this field to decide whether to call `render_prompt_with_includes` (when `includes` is non-empty) or `render_prompt` (when empty).

### Rules and Limits

| Rule | Behavior |
|------|----------|
| **Max depth: 5** | Include chains deeper than 5 levels raise `ValueError` |
| **Circular detection** | `A → B → A` raises `"Circular include detected"` |
| **Must be active** | Only prompts with `active = 1` can be included |
| **Same app only** | Includes are scoped to the same `app_id` |
| **Shared variables** | All variables are shared across the include tree |

### Example: Composed Prompt

**`safety_disclaimer` prompt:**
```markdown
---
name: safety_disclaimer
---
Important: Always prioritize user safety. Never provide harmful advice.
```

**`meditation_preamble` prompt:**
```markdown
---
name: meditation_preamble
---
You are an expert meditation instructor with {{ years | default("10") }} years of experience.
```

**`meditation_guide` prompt (main):**
```markdown
---
name: meditation_guide
includes:
  - safety_disclaimer
  - meditation_preamble
---
{% include "safety_disclaimer" %}

{% include "meditation_preamble" %}

Guide {{ user_name }} through a {{ duration }}-minute {{ session_type }} meditation.
```

**Rendered** with `{"user_name": "Alice", "duration": "15", "session_type": "morning"}`:
```
Important: Always prioritize user safety. Never provide harmful advice.

You are an expert meditation instructor with 10 years of experience.

Guide Alice through a 15-minute morning meditation.
```

---

## 5. Rendering Paths (Server vs Client)

There are three ways to render a prompt:

### Comparison

| Feature | Server-side render | Python SDK local | JS/TS SDK local |
|---------|-------------------|------------------|-----------------|
| **Variables** `{{ var }}` | Yes | Yes | Yes |
| **Filters** `\| upper` | Yes | Yes | No |
| **Conditionals** `{% if %}` | Yes | Yes | No |
| **Loops** `{% for %}` | Yes | Yes | No |
| **Includes** `{% include %}` | Yes | No | No |
| **Sandbox security** | Yes | Yes | N/A (regex only) |
| **Network required** | Yes (POST) | No | No |
| **Nested variables** `{{ a.b }}` | Yes | Yes | No |

### Server-Side Render

Full Jinja2 with include resolution. Requires an API call:

```
POST /api/v1/prompts/{id}/render
```

### Python SDK Local Render

Full Jinja2 via `SandboxedEnvironment`, but no include support (no DB access client-side):

```python
prompt = client.get("prompt-id")
rendered = prompt.render({"name": "Alice"})
```

### JS/TS SDK Local Render

Basic `{{ variable }}` regex substitution only. No Jinja2 features:

```javascript
const rendered = client.renderLocal(prompt.body, { name: "Alice" });
```

The regex pattern: `/\{\{\s*(\w+)\s*\}\}/g` — matches `{{ word }}` and replaces with the variable value or empty string.

---

## 6. SDK Usage Examples

### Python (Synchronous)

```python
from promptdis import PromptClient

with PromptClient(base_url="https://prompts.example.com", api_key="pm_live_...") as client:
    # Fetch by name
    prompt = client.get_by_name("myorg", "myapp", "greeting")

    # Local render (full Jinja2, no includes)
    rendered = prompt.render({"name": "Alice", "formal": True})
    print(rendered)

    # Server-side render (full Jinja2 + includes)
    rendered_server = client.render(prompt.id, {"name": "Bob"})
    print(rendered_server)
```

### Python (Async)

```python
from promptdis import AsyncPromptClient

async with AsyncPromptClient(base_url="https://prompts.example.com", api_key="pm_live_...") as client:
    prompt = await client.get_by_name("myorg", "myapp", "greeting")

    # Local render
    rendered = prompt.render({"name": "Alice"})

    # Server-side render
    rendered_server = await client.render(prompt.id, {"name": "Bob"})
```

### Python + LLM Integration

```python
import anthropic
from promptdis import PromptClient

with PromptClient(base_url="https://prompts.example.com", api_key="pm_live_...") as client:
    prompt = client.get_by_name("myorg", "myapp", "meditation_guide")
    system_prompt = prompt.render({
        "user_name": "Alice",
        "session_type": "morning",
        "duration": "10",
    })

    # Use the rendered prompt with Claude
    claude = anthropic.Anthropic()
    response = claude.messages.create(
        model=prompt.model.get("default", "claude-sonnet-4-5-20250514"),
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": "I'm ready to begin."}],
    )
```

### JavaScript

```javascript
import { PromptClient } from "@promptdis/sdk";

const client = new PromptClient({
  baseUrl: "https://prompts.example.com",
  apiKey: "pm_live_...",
});

// Fetch prompt
const prompt = await client.get("550e8400-e29b-41d4-a716-446655440000");

// Local render (basic {{var}} substitution only)
const local = client.renderLocal(prompt.body, { name: "Alice" });

// Server-side render (full Jinja2 + includes)
const { rendered_body, meta } = await client.render(prompt.id, {
  name: "Alice",
  formal: true,
});
```

### TypeScript

```typescript
import { PromptClient } from "@promptdis/sdk";

const client = new PromptClient({
  baseUrl: "https://prompts.example.com",
  apiKey: "pm_live_...",
});

const prompt = await client.get("550e8400-e29b-41d4-a716-446655440000");

// Local render (basic {{var}} only)
const local: string = client.renderLocal(prompt.body, { name: "Alice" });

// Server render (full Jinja2 + includes)
const result: { rendered_body: string; meta: Record<string, unknown> } =
  await client.render(prompt.id, { name: "Alice" });
```

---

## 7. API Reference

### Render Prompt

```
POST /api/v1/prompts/{prompt_id}/render
```

Renders a prompt server-side with full Jinja2 support and include resolution.

**Request:**
```json
{
  "variables": {
    "name": "Alice",
    "session_type": "morning",
    "duration": "10"
  }
}
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "meditation_guide",
  "rendered_body": "Important: Always prioritize user safety...\n\nGuide Alice through a 10-minute morning meditation.",
  "meta": {
    "name": "meditation_guide",
    "version": "1.2",
    "model": { "default": "claude-sonnet-4-5-20250514" },
    "_body": "..."
  },
  "model": {
    "default": "claude-sonnet-4-5-20250514"
  }
}
```

**Error (400 — Render Error):**
```json
{
  "error": {
    "code": "RENDER_ERROR",
    "message": "Template rendering failed: unexpected '}'"
  }
}
```

**Error (404 — Not Found):**
```json
{
  "error": {
    "code": "PROMPT_NOT_FOUND",
    "message": "No prompt found with id '...'"
  }
}
```

**Headers:** Requires `Authorization: Bearer pm_live_...` or `pm_test_...`

### TTS Preview (Admin)

```
POST /api/v1/admin/prompts/{prompt_id}/tts-preview
```

Renders the prompt with Jinja2 variables, then synthesizes TTS audio via ElevenLabs. Requires admin authentication.

**Request:**
```json
{
  "variables": { "user_name": "Alice" },
  "tts_config": { "voice_id": "..." }
}
```

**Response:** `302 Redirect` to S3 presigned URL, or direct audio file response.

---

## 8. Security Model

### SandboxedEnvironment

All Jinja2 rendering uses `jinja2.sandbox.SandboxedEnvironment`, which:

- **Blocks attribute traversal** — Access to `__class__`, `__mro__`, `__subclasses__`, `__globals__`, etc. is denied
- **Blocks method calls** on unsafe types
- **Prevents arbitrary code execution** — No `import`, `eval`, `exec`, or similar operations

**Example of blocked attack:**
```jinja
{# This will raise an error, not execute #}
{{ ''.__class__.__mro__[1].__subclasses__() }}
```

### Why `autoescape=False`

Prompts are **plain text** sent to LLMs, not HTML rendered in browsers. HTML escaping would corrupt prompt content (e.g., turning `&` into `&amp;`). There is no XSS risk because the output is never rendered as HTML.

### Configuration

```python
SandboxedEnvironment(
    loader=BaseLoader(),       # No filesystem access
    autoescape=False,          # Plain text output
    keep_trailing_newline=True # Preserve formatting
)
```

---

## 9. Error Handling

### Error Responses

All rendering errors return HTTP `400` with code `RENDER_ERROR`:

| Scenario | Error Message |
|----------|--------------|
| **Syntax error** | `Template rendering failed: unexpected '}'` |
| **Missing include** | `Include not found: 'nonexistent'` |
| **Circular include** | `Circular include detected: 'prompt_a' already included` |
| **Depth exceeded** | `Include depth exceeded maximum of 5` |
| **Sandbox violation** | `Template rendering failed: ...` |

### Missing Variables

Missing variables are **not an error**. They render as empty strings:

```python
render_prompt("Hello {{ name }}!", {})
# Returns: "Hello !"
```

Use the `default` filter to provide fallback values:

```jinja
Hello {{ name | default("World") }}!
{# Returns: "Hello World!" when name is missing #}
```

---

## 10. Testing

### Test File

All rendering tests are in `tests/server/test_render_service.py` (17 tests).

### Running Tests

```bash
pytest tests/server/test_render_service.py -v
```

### Test Coverage

| Test | What it verifies |
|------|-----------------|
| `test_basic_render` | Simple `{{ name }}` substitution |
| `test_multiple_variables` | Multiple variables in one template |
| `test_missing_variable_renders_empty` | Missing vars → empty string |
| `test_no_variables_passthrough` | Static text passes through unchanged |
| `test_filter_upper` | `\| upper` filter |
| `test_filter_default` | `\| default(...)` filter |
| `test_conditional` | `{% if %}` / `{% else %}` |
| `test_loop` | `{% for %}` loop |
| `test_invalid_template_raises` | Syntax errors raise `ValueError` |
| `test_sandbox_blocks_dangerous_operations` | `__class__` access blocked |
| `test_multiline_template` | Multi-line templates render correctly |
| `test_trailing_newline_preserved` | `keep_trailing_newline=True` works |
| `test_render_with_single_include` | Single `{% include %}` resolved from DB |
| `test_render_with_nested_include` | Nested includes (A → B → C) |
| `test_circular_include_raises` | Circular dependency detection |
| `test_max_depth_exceeded` | Depth > 5 raises error |
| `test_missing_include_raises` | Missing include raises error |

### Testing Includes Locally

Include tests use an **in-memory SQLite** database. The test helper creates the schema, seeds an org/app, and adds prompts:

```python
import aiosqlite
import json

async def setup():
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    # Run migrations...

    # Add a prompt for include resolution
    fm = json.dumps({"_body": "You are a helpful assistant.", "name": "preamble"})
    await db.execute(
        "INSERT INTO prompts (id, app_id, name, file_path, front_matter, active) "
        "VALUES (?, ?, ?, ?, ?, 1)",
        ("id-preamble", "app-1", "preamble", "prompts/preamble.md", fm),
    )
    await db.commit()

    # Render with includes
    result = await render_prompt_with_includes(
        '{% include "preamble" %}\nHelp {{ name }}.',
        {"name": "Alice"},
        db,
        "app-1",
    )
    # "You are a helpful assistant.\nHelp Alice."
```

---

## 11. Internals / Source Files

### Source File Map

| File | Role |
|------|------|
| `server/services/render_service.py` | Core rendering engine — `render_prompt()`, `render_prompt_with_includes()`, include resolution |
| `server/api/public.py` | `POST /{id}/render` endpoint (lines 200-233) |
| `server/api/admin.py` | TTS preview endpoint with render (lines 880-954) |
| `sdk-py/src/promptdis/models.py` | `Prompt.render()` — local Jinja2 rendering (line 38-43) |
| `sdk-py/src/promptdis/client.py` | `PromptClient.render()` — fetch + local render (line 63-65) |
| `sdk-py/src/promptdis/async_client.py` | `AsyncPromptClient.render()` — async fetch + local render (line 53-54) |
| `sdk-js/src/models.js` | `renderLocal()` — regex `{{var}}` substitution (lines 33-37) |
| `sdk-js/src/client.js` | `PromptClient.render()` (server) + `renderLocal()` (lines 73-89) |
| `sdk-ts/src/client.ts` | `PromptClient.render()` (server) + `renderLocal()` (lines 64-77) |
| `sdk-ts/src/models.ts` | `renderLocal()` TypeScript implementation + `Prompt` type |
| `tests/server/test_render_service.py` | 17 tests covering all rendering paths |

### Key Functions

```python
# Simple render (no includes)
def render_prompt(template_body: str, variables: dict) -> str

# Include-aware render (async, needs DB)
async def render_prompt_with_includes(
    template_body: str,
    variables: dict,
    db,           # aiosqlite connection
    app_id: str,
) -> str

# Internal: recursively resolve include references
async def _resolve_includes(
    template_body: str,
    db,
    app_id: str,
    resolved: dict[str, str],  # name → body accumulator
    seen: set[str],            # circular detection
    depth: int,                # max 5
) -> None
```

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `_MAX_INCLUDE_DEPTH` | `5` | Maximum nesting depth for includes |
| `_INCLUDE_RE` | `r'\{%[-\s]*include\s+["\']([^"\']+)["\']'` | Regex to find include directives |
