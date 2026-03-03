# Plan: Fix Web Container TypeScript Build Errors (17 errors across 11 files)

## Context

The GitHub CI/CD Docker build (`npm run build` via `tsc -b && vite build`) fails with 17 TypeScript errors. These fall into 4 categories: missing Vite type declarations, unused imports/variables, missing npm type package, and type mismatches.

---

## Fix 1 — Create `web/src/vite-env.d.ts` (fixes 4 TS2339 errors)

**Files:** `client.ts:1`, `prompts.ts:175,283`, `LoginPage.tsx:1`
**Error:** `Property 'env' does not exist on type 'ImportMeta'`

Vite projects need a type reference file so TypeScript knows about `import.meta.env`.

**Create** `web/src/vite-env.d.ts`:
```ts
/// <reference types="vite/client" />
```

---

## Fix 2 — Install `@types/js-yaml` (fixes 1 TS7016 error)

**File:** `PromptEditorPage.tsx:9`
**Error:** No declaration file for module `js-yaml`

**Run:** `cd web && npm install --save-dev @types/js-yaml`

---

## Fix 3 — Remove unused imports/variables (fixes 6 TS6133/TS6192 errors)

| File | Line | Change |
|------|------|--------|
| `src/api/client.test.ts` | 36 | `const [url, options]` → `const [, options]` |
| `src/components/layout/Sidebar.tsx` | 2 | Delete line `import { useOrgs, useApps } from ...` (neither is used) |
| `src/hooks/useAuth.ts` | 2 | Remove `User` from import: `import { fetchCurrentUser, logout as logoutApi } from "../api/auth"` |
| `src/hooks/useAutoSave.test.ts` | 1 | Remove `vi, afterEach`: `import { describe, it, expect, beforeEach } from "vitest"` |
| `src/pages/EvaluationPage.tsx` | 15-18 | Remove `refetch` from destructuring |

---

## Fix 4 — MarkdownEditor StreamParser type (fixes 1 TS2345 error)

**File:** `src/components/editor/MarkdownEditor.tsx:44`
**Error:** Inline stream type `{ match: (re: RegExp) => string[] | null; ... }` conflicts with CodeMirror's `StringStream` (whose `match()` returns `boolean | RegExpMatchArray | null`).

**Change:** Import `StreamParser` type and annotate the const instead of inline parameter types. Remove the manual `stream`/`state` type annotations so they're inferred from the generic:

```typescript
import { StreamLanguage, StreamParser } from "@codemirror/language";
// remove separate LanguageSupport import, combine into above

const jinja2StreamParser: StreamParser<{ inBlock: string | null }> = {
  startState() {
    return { inBlock: null };
  },
  token(stream, state) {
    // ... body unchanged
  },
};
```

---

## Fix 5 — EvalResults `componentResults` (fixes 1 TS2339 error)

**File:** `src/components/eval/EvalResults.tsx:147`
**Error:** `Property 'componentResults' does not exist on type '{}'` — `r.gradingResult` is `unknown`, can't access properties on it.

**Change:**
```typescript
// Before:
const assertions = (r.gradingResult?.componentResults ?? []) as Array<Record<string, unknown>>;

// After:
const gradingResult = r.gradingResult as Record<string, unknown> | undefined;
const assertions = (gradingResult?.componentResults ?? []) as Array<Record<string, unknown>>;
```

---

## Fix 6 — PromptEditorPage type fixes (fixes 4 TS2345/TS2353 errors)

**File:** `src/pages/PromptEditorPage.tsx`

### 6a — `extractFrontMatter` parameter type (line 33, 343)

**Error:** `PromptDetail` not assignable to `Record<string, unknown>` (interfaces lack implicit index signatures).

**Change:** Import `PromptDetail` and use it as the parameter type:
```typescript
// Add to imports line 5:
import { exportPrompty, PromptDetail } from "../api/prompts";

// Change function signature at line 343:
function extractFrontMatter(prompt: PromptDetail): Record<string, unknown> {
  const { body: _body, git_sha: _sha, updated_at: _upd, ...fm } = prompt;
  return fm as Record<string, unknown>;
}
```

### 6b — `expected_sha` in updatePrompt data type (lines 52, 111)

**Error:** `expected_sha` does not exist in update data type.

**Change** in `src/api/prompts.ts:126`:
```typescript
// Before:
data: { front_matter?: Record<string, unknown>; body?: string; commit_message: string }

// After:
data: { front_matter?: Record<string, unknown>; body?: string; commit_message: string; expected_sha?: string | null }
```

---

## Files to Modify

| File | Errors Fixed | Action |
|------|-------------|--------|
| `web/src/vite-env.d.ts` | TS2339 ×4 | **Create** — Vite type reference |
| `web/package.json` | TS7016 ×1 | `npm i -D @types/js-yaml` |
| `web/src/api/client.test.ts` | TS6133 ×1 | Remove unused `url` |
| `web/src/api/prompts.ts` | TS2353 ×2 | Add `expected_sha` to update type |
| `web/src/components/editor/MarkdownEditor.tsx` | TS2345 ×1 | Use `StreamParser` generic type |
| `web/src/components/eval/EvalResults.tsx` | TS2339 ×1 | Cast `gradingResult` |
| `web/src/components/layout/Sidebar.tsx` | TS6192 ×1 | Delete unused import line |
| `web/src/hooks/useAuth.ts` | TS6133 ×1 | Remove unused `User` |
| `web/src/hooks/useAutoSave.test.ts` | TS6133 ×2 | Remove unused `vi, afterEach` |
| `web/src/pages/EvaluationPage.tsx` | TS6133 ×1 | Remove unused `refetch` |
| `web/src/pages/PromptEditorPage.tsx` | TS2345 ×1 + TS7016 ×1 | Fix `extractFrontMatter` type |

---

## Verification

```bash
cd web && npx tsc -b --noEmit
# Expected: 0 errors

cd web && npm run build
# Expected: clean build
```
