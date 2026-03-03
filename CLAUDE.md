# CLAUDE.md — Promptdis

## What is this?

Promptdis is a Git-native LLM prompt management platform. Prompts are stored as `.md` files with YAML front-matter in GitHub repos (source of truth), edited via a web UI, and served via API/SDK for hot-reload.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| Database | SQLite via aiosqlite (index/cache only) |
| Git Integration | PyGithub (GitHub API) |
| Auth | GitHub OAuth SSO + bcrypt API keys |
| Frontend | React 18 + Vite + TailwindCSS + TypeScript |
| Editor | CodeMirror 6 |
| SDK | Python package `promptdis` |

## Architecture

- **GitHub is source of truth** — all prompt `.md` files live in GitHub repos
- **SQLite is index/cache** — stores metadata for fast search, rebuildable from GitHub
- **GitHub webhooks** trigger re-indexing on push events
- **Public API** serves prompts to SDK/services with ETag caching
- **Admin API** provides CRUD that commits changes to GitHub

## Running Locally

```bash
# Backend
uv sync
uvicorn server.main:app --reload --port 8000

# Frontend
cd web && npm install && npm run dev
```

## Key Files

- `server/main.py` — FastAPI app entry point
- `server/config.py` — Pydantic Settings (env vars)
- `server/db/migrations/001_initial.sql` — SQLite schema
- `server/api/public.py` — Public prompt fetch API
- `server/api/admin.py` — Admin CRUD API
- `server/services/github_service.py` — PyGithub wrapper
- `server/services/sync_service.py` — GitHub → SQLite sync
- `sdk/src/promptdis/client.py` — Python SDK client

## Spec

Full PRD/spec lives at: `../dwight_docs/prompt_mgmt/PROMPT_APP.md`
