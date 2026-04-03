# Options — Browse Filter & Navigation Fix

**Initiative:** `20260312-1600-feature-browse-filter-navigation-fix`  
**Last Updated:** 2026-03-12

---

## Shared Fixes (All Options Include These)

These are independent bug fixes required regardless of option chosen:

| Fix | Issue | File | Change | Level |
|-----|-------|------|--------|-------|
| F-1 | I-1 | `app.tsx` L525 | `onBack={handleBackToHome}` → `onBack` navigates to `collections-browse` | L0 |
| F-2 | I-6 | `TechniqueFocusPage.tsx` L74 | `useState('technique')` → `useState('all')` | L0 |
| F-3 | I-2 | `CollectionsPage.tsx` | Remove `<ContentTypeFilter />` JSX + unused import | L0 |
| F-4 | I-9 | `routes.ts` `parseRoute()` | Add 3 shorthand route patterns: `/collection/{slug}`, `/training/{slug}`, `/technique/{slug}` → redirect to corresponding context routes | L1 |

---

## Option A: `useBrowseParams` Hook (New Shared Abstraction)

### Approach

Create a lightweight `useBrowseParams<T extends Record<string, string>>(defaults: T)` hook that reads/writes **string** URL search params via `history.replaceState`. Each browse page declares its param schema and uses this hook instead of `useState` for URL-synced state.

### Architecture

```
useBrowseParams<T>(defaults: T) → { params: T, setParam(key, value), clearParams() }
  ├── Reads: window.location.search → URLSearchParams → merge with defaults
  ├── Writes: history.replaceState (no history entries, same as useCanonicalUrl)
  └── Listens: popstate event for back/forward
```

### File Changes

| File | Change |
|------|--------|
| `hooks/useBrowseParams.ts` | **NEW** — ~60 lines. Generic string-param hook. |
| `TechniqueFocusPage.tsx` | Replace `useState('all')` / `useState('name')` with `useBrowseParams({ cat: 'all', s: 'name' })` |
| `TrainingSelectionPage.tsx` | Replace `useState('all')` with `useBrowseParams({ cat: 'all' })` |
| `CollectionsPage.tsx` | Replace `useState('')` with `useBrowseParams({ q: '' })` |
| `app.tsx` | Fix collection back button (F-1) |
| `routes.ts` | Add shorthand routes (F-4) |

### ContentTypeFilter Strategy (I-5)

Remove `ContentTypeFilter` from all three browse pages (TechniqueFocusPage, TrainingSelectionPage, CollectionsPage) since browse pages don't have shard-level data to produce meaningful counts. CTF stays only on context pages where `useShardFilters` provides real distribution data.

### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| OPT-A1 | Complexity | **Low-Medium** — 1 new file (~60 lines), 3 page edits, 2 infra edits |
| OPT-A2 | Reusability | **High** — any future browse page gets URL-synced params for free |
| OPT-A3 | Isolation | **High** — completely separate from `useCanonicalUrl`/context system |
| OPT-A4 | Test impact | **Medium** — need unit tests for new hook + page behavior tests |
| OPT-A5 | Rollback | **Easy** — revert hook + page changes; context route system untouched |
| OPT-A6 | Risk | **Low** — no changes to routing infrastructure or context page behavior |
| OPT-A7 | YAGNI | **Borderline** — new abstraction, but 3 pages use it immediately |
| OPT-A8 | Architecture | Clean separation — browse params ≠ context filters |

### Risks

- **R-A1**: New file creation triggers structural checklist (MANDATORY CHECKLIST). Mitigation: 3 immediate consumers justify the abstraction.
- **R-A2**: `popstate` event listener coordination with existing routing. Mitigation: Hook only reads params — doesn't affect route matching.

---

## Option B: Extend Route Union + Canonical System

### Approach

Extend the `Route` type union to include optional params on browse route types. Extend `parseRoute()` to parse search params for browse routes and `serializeRoute()` to serialize them. Pages read state from route props rather than managing it themselves.

### Architecture

```
Route union (extended):
  | { type: 'collections-browse', params: { q?: string } }
  | { type: 'technique-browse', params: { cat?: string, s?: string } }
  | { type: 'training-browse', params: { cat?: string } }

parseRoute(pathname, search) → Route with params
serializeRoute(route) → URL with query string
```

### File Changes

| File | Change |
|------|--------|
| `routes.ts` | Extend Route types, `parseRoute()` and `serializeRoute()` for browse params + shorthand routes |
| `canonicalUrl.ts` | Add browse-param parse/serialize helpers (or keep in routes.ts) |
| `app.tsx` | Pass route params to browse page components; fix collection back |
| `TechniqueFocusPage.tsx` | Read `params.cat`/`params.s` from props instead of `useState`; write back via `navigateTo` or `replaceState` |
| `TrainingSelectionPage.tsx` | Read `params.cat` from props instead of `useState` |
| `CollectionsPage.tsx` | Read `params.q` from props instead of `useState` |

### ContentTypeFilter Strategy (I-5)

Same as Option A — remove from browse pages.

### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| OPT-B1 | Complexity | **Medium-High** — touches routing core (Route union + parse + serialize) |
| OPT-B2 | Reusability | **High** — route-level params are "correct" from a routing POV |
| OPT-B3 | Isolation | **Low** — modifies shared routing infrastructure |
| OPT-B4 | Test impact | **High** — must update all route parse/serialize tests + page tests |
| OPT-B5 | Rollback | **Hard** — Route type changes affect all consumers |
| OPT-B6 | Risk | **Medium** — any parseRoute/serializeRoute bug affects ALL pages |
| OPT-B7 | YAGNI | **Higher concern** — Route union is already a clean discriminated union; adding per-type optional params complicates the pattern |
| OPT-B8 | Architecture | Unified — but mixes string browse params with numeric context params |

### Risks

- **R-B1**: Route type change is a cross-cutting modification — `serializeRoute` is called from `navigateTo`, `useRouteChange`, and multiple components. Regression surface is large.
- **R-B2**: TypeScript strict mode will force handling of optional `params` in every Route consumer.
- **R-B3**: Merging string browse params into the same URL model that uses numeric context filters creates architectural ambiguity.

---

## Option C: Per-Page Inline URLSearchParams (No Abstraction)

### Approach

Each browse page directly reads `window.location.search` on mount and writes via `history.replaceState` on changes. No shared hook, no routing changes. Minimal code, maximum containment.

### File Changes

| File | Change |
|------|--------|
| `TechniqueFocusPage.tsx` | Replace `useState` with direct `URLSearchParams` read/write (~15 lines inline logic) |
| `TrainingSelectionPage.tsx` | Same pattern (~10 lines) |
| `CollectionsPage.tsx` | Same pattern (~10 lines) |
| `app.tsx` | Fix collection back button (F-1) |
| `routes.ts` | Add shorthand routes (F-4) |

### ContentTypeFilter Strategy (I-5)

Same as Options A/B — remove from browse pages.

### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| OPT-C1 | Complexity | **Lowest** — no new files, no infrastructure changes |
| OPT-C2 | Reusability | **None** — each page duplicates the pattern |
| OPT-C3 | Isolation | **Highest** — each page manages its own params |
| OPT-C4 | Test impact | **Low** — only page-level behavior tests needed |
| OPT-C5 | Rollback | **Easiest** — page-contained changes only |
| OPT-C6 | Risk | **Lowest** — no shared infrastructure touched |
| OPT-C7 | YAGNI | **Best** — no new abstractions, just fix what's broken |
| OPT-C8 | Architecture | **DRY violation** — same 10-15 lines repeated in 3 pages |

### Risks

- **R-C1**: Copy-paste divergence over time — 3 pages with similar but slightly different param logic.
- **R-C2**: Missing `popstate` listener in one page → inconsistent back/forward behavior.
- **R-C3**: No standard for param naming conventions across pages.

---

## Comparison Matrix

| Criterion | Option A (Hook) | Option B (Route) | Option C (Inline) |
|-----------|----------------|------------------|--------------------|
| New files | 1 (+~60 lines) | 0 | 0 |
| Files modified | 5 | 6 | 5 |
| Lines changed (est.) | ~200 | ~300 | ~150 |
| Routing system touched | No | Yes | No |
| Test surface | Hook + pages | Routes + pages | Pages only |
| DRY compliance | Good | Good | Poor (3× duplicate) |
| Rollback risk | Low | Medium | Lowest |
| Regression risk | Low | Medium-High | Lowest |
| Future extensibility | Good | Good | Poor |
| Correction Level | L3 | L3 | L2-L3 |

---

## Recommendation

**Option A: `useBrowseParams` Hook**

Rationale:
1. **Best isolation/DRY balance** — single shared hook without touching routing core
2. **3 immediate consumers** — meets the "don't abstract for one use" threshold
3. **Clean architectural boundary** — browse params ≠ context filters; separate hook reflects this
4. **Low regression risk** — context routes and existing `useCanonicalUrl` completely untouched
5. **Governance-aligned** — addresses GV-3 and GV-5 concerns about not polluting the context system

Option C is tempting for its simplicity but creates DRY debt that governance would flag on review. Option B is architecturally "correct" but the blast radius of modifying the Route union for 3 pages of string params is disproportionate.

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Feature scope + Design Decisions section
> - [15-research.md](./15-research.md) — UX Audit evidence
> - [70-governance-decisions.md](./70-governance-decisions.md) — Charter approval
