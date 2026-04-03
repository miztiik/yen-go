# Clarifications — Timed Puzzle JSON-to-SQL Migration

**Initiative**: `20260324-1900-feature-timed-puzzle-json-to-sql`
**Last Updated**: 2026-03-24

---

## Research Summary

Live codebase audit confirmed the entire timed puzzle chain is **dead code with 0 consumers**:

### Import Chain Verification

| File | Imported By | External Consumers | Status |
|------|-----------|-------------------|--------|
| `hooks/useTimedPuzzles.ts` | None | **0** | DEAD |
| `lib/puzzle/timed-loader.ts` | `useTimedPuzzles.ts` only | **0** | DEAD |
| `lib/puzzle/daily-loader.ts` | `timed-loader.ts`, `tag-loader.ts` | **0** | DEAD |
| `lib/puzzle/tag-loader.ts` | None | **0** | DEAD |
| `utils/dailyPath.ts` | `daily-loader.ts` only | **0** | DEAD |

### Latent Crash Confirmation

`useTimedPuzzles.ts` imports `adaptToLegacyPuzzle` from `services/puzzleAdapter.ts`, but `puzzleAdapter.ts` explicitly documents this function was **removed in spec 115**:

> _"Legacy adapter functions (adaptToLegacyPuzzle, adaptToLegacyPuzzles) have been removed as part of spec 115 (Frontend PuzzleView Consolidation)."_

If this hook were ever invoked, it would crash at import time.

### Additional Dead File Found: `utils/dailyPath.ts`

`utils/dailyPath.ts` provides `getDailyPath()`, `getDailyUrl()`, `parseDailyPath()`. Its **only consumer** is `lib/puzzle/daily-loader.ts` (dead). The canonical daily path logic lives in `services/dailyQueryService.ts` (SQLite-based). This file should be deleted as part of this initiative.

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | **90** |
| Risk Level | **low** |

Score breakdown:
- Architecture seams crystal clear (dead chain with 0 consumers): -0
- collectionService.ts scope well-understood (vestigial metadata, not HTTP fetches): -5
- No external precedent needed: -0
- Quality/performance impact: zero (removing dead code + cosmetic cleanup): -0
- Test strategy: verify no imports remain, vitest passes: -0
- Rollout/rollback: git revert single commit: -5

Research NOT triggered (score >= 70, risk = low). Codebase audit was done inline.

---

## Clarification Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? | A: No / B: Some compat | A: No — dead code, 0 consumers | **A** (from parent initiative) | ✅ resolved |
| Q2 | Should old code be removed? | A: Yes / B: Deprecate | A: Yes — delete, don't deprecate | **A** (from parent initiative) | ✅ resolved |
| Q3 | Include `utils/dailyPath.ts` in deletion scope? | A: Yes / B: No (separate) | A: Yes — only consumer is dead `daily-loader.ts` | **A** | ✅ resolved |
| Q4 | Should `types/indexes.ts` types used ONLY by deleted files be cleaned? | A: Yes / B: No (defer) | A: Yes — YAGNI | **A** | ✅ resolved |
| Q5 | Include `collectionService.ts` JSON refs in scope? | A: Yes / B: No — separate initiative | B: No — `collectionService` has active consumers, different blast radius | **A** — user overrode recommendation | ✅ resolved |

---

## Pending User Input Required — ALL RESOLVED

All clarifications resolved. Proceeding to charter.

---

## §Q5-ANALYSIS: collectionService.ts JSON Path References

### Current State

`collectionService.ts` already uses SQLite for all actual data loading:
- `loadLevelViewIndex()` → calls `getPuzzlesByLevel()` from `puzzleQueryService`
- `loadTagIndex()` → calls `getPuzzlesByTag()` from `puzzleQueryService`
- `discoverAvailableTags()` → calls `getTagCounts()` from `puzzleQueryService`
- `loadCollectionViewIndex()` → calls `getPuzzlesByCollection()` from `puzzleQueryService`

The `views/by-level/` and `views/by-tag/` strings appear **only as metadata** in `CollectionSummary.path` fields (lines 345, 375). These paths point to JSON files that may not exist — they're vestigial metadata from the old architecture.

### Consumers of `CollectionSummary.path`

`CollectionSummary.path` is defined in `models/collection.ts` (line 86). No code outside `collectionService.ts` reads the `.path` field to fetch data — the field is populated but never consumed for actual HTTP requests.

### Additional Dead Files Found

| File | Consumers | Status |
|------|----------|--------|
| `config/cdn.ts` | **0 active imports** (only comment mentions) | DEAD |
| `app.tsx.new` | **0** | DEAD (stale copy) |

### Scope for Q5

1. Remove vestigial `views/by-level/` and `views/by-tag/` path strings from `collectionService.ts` (or replace with empty string / SQLite reference)
2. Update doc comments in `collectionService.ts` that reference old JSON architecture
3. Delete `config/cdn.ts` (0 importers)
4. Delete `app.tsx.new` (dead stale file)
5. Update `config/cdn.ts` comment references in other files (they're just comments, won't break)
