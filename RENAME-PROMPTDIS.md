# Plan: Rename Promptory → Promptdis

## Context

Renaming the app from "Promptory" to "Promptdis" across the entire codebase. The `d` in "dis" stays lowercase even when capitalized: **Promptdis** (not PromptDis). All GitHub URLs updated to match.

**47 files** across Python SDK, Go SDK, TypeScript SDK, server, frontend, infrastructure, tests, and docs.

---

## Naming Rules

| Old | New |
|-----|-----|
| `promptory` | `promptdis` |
| `Promptory` | `Promptdis` |
| `PROMPTORY` | `PROMPTDIS` |
| `PromptoryError` | `PromptdisError` |
| `futureself-app/promptory` | `futureself-app/promptdis` |

**Unchanged**: `PromptClient`, `AsyncPromptClient`, `PromptCache`, `Prompt`, `NotFoundError`, `AuthenticationError`, `RateLimitError` (no "promptory" in the name).

---

## Execution Order

### Step 0: Prep
- Clean `sdk/src/promptory/__pycache__/`
- Verify clean git state

### Step 1: Directory Rename
```bash
git mv sdk/src/promptory sdk/src/promptdis
```
Do this **first** so git tracks it as a rename with identical content.

### Step 2: Python SDK Source (`sdk/src/promptdis/`)
Update 6 files — change all `from promptory.` → `from promptdis.`, `PromptoryError` → `PromptdisError`, docstrings:
- `__init__.py`
- `exceptions.py`
- `client.py`
- `async_client.py`
- `models.py`
- `cache.py` (only if it has references)

### Step 3: Python SDK Config
- `sdk/pyproject.toml` — name, description, URLs, packages path

### Step 4: Python SDK Tests
- `tests/sdk/test_client.py` — imports, class names, test method names
- `tests/sdk/test_cache.py` — import
- `tests/sdk/test_models.py` — import

### Step 5: Server Source
- `server/main.py` — docstring, log messages, FastAPI title, service identifier
- `server/config.py` — `promptory.db` → `promptdis.db`, DynamoDB table name
- `server/auth/github_oauth.py` — cookie name `promptory_session` → `promptdis_session`
- `server/auth/middleware.py` — cookie name
- `server/utils/prompty_converter.py` — docstrings
- `server/db/migrations/001_initial.sql` — comment
- `pyproject.toml` (root) — `promptory-server` → `promptdis-server`

### Step 6: Server Tests
- `tests/conftest.py` — docstring
- `tests/server/test_public_api.py` — service name assertion
- `tests/server/test_admin_api.py` — cookie name
- `tests/server/test_analytics.py` — cookie name
- `tests/server/test_render_service.py` — test data

### Step 7: TypeScript SDK
- `sdk-ts/src/errors.ts` — `PromptoryError` → `PromptdisError`
- `sdk-ts/src/client.ts` — import + usage of error class
- `sdk-ts/src/index.ts` — re-export
- `sdk-ts/src/models.ts` — docstring
- `sdk-ts/package.json` — `@promptory/client` → `@promptdis/client`
- `sdk-ts/README.md`

### Step 8: Go SDK
- `sdk-go/go.mod` — module path
- `sdk-go/doc.go` — package name + docs
- `sdk-go/errors.go` — `package promptory` → `package promptdis`, `PromptoryError` → `PromptdisError` (~20 changes)
- `sdk-go/client.go` — package + error references (~18 changes)
- `sdk-go/models.go`, `sdk-go/cache.go` — package declaration
- `sdk-go/client_test.go`, `sdk-go/cache_test.go`, `sdk-go/models_test.go` — package + assertions
- `sdk-go/README.md`

### Step 9: Frontend
- `web/index.html` — `<title>`
- `web/src/hooks/useAutoSave.ts` — localStorage key prefix `promptory_draft_` → `promptdis_draft_`
- `web/src/hooks/useAutoSave.test.ts` — test assertions
- `web/src/pages/LoginPage.tsx` — branding text
- `web/src/components/layout/Sidebar.tsx` — branding text
- `web/package.json` — name

### Step 10: Infrastructure
- `infra/template.yaml` — ~25 resource name changes (`promptory-${Stage}-*` → `promptdis-${Stage}-*`)
- `infra/samconfig.toml` — stack name, s3 prefix

### Step 11: Docker/CI
- `Containerfile` — image tag comments
- `web/Containerfile` — image tag comments
- `.github/workflows/ci.yml` — build tags, stack name default
- `.github/workflows/prompt-evals.yml` — HTML comment marker

### Step 12: Scripts
- `scripts/deploy-web.sh` — comment + usage example
- `scripts/deploy-serverless.sh` — comment
- `scripts/cleanup_sessions_handler.py` — docstring

### Step 13: Config
- `.env.example` — database path

### Step 14: Documentation
- `CLAUDE.md` — title, description, SDK reference, file path
- `README.md` — ~20 changes (title, URLs, install commands, imports, db path)
- `sdk/README.md` — package name, imports, URLs
- `sdk-ts/README.md` — package name, imports, URLs
- `sdk-go/README.md` — module path, imports, URLs

### Step 15: Lock Files
- Edit `web/package-lock.json` name field (lines 2, 8)
- Edit `sdk-ts/package-lock.json` name field (lines 2, 8)

---

## Breaking Changes to Note

1. **Session cookies**: `promptory_session` → `promptdis_session` invalidates existing sessions (users must re-login)
2. **localStorage keys**: `promptory_draft_*` → `promptdis_draft_*` orphans any unsaved drafts
3. **Database file path**: `promptory.db` → `promptdis.db` — existing deployments need file rename or explicit env var
4. **AWS resources**: Changed SAM resource names will create new resources on deploy, not rename existing ones

---

## Verification

```bash
# 1. No remaining references (exclude .git, .txt logs)
grep -ri "promptory" --include='*.py' --include='*.ts' --include='*.tsx' \
  --include='*.go' --include='*.toml' --include='*.yaml' --include='*.yml' \
  --include='*.json' --include='*.md' --include='*.html' --include='*.sh' \
  --include='*.sql' .

# 2. Python tests
pytest tests/ -v

# 3. Frontend tests
cd web && npm test

# 4. Go tests
cd sdk-go && go test ./...

# 5. TypeScript type-check
cd sdk-ts && npx tsc --noEmit

# 6. Quick Python import check
python -c "import sys; sys.path.insert(0, 'sdk/src'); from promptdis import PromptClient, PromptdisError"
```
