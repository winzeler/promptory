# Contributing to Promptdis

Thanks for your interest in contributing! This document covers the basics for getting started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/futureself-app/promptdis.git
cd prompt-mgmt

# Backend (Python 3.11+)
pip install -e ".[dev]"

# Frontend (Node 18+)
cd web && npm install && cd ..

# Copy environment config
cp .env.example .env
# Edit .env with your GitHub OAuth credentials (see README)
```

### Running locally

```bash
# Terminal 1 - API server
uvicorn server.main:app --reload --port 8000

# Terminal 2 - Frontend dev server
cd web && npm run dev
```

The API runs at `http://localhost:8000` and the web UI at `http://localhost:5173`.

## Running Tests

```bash
# Backend (Python)
python -m pytest tests/ -v

# Frontend (React)
cd web && npx vitest run

# TypeScript SDK
cd sdk-ts && npx vitest run
```

## Code Style

- **Python:** Formatted and linted with [ruff](https://docs.astral.sh/ruff/). Run `ruff check .` and `ruff format .` before committing.
- **TypeScript:** Strict mode enabled. The frontend uses ESLint with the project config.
- **Commits:** Write clear, concise commit messages. Reference issue numbers where applicable.

CI runs these checks automatically on every PR.

## Pull Request Process

1. Fork the repo and create a feature branch from `main`
2. Make your changes with tests where appropriate
3. Ensure all tests pass and linting is clean
4. Open a PR against `main` with a clear description of the changes
5. CI must pass before merge

Keep PRs focused — one feature or fix per PR is ideal.

## Reporting Bugs

Open a [GitHub Issue](https://github.com/futureself-app/promptdis/issues/new?template=bug_report.md) with:

- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python/Node version, browser)

## Feature Requests

Open a [GitHub Issue](https://github.com/futureself-app/promptdis/issues/new?template=feature_request.md) with the `enhancement` label. Describe the problem you're solving and your proposed approach.

## Questions?

Open a [Discussion](https://github.com/futureself-app/promptdis/discussions) or comment on a relevant issue.
