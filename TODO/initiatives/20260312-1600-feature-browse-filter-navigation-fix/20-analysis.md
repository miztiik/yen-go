# Analysis — Browse Filter & Navigation Fix

**Initiative:** `20260312-1600-feature-browse-filter-navigation-fix`  
**Last Updated:** 2026-03-12

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 85 |
| Risk Level | medium |
| Research Invoked | Yes (Feature-Researcher — UX persona audit) |
| Research Trigger | UX friction evidence needed for option quality |

---

## Ripple-Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | downstream | 3 browse pages | Medium | New hook replaces `useState` for URL-synced params; functional behavior preserved | T5, T6, T7 | ✅ addressed |
| RE-2 | lateral | `popstate` event coordination | Medium | Path-change guard in `useBrowseParams` prevents cross-page param leakage (RC-1) | T3 | ✅ addressed |
| RE-3 | upstream | `useCanonicalUrl` hook | None | NOT modified — Option A preserves complete isolation | — | ✅ addressed |
| RE-4 | upstream | Route union / `parseRoute` / `serializeRoute` | None | NOT modified for browse params; only shorthand aliases added to `parseRoute` | T8 | ✅ addressed |
| RE-5 | downstream | `ContentTypeFilter` component | None | Component file retained; only browse-page JSX usage + imports removed | T5, T6, T7 | ✅ addressed |
| RE-6 | lateral | existing route tests | Low | Shorthand routes add new test cases; existing tests must continue passing | T9 | ✅ addressed |
| RE-7 | lateral | `app.tsx` route rendering | Low | `onBack` callback change for collection context only; other contexts unchanged | T4 | ✅ addressed |
| RE-8 | downstream | browser history stack | None | `history.replaceState` (not pushState) — no history pollution, matches existing pattern | T3 | ✅ addressed |

---

## Consistency Findings

| finding_id | severity | finding | resolution |
|------------|----------|---------|------------|
| F-1 | Info | Q7 resolved as "include CTF counts" but options converged on "remove CTF from browse pages" | CTF removal is the correct option — browse pages lack shard-level data for counts. Q7 superseded by options analysis. |
| F-2 | Low | Charter AC-8/9/10 reference shorthand routes; plan must map these to specific route patterns | Mapped in plan: 3 regex patterns in `parseRoute()` |
| F-3 | Info | 14 existing hooks in `hooks/` directory — `useBrowseParams` fits established pattern | No structural concern |
| F-4 | **Medium (corrected)** | `TechniqueFocusPage` uses both `useCanonicalUrl` (for level filter) and `useBrowseParams` (for category/sort) — both hooks replace the full URL search string via `replaceState`. **Conflict identified at Gate 3:** `buildSearchString` in `useCanonicalUrl.ts` (L116-140) creates a new `URLSearchParams` from only canonical keys, discarding unmanaged params. Similarly, `useBrowseParams` would overwrite canonical params. **Resolution (RC-2, RC-3):** Both hooks must use read-merge-write pattern — read current `URLSearchParams`, update only managed keys, write back ALL params. Dual-hook integration test added to T9 (RC-5). |
| F-5 | Info | Charter requires existing vitest tests pass (AC-12) | Regression verification task included |

---

## Coverage Map

| Charter Goal | Primary Issue | Tasks | AC Coverage |
|-------------|---------------|-------|-------------|
| G1: Fix navigation | I-1 | T4 | AC-1 |
| G2: Filter persistence | I-3 | T3, T5, T6 | AC-2, AC-3, AC-4 |
| G3: Cosmetic filters | I-2, I-6 | T5, T7 | AC-6, AC-7 |
| G4: URL-sync search | I-4 | T7 | AC-5 |
| G5: Shorthand routes | I-9 | T8, T9 | AC-8, AC-9, AC-10, AC-11 |
| G6: CTF consistency | I-5 | T5, T6, T7 | AC-6 |

## Unmapped Tasks

None — all tasks trace to charter goals/issues.

---

> **See also**:
> - [25-options.md](./25-options.md) — Selected Option A
> - [30-plan.md](./30-plan.md) — Implementation plan
> - [40-tasks.md](./40-tasks.md) — Task decomposition
