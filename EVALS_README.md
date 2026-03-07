# Promptdis Evaluation System

Test prompt quality across models with assertions, auto-generate test cases, and integrate evals into CI/CD.

---

## Table of Contents

1. [Overview & Architecture](#overview--architecture)
2. [Eval Configuration in Prompt Files](#eval-configuration-in-prompt-files)
3. [Running Evaluations from the UI](#running-evaluations-from-the-ui)
4. [Auto-Generate Tests (PromptPex)](#auto-generate-tests-promptpex)
5. [Under the Hood: promptfoo Integration](#under-the-hood-promptfoo-integration)
6. [Credential Resolution](#credential-resolution)
7. [Data Model](#data-model)
8. [API Reference](#api-reference)
9. [CI/CD Integration](#cicd-integration)
10. [SDK Usage](#sdk-usage)
11. [Testing](#testing)
12. [Error Handling](#error-handling)
13. [Source Files](#source-files)

---

## Overview & Architecture

The evaluation system lets you test prompt quality by running prompts against multiple LLM providers and validating outputs with assertions. It has two main capabilities:

- **Run Evals** — execute prompts via [promptfoo](https://www.promptfoo.dev/) against selected models with configurable assertions
- **Auto-Generate Tests** — use PromptPex (LLM-based test generation via Gemini) to create test cases automatically

Supported providers: **OpenAI**, **Anthropic**, **Google (Gemini)**

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Evaluation Pipeline                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User clicks "Run Eval"                                             │
│       │                                                             │
│       ▼                                                             │
│  POST /api/v1/admin/prompts/{id}/eval                               │
│       │                                                             │
│       ├── Resolve provider credentials (cascade)                    │
│       ├── Create eval_run records in SQLite (status: pending)       │
│       └── Fire async background tasks                               │
│              │                                                      │
│              ▼                                                      │
│       For each model:                                               │
│         1. Generate promptfoo YAML config                           │
│         2. Write to temp directory                                  │
│         3. Run: promptfoo eval --config ... --output ... --no-cache │
│         4. Parse output.json results                                │
│         5. Extract cost, duration                                   │
│         6. Update eval_run record (completed/failed)                │
│                                                                     │
│  Frontend polls GET /eval/runs/{id} every 3s                        │
│       │                                                             │
│       ▼                                                             │
│  Display results: status badges, cost, assertions (PASS/FAIL)       │
│  Compare models: grid view (side-by-side) or diff view              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Eval Configuration in Prompt Files

Evaluation config lives in the `eval:` section of a prompt's YAML front-matter.

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `eval.provider` | string | `"promptfoo"` | Eval framework |
| `eval.dataset` | string | `null` | Path or reference to test dataset |
| `eval.assertions` | list | `[]` | List of assertion objects |

### Assertion Types

| Type | Description |
|------|-------------|
| `contains` | Output must contain the specified substring |
| `llm-rubric` | LLM judges output against a rubric (supports `threshold`) |
| `javascript` | Custom JS assertion function |

### Example: Full Prompt with Eval Config

```markdown
---
name: meditation_script_relax
version: "1.3.0"
description: "Guided relaxation meditation with binaural beats"
type: tts
role: system
domain: wellness
environment: production
active: true
tags: [meditation, relaxation, guided, audio]
model:
  default: gpt-4o
  temperature: 0.8
  max_tokens: 8000
modality:
  input: text
  output: tts
tts:
  provider: elevenlabs
  voice_id: "pNInz6obpgDQGcFmaJgB"
  model_id: eleven_multilingual_v2
  stability: 0.7
  similarity_boost: 0.8
eval:
  provider: promptfoo
  assertions:
    - type: contains
      value: "[PAUSE"
    - type: llm-rubric
      value: "Script is calming, uses present tense, and includes breathing cues"
      threshold: 0.85
---
Create a {{ duration_minutes }}-minute guided relaxation meditation
for {{ listener_name | default('the listener') }}.

Focus area: {{ focus | default('general relaxation') }}

Use the pause marker [PAUSE:3s] for natural breathing pauses.
Tone: warm, gentle, unhurried. Speak in second person present tense.
```

---

## Running Evaluations from the UI

### EvalRunner Component

The eval runner (`web/src/components/eval/EvalRunner.tsx`) provides:

- **Model selection chips** — toggle models on/off with pill buttons
- **Default models:** `gemini-2.0-flash`, `gpt-4o`, `claude-sonnet-4-5-20250929`, `gpt-4o-mini`
- **Custom model input** — type any model identifier and press Enter/Add
- **Provider warning badges** — yellow `!` indicator when a selected model's provider has no API key configured
- **Variables JSON textarea** — expandable input for template variables (e.g. `{"name": "Alice"}`)

### What Happens on Click

1. Frontend POSTs to `/api/v1/admin/prompts/{id}/eval` with selected models and variables
2. API creates `eval_run` records (one per model, status: `pending`)
3. Background tasks fire for each model (async, non-blocking)
4. API returns immediately with run IDs
5. Frontend polls `GET /eval/runs` every **3 seconds** until all runs complete

### EvalResults Component

`web/src/components/eval/EvalResults.tsx` displays:

- **Results table** — model, status badge (color-coded), cost (`$0.0012`), duration, date
- **Status badges:** green=completed, red=failed, blue=running, gray=pending
- **Expandable rows** — click to see full output and assertion details
- **Assertion display** — each assertion shows `PASS` (green) or `FAIL` (red) with score
- **Export JSON** button — downloads all runs as a `.json` file

### ModelComparison Component

`web/src/components/eval/ModelComparison.tsx` — available when 2+ runs complete:

- **Grid view** — side-by-side cards with output, latency, cost, and badges:
  - `Fastest` (green) — lowest latency
  - `Cheapest` (blue) — lowest cost
- **Diff view** — line-by-line comparison of first two models with red/green highlighting for differences

---

## Auto-Generate Tests (PromptPex)

PromptPex uses an LLM (Gemini by default) to analyze a prompt template and generate test cases automatically.

### How It Works

1. The system prompt (`_TEST_GEN_SYSTEM` in `promptpex_service.py`) instructs the LLM to produce 3-5 diverse test cases covering:
   - Happy path with typical inputs
   - Edge cases (empty inputs, long inputs, special characters)
   - Quality checks (tone, relevance, completeness)

2. The LLM returns a JSON array of test cases, each containing `description`, `vars`, and `assertions`.

3. **Parsing & validation** (`parse_generated_tests()`):
   - Strips markdown code fences if present
   - Extracts JSON array from LLM output (handles extra text around the JSON)
   - `_validate_tests()` normalizes structure, ensures each assertion has `type` and `value`

4. **Conversion** (`tests_to_eval_config()`): transforms generated tests into promptfoo-compatible eval config with `vars`, `assert`, and `description` fields.

### Fallback Behavior

When the `google-generativeai` package is unavailable or the API call fails:

- Extracts Jinja2 variables from the template using regex: `{{ var_name }}`
- Generates 2 basic test cases:
  - **Happy path** with `test_<var>` sample values + `contains` assertion
  - **Empty variables** with empty strings + `llm-rubric` assertion for graceful handling
- If no variables found: generates 1 test with an `llm-rubric` coherence check

### Google API Key Resolution

The generate-tests endpoint resolves the Google API key via the credential cascade (see [Credential Resolution](#credential-resolution)). Falls back to the `GOOGLE_API_KEY` environment variable.

### UI Flow

1. Click **"Auto-Generate Tests"** button in EvalRunner
2. POST to `/api/v1/admin/prompts/{id}/generate-tests`
3. Preview panel appears (purple border) showing generated test cases as JSON
4. User reviews the tests
5. User manually adds relevant tests to the prompt's `eval:` front-matter

---

## Under the Hood: promptfoo Integration

### Config Generation

`generate_promptfoo_config()` in `server/services/eval_service.py` builds a promptfoo config dict:

```yaml
# Generated promptfoo config structure
prompts:
  - "Hello {{ name }}, welcome to {{ place }}."    # Raw Jinja2 body

providers:
  - "openai:gpt-4o"                                # Mapped via get_promptfoo_provider()
  - "anthropic:claude-sonnet-4-5-20250929"

tests:
  - vars:                                           # From user-supplied variables
      name: "Alice"
      place: "Wonderland"
    assert:                                         # From eval.assertions front-matter
      - type: contains
        value: "Hello"
      - type: llm-rubric
        value: "Response is friendly"
        threshold: 0.8
```

### Evaluation Execution

`run_evaluation()` runs a single model evaluation:

1. **Check promptfoo installed** — `shutil.which("promptfoo")`; if missing, marks run as failed
2. **Mark as running** — updates DB status
3. **Generate config** — calls `generate_promptfoo_config()` for the single model
4. **Write temp file** — YAML config to a temporary directory
5. **Execute subprocess:**
   ```
   promptfoo eval --config /tmp/.../promptfooconfig.yaml --output output.json --no-cache
   ```
   - Merges resolved provider credentials into subprocess environment
   - **120-second timeout** via `asyncio.wait_for`
6. **Parse results** — reads `output.json`, extracts cost from results array
7. **Update record** — sets status to `completed` or `failed`, stores results JSON, cost, duration

### Provider Mapping

`get_promptfoo_provider()` in `provider_registry.py` maps model strings to promptfoo format:

| Input Model | Pattern Match | promptfoo Provider String |
|-------------|--------------|--------------------------|
| `gpt-4o` | `gpt`, `openai`, `o1`, `o3` | `openai:gpt-4o` |
| `claude-sonnet-4-5-20250929` | `claude`, `anthropic` | `anthropic:claude-sonnet-4-5-20250929` |
| `gemini-2.0-flash` | `gemini`, `google` | `google:gemini-2.0-flash` |
| `custom-model-v1` | (no match) | `custom-model-v1` (passthrough) |

### Provider Registry

Full registry in `server/services/provider_registry.py`:

| Provider | Category | Models |
|----------|----------|--------|
| `openai` | llm+tts | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`, `o1`, `o1-mini`, `o3-mini` |
| `anthropic` | llm | `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-sonnet-4-5-20250929`, `claude-haiku-4-5-20251001`, `claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307` |
| `google` | llm | `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-pro`, `gemini-1.5-flash` |
| `elevenlabs` | tts | `eleven_multilingual_v2`, `eleven_monolingual_v1`, `eleven_turbo_v2`, `eleven_turbo_v2_5` |

---

## Credential Resolution

Provider API keys are resolved via a cascading lookup in `server/services/credential_service.py`.

### Cascade Order

| Priority | Scope | Environment |
|----------|-------|-------------|
| 1 | App-level | Matching environment |
| 2 | App-level | All environments (NULL) |
| 3 | User-level | Matching environment |
| 4 | User-level | All environments (NULL) |
| 5 | Global | Environment variable fallback |

### `resolve_eval_env_vars()`

Builds an environment variable dict for the promptfoo subprocess:

1. Deduplicates providers across all selected models
2. Resolves credentials per provider via the cascade
3. Returns a dict like:
   ```python
   {"OPENAI_API_KEY": "sk-...", "ANTHROPIC_API_KEY": "sk-...", "GOOGLE_API_KEY": "AI..."}
   ```

### `resolve_provider_status()`

Returns per-provider status for the UI, showing whether each provider is configured and from what source (app, user, or global).

### Environment Variable Names

| Provider | Env Var |
|----------|---------|
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
| `elevenlabs` | `ELEVENLABS_API_KEY` |

---

## Data Model

### `eval_runs` Table

```sql
CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    prompt_version TEXT,
    provider TEXT,
    model TEXT,
    status TEXT DEFAULT 'pending',
    results TEXT,              -- JSON string of promptfoo output
    error_message TEXT,
    cost_usd REAL,
    duration_ms INTEGER,
    triggered_by TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

Index: `idx_eval_runs_prompt` on `(prompt_id, created_at)`

### Status Lifecycle

```
pending  ──▶  running  ──▶  completed
                  │
                  └──────▶  failed
```

### Pydantic Models

```python
class EvalRunCreate(BaseModel):
    models: list[str] = []
    dataset: str | None = None

class EvalRun(BaseModel):
    id: str
    prompt_id: str
    prompt_version: str | None = None
    provider: str | None = None
    model: str | None = None
    status: str = "pending"
    results: dict | None = None
    error_message: str | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    triggered_by: str = "manual"
    created_at: str | None = None
```

### DB Queries

| Function | Description |
|----------|-------------|
| `create_eval_run()` | Insert new run with UUID, returns `run_id` |
| `update_eval_run()` | Update status, results, error, cost, duration |
| `list_eval_runs()` | List runs for a prompt, ordered by `created_at DESC`, limit 20 |
| `get_eval_run()` | Get single run by ID |
| `delete_eval_run()` | Delete run by ID |

---

## API Reference

All eval endpoints require session authentication (admin API).

### Run Evaluation

```
POST /api/v1/admin/prompts/{prompt_id}/eval
```

**Request:**
```json
{
  "models": ["gpt-4o", "gemini-2.0-flash"],
  "variables": {"name": "Alice", "topic": "meditation"}
}
```

**Response:**
```json
{
  "runs": [
    {"id": "uuid-1", "model": "gpt-4o", "status": "pending"},
    {"id": "uuid-2", "model": "gemini-2.0-flash", "status": "pending"}
  ],
  "message": "Evaluation started. Poll GET /eval/runs/{id} for results."
}
```

### List Eval Runs

```
GET /api/v1/admin/prompts/{prompt_id}/eval/runs
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid-1",
      "prompt_id": "prompt-uuid",
      "model": "gpt-4o",
      "status": "completed",
      "results": { "results": [...] },
      "cost_usd": 0.0023,
      "duration_ms": 4500,
      "created_at": "2025-03-01T12:00:00"
    }
  ]
}
```

### Get Single Run

```
GET /api/v1/admin/eval/runs/{run_id}
```

Returns the full eval run object including parsed `results` JSON.

### Delete Run

```
DELETE /api/v1/admin/eval/runs/{run_id}
```

**Response:** `{"ok": true}`

### Auto-Generate Tests

```
POST /api/v1/admin/prompts/{prompt_id}/generate-tests
```

**Request (optional):**
```json
{
  "model": "gemini-2.0-flash"
}
```

**Response:**
```json
{
  "tests": [
    {
      "description": "Happy path with typical inputs",
      "vars": {"duration_minutes": "10", "listener_name": "Sarah"},
      "assertions": [
        {"type": "contains", "value": "[PAUSE"},
        {"type": "llm-rubric", "value": "Script is calming and uses present tense", "threshold": 0.8}
      ]
    }
  ],
  "eval_config": {
    "tests": [
      {
        "description": "Happy path with typical inputs",
        "vars": {"duration_minutes": "10", "listener_name": "Sarah"},
        "assert": [
          {"type": "contains", "value": "[PAUSE"},
          {"type": "llm-rubric", "value": "Script is calming and uses present tense", "threshold": 0.8}
        ]
      }
    ]
  },
  "message": "Generated 1 test cases. Review and add to prompt's eval config."
}
```

---

## CI/CD Integration

A GitHub Actions workflow template is provided at `templates/prompt-evals.yml`. Copy it to `.github/workflows/` in your prompt content repo.

### Trigger

Runs on pull requests that modify `.md` files (excluding `README.md` and `CLAUDE.md`):

```yaml
on:
  pull_request:
    paths:
      - "**/*.md"
      - "!README.md"
      - "!CLAUDE.md"
```

### Pipeline

1. **Find changed files** — `git diff` between PR base and HEAD, filtered to `.md` files
2. **Parse front-matter** — Python extracts `eval` config from each changed prompt
3. **Generate promptfoo config** — calls `generate_promptfoo_config()` with models from eval config
4. **Run evals** — `promptfoo eval --config ... --output ... --no-cache --no-progress-bar`
5. **Parse results** — counts passes/failures per provider
6. **Post PR comment** — creates or updates a comment using `<!-- promptdis-eval-results -->` marker for idempotent upserts

### PR Comment

The comment includes:
- Summary: total passes/failures across all files
- Per-file table with provider and PASS/FAIL status
- Merge-blocking warning if enabled

### Merge Gating

Set `EVAL_BLOCK_MERGE=true` as a GitHub repo variable (Settings > Secrets and variables > Actions > Variables) to fail the workflow when evals fail, blocking merge.

### Required Secrets

| Secret | Provider |
|--------|----------|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `GOOGLE_API_KEY` | Google / Gemini |

---

## SDK Usage

The SDKs (`promptdis` Python package) don't have dedicated eval methods — evaluations are an admin/UI concern, not a runtime concern.

### Programmatic Eval via Admin API

```bash
# Run evaluation
curl -X POST http://localhost:8000/api/v1/admin/prompts/{id}/eval \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"models": ["gpt-4o", "gemini-2.0-flash"]}'

# Poll for results
curl http://localhost:8000/api/v1/admin/eval/runs/{run_id} \
  -H "Cookie: session=..."
```

```javascript
// Frontend API client (web/src/api/eval.ts)
const { runs } = await runEval(promptId, ["gpt-4o", "gemini-2.0-flash"], { name: "Alice" });
const { items } = await fetchEvalRuns(promptId);
const run = await fetchEvalRun(runId);
```

---

## Testing

### Backend Tests

`tests/server/test_eval_service.py` — 12 tests across 2 classes:

| Class | Test | What It Covers |
|-------|------|---------------|
| `TestGeneratePromptfooConfig` | `test_basic_config` | Single model, no tests section |
| | `test_multiple_providers` | Three providers mapped correctly |
| | `test_unknown_provider_passthrough` | Unknown model passed through as-is |
| | `test_with_variables` | Variables appear in test case `vars` |
| | `test_with_assertions` | Assertions with `contains` and `llm-rubric` (including threshold) |
| | `test_with_variables_and_assertions` | Both vars and assertions in single test case |
| | `test_no_eval_config` | No `tests` key when eval_config is None |
| | `test_google_provider_variants` | `gemini-*`, `google-*` all map to `google:` prefix |
| | `test_openai_provider_variants` | `gpt-*`, `openai-*` all map to `openai:` prefix |
| | `test_anthropic_provider_variants` | `claude-*`, `anthropic-*` all map to `anthropic:` prefix |
| `TestRunEvaluation` | `test_promptfoo_not_installed` | Run fails with helpful install message |
| | `test_successful_run` | Mocked subprocess, status=completed, duration recorded |
| | `test_eval_run_lifecycle` | Full CRUD: create, update, list, get, delete |

### Running Tests

```bash
pytest tests/server/test_eval_service.py -v
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| **promptfoo CLI not installed** | `status=failed`, error: `"promptfoo CLI not found. Install with: npm install -g promptfoo"` |
| **Subprocess timeout (120s)** | `status=failed`, error: `"Evaluation timed out after 120 seconds"` |
| **Empty prompt body** | HTTP 400 with `"code": "EMPTY_PROMPT"` |
| **Provider API key missing** | promptfoo subprocess fails, stderr captured in error_message |
| **Invalid JSON from promptfoo** | Raw output stored (first 5000 chars) as `{"raw_output": "..."}` |
| **No output.json produced** | stdout/stderr + exit code stored in results |
| **Test generation: Gemini unavailable** | Falls back to regex-based variable extraction, generates 2 basic test cases |
| **Test generation: no variables found** | Generates 1 test with `llm-rubric` coherence check |
| **General subprocess exception** | Logged, `status=failed`, error message truncated to 2000 chars |

---

## Source Files

| File | Role |
|------|------|
| `server/api/eval.py` | API endpoints: run eval, list/get/delete runs, generate tests |
| `server/services/eval_service.py` | promptfoo config generation, subprocess execution |
| `server/services/promptpex_service.py` | LLM-based test generation, parsing, fallback |
| `server/services/credential_service.py` | Credential cascade resolution, env var building |
| `server/services/provider_registry.py` | Provider/model mapping, promptfoo prefixes |
| `server/db/queries/eval_runs.py` | SQLite CRUD queries for eval_runs |
| `server/db/migrations/001_initial.sql` | `eval_runs` table schema |
| `server/models/eval.py` | Pydantic models: `EvalRunCreate`, `EvalRun` |
| `web/src/pages/EvaluationPage.tsx` | Main evaluation page, orchestrates components |
| `web/src/components/eval/EvalRunner.tsx` | Model selection chips, variables input, run button |
| `web/src/components/eval/EvalResults.tsx` | Results table, assertion display, JSON export |
| `web/src/components/eval/ModelComparison.tsx` | Grid/diff model comparison view |
| `web/src/api/eval.ts` | Frontend API client functions |
| `templates/prompt-evals.yml` | GitHub Actions CI/CD workflow template |
| `tests/server/test_eval_service.py` | Backend test suite (12 tests) |
