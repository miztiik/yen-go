# Tasks — Browse Filter & Navigation Fix

**Initiative:** `20260312-1600-feature-browse-filter-navigation-fix`  
**Selected Option:** A — `useBrowseParams` Hook  
**Last Updated:** 2026-03-12

---

## Task Dependency Graph

```
T1 (branch) ──┐
               ├─► T3 (hook) ──┬─► T5 (technique page)  [P]
               │                ├─► T6 (training page)    [P]
               │                └─► T7 (collections page) [P]
               ├─► T4 (back button) ─────────────────┐               ├─► T4b (useCanonicalUrl RMW, RC-3) ────┐               └─► T8 (shorthand routes) ─────────────┤
                                                       ├─► T9 (tests)
T5 ────────────────────────────────────────────────────┤
T6 ────────────────────────────────────────────────────┤
T7 ────────────────────────────────────────────────────┤
T8 ────────────────────────────────────────────────────┤
                                                       └─► T10 (docs)
                                                       └─► T11 (regression + AC)
                                                       └─► T12 (cleanup)
```

---

## Tasks

### T1 — Create feature branch
- **Files:** git
- **Action:** `git checkout -b feature/browse-filter-navigation-fix`
- **Depends on:** none

### T2 — [REMOVED] *(reserved)*

### T3 — Create `useBrowseParams` hook [P-ready after T1]
- **File:** `frontend/src/hooks/useBrowseParams.ts` (NEW)
- **Action:** Implement generic `useBrowseParams<T extends Record<string, string>>(defaults: T)` hook
- **Requirements:**
  - Read `URLSearchParams` on mount, merge with defaults
  - `setParam(key, value)` → **read-merge-write**: read current `URLSearchParams`, update only managed keys (those in `defaults`), write back ALL params via `history.replaceState` (RC-2)
  - `clearParams()` → read-merge-write: delete only managed keys, preserve others, `replaceState`
  - `popstate` listener with **pathname guard** (RC-1): only re-read params when `window.location.pathname` unchanged
  - Cleanup listener on unmount
  - Omit default-valued params from URL (clean URLs)
- **Depends on:** T1
- **AC:** AC-2, AC-3, AC-4, AC-5 (mechanism)

### T4 — Fix collection back button [P]
- **File:** `frontend/src/app.tsx` (~line 525)
- **Action:** Change `onBack={handleBackToHome}` to navigate to `{ type: 'collections-browse' }` instead of `{ type: 'home' }`
- **Depends on:** T1
- **AC:** AC-1

### T4b — Modify `useCanonicalUrl.writeToUrl` for read-merge-write (RC-3) [P]
- **File:** `frontend/src/hooks/useCanonicalUrl.ts`
- **Action:** Modify `buildSearchString` to use read-merge-write pattern:
  1. Start from `new URLSearchParams(window.location.search)` instead of empty
  2. Set/delete only canonical keys (`l`, `t`, `c`, `q`, `ct`, `offset`, `id`)
  3. Remove any canonical key not present in current filters
  4. Write back all params (preserves `cat`, `s`, `q` from browse hooks)
- **Impact:** ~5-line change; backward-compatible (existing behavior preserved when no unmanaged params exist)
- **Depends on:** T1
- **AC:** AC-2, AC-3, AC-4 (mutual preservation)

### T5 — Refactor TechniqueFocusPage [P after T3]
- **File:** `frontend/src/pages/TechniqueFocusPage.tsx`
- **Actions:**
  1. Replace `useState('technique')` / `useState('name')` with `useBrowseParams({ cat: 'all', s: 'name' })`
  2. Default category → `'all'` (fixes I-6)
  3. Remove `<ContentTypeFilter />` JSX + unused import (fixes I-5)
  4. Update category/sort change handlers to use `setParam()`
- **Depends on:** T3
- **AC:** AC-2, AC-3, AC-6, AC-7

### T6 — Refactor TrainingSelectionPage [P]
- **File:** `frontend/src/pages/TrainingSelectionPage.tsx`
- **Actions:**
  1. Replace `useState<CategoryFilter>('all')` with `useBrowseParams({ cat: 'all' })`
  2. Remove `<ContentTypeFilter />` JSX + unused import (fixes I-5)
  3. Update category change handler to use `setParam()`
- **Depends on:** T3
- **AC:** AC-4, AC-6

### T7 — Refactor CollectionsPage [P]
- **File:** `frontend/src/pages/CollectionsPage.tsx`
- **Actions:**
  1. Replace `useState('')` with `useBrowseParams({ q: '' })`
  2. Remove `<ContentTypeFilter />` JSX + unused import (fixes I-2)
  3. Update search handler to use `setParam()`
- **Depends on:** T3
- **AC:** AC-5, AC-6

### T8 — Add shorthand route aliases [P after T1]
- **File:** `frontend/src/lib/routing/routes.ts`
- **Action:** Add 3 shorthand patterns to `parseRoute()`:
  - `/collection/{slug}` → `{ type: 'context', dimension: 'collection', slug, filters: {} }`
  - `/training/{slug}` → `{ type: 'context', dimension: 'training', slug, filters: {} }`
  - `/technique/{slug}` → `{ type: 'context', dimension: 'technique', slug, filters: {} }`
- **Note:** Insert AFTER existing `CONTEXT_RE` match, BEFORE fallback-to-home
- **Note:** `serializeRoute()` unchanged — canonical output stays as `/contexts/...`
- **Depends on:** T1
- **AC:** AC-8, AC-9, AC-10

### T9 — Write tests
- **Files:**
  - `frontend/tests/unit/useBrowseParams.test.ts` (NEW) — hook unit tests
  - `frontend/tests/unit/routes.test.ts` (MODIFY) — add shorthand route tests
- **Test cases for hook:**
  - Returns defaults when URL has no params
  - Reads existing URL params on mount
  - `setParam()` updates state and calls `replaceState`
  - `setParam()` preserves params NOT in managed keys (read-merge-write, RC-2)
  - `clearParams()` resets managed keys only, preserves unmanaged
  - `popstate` with same pathname → re-reads params
  - `popstate` with different pathname → ignores (RC-1 guard)
  - Omits default-valued params from URL
- **Test cases for dual-hook integration (RC-5):**
  - Simulate `useCanonicalUrl` writing `l=120` while `useBrowseParams` has `cat=tesuji` → both params preserved
  - Simulate `useBrowseParams` writing `cat=objective` while URL has `l=120` → both params preserved
- **Test cases for `useCanonicalUrl` read-merge-write (RC-3):**
  - `writeToUrl` with existing unmanaged param `cat=tesuji` in URL → `cat` preserved
  - `writeToUrl` setting `l=120` → canonical keys set correctly
- **Test cases for routes:****
  - `/collection/cho-chikun-elementary` → context route with dimension `collection`
  - `/training/intermediate` → context route with dimension `training`
  - `/technique/life-and-death` → context route with dimension `technique`
  - Existing `/contexts/collection/...` still works (AC-11 regression)
- **Depends on:** T3, T5, T6, T7, T8
- **AC:** AC-8, AC-9, AC-10, AC-11, AC-12

### T10 — Documentation
- **Files:**
  - `docs/concepts/browse-url-params.md` (NEW) — browse param pattern documentation
  - `frontend/CLAUDE.md` (MODIFY) — add `useBrowseParams` to conventions
- **Depends on:** T5, T6, T7, T8
- **AC:** Documentation requirement

### T11 — Regression verification
- **Action:** Run `cd frontend && npm test` — all existing tests must pass
- **Action:** Manual verification of AC-1 through AC-12
- **Depends on:** T9

### T12 — Dead code cleanup verification
- **Action:** Grep for unused `ContentTypeFilter` imports across modified files
- **Action:** Verify no `[DEBUG]` statements remain
- **Depends on:** T11

---

## Parallel Execution Markers

| Phase | Tasks | Parallel? |
|-------|-------|-----------|
| 1 | T1 | Sequential (branch creation) |
| 2 | T3, T4, T4b, T8 | [P] All four independent after T1 |
| 3 | T5, T6, T7 | [P] All three independent after T3 + T4b |
| 4 | T9 | Sequential (depends on T3-T8 + T4b) |
| 5 | T10, T11 | [P] Docs and verification independent |
| 6 | T12 | Sequential (final cleanup check) |

---

## Compatibility Strategy

- **Backward compatible:** Existing `/contexts/` URLs unchanged (AC-11)
- **Legacy removal:** Cosmetic `ContentTypeFilter` on browse pages deleted (dead code policy)
- **No legacy compat shim needed:** New shorthand routes are additive only

---

> **See also**:
> - [30-plan.md](./30-plan.md) — Architecture and file-level changes
> - [20-analysis.md](./20-analysis.md) — Ripple-effects and coverage
> - [00-charter.md](./00-charter.md) — Acceptance criteria
