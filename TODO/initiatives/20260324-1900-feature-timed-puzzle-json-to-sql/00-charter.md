# Charter — Timed Puzzle JSON-to-SQL Migration

**Initiative**: `20260324-1900-feature-timed-puzzle-json-to-sql`
**Last Updated**: 2026-03-24
**Correction Level**: Level 2 (Medium Single — 5-8 file deletes + 2-3 file edits, explicit behavior change: dead code removal)

---

## Goals

1. **Delete the dead timed-puzzle JSON loading chain** — 5 files with 0 consumers that fetch from `views/daily/` and `views/by-tag/` JSON endpoints that no longer exist in the SQLite architecture.
2. **Remove latent runtime crash** — `useTimedPuzzles.ts` imports `adaptToLegacyPuzzle` which was deleted in spec 115.
3. **Clean orphaned types** from `types/indexes.ts` that are used exclusively by deleted files.
4. **Remove vestigial JSON path references** from `collectionService.ts` that point to non-existent `views/by-level/` and `views/by-tag/` JSON files.
5. **Delete additional dead files** — `config/cdn.ts` (0 importers), `app.tsx.new` (stale copy).
6. **Update AGENTS.md** — reflect file deletions.

## Non-Goals

- Rewriting or migrating any active functionality (all data loading already uses SQLite)
- Modifying the SQLite query layer (`sqliteService`, `puzzleQueryService`, `dailyQueryService`)
- Changing `collectionService.ts` data loading logic (already SQLite-based)
- Removing `types/indexes.ts` types that are still used by active services (`DailyIndex`, `DailyPuzzleEntry`, `DailyStandard`, `DailyTimedV2`, etc. used by `dailyChallengeService.ts`)
- Migrating `collectionService.ts` away from JSON fetches for curated collections (`views/by-collection/`)

## Constraints

- No backward compatibility required (user decision: Q1=A, Q2=A)
- Delete, don't deprecate (project policy: "Dead code policy — Delete, don't deprecate")
- Follow git safety rules (never `git add .`, selective staging only)
- Tests must pass after changes (vitest frontend, zero broken imports)
- AGENTS.md must be updated in the same commit as structural changes

## Files to Delete

| # | File | Lines | Reason |
|---|------|-------|--------|
| D1 | `frontend/src/hooks/useTimedPuzzles.ts` | ~185 | 0 consumers, latent crash |
| D2 | `frontend/src/lib/puzzle/timed-loader.ts` | ~200 | Only consumer is D1 |
| D3 | `frontend/src/lib/puzzle/daily-loader.ts` | ~300 | Only consumers are D2 and D4 |
| D4 | `frontend/src/lib/puzzle/tag-loader.ts` | ~350 | 0 consumers |
| D5 | `frontend/src/utils/dailyPath.ts` | ~80 | Only consumer is D3 |
| D6 | `frontend/src/config/cdn.ts` | ~55 | 0 active importers |
**Total: ~1,170 lines removed** (D7 dropped — `app.tsx.new` does not exist; `SolutionTreeView.tsx.new` out of scope)

## Files to Edit

| # | File | Change | Reason |
|---|------|--------|--------|
| E1 | `frontend/src/types/indexes.ts` | Remove 2 orphan functions: `isDailyIndexV2` and `isTimedV2` (0 active consumers). Note: 6 interface types (`TimedScoring`, `DailyTimedSet`, `DailyByTagEntry`, `DailyTag`, `DailyGauntlet`, `DailySourceSpotlight`) are KEPT — they're field types within active `DailyIndex` interface. `VIEW_PATHS` is NOT orphaned (active consumer: `pagination.ts`). | YAGNI |
| E2 | `frontend/src/services/collectionService.ts` | Remove vestigial `views/by-level/` (~line 345), `views/by-tag/` (~line 375), and `views/by-collection/` (~line 405) path strings from `CollectionSummary` construction + update comments | Dead JSON refs (field removed in E3) |
| E3 | `frontend/src/models/collection.ts` | Remove `path` field from `CollectionSummary` interface (0 consumers read it — verified: `CollectionCard`, `CollectionList`, `CollectionsModal`, `MyCollectionsPage` none access `.path`). Note: `CollectionPuzzleEntry.path` is KEPT (actively used for SGF URL construction at `collectionService.ts:918,926`) | Dead vestigial field |
| E4 | `frontend/src/AGENTS.md` | Remove deleted file entries, update file count | Structural change |
| E5 | `frontend/src/lib/puzzle/loader.ts` | Remove stale CDN comment referencing `@/config/cdn` (lines 35, 40) | Dead ref to D6 |

## Acceptance Criteria

- [ ] AC-1: All 7 files deleted with 0 remaining imports in codebase
- [ ] AC-2: `grep -r "useTimedPuzzles\|timed-loader\|daily-loader\|tag-loader\|dailyPath\|cdn\.ts" frontend/src/` returns 0 results
- [ ] AC-3: `types/indexes.ts` has no exports used only by deleted files
- [ ] AC-4: `collectionService.ts` contains no references to `views/by-level/` or `views/by-tag/` JSON paths
- [ ] AC-5: `vitest run` passes with 0 new failures
- [ ] AC-6: TypeScript compilation succeeds (`tsc --noEmit`)
- [ ] AC-7: AGENTS.md updated to reflect deletions
