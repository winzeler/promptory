# Fix: Export button not including prompt body after YAML

## Context

The Export button downloads a `.prompty` file that contains the YAML front-matter but is missing the prompt body text after it. Users get an empty body in their exported files.

## Root Cause

In `server/api/admin.py:626`, the export endpoint extracts the body from `fm.pop("_body", "")` — looking for `_body` inside the `front_matter` JSON column. However, when prompts are synced from GitHub (via `sync_service.py`), the body is stored in a **separate `body` column** in SQLite, NOT embedded as `_body` inside the `front_matter` JSON. So `fm.pop("_body", "")` always returns `""`.

Other endpoints handle this correctly. For example, `server/api/eval.py:42` does:
```python
prompt_body = prompt.get("body") or fm.get("_body", "")
```
This checks the `body` column first, then falls back to `_body` in front_matter.

## Fix

**File:** `server/api/admin.py` — line 626

Change:
```python
body = fm.pop("_body", "")
```

To:
```python
body = prompt.get("body") or fm.pop("_body", "")
```

This checks the `body` column from the SQLite row first (where sync_service stores it), then falls back to `_body` in front_matter for backwards compatibility with any legacy data.

## Verification

1. Run existing tests: `pytest tests/server/test_prompty_converter.py`
2. Run admin API tests: `pytest tests/server/test_admin_api.py`
3. Manual test: Export a prompt via the UI and verify the body appears after the YAML front-matter in the downloaded `.prompty` file
