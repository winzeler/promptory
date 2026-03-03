# Plan: Fix Backend Test RuntimeWarnings

## Context

The test suite produces 7 `RuntimeWarning`s about unawaited coroutines across two test files. All 253 tests pass, but the warnings are noisy and indicate real async/sync bridging issues. This plan fixes both root causes.

---

## Warning Group 1: `test_github_service.py` — MagicMock async leakage

**Affected tests (2):**
- `TestListMdFiles::test_lists_md_files_empty_repo` (line 77)
- `TestGetFileHistory::test_respects_limit` (line 156)

**Root cause:** Python's `MagicMock` auto-generates child mocks via attribute access. When deeply chained (`c.commit.author.date.isoformat`), the mock framework's `AsyncMockMixin` kicks in and creates internal coroutines that are never awaited. This only triggers under specific conditions (empty return lists, high iteration counts).

### Fix: Explicit mock construction (2 surgical edits)

**File:** `tests/server/test_github_service.py`

**Fix 1 — `test_lists_md_files_empty_repo` (line 80):**

Change:
```python
repo.get_contents.return_value = []
```
To:
```python
repo.get_contents = MagicMock(return_value=[])
```

Explicitly constructing `get_contents` as a fresh `MagicMock` prevents the auto-generated async child path.

**Fix 2 — `test_respects_limit` (lines 160-167):**

Replace the deep attribute chaining:
```python
c = MagicMock()
c.sha = f"sha-{i}"
c.commit.message = f"Commit {i}"
c.commit.author.name = "User"
c.commit.author.date.isoformat.return_value = "2026-01-01"
```

With explicit level-by-level construction:
```python
date_mock = MagicMock()
date_mock.isoformat = MagicMock(return_value="2026-01-01")
author_mock = MagicMock()
author_mock.name = "User"
author_mock.date = date_mock
commit_inner = MagicMock()
commit_inner.message = f"Commit {i}"
commit_inner.author = author_mock
c = MagicMock()
c.sha = f"sha-{i}"
c.commit = commit_inner
```

Note: `test_returns_commit_history` (line 139) uses the same chain syntax with only 1 commit — it does NOT produce warnings and does not need changing.

---

## Warning Group 2: `test_render_service.py` — Async/sync bridge in Jinja2 include loader

**Affected tests (5):**
- `test_render_with_single_include`
- `test_render_with_nested_include`
- `test_circular_include_raises`
- `test_max_depth_exceeded`
- `test_render_with_includes_and_variables`

**Root cause:** `render_prompt_with_includes()` is async, but Jinja2's `template.render()` is sync. When Jinja2 hits `{% include %}`, it calls `PromptIncludeLoader.get_source()` synchronously. That method tries `run_until_complete()` (fails — loop already running under pytest-asyncio), then falls back to `ThreadPoolExecutor` + `asyncio.run()` in a new thread — but the `aiosqlite` connection is bound to the original loop. The `_load()` coroutine is created but never properly awaited, leaking warnings.

### Fix: Pre-resolve includes before rendering, use `DictLoader`

**File:** `server/services/render_service.py`

**Step 1 — Add `_resolve_includes()` async helper:**

```python
async def _resolve_includes(
    template_body: str,
    db,
    app_id: str,
    resolved: dict[str, str],
    seen: set[str],
    depth: int,
) -> None:
```

This function:
1. Uses `re.findall(r'\{%[-\s]*include\s+["\']([^"\']+)["\']', template_body)` to find all `{% include "name" %}` references
2. For each name:
   - Checks `depth >= _MAX_INCLUDE_DEPTH` → raises `ValueError("Include depth exceeded maximum of 5")` (same message)
   - Checks `name in seen` → raises `ValueError("Circular include detected: 'name' already included")` (same message)
   - Skips if `name in resolved` (already fetched)
   - Fetches body from DB with `await db.execute(...)` (same SQL as current `_load`)
   - If no row → raises `ValueError("Include not found: 'name'")` (same message)
   - Stores in `resolved[name] = body`
   - Recurses: `await _resolve_includes(body, db, app_id, resolved, seen | {name}, depth + 1)`

**Step 2 — Rewrite `render_prompt_with_includes()`:**

```python
async def render_prompt_with_includes(template_body, variables, db, app_id):
    resolved = {}
    await _resolve_includes(template_body, db, app_id, resolved, set(), 0)
    loader = DictLoader(resolved)
    env = SandboxedEnvironment(loader=loader, autoescape=False, keep_trailing_newline=True)
    try:
        template = env.from_string(template_body)
        return template.render(**variables)
    except ValueError:
        raise
    except Exception as e:
        logger.error("Template rendering with includes failed: %s", e)
        raise ValueError(f"Template rendering failed: {e}")
```

**Step 3 — Delete `PromptIncludeLoader` class** (lines 41-96, entire class)

**Step 4 — Update imports:**
- Add: `import re`
- Add: `from jinja2.loaders import DictLoader`
- Remove: `from jinja2 import BaseLoader` (no longer used — verify `_env` on line 13 uses `BaseLoader()` and change it to `DictLoader({})` or keep `BaseLoader` import if still needed there)

Actually `_env` at line 13 uses `BaseLoader()` as loader for the simple `render_prompt()` function. Keep the `BaseLoader` import; just add `DictLoader`.

### No test changes needed

All 5 render tests call `render_prompt_with_includes` via its public async interface and assert on return values or `ValueError` messages. The error message strings are preserved verbatim so all `pytest.raises(ValueError, match=...)` assertions continue to pass.

---

## Files to Modify

| File | Change |
|------|--------|
| `tests/server/test_github_service.py` | Fix 2 mock constructions (lines 80 and 160-167) |
| `server/services/render_service.py` | Delete `PromptIncludeLoader`, add `_resolve_includes`, rewrite `render_prompt_with_includes`, add `re` and `DictLoader` imports |

---

## Verification

```bash
# All 253 tests pass with zero warnings (except the pytest-asyncio deprecation which is unrelated)
python -m pytest tests/ -v -W error::RuntimeWarning

# Specifically verify the previously-warning tests pass cleanly
python -m pytest tests/server/test_github_service.py tests/server/test_render_service.py -v -W error::RuntimeWarning
```
