
 ▐▛███▜▌   Claude Code v2.1.70
▝▜█████▛▘  Opus 4.6 · Claude Max
  ▘▘ ▝▝    ~/src/futureself/prompt-mgmt

╭──────────────────────────────────────────────────────────────────────────────╮
│ Plan to implement                                                            │
│                                                                              │
│ Plan: Create EVALS_README.md                                                 │
│                                                                              │
│ Context                                                                      │
│                                                                              │
│ The user wants a comprehensive explainer document for the Promptdis          │
│ evaluation system — how promptfoo evals are run from the UI, how PromptPex   │
│ auto-generates test cases, the full data flow, API, frontend components,     │
│ CI/CD integration, and SDK usage. Documentation-only task — one new file, no │
│  code changes.                                                               │
│                                                                              │
│ What to create                                                               │
│                                                                              │
│ File: EVALS_README.md (project root)                                         │
│                                                                              │
│ A thorough guide covering the entire evaluation pipeline. Target audience:   │
│ developers using or contributing to Promptdis who want to understand how     │
│ prompt quality testing works.                                                │
│                                                                              │
│ Document outline                                                             │
│                                                                              │
│ 1. Overview & Architecture                                                   │
│                                                                              │
│ - What evals do in Promptdis (test prompt quality across models with         │
│ assertions)                                                                  │
│ - ASCII flow diagram showing the full pipeline:                              │
│ User clicks "Run Eval" → API creates eval_run records → async subprocess     │
│ → promptfoo CLI generates config → calls LLM providers → runs assertions     │
│ → results parsed → stored in SQLite → UI polls and displays                  │
│ - Two main capabilities: Run Evals (promptfoo) and Auto-Generate Tests       │
│ (PromptPex)                                                                  │
│ - Provider model support: OpenAI, Anthropic, Google                          │
│                                                                              │
│ 2. Eval Configuration in Prompt Files                                        │
│                                                                              │
│ - The eval: front-matter section from PROMPT_FORMAT.md                       │
│ - Fields: provider, dataset, assertions[]                                    │
│ - Assertion types: contains, llm-rubric (with threshold), javascript         │
│ - Complete example prompt file with eval config (use the                     │
│ meditation_script_relax example from PROMPT_FORMAT.md)                       │
│                                                                              │
│ 3. Running Evaluations from the UI                                           │
│                                                                              │
│ - EvalRunner component: model selection chips, custom model input, variables │
│  JSON textarea                                                               │
│ - Default models: gemini-2.0-flash, gpt-4o, claude-sonnet-4-5-20250929,      │
│ gpt-4o-mini                                                                  │
│ - Provider warning badges when API keys not configured                       │
│ - What happens on click: POST creates records, async tasks fire, frontend    │
│ polls every 3s                                                               │
│ - EvalResults component: status badges, cost, duration, expandable assertion │
│  details (PASS/FAIL)                                                         │
│ - ModelComparison component: grid view (side-by-side cards with              │
│ Fastest/Cheapest badges) and diff view (line-by-line red/green)              │
│ - Export to JSON button                                                      │
│                                                                              │
│ 4. Auto-Generate Tests (PromptPex)                                           │
│                                                                              │
│ - What PromptPex is: LLM-based test case generation (uses Gemini by default) │
│ - The system prompt that instructs Gemini (from _TEST_GEN_SYSTEM in          │
│ promptpex_service.py)                                                        │
│ - What gets generated: 3-5 test cases with description, vars, assertions     │
│ - Parsing & validation: markdown fence stripping, JSON extraction,           │
│ _validate_tests()                                                            │
│ - Fallback behavior when Gemini unavailable: regex extraction of {{ vars }}, │
│  2 basic test cases                                                          │
│ - tests_to_eval_config() conversion to promptfoo format                      │
│ - UI flow: button click → preview panel → user reviews → adds to             │
│ front-matter                                                                 │
│ - API credential resolution cascade for Google API key                       │
│                                                                              │
│ 5. Under the Hood: promptfoo Integration                                     │
│                                                                              │
│ - generate_promptfoo_config(): how prompt data maps to promptfoo YAML        │
│   - Show actual generated YAML structure with prompts, providers, tests,     │
│ assertions                                                                   │
│ - run_evaluation(): the async subprocess pipeline                            │
│   - Check promptfoo installed (shutil.which)                                 │
│   - Write temp promptfooconfig.yaml                                          │
│   - Execute promptfoo eval --config ... --output output.json --no-cache      │
│   - 120s timeout                                                             │
│   - Parse results JSON, extract cost                                         │
│   - Update eval_run record                                                   │
│ - Provider mapping: get_promptfoo_provider() → e.g. "gpt-4o" becomes         │
│ "openai:gpt-4o"                                                              │
│ - Provider registry table (from provider_registry.py)                        │
│                                                                              │
│ 6. Credential Resolution                                                     │
│                                                                              │
│ - Cascade order (from credential_service.py):                                │
│   a. App-level + environment-specific                                        │
│   b. App-level + all-environments (NULL)                                     │
│   c. User-level + environment-specific                                       │
│   d. User-level + all-environments                                           │
│   e. Global env var fallback                                                 │
│ - resolve_eval_env_vars(): builds env dict for subprocess                    │
│ - resolve_provider_status(): UI status display per provider                  │
│ - ENV_VAR_NAMES mapping table                                                │
│                                                                              │
│ 7. Data Model                                                                │
│                                                                              │
│ - eval_runs SQLite table schema (from 001_initial.sql)                       │
│ - Status lifecycle: pending → running → completed / failed                   │
│ - Pydantic models: EvalRunCreate, EvalRun (from server/models/eval.py)       │
│ - DB queries: create, update, list, get, delete (from eval_runs.py)          │
│                                                                              │
│ 8. API Reference                                                             │
│                                                                              │
│ - POST /api/v1/admin/prompts/{id}/eval — run eval (request/response with     │
│ examples)                                                                    │
│ - GET /api/v1/admin/prompts/{id}/eval/runs — list runs                       │
│ - GET /api/v1/admin/eval/runs/{id} — get single run with results             │
│ - DELETE /api/v1/admin/eval/runs/{id} — delete run                           │
│ - POST /api/v1/admin/prompts/{id}/generate-tests — auto-generate tests       │
│ (request/response)                                                           │
│ - All require session auth (admin endpoints)                                 │
│                                                                              │
│ 9. CI/CD Integration                                                         │
│                                                                              │
│ - GitHub Actions workflow template (templates/prompt-evals.yml)              │
│ - Trigger: PRs that modify .md files (excluding README, CLAUDE.md)           │
│ - Pipeline: find changed files → Python parses front-matter → generate       │
│ promptfoo config → run evals → parse results → post PR comment               │
│ - EVAL_BLOCK_MERGE repo variable for merge gating                            │
│ - PR comment: uses <!-- promptdis-eval-results --> marker for upsert         │
│ - Environment secrets needed: OPENAI_API_KEY, ANTHROPIC_API_KEY,             │
│ GOOGLE_API_KEY                                                               │
│                                                                              │
│ 10. SDK Usage                                                                │
│                                                                              │
│ - Note: SDKs don't have dedicated eval methods — evals are an admin/UI       │
│ concern                                                                      │
│ - Programmatic eval via the admin API (curl/fetch examples)                  │
│ - How SDK-fetched prompts relate to evals (prompt.model, prompt body)        │
│                                                                              │
│ 11. Testing                                                                  │
│                                                                              │
│ - tests/server/test_eval_service.py — test coverage table                    │
│   - TestGeneratePromptfooConfig: basic config, multiple providers, unknown   │
│ provider passthrough, variables, assertions, provider variants               │
│   - TestRunEvaluation: promptfoo not installed, successful run (mocked),     │
│ eval run CRUD lifecycle                                                      │
│ - web/src/components/eval/EvalRunner.test.tsx — frontend component tests     │
│ - How to run: pytest tests/server/test_eval_service.py -v                    │
│                                                                              │
│ 12. Error Handling                                                           │
│                                                                              │
│ - Table of error scenarios:                                                  │
│   - promptfoo CLI not installed → status=failed, "Install with: npm install  │
│ -g promptfoo"                                                                │
│   - Subprocess timeout (120s) → status=failed                                │
│   - Empty prompt body → 400 EMPTY_PROMPT                                     │
│   - Provider API key missing → promptfoo subprocess fails                    │
│   - Invalid JSON from promptfoo → raw output stored (first 5000 chars)       │
│   - Test generation: Gemini unavailable → fallback tests                     │
│                                                                              │
│ 13. Internals / Source Files                                                 │
│                                                                              │
│ - Source file map table (all files with roles)                               │
│ - Key function signatures                                                    │
│                                                                              │
│ Source files to reference (all read and verified)                            │
│                                                                              │
│ ┌───────────────────────────────────────────┬─────────────────────────────┐  │
│ │                   File                    │       What to extract       │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ server/api/eval.py                        │ All 5 API endpoints (151    │  │
│ │                                           │ lines)                      │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │                                           │ generate_promptfoo_config() │  │
│ │ server/services/eval_service.py           │ , run_evaluation() (192     │  │
│ │                                           │ lines)                      │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │                                           │ PromptPex LLM test gen,     │  │
│ │ server/services/promptpex_service.py      │ parsing, fallback (196      │  │
│ │                                           │ lines)                      │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │                                           │ Credential cascade,         │  │
│ │ server/services/credential_service.py     │ resolve_eval_env_vars()     │  │
│ │                                           │ (146 lines)                 │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │                                           │ Provider mapping,           │  │
│ │ server/services/provider_registry.py      │ get_promptfoo_provider()    │  │
│ │                                           │ (119 lines)                 │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ server/db/queries/eval_runs.py            │ CRUD queries (64 lines)     │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ server/db/migrations/001_initial.sql      │ eval_runs table schema      │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ server/models/eval.py                     │ Pydantic models (24 lines)  │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ web/src/pages/EvaluationPage.tsx          │ Main eval page (171 lines)  │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ web/src/components/eval/EvalRunner.tsx    │ Model selection + run UI    │  │
│ │                                           │ (165 lines)                 │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ web/src/components/eval/EvalResults.tsx   │ Results table + assertion   │  │
│ │                                           │ display (177 lines)         │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ web/src/components/eval/ModelComparison.t │ Grid/diff comparison (133   │  │
│ │ sx                                        │ lines)                      │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ web/src/api/eval.ts                       │ Frontend API client (57     │  │
│ │                                           │ lines)                      │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ templates/prompt-evals.yml                │ GitHub Actions CI/CD        │  │
│ │                                           │ template (233 lines)        │  │
│ ├───────────────────────────────────────────┼─────────────────────────────┤  │
│ │ tests/server/test_eval_service.py         │ 12 tests (180 lines)        │  │
│ └───────────────────────────────────────────┴─────────────────────────────┘  │
│                                                                              │
│ Verification                                                                 │
│                                                                              │
│ - Review the doc reads well end-to-end                                       │
│ - Verify all code snippets are accurate (pulled from actual source files     │
│ already read)                                                                │
│ - Confirm ASCII diagrams render in GitHub markdown                           │
│ - No code changes, so no tests to run                                        │
╰──────────────────────────────────────────────────────────────────────────────╯

❯ Tool loaded. 

⏺ Let me read all the source files to ensure accuracy.

⏺ Read 14 files (ctrl+o to expand)

⏺ Now let me read the tests file and the PROMPT_FORMAT.md for the eval config
  example.

⏺ Searched for 3 patterns, read 2 files (ctrl+o to expand)

⏺ Now I have all the source material. Let me write the document.

⏺ Write(EVALS_README.md)
  ⎿  Wrote 643 lines to EVALS_README.md
       1 # Promptdis Evaluation System
       2 
       3 Test prompt quality across models with assertions, auto-generate
          test cases, and integrate evals into CI/CD.
       4 
       5 ---
       6 
       7 ## Table of Contents
       8 
       9 1. [Overview & Architecture](#overview--architecture)
      10 2. [Eval Configuration in Prompt Files](#eval-configuration-in-p
         rompt-files)
     … +633 lines (ctrl+o to expand)

⏺ Created EVALS_README.md with all 13 sections covering:

  - Architecture diagram showing the full eval pipeline
  - Eval config format with the meditation_script_relax example from
  PROMPT_FORMAT.md
  - UI components (EvalRunner, EvalResults, ModelComparison) with their features
  - PromptPex auto-generation including the system prompt, parsing, validation,
  and fallback behavior
  - promptfoo integration details (config generation, subprocess execution,
  provider mapping)
  - Credential resolution cascade (5 levels)
  - Data model (SQLite schema, Pydantic models, CRUD queries)
  - API reference with request/response examples for all 5 endpoints
  - CI/CD workflow (trigger, pipeline, PR comments, merge gating)
  - SDK usage notes with curl/JS examples
  - Test coverage table (12 tests)
  - Error handling table (9 scenarios)
  - Source file map (15 files)

  All code snippets and details are pulled from the actual source files.

✻ Crunched for 2m 46s