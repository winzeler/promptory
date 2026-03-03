# Promptdis — Runbook

Operational guide for deploying, administering, and troubleshooting **Promptdis**, a Git-native LLM prompt management platform.

> **Naming note:** This project was previously called "Promptory." All references now use "Promptdis."

---

## Table of Contents

1. [Prerequisites & Environment Setup](#1-prerequisites--environment-setup)
2. [Local Development](#2-local-development)
3. [Deployment](#3-deployment)
4. [Day-to-Day Operations](#4-day-to-day-operations)
5. [Database Operations](#5-database-operations)
6. [Updating & Rollback](#6-updating--rollback)
7. [Secret Management](#7-secret-management)
8. [Troubleshooting](#8-troubleshooting)
9. [Teardown](#9-teardown)
10. [Architecture Quick Reference](#10-architecture-quick-reference)

---

## 1. Prerequisites & Environment Setup

### Tool Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 20+ | Frontend build, TypeScript SDK |
| Docker or Podman | Latest | Container deployment |
| AWS CLI | v2 | Serverless deployment |
| AWS SAM CLI | Latest | Lambda packaging and deploy |
| `uv` (optional) | Latest | Fast Python dependency management |

### GitHub OAuth App Setup

Create a GitHub OAuth App at <https://github.com/settings/developers>.

| Field | Local | Container | Serverless |
|-------|-------|-----------|------------|
| Homepage URL | `http://localhost:5173` | `http://localhost:5173` | CloudFront URL |
| Authorization callback URL | `http://localhost:8000/auth/github/callback` | `http://localhost:8000/auth/github/callback` | `https://<api-gw>.execute-api.<region>.amazonaws.com/<stage>/auth/github/callback` |

After creation, copy the **Client ID** and generate a **Client secret**.

### Environment Variables

All configuration is via environment variables (loaded from `.env` in local/container mode).

Copy the template:

```bash
cp .env.example .env
```

#### Complete Variable Reference

| Variable | Default | Required | Mode | Description |
|----------|---------|----------|------|-------------|
| `GITHUB_CLIENT_ID` | — | Yes | All | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | — | Yes | All | GitHub OAuth App client secret |
| `APP_SECRET_KEY` | `change-me-in-production` | Yes | All | Session/token encryption key |
| `APP_BASE_URL` | `http://localhost:8000` | No | All | Server base URL |
| `FRONTEND_URL` | `http://localhost:5173` | No | All | Frontend URL (OAuth redirect) |
| `DATABASE_PATH` | `./data/promptdis.db` | No | All | SQLite database file path |
| `LOG_LEVEL` | `info` | No | All | Logging level (`debug`, `info`, `warning`, `error`) |
| `RATE_LIMIT_PER_MINUTE` | `100` | No | All | API rate limit per key/IP |
| `CORS_ORIGINS` | `http://localhost:5173` | No | All | Comma-separated allowed origins |
| `DEPLOYMENT_MODE` | `container` | No | All | `container` or `lambda` |
| `AWS_REGION` | `us-west-2` | No | Lambda | AWS region |
| `DYNAMODB_STATE_TABLE` | `promptdis-oauth-states` | No | Lambda | DynamoDB table for OAuth CSRF state |
| `S3_TTS_BUCKET` | — | No | Lambda | S3 bucket for TTS audio cache |
| `ELEVENLABS_API_KEY` | — | No | All | ElevenLabs API key for TTS preview |
| `ELEVENLABS_DEFAULT_MODEL` | `eleven_multilingual_v2` | No | All | Default TTS model |
| `ELEVENLABS_DEFAULT_VOICE_ID` | — | No | All | Fallback voice ID |
| `TTS_CACHE_DIR` | `./data/tts_cache` | No | Container | TTS audio cache directory |
| `TTS_CACHE_MAX_ENTRIES` | `100` | No | Container | Max cached TTS files |
| `TTS_CACHE_TTL_HOURS` | `24` | No | Container | TTS cache expiry in hours |

#### Generate a Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 2. Local Development

### Option A: Direct Install (uv)

```bash
# Install backend dependencies
uv sync

# Install frontend dependencies
cd web && npm install && cd ..
```

Start both services:

```bash
# Terminal 1 — API server
uvicorn server.main:app --reload --port 8000

# Terminal 2 — Frontend dev server
cd web && npm run dev
```

- API: <http://localhost:8000> (Swagger docs at `/docs`)
- Web UI: <http://localhost:5173>

### Option B: Direct Install (pip)

```bash
pip install -e ".[dev]"
cd web && npm install && cd ..
```

Same start commands as Option A.

### Option C: Docker Compose

```bash
docker compose up
```

Or with Podman:

```bash
podman-compose up
```

This starts the API on port 8000 and the web UI on port 5173. Pass configuration via `.env` (auto-loaded by the `api` service).

### Running Tests

```bash
# Backend (Python — 253 tests)
python -m pytest tests/ -v

# Frontend (Vitest — 66 tests)
cd web && npx vitest run

# TypeScript SDK (18 tests)
cd sdk-ts && npx vitest run
```

### First-Time Setup

1. Open <http://localhost:5173> and sign in with GitHub
2. Your GitHub organizations are synced automatically
3. Go to **Settings** > **Add Application** > enter a GitHub repo containing `.md` prompt files
4. Promptdis indexes all `.md` files from the repo into SQLite
5. Browse, edit, and create prompts through the web UI

---

## 3. Deployment

### Container Deployment

#### Build Images

```bash
# API container
docker build -t promptdis -f Containerfile .

# Web UI container (nginx)
docker build -t promptdis-web -f web/Containerfile web/
```

Or with Podman:

```bash
podman build -t promptdis -f Containerfile .
podman build -t promptdis-web -f web/Containerfile web/
```

#### Run Standalone

```bash
# API
docker run -d \
  --name promptdis-api \
  -p 8000:8000 \
  -v promptdis-data:/app/data \
  -e GITHUB_CLIENT_ID=... \
  -e GITHUB_CLIENT_SECRET=... \
  -e APP_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  -e APP_BASE_URL=https://api.example.com \
  -e FRONTEND_URL=https://app.example.com \
  -e CORS_ORIGINS=https://app.example.com \
  promptdis

# Web UI
docker run -d \
  --name promptdis-web \
  -p 80:80 \
  promptdis-web
```

The web container serves a static Vite build via nginx. Set `VITE_API_BASE_URL` at **build time**:

```bash
docker build -t promptdis-web \
  --build-arg VITE_API_BASE_URL=https://api.example.com \
  -f web/Containerfile web/
```

#### Run with Docker Compose

```bash
docker compose up -d
```

Compose mounts `./server` and `./web/src` for hot-reload in development.

### Serverless Deployment (AWS Lambda)

Architecture: Lambda + API Gateway + EFS (SQLite) + DynamoDB (OAuth state) + S3 (TTS cache + web assets) + CloudFront (web UI CDN).

#### First-Time Deploy (Guided)

```bash
./scripts/deploy-serverless.sh --guided
```

This runs `sam build` then `sam deploy --guided`, which prompts for:

- Stack name (e.g., `promptdis-dev`)
- AWS region
- Parameter values: `GitHubClientId`, `GitHubClientSecret`, `AppSecretKey`, `Stage`, etc.
- SAM saves answers to `infra/samconfig.toml` for future deploys

#### Subsequent Deploys

```bash
./scripts/deploy-serverless.sh
```

#### Deploy Web UI to S3 + CloudFront

```bash
./scripts/deploy-web.sh --stack promptdis-dev
```

This script:
1. Reads stack outputs (S3 bucket, CloudFront distribution ID, API URL)
2. Builds the web UI with `VITE_API_BASE_URL` set to the API Gateway URL
3. Syncs `dist/` to S3
4. Invalidates CloudFront cache

#### Post-Deploy: Set Frontend URL

After the first deploy, update the `FrontendUrl` parameter with the CloudFront distribution URL:

```bash
cd infra && sam deploy --parameter-overrides \
  "FrontendUrl=https://d1234567890.cloudfront.net" \
  "GitHubClientId=..." \
  "GitHubClientSecret=..." \
  "AppSecretKey=..."
```

Also update the GitHub OAuth App's callback URL to point to the API Gateway URL.

### CI/CD Pipeline

The `.github/workflows/ci.yml` workflow runs on every push/PR to `main`:

| Job | What it does |
|-----|-------------|
| `backend` | Install deps, `ruff check`, `pytest` |
| `frontend` | `npm ci`, `tsc --noEmit`, `npm test`, `npm run build` |
| `containers` | Build API + Web container images |
| `deploy-serverless` | (main branch only) `sam build` + `sam deploy` + deploy web UI |

#### Required GitHub Secrets

| Secret | Used by |
|--------|---------|
| `AWS_DEPLOY_ROLE_ARN` | `ci.yml` — OIDC role for SAM deploy |

#### Required GitHub Variables

| Variable | Used by | Default |
|----------|---------|---------|
| `AWS_REGION` | `ci.yml` | `us-west-2` |
| `SAM_STACK_NAME` | `ci.yml` | `promptdis-dev` |
| `EVAL_BLOCK_MERGE` | `prompt-evals.yml` | `false` |

#### Prompt Evaluation CI

`prompt-evals.yml` runs on PRs that modify `.md` files (excluding README/CLAUDE.md):

1. Detects changed prompt files
2. Parses front-matter `eval` config
3. Runs promptfoo evaluations
4. Posts results as a PR comment
5. Optionally blocks merge if `EVAL_BLOCK_MERGE=true`

Eval secrets: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`.

#### SDK Publishing

`publish.yml` publishes the Python SDK to PyPI when you push a `v*` tag:

```bash
git tag v0.2.0
git push origin v0.2.0
```

---

## 4. Day-to-Day Operations

### Health Checks

```bash
# Local / container
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"promptdis","version":"0.1.0"}

# Lambda
curl https://<api-gw-id>.execute-api.<region>.amazonaws.com/<stage>/health
```

### Force Sync (Re-index from GitHub)

```bash
# Via API (requires admin session cookie)
curl -X POST http://localhost:8000/api/v1/admin/sync \
  -H "Cookie: session=<session-id>"
```

Or use the web UI: **Sync Status** page > **Force Sync**.

### Monitoring (Serverless)

#### Tail CloudWatch Logs

```bash
# API function
aws logs tail /aws/lambda/promptdis-dev-api --follow

# Cleanup function
aws logs tail /aws/lambda/promptdis-dev-cleanup --follow
```

#### Key Metrics

| Metric | Namespace | Dimension |
|--------|-----------|-----------|
| Invocations | `AWS/Lambda` | `FunctionName: promptdis-<stage>-api` |
| Errors | `AWS/Lambda` | `FunctionName: promptdis-<stage>-api` |
| Duration | `AWS/Lambda` | `FunctionName: promptdis-<stage>-api` |
| Throttles | `AWS/Lambda` | `FunctionName: promptdis-<stage>-api` |
| 5XXError | `AWS/ApiGateway` | `ApiId: <http-api-id>` |

#### Configured Alarms (from `infra/template.yaml`)

| Alarm | Condition |
|-------|-----------|
| `promptdis-<stage>-api-errors` | Lambda errors > 5 in 5 minutes |
| `promptdis-<stage>-api-duration` | p99 duration > 10 seconds |
| `promptdis-<stage>-api-throttles` | Any throttle events |

### Webhook Verification

When an application is added, Promptdis registers a GitHub webhook. Verify it's working:

1. Push a change to a prompt `.md` file in the connected repo
2. Check **Sync Status** in the web UI for a new sync entry
3. Or check webhook deliveries in GitHub: repo **Settings** > **Webhooks** > **Recent Deliveries**

### Built-in Analytics

```bash
# Requests per day (admin session required)
curl http://localhost:8000/api/v1/admin/analytics/requests-per-day \
  -H "Cookie: session=<session-id>"

# Top prompts
curl http://localhost:8000/api/v1/admin/analytics/top-prompts \
  -H "Cookie: session=<session-id>"
```

Or view the **Dashboard** page in the web UI.

---

## 5. Database Operations

### Schema Overview

SQLite is an **index/cache only** — GitHub is the source of truth. The database can be rebuilt from scratch at any time via force sync.

**11 tables** across 2 migration files:

| Table | Purpose | Migration |
|-------|---------|-----------|
| `schema_version` | Migration tracking | 001 |
| `organizations` | GitHub orgs | 001 |
| `applications` | GitHub repos (prompt sources) | 001 |
| `prompts` | Prompt metadata + body | 001 + 002 |
| `users` | GitHub OAuth users | 001 |
| `sessions` | Login sessions | 001 |
| `api_keys` | SDK/API authentication keys | 001 |
| `org_memberships` | User ↔ org mapping | 001 |
| `eval_runs` | Evaluation history | 001 |
| `prompt_access_log` | API usage tracking | 001 |
| `webhook_deliveries` | Webhook idempotency | 002 |
| `prompts_fts` | FTS5 full-text search (virtual) | 002 |

### Auto-Migration

Migrations run automatically on server startup. The server reads `server/db/migrations/*.sql`, compares versions against `schema_version`, and applies pending files in order.

No manual migration step is needed.

### Manual SQLite Inspection

```bash
# Open the database
sqlite3 data/promptdis.db

# Check schema version
SELECT * FROM schema_version;

# Count prompts
SELECT COUNT(*) FROM prompts;

# List applications and their prompt counts
SELECT a.github_repo, COUNT(p.id) as prompt_count
FROM applications a
LEFT JOIN prompts p ON p.app_id = a.id
GROUP BY a.id;

# Full-text search
SELECT name, description FROM prompts_fts WHERE prompts_fts MATCH 'meditation';

# Check active sessions
SELECT u.github_login, s.expires_at
FROM sessions s JOIN users u ON u.id = s.user_id
WHERE s.expires_at > datetime('now');

# Recent webhook deliveries
SELECT * FROM webhook_deliveries ORDER BY processed_at DESC LIMIT 10;

# API usage last 7 days
SELECT date(created_at) as day, COUNT(*) as requests
FROM prompt_access_log
WHERE created_at > datetime('now', '-7 days')
GROUP BY day ORDER BY day;
```

### Backup and Restore

```bash
# Backup (while server is running — WAL mode allows concurrent reads)
sqlite3 data/promptdis.db ".backup data/promptdis-backup.db"

# Restore
cp data/promptdis-backup.db data/promptdis.db
# Restart the server
```

For Lambda (EFS), backup from a bastion/EC2 with the EFS mounted, or snapshot the EFS filesystem.

### Rebuild from Scratch

Since GitHub is the source of truth, the database can be fully rebuilt:

```bash
# 1. Stop the server
# 2. Delete the database
rm data/promptdis.db data/promptdis.db-wal data/promptdis.db-shm 2>/dev/null

# 3. Start the server (auto-creates DB and runs migrations)
uvicorn server.main:app --port 8000

# 4. Force sync to re-index all prompts from GitHub
curl -X POST http://localhost:8000/api/v1/admin/sync \
  -H "Cookie: session=<session-id>"
```

**Note:** Rebuilding loses local-only data: sessions, API keys, eval history, and access logs. Users will need to re-authenticate and regenerate API keys.

### Journal Mode

| Mode | Deployment | Reason |
|------|-----------|--------|
| **WAL** (Write-Ahead Logging) | Container / local | Concurrent reads during writes, better performance |
| **DELETE** | Lambda (EFS) | EFS lacks mmap support required for WAL |

The server sets the journal mode automatically based on `DEPLOYMENT_MODE` (see `server/db/database.py`).

---

## 6. Updating & Rollback

### Code Updates

#### Local

```bash
git pull origin main
pip install -e ".[dev]"       # if dependencies changed
cd web && npm install && cd .. # if frontend deps changed
# Restart uvicorn (or rely on --reload)
```

#### Container

```bash
git pull origin main
docker compose build
docker compose up -d
```

#### Serverless

Push to `main` triggers CI/CD which runs `sam deploy` + web deploy automatically.

Manual deploy:

```bash
git pull origin main
./scripts/deploy-serverless.sh
./scripts/deploy-web.sh --stack promptdis-dev
```

### Serverless Rollback

#### Rollback to Previous Commit

```bash
git checkout <previous-sha>
./scripts/deploy-serverless.sh
./scripts/deploy-web.sh --stack promptdis-dev
git checkout main
```

#### Rollback Lambda Code Only

```bash
# List recent versions
aws lambda list-versions-by-function \
  --function-name promptdis-dev-api \
  --query "Versions[-5:].[Version,Description]"

# Point alias to previous version (if using aliases)
aws lambda update-alias \
  --function-name promptdis-dev-api \
  --name live \
  --function-version <version-number>
```

### Prompt-Level Rollback

Roll back an individual prompt to a previous Git commit:

```bash
# View prompt history
curl http://localhost:8000/api/v1/admin/prompts/<prompt-id>/history \
  -H "Cookie: session=<session-id>"

# View content at a specific commit
curl http://localhost:8000/api/v1/admin/prompts/<prompt-id>/at/<sha> \
  -H "Cookie: session=<session-id>"

# Rollback to that commit
curl -X POST http://localhost:8000/api/v1/admin/prompts/<prompt-id>/rollback \
  -H "Cookie: session=<session-id>" \
  -H "Content-Type: application/json" \
  -d '{"sha": "<commit-sha>"}'
```

Or use the **Prompt Editor** > **History** tab > **Rollback** button in the web UI.

---

## 7. Secret Management

### Secrets Inventory

| Secret | Where stored | Rotation impact |
|--------|-------------|-----------------|
| `APP_SECRET_KEY` | `.env` / SAM parameter | Invalidates all sessions — users must re-login |
| `GITHUB_CLIENT_ID` | `.env` / SAM parameter | Must match GitHub OAuth App |
| `GITHUB_CLIENT_SECRET` | `.env` / SAM parameter | Must match GitHub OAuth App |
| `ELEVENLABS_API_KEY` | `.env` / SAM parameter | TTS preview stops working until updated |
| API keys (`pm_live_...`) | SQLite `api_keys` table (bcrypt hash) | Per-key; revoke old, generate new |

### Rotating APP_SECRET_KEY

```bash
# 1. Generate new key
python -c "import secrets; print(secrets.token_hex(32))"

# 2. Update .env (local/container) or SAM parameter (serverless)
# 3. Restart the server
# All existing sessions are invalidated — users must re-login
```

### Rotating GitHub OAuth Credentials

1. Go to <https://github.com/settings/developers> > your OAuth App
2. Generate a new client secret (old one stays active briefly)
3. Update `GITHUB_CLIENT_SECRET` in `.env` or SAM parameters
4. Restart the server
5. Delete the old secret in the GitHub OAuth App settings

### API Key Management

```bash
# Create a new API key scoped to specific applications (via web UI or API)
curl -X POST http://localhost:8000/api/v1/admin/api-keys \
  -H "Cookie: session=<session-id>" \
  -H "Content-Type: application/json" \
  -d '{"name": "production-service", "scopes": {"app_ids": ["<app-uuid>"], "permissions": ["read"]}}'
# Response includes the full key (pm_live_...) — store it securely, it's only shown once
# Note: app_ids is required and must be a non-empty list of valid application UUIDs

# List keys
curl http://localhost:8000/api/v1/admin/api-keys \
  -H "Cookie: session=<session-id>"

# Revoke a key
curl -X DELETE http://localhost:8000/api/v1/admin/api-keys/<key-id> \
  -H "Cookie: session=<session-id>"
```

### Lambda Secret Storage

Secrets are passed as SAM template parameters and set as Lambda environment variables. For enhanced security, consider migrating to AWS Secrets Manager and fetching at runtime.

Current flow: `sam deploy --parameter-overrides` > CloudFormation parameters (NoEcho) > Lambda env vars.

---

## 8. Troubleshooting

### **OAuth login fails — redirects back to login page**

- Verify `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` match your GitHub OAuth App
- Confirm the **Authorization callback URL** in the OAuth App matches `APP_BASE_URL` + `/auth/github/callback`
- Check `FRONTEND_URL` matches where the web UI is served
- In Lambda mode, check that the API Gateway URL is used as `APP_BASE_URL`, not `localhost`
- Check server logs for the specific OAuth error

```bash
# Local: check uvicorn stdout
# Lambda:
aws logs tail /aws/lambda/promptdis-dev-api --follow --filter-pattern "oauth"
```

### **"database is locked" errors**

- In container mode: ensure only one server instance writes to the database. WAL mode supports concurrent reads but only one writer.
- In Lambda mode: `ReservedConcurrentExecutions` is set to `1` in `template.yaml` to prevent concurrent writes. If you increased this, reduce it back to 1.
- Check if a `sqlite3` CLI session is holding a lock: close it.

```bash
# Check for lock files
ls -la data/promptdis.db*

# Force-close (destructive — only if server is stopped)
rm data/promptdis.db-wal data/promptdis.db-shm
```

### **Webhooks not triggering re-index**

- Verify the webhook exists: GitHub repo **Settings** > **Webhooks**
- Check delivery history for failures (HTTP status, response body)
- Confirm the webhook URL is reachable from GitHub (not `localhost`)
- For Lambda, the API Gateway URL must be publicly accessible
- Check `webhook_deliveries` table for duplicate delivery IDs (idempotency)

```sql
SELECT * FROM webhook_deliveries ORDER BY processed_at DESC LIMIT 5;
```

### **Cold start slow on Lambda**

- Default memory: 512 MB. Increasing to 1024 MB gives proportionally more CPU and reduces cold start.
- Python 3.11 cold starts are typically 3-5 seconds with EFS mount.
- The EFS mount adds ~1-2 seconds on cold start. This is unavoidable.
- Consider provisioned concurrency for latency-sensitive workloads:

```bash
aws lambda put-provisioned-concurrency-config \
  --function-name promptdis-dev-api \
  --qualifier live \
  --provisioned-concurrent-executions 1
```

### **Prompts not appearing after sync**

- Check sync status: **Sync Status** page or `applications.last_synced_at` in SQLite
- Verify the GitHub repo has `.md` files with valid YAML front-matter
- Check that the `subdirectory` on the application matches where prompt files live
- Force a manual sync:

```bash
curl -X POST http://localhost:8000/api/v1/admin/sync \
  -H "Cookie: session=<session-id>"
```

- Check server logs for parsing errors on specific files

### **TTS preview errors**

- Verify `ELEVENLABS_API_KEY` is set and valid
- Check that the prompt has `type: tts` in its front-matter
- Verify `ELEVENLABS_DEFAULT_VOICE_ID` is set (or the prompt specifies a `voice_id` in its `tts` front-matter)
- In Lambda mode, TTS audio is cached in S3 (`S3_TTS_BUCKET`). Verify the bucket exists and the Lambda has `s3:PutObject`/`s3:GetObject` permissions.

### **FTS (full-text search) not returning results**

- FTS is powered by SQLite FTS5 (`prompts_fts` virtual table, migration 002)
- If the database was created before migration 002, verify it was applied:

```sql
SELECT * FROM schema_version;
-- Should show version 2
```

- If FTS index is out of sync, rebuild it:

```sql
INSERT INTO prompts_fts(prompts_fts) VALUES('rebuild');
```

### **403 Forbidden on public API**

- The API key is scoped to specific applications and the requested prompt belongs to a different application
- Check the key's `scopes.app_ids` — it must include the `app_id` of the prompt being fetched
- Existing keys with `scopes=NULL` (created before scope enforcement) have access to all apps
- To fix: create a new key with the correct application(s) selected, or use an unscoped legacy key

### **Rate limiting (429 Too Many Requests)**

- Default limit: 100 requests/minute per API key or IP
- Increase via `RATE_LIMIT_PER_MINUTE` env var
- API Gateway (Lambda) also has throttling: burst limit 50, rate limit 100/sec (configured in `template.yaml`)

### **EFS mount fails on Lambda**

- Both Lambda subnets must have a mount target. Check `MountTargetA` and `MountTargetB` in the CloudFormation stack.
- The Lambda security group must allow outbound NFS (port 2049) to the EFS security group.
- Verify the EFS access point exists and has correct POSIX permissions (UID/GID 1000):

```bash
aws efs describe-access-points --file-system-id <efs-id>
```

### **"Module not found" on Lambda**

- Ensure `sam build` ran successfully before deploy. SAM copies dependencies into `.aws-sam/build/`.
- The `CodeUri` in `template.yaml` is `..` (repo root). Verify `server/` exists relative to `infra/`.
- Check that `mangum` is in `pyproject.toml` dependencies (it's the ASGI-to-Lambda adapter).
- If using layers, verify the layer ARN and runtime match.

---

## 9. Teardown

### Local Cleanup

```bash
# Remove database and cache
rm -rf data/

# Remove Python environment
rm -rf .venv/

# Remove frontend dependencies
rm -rf web/node_modules/
```

### Container Cleanup

```bash
# Stop and remove containers + volumes
docker compose down -v

# Remove images
docker rmi promptdis promptdis-web
```

### Serverless Teardown

```bash
# Delete the SAM stack
cd infra && sam delete --stack-name promptdis-dev
```

**Manual cleanup** — these resources may not be auto-deleted:

| Resource | Cleanup Command |
|----------|----------------|
| S3 web bucket | `aws s3 rb s3://promptdis-web-dev --force` |
| S3 TTS cache bucket | `aws s3 rb s3://promptdis-tts-cache-dev --force` |
| EFS filesystem | `aws efs delete-file-system --file-system-id <id>` |
| CloudWatch log groups | `aws logs delete-log-group --log-group-name /aws/lambda/promptdis-dev-api` |
| GitHub OAuth App | Delete manually at <https://github.com/settings/developers> |

**Note:** S3 buckets must be emptied before deletion. `--force` handles this.

---

## 10. Architecture Quick Reference

### Container Mode

```
┌─────────────────┐     ┌──────────────────────────┐     ┌────────────┐
│  React Frontend │────▶│   FastAPI Server          │────▶│   GitHub   │
│  (Vite / nginx) │     │   (uvicorn)               │     │   (repos)  │
│  :5173 / :80    │     │   :8000                   │     └────────────┘
└─────────────────┘     │  ┌─────────┐ ┌────────┐  │            │
                        │  │ SQLite  │ │ TTS    │  │     ┌──────┴─────┐
┌─────────────────┐     │  │ (WAL)   │ │ cache  │  │     │  Webhooks  │
│  Python SDK     │────▶│  └─────────┘ └────────┘  │     └────────────┘
│  TypeScript SDK │     └──────────────────────────┘
└─────────────────┘              │
                          ./data/ volume
```

### Serverless Mode (AWS)

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────────────┐
│  CloudFront CDN │────▶│  S3 Bucket   │     │   GitHub                │
│  (web UI)       │     │  (static)    │     │   (source of truth)     │
└─────────────────┘     └──────────────┘     └────────────┬────────────┘
                                                          │ webhooks
┌─────────────────┐     ┌──────────────┐     ┌────────────▼────────────┐
│  SDKs / clients │────▶│  API Gateway │────▶│  Lambda (FastAPI+Mangum)│
└─────────────────┘     │  (HTTP API)  │     │  ┌───────┐ ┌─────────┐ │
                        └──────────────┘     │  │ EFS   │ │DynamoDB │ │
                                             │  │SQLite │ │OAuth st.│ │
                                             │  └───────┘ └─────────┘ │
                                             │  ┌─────────┐           │
                                             │  │ S3 TTS  │           │
                                             │  │ cache   │           │
                                             │  └─────────┘           │
                                             └────────────────────────┘
```

### Key File Paths

| File | Purpose |
|------|---------|
| `server/main.py` | FastAPI app entry point, middleware, lifespan |
| `server/config.py` | Pydantic Settings — all env vars |
| `server/lambda_handler.py` | Mangum adapter for AWS Lambda |
| `server/db/database.py` | DB init, migration runner, journal mode |
| `server/db/migrations/001_initial.sql` | Base schema (10 tables) |
| `server/db/migrations/002_body_fts_webhooks.sql` | FTS5, body column, webhook tracking |
| `server/auth/github_oauth.py` | GitHub OAuth flow |
| `server/auth/sessions.py` | Session management + cleanup |
| `server/auth/middleware.py` | Auth middleware |
| `server/auth/rate_limiter.py` | Rate limiting middleware |
| `server/api/public.py` | Public prompt fetch API |
| `server/api/admin.py` | Admin CRUD API |
| `server/api/webhooks.py` | GitHub webhook handler |
| `server/api/eval.py` | Evaluation endpoints |
| `server/api/api_keys.py` | API key management |
| `server/services/github_service.py` | PyGithub wrapper |
| `server/services/sync_service.py` | GitHub-to-SQLite sync |
| `server/services/render_service.py` | Jinja2 rendering |
| `server/services/eval_service.py` | Promptfoo runner |
| `server/utils/front_matter.py` | YAML front-matter parser |
| `infra/template.yaml` | SAM template — all AWS resources |
| `scripts/deploy-serverless.sh` | SAM build + deploy |
| `scripts/deploy-web.sh` | Web UI build + S3 sync + CloudFront invalidation |
| `scripts/cleanup_sessions_handler.py` | Lambda: hourly session cleanup |
| `docker-compose.yml` | Local dev composition |
| `Containerfile` | API multi-stage Docker build |
| `web/Containerfile` | Web UI multi-stage Docker build (nginx) |

### API Endpoint Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Health check |
| `GET` | `/` | None | Service info |
| `GET` | `/auth/github/login` | None | Start OAuth |
| `GET` | `/auth/github/callback` | None | OAuth callback |
| `POST` | `/auth/logout` | Session | End session |
| `GET` | `/auth/me` | Session | Current user |
| `GET` | `/api/v1/prompts/{id}` | API key | Fetch prompt |
| `GET` | `/api/v1/prompts/by-name/{org}/{app}/{name}` | API key | Fetch by name |
| `POST` | `/api/v1/prompts/{id}/render` | API key | Render with vars |
| `GET` | `/api/v1/admin/orgs` | Session | List orgs |
| `POST` | `/api/v1/admin/sync` | Session | Force sync |
| `GET` | `/api/v1/admin/analytics/*` | Session | Analytics data |
| `POST` | `/webhooks/github` | Webhook secret | GitHub push events |

See the [full API reference](README.md#api-overview) for all admin endpoints.

### Container vs Serverless Comparison

| Aspect | Container | Serverless (Lambda) |
|--------|-----------|---------------------|
| **Compute** | uvicorn (long-running) | Lambda + Mangum (per-request) |
| **Database** | SQLite on local volume (WAL) | SQLite on EFS (DELETE journal) |
| **OAuth state** | SQLite sessions table | DynamoDB (TTL auto-expiry) |
| **TTS cache** | Local filesystem | S3 bucket (1-day lifecycle) |
| **Web UI** | nginx container / Vite dev server | S3 + CloudFront CDN |
| **Session cleanup** | Background asyncio task (hourly) | Separate Lambda (EventBridge hourly) |
| **Scaling** | Manual (replicas) | Automatic (concurrency=1 for SQLite safety) |
| **Cold start** | None | ~3-5 sec (Python + EFS mount) |
| **Cost (low traffic)** | Fixed (server always running) | Near-zero (pay per request) |
| **CORS** | FastAPI middleware | API Gateway + FastAPI middleware |

---

## Cross-References

These documents provide additional context but are not required for day-to-day operations:

- **Full PRD/spec:** `../dwight_docs/prompt_mgmt/PROMPT_APP.md`
- **Serverless rationale:** `../dwight_docs/prompt_mgmt/SERVERLESS_PLAN.md`
- **API schema docs:** `../dwight_docs/prompt_mgmt/PROMPTDIS_API_DOCS.md`
- **FutureSelf platform deployment:** `../dwight_docs/DEPLOYMENT.md`
