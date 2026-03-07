# Plan: Automate Version Numbering

## Context

Promptdis is stuck at `v0.1.0` — the version is hard-coded in 7 places across the monorepo with no automation. We need a single source of truth for the version and a way to auto-increment it (or at minimum, make it easy to bump consistently across all components).

## Current State

Version `0.1.0` is hard-coded in these 7 locations:

| # | File | Line | How it's used |
|---|------|------|---------------|
| 1 | `pyproject.toml` | 3 | Backend build metadata |
| 2 | `sdk-py/pyproject.toml` | 3 | Python SDK build metadata |
| 3 | `sdk-js/package.json` | 3 | JS SDK build metadata |
| 4 | `sdk-ts/package.json` | 3 | TS SDK build metadata |
| 5 | `web/package.json` | 4 | Web UI build metadata |
| 6 | `server/main.py` | 64, 93 | FastAPI app config + /health endpoint |
| 7 | `web/src/components/layout/Sidebar.tsx` | 56 | UI footer display |

No `__version__` variable exists. No version bumping in CI. The publish workflow triggers on `v*` tags but doesn't set the version — it relies on whatever's in `pyproject.toml`.

## Approach: Single source of truth + bump script

### Step 1: Create `VERSION` file (single source of truth)

Create a root `VERSION` file containing just the semver string (e.g., `0.2.0`). All components read from this.

### Step 2: Backend reads version at runtime

Add `server/_version.py` that reads the `VERSION` file:
```python
from pathlib import Path
__version__ = (Path(__file__).parent.parent / "VERSION").read_text().strip()
```

Update `server/main.py` to import and use `__version__` instead of hard-coded strings (FastAPI config + /health endpoint).

Configure `pyproject.toml` to use hatch-vcs or dynamic versioning from the `VERSION` file.

### Step 3: Web UI reads version at build time

In `web/vite.config.ts`, define a global constant from the `VERSION` file. Replace the hard-coded string in `Sidebar.tsx` with the injected value.

### Step 4: Create `scripts/bump-version.sh`

A script that:
1. Takes a version argument (e.g., `0.2.0`) or bump type (`patch`, `minor`, `major`)
2. Updates `VERSION` file
3. Updates `pyproject.toml` (root + sdk-py)
4. Updates `package.json` (web, sdk-js, sdk-ts) via `npm version --no-git-tag-version`
5. Outputs a summary of changes

### Step 5: GitHub Actions — auto-tag on merge to main

Add a workflow step in `ci.yml` that reads the `VERSION` file on main branch pushes. If the version changed compared to the previous commit, auto-create a git tag `v{version}`. This triggers the existing `publish.yml` workflow.

### Files to create/modify

| Action | File |
|--------|------|
| CREATE | `VERSION` |
| CREATE | `server/_version.py` |
| CREATE | `scripts/bump-version.sh` |
| MODIFY | `pyproject.toml` — dynamic version from `VERSION` |
| MODIFY | `server/main.py:64,93` — import `__version__` |
| MODIFY | `web/vite.config.ts` — inject version constant |
| MODIFY | `web/src/components/layout/Sidebar.tsx:56` — use injected constant |
| MODIFY | `.github/workflows/ci.yml` — auto-tag step |
| MODIFY | `RUNBOOK.md:328` — update health check example |
| UPDATE | `~/src/futureself/dwight_docs/prompt_mgmt/PROMPT_APP.md` — add versioning section |

### SDK versions

The SDKs (`sdk-py`, `sdk-js`, `sdk-ts`) may version independently from the platform eventually, but for now the bump script keeps them in sync. The `VERSION` file is the platform version; SDK `pyproject.toml`/`package.json` are updated by the bump script.

## Workflow for developers

1. Work on a branch, merge PR to main
2. When ready to release: `./scripts/bump-version.sh minor` (or `patch`/`major`/explicit version)
3. Commit the version bump, push to main
4. CI detects version change → creates `v0.2.0` tag
5. Tag triggers `publish.yml` → publishes Python SDK to PyPI

## Verification

```bash
# After implementation, verify:
./scripts/bump-version.sh 0.2.0
grep -r "0.2.0" VERSION pyproject.toml sdk-py/pyproject.toml sdk-js/package.json sdk-ts/package.json web/package.json
python -c "from server._version import __version__; print(__version__)"
pytest tests/ -v  # ensure nothing breaks
```

## Docs to update

- `~/src/futureself/dwight_docs/prompt_mgmt/PROMPT_APP.md` — add §15.5 Versioning Strategy (or appropriate section)
- `RUNBOOK.md` — update health check example to show dynamic version
