# Plan: Fix Ruff Linter Errors (14 errors across 5 files)

## Context

The GitHub PR CI/CD pipeline fails on ruff lint checks. There are 14 errors across 5 files: 3 unused variable assignments (F841) and 11 late imports (E402). All are straightforward fixes.

---

## Fix 1 — `server/api/admin.py:618` — F841 unused `user`

`_require_user(request)` raises `HTTPException(401)` if unauthenticated — the call is needed for its side effect but the return value is unused in `export_prompty`.

**Change:** `user = _require_user(request)` → `_require_user(request)`

---

## Fix 2 — `server/main.py:77-82` — E402 late router imports (6 errors)

Router imports are placed after app creation + middleware setup. No circular imports exist (routers don't import from `server.main`).

**Change:** Move the 6 `from server.auth/api...` import lines to the top of the file (after line 16, before the logging setup), keeping the `app.include_router()` calls where they are (lines 84-89).

---

## Fix 3 — `server/services/prompt_service.py:130` — F841 unused `commit_sha`

`github.create_file(...)` returns a commit SHA that is never used — the function later fetches the prompt from SQLite after sync.

**Change:** `commit_sha = github.create_file(...)` → `github.create_file(...)`

---

## Fix 4 — `tests/sdk/test_client.py:17-22` — E402 late imports (5 errors)

Imports are after `sys.path.insert()` on line 14 — this is intentional and necessary (SDK path must be added before `from promptdis...` imports). Best fix is a per-file ruff ignore.

**Change:** Add to `pyproject.toml` under `[tool.ruff]`:
```toml
[tool.ruff.per-file-ignores]
"tests/sdk/test_client.py" = ["E402"]
```

---

## Fix 5 — `tests/server/test_eval_service.py:136` — F841 unused `mock_config_path`

`mock_config_path` is assigned from the same expression as `mock_output_path` (line 137) and never used or configured. Dead code.

**Change:** Delete line 136 (`mock_config_path = ...`).

---

## Files to Modify

| File | Error(s) | Fix |
|------|----------|-----|
| `server/api/admin.py` | F841 ×1 | Drop `user =` assignment |
| `server/main.py` | E402 ×6 | Move 6 router imports to top |
| `server/services/prompt_service.py` | F841 ×1 | Drop `commit_sha =` assignment |
| `pyproject.toml` | — | Add per-file-ignores for test_client.py |
| `tests/server/test_eval_service.py` | F841 ×1 | Delete unused line |

---

## Verification

```bash
ruff check server/ sdk/ tests/
# Expected: 0 errors
```
