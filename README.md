# Promptdis

Git-native LLM prompt management platform. Store prompts as Markdown files in GitHub, edit them through a web UI, fetch them at runtime via SDK.

## What It Does

- **GitHub is the source of truth** — prompts are `.md` files with YAML front-matter in a GitHub repo
- **SQLite index** — fast search, filtering, and metadata queries without hitting GitHub
- **Web editor** — split-pane UI with structured YAML form + CodeMirror body editor
- **Jinja2 rendering** — server-side template rendering with variable substitution, conditionals, loops, includes
- **SDKs** — Python and TypeScript clients with LRU cache, ETag revalidation, and retry logic
- **Eval framework** — run promptfoo evaluations from the UI, auto-generate tests with PromptPex
- **TTS preview** — render prompts and synthesize audio via ElevenLabs directly in the editor
- **Analytics** — track API usage, cache hit rates, top prompts, and per-key consumption

## Architecture

```
┌─────────────────┐     ┌──────────────────────────┐     ┌────────────┐
│  React Frontend │────▶│   FastAPI Server          │────▶│   GitHub   │
│  (Vite + TS)    │     │                          │     │   (repos)  │
└─────────────────┘     │  ┌─────────┐ ┌────────┐  │     └────────────┘
                        │  │ SQLite  │ │ Cache  │  │            │
┌─────────────────┐     │  │ (index) │ │ (LRU)  │  │     ┌──────┴─────┐
│  Python SDK     │────▶│  └─────────┘ └────────┘  │     │  Webhooks  │
│  TypeScript SDK │     └──────────────────────────┘     └────────────┘
└─────────────────┘
```

- **Server:** FastAPI + aiosqlite + PyGithub
- **Frontend:** React 18 + Vite + Tailwind CSS + TanStack Query + CodeMirror 6
- **Database:** SQLite (index/cache only — GitHub is the source of truth)
- **Auth:** GitHub OAuth SSO (web) + API keys (SDK)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A GitHub OAuth App ([create one](https://github.com/settings/developers))

### 1. Clone and install

```bash
git clone https://github.com/futureself-app/promptdis.git
cd prompt-mgmt

# Backend
pip install -e ".[dev]"

# Frontend
cd web && npm install && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Required — GitHub OAuth App credentials
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret

# Required — random secret for session encryption
APP_SECRET_KEY=generate-a-random-64-char-hex-string

# Server URLs
APP_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

# Database (created automatically)
DATABASE_PATH=./data/promptdis.db

# Optional — ElevenLabs TTS preview
ELEVENLABS_API_KEY=

# Optional
# LOG_LEVEL=info
# CORS_ORIGINS=http://localhost:5173
# RATE_LIMIT_PER_MINUTE=100
```

### 3. Start the server

```bash
# Terminal 1 — API server
uvicorn server.main:app --reload --port 8000

# Terminal 2 — Frontend dev server
cd web && npm run dev
```

The API is at `http://localhost:8000` (docs at `/docs`). The web UI is at `http://localhost:5173`.

### 4. First-time setup

1. Open `http://localhost:5173` and sign in with GitHub
2. Your GitHub organizations are synced automatically
3. Go to **Settings** → **Add Application** → enter a GitHub repo containing `.md` prompt files
4. Promptdis indexes all `.md` files from the repo into SQLite
5. Browse, edit, and create prompts through the web UI

### Docker / Podman

```bash
# Build and run both services
docker compose up

# Or with Podman
podman-compose up
```

This starts the API on port 8000 and the web UI on port 5173. Mount a `.env` file or pass env vars.

## Prompt File Format

Prompts are Markdown files with YAML front-matter:

```markdown
---
name: meditation_script_relax
domain: meditation
type: chat
role: system
version: "1.0.0"
description: Guided relaxation meditation script
model:
  default: gemini-2.0-flash
  temperature: 0.7
  max_tokens: 4000
environment: production
active: true
tags: [meditation, relax, tts]
tts:
  provider: elevenlabs
  voice_id: "{{ user.elevenlabs_voice_id }}"
  stability: 0.6
---

You are the FutureSelf guide for {{ user.display_name }}.

Their identity statement: "{{ vision.identity_statement }}"

Generate a calming {{ duration_minutes }}-minute relaxation meditation...
```

The body supports full Jinja2 syntax: `{{ variables }}`, `{% if %}`, `{% for %}`, `{% include "other_prompt" %}`.

See [PROMPTDIS_API_DOCS.md](../dwight_docs/prompt_mgmt/PROMPTDIS_API_DOCS.md) for the complete YAML front-matter schema.

## Using the SDKs

### Python

```bash
pip install promptdis
```

```python
from promptdis import PromptClient

client = PromptClient(
    base_url="http://localhost:8000",
    api_key="pm_live_...",
)

# Fetch by ID
prompt = client.get("550e8400-e29b-41d4-a716-446655440000")

# Fetch by name
prompt = client.get_by_name("myorg", "myapp", "meditation_script_relax")

# Render with variables
rendered = prompt.render(variables={
    "user": {"display_name": "Alice"},
    "vision": {"identity_statement": "I am confident"},
})
```

See [`sdk/README.md`](sdk/README.md) for full documentation.

### TypeScript

```bash
npm install @promptdis/client
```

```typescript
import { PromptClient } from "@promptdis/client";

const client = new PromptClient({
  baseUrl: "http://localhost:8000",
  apiKey: "pm_live_...",
});

const prompt = await client.get("550e8400-...");
const { rendered_body } = await client.render(prompt.id, {
  user: { display_name: "Alice" },
});
```

See [`sdk-ts/README.md`](sdk-ts/README.md) for full documentation.

## API Overview

All endpoints are under `/api/v1`. Full documentation: [PROMPTDIS_API_DOCS.md](../dwight_docs/prompt_mgmt/PROMPTDIS_API_DOCS.md)

### Public API (API key auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/prompts/{id}` | Fetch prompt by UUID |
| `GET` | `/prompts/by-name/{org}/{app}/{name}` | Fetch by qualified name |
| `POST` | `/prompts/{id}/render` | Render with Jinja2 variables |

### Admin API (session auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/orgs` | List organizations |
| `GET` | `/admin/orgs/{id}/apps` | List applications |
| `POST` | `/admin/orgs/{id}/apps` | Create application |
| `GET` | `/admin/apps/{id}/prompts` | List prompts (search, filter, paginate) |
| `GET` | `/admin/prompts/{id}` | Prompt detail with full content |
| `POST` | `/admin/prompts` | Create prompt (commits to GitHub) |
| `PUT` | `/admin/prompts/{id}` | Update prompt (commits to GitHub) |
| `DELETE` | `/admin/prompts/{id}` | Delete prompt |
| `GET` | `/admin/prompts/{id}/history` | Git commit history |
| `GET` | `/admin/prompts/{id}/diff/{sha}` | Diff at commit |
| `POST` | `/admin/prompts/{id}/rollback` | Rollback to SHA |
| `GET` | `/admin/prompts/{id}/at/{sha}` | Content at specific commit |
| `POST` | `/admin/prompts/batch` | Batch update fields |
| `POST` | `/admin/prompts/batch-delete` | Batch delete |
| `GET` | `/admin/prompts/{id}/export/prompty` | Export as .prompty |
| `POST` | `/admin/prompts/import/prompty` | Import .prompty file |
| `POST` | `/admin/prompts/{id}/eval` | Run evaluation |
| `POST` | `/admin/prompts/{id}/tts-preview` | TTS audio preview |
| `POST` | `/admin/sync` | Force sync all apps |
| `GET` | `/admin/analytics/requests-per-day` | API usage chart data |
| `GET` | `/admin/analytics/top-prompts` | Most-used prompts |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/auth/github/login` | Start GitHub OAuth |
| `GET` | `/auth/github/callback` | OAuth callback |
| `POST` | `/auth/logout` | End session |
| `GET` | `/auth/me` | Current user |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhooks/github` | GitHub push event handler |

## Web UI Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Analytics overview — requests/day chart, cache hit rate, top prompts, API key usage |
| **Prompt Browser** | Grid view with search, filters (type, environment, domain, tags), multi-select batch operations |
| **Prompt Editor** | Split-pane: YAML front-matter form (left) + CodeMirror body editor (right). Diff view, promote, export .prompty |
| **Prompt Preview** | Render with variables, TTS audio preview |
| **Evaluation** | Run promptfoo evals, model comparison, auto-generate tests |
| **App Settings** | GitHub repo connection, webhook configuration |
| **API Keys** | Generate and manage API keys |
| **Sync Status** | Sync history, force re-sync |

## Key Features

### Prompt Composition

Use `{% include "prompt_name" %}` to compose prompts from reusable fragments:

```markdown
---
name: meditation_full
includes: [safety_preamble, meditation_base]
---

{% include "safety_preamble" %}

{% include "meditation_base" %}

Now personalize for {{ user.display_name }}...
```

Includes are resolved at render time from the same application's prompts. Max depth: 5 levels. Circular references are detected and rejected.

### Environment Promotion

Prompts move through environments: `development` → `staging` → `production`.

- Use the **Promote** button in the editor to advance a prompt
- Batch promote multiple prompts at once via the browser's select mode
- Each promotion creates a Git commit with an auto-generated message

### Evaluations

Run [promptfoo](https://www.promptfoo.dev/) evaluations directly from the UI:

1. Define assertions in the prompt's `eval` front-matter section
2. Click **Run Eval** → select models → view pass/fail results
3. Auto-generate test cases with [PromptPex](https://microsoft.github.io/promptpex/)
4. CI/CD: GitHub Action runs evals on PRs that modify prompt files

### Prompty Compatibility

Import and export [.prompty](https://prompty.ai/) files (Microsoft's open prompt format):

- **Export:** Download any prompt as a `.prompty` file from the editor
- **Import:** Upload `.prompty` files from the browser — they're converted to `.md` and committed to GitHub

### TTS Preview

For prompts with `type: tts`, render the template and synthesize audio via ElevenLabs:

1. Set `ELEVENLABS_API_KEY` in `.env`
2. Click **TTS Preview** in the editor
3. Audio plays in-browser with file-based caching on the server

### Batch Operations

Select multiple prompts in the browser and apply bulk changes in a single Git commit:

- Set environment (dev/staging/production)
- Toggle active/inactive
- Delete selected
- Batch promotion

## Project Structure

```
prompt-mgmt/
├── server/                  # FastAPI backend
│   ├── main.py              # App entry, lifespan, middleware
│   ├── config.py            # Pydantic Settings (env vars)
│   ├── auth/                # GitHub OAuth, sessions, API keys, middleware
│   ├── api/                 # Route handlers (public, admin, webhooks, eval)
│   ├── services/            # Business logic (github, sync, render, eval, tts)
│   ├── db/                  # aiosqlite, migrations, query modules
│   ├── models/              # Pydantic models
│   └── utils/               # Front-matter parser, crypto, prompty converter
├── web/                     # React + Vite frontend
│   └── src/
│       ├── pages/           # 9 route pages
│       ├── components/      # Layout, editor, prompts, eval components
│       ├── hooks/           # React Query hooks
│       ├── api/             # API client functions
│       └── lib/             # Zod schemas, constants
├── sdk/                     # Python SDK (pip install promptdis)
│   └── src/promptdis/       # Client, async client, cache, models, exceptions
├── sdk-ts/                  # TypeScript SDK (@promptdis/client)
│   └── src/                 # Client, cache, models, errors
├── tests/                   # Python test suite
│   ├── conftest.py          # Shared fixtures (in-memory DB, seed data)
│   ├── server/              # Backend tests (18 files)
│   └── sdk/                 # SDK tests (3 files)
├── .github/workflows/       # CI, prompt evals, PyPI publish
├── pyproject.toml           # Server dependencies
├── docker-compose.yml       # Dev environment
├── Dockerfile               # Production build
└── .env.example             # Environment template
```

## Testing

```bash
# Backend (224 tests)
python -m pytest tests/ -v

# Frontend (66 tests)
cd web && npx vitest run

# TypeScript SDK (18 tests)
cd sdk-ts && npx vitest run
```

**308 total tests** across Python backend, web frontend, and TypeScript SDK.

## CI/CD

### GitHub Actions

- **`ci.yml`** — Runs on every push: ruff lint, tsc type-check, pytest, vitest, container build
- **`prompt-evals.yml`** — Runs on PRs that modify `.md` files: executes promptfoo evaluations, posts results as PR comment, optionally blocks merge
- **`publish.yml`** — Publishes Python SDK to PyPI on `v*` git tags

## Configuration Reference

All configuration is via environment variables (loaded from `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_CLIENT_ID` | (required) | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | (required) | GitHub OAuth App client secret |
| `APP_SECRET_KEY` | `change-me-in-production` | Secret for session/token encryption |
| `APP_BASE_URL` | `http://localhost:8000` | Server base URL |
| `FRONTEND_URL` | `http://localhost:5173` | Frontend URL (for OAuth redirect) |
| `DATABASE_PATH` | `./data/promptdis.db` | SQLite database file path |
| `LOG_LEVEL` | `info` | Logging level |
| `RATE_LIMIT_PER_MINUTE` | `100` | API rate limit per key/IP |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `ELEVENLABS_API_KEY` | (empty) | ElevenLabs API key for TTS preview |
| `ELEVENLABS_DEFAULT_MODEL` | `eleven_multilingual_v2` | Default TTS model |
| `ELEVENLABS_DEFAULT_VOICE_ID` | (empty) | Fallback voice ID |
| `TTS_CACHE_DIR` | `./data/tts_cache` | TTS audio cache directory |
| `TTS_CACHE_MAX_ENTRIES` | `100` | Max cached TTS files |
| `TTS_CACHE_TTL_HOURS` | `24` | TTS cache expiry |

## Database

SQLite is used as a fast index/cache layer. GitHub remains the source of truth for all prompt content.

**Schema (11 tables):** organizations, applications, prompts, users, sessions, org_memberships, api_keys, eval_runs, prompt_access_log, webhook_deliveries, schema_version

Migrations run automatically on server startup from `server/db/migrations/`. The database file is created at `DATABASE_PATH` if it doesn't exist.

## Build Phases

The project was built in 4 phases (Phase 5 is FutureSelf-specific integration):

| Phase | Scope | Status |
|-------|-------|--------|
| **1. Core Platform** | FastAPI scaffold, SQLite, GitHub OAuth, sync, public/admin API, Python SDK, React frontend (9 pages) | Complete |
| **2. Eval & Testing** | Promptfoo runner, PromptPex, eval UI, CI/CD, 238 tests | Complete |
| **3. Multi-Modal & TTS** | TTS/audio front-matter UI, ElevenLabs preview, modality badges | Complete |
| **4. Advanced Features** | TypeScript SDK, prompt composition, analytics, diff viewer, batch ops, Prompty import/export, environment promotion | Complete |
| **5. FutureSelf Integration** | Server deployment, SDK integration, prompt migration | Planned |

See [PROMPT_APP_BUILD_CHECKLIST.md](../dwight_docs/prompt_mgmt/PROMPT_APP_BUILD_CHECKLIST.md) for the full sprint-by-sprint tracker.

## Incomplete / Planned Items

- **TypeScript SDK `render()`** — local rendering supports basic `{{var}}` substitution only (no Jinja2). Use `client.render()` for server-side rendering with full Jinja2 support.
- **Analytics percentiles** — SQLite approximation (avg/min/max) instead of exact p50/p90/p99.
- **Prompty import** — core fields mapped; Prompty-specific `sample` field is best-effort.
- **npm publish workflow** — TypeScript SDK does not yet have a publish workflow (`sdk-ts/` needs npm publish CI).
- **Docker Compose for TS SDK** — not included in `docker-compose.yml`.
- **Phase 5** — FutureSelf integration (server deployment, SDK wiring, prompt migration) is not started.

## License

MIT
