# Plan — Timed Puzzle JSON-to-SQL Migration

**Initiative**: `20260324-1900-feature-timed-puzzle-json-to-sql`
**Last Updated**: 2026-03-24
**Selected Option**: OPT-1 (Single-Commit Deletion)

---

## 1. Architecture & Design

### Approach

Single atomic commit that:
1. Deletes 6 dead files (D1-D6) — all have 0 active consumers
2. Edits 5 live files (E1-E5) — removes orphaned functions, vestigial strings, dead interface fields, stale comments
3. Updates AGENTS.md (E4) — reflects structural change

No new code is introduced. All changes are subtractive.

Note: D7 (`app.tsx.new`) dropped — file does not exist. `SolutionTreeView.tsx.new` exists but is out of scope.

### Design Decisions

| DD-id | Decision | Rationale |
|-------|----------|-----------|
| DD-1 | Delete all 7 files atomically (not phased) | All have 0 consumers; phasing adds overhead with no risk reduction |
| DD-2 | Remove `CollectionSummary.path` field (E3) | 0 consumers read it (verified: CollectionCard, CollectionList, CollectionsModal, MyCollectionsPage — none access `.path`). Note: `CollectionPuzzleEntry.path` is KEPT (actively used for SGF URL construction) |
| DD-3 | Remove only 2 orphan functions from indexes.ts; keep all interface types | The 6 interface types (`TimedScoring`, `DailyTimedSet`, `DailyByTagEntry`, `DailyTag`, `DailyGauntlet`, `DailySourceSpotlight`) are field types within `DailyIndex` / `DailyTimed` / `DailyTimedV2` which are actively used. Removing them would break `tsc`. Only `isDailyIndexV2` and `isTimedV2` are true orphans (0 imports). |
| DD-4 | Remove stale CDN comment in loader.ts | Comment references deleted `@/config/cdn`; becomes misleading |
| DD-5 | Keep `VIEW_PATHS` in indexes.ts | Active consumer: `pagination.ts` → `usePaginatedPuzzles.ts` |

---

## 2. Data Model Impact

### Interface Changes

| Change | Before | After |
|--------|--------|-------|
| `CollectionSummary.path` removed | `readonly path: string` in interface | Field deleted; consumers unaffected (0 read it) |
| `collectionService.ts` path string | `path: 'views/by-level/.../page-001.json'` and `path: 'views/by-tag/.../page-001.json'` | Lines deleted (field no longer exists on interface) |

### Type Deletions from `indexes.ts`

2 orphan function exports removed:

| Function | Was Used By | Active Consumers |
|----------|------------|------------------|
| `isDailyIndexV2` | Zero imports | 0 |
| `isTimedV2` | Only dead `daily-loader.ts` | 0 |

**NOT removed**: All 6 interface types (`TimedScoring`, `DailyTimedSet`, `DailyByTagEntry`, `DailyTag`, `DailyGauntlet`, `DailySourceSpotlight`) are field types within active `DailyIndex` interface. Removing them would break TypeScript compilation.

---

## 3. Contracts & Interfaces

No public API changes. No HTTP endpoints. No database schema changes. No config schema changes.

The only interface change (`CollectionSummary.path` removal) is internal TypeScript — 0 consumers read the field.

---

## 4. Risks & Mitigations

| R-id | Risk | Probability | Impact | Mitigation |
|------|------|------------|--------|------------|
| R-1 | Hidden consumer of deleted file not caught by grep | Very low | Build break (caught by tsc) | `tsc --noEmit` verification gate |
| R-2 | Orphan type deletion breaks structural type compatibility | Very low | TS error (caught by tsc) | Only remove types with 0 external imports; keep barrel-re-exported types |
| R-3 | `CollectionSummary.path` removal breaks runtime | Very low | TS error (caught by tsc) | Verified 0 consumers via grep of `.path` access on CollectionSummary instances |
| R-4 | Test files reference deleted types/files | Low | Test failure (caught by vitest) | `vitest run` verification gate |

---

## 5. Rollback Strategy

Single `git revert <commit>` restores all 6 files and reverts all 5 edits. No data migration, no state to unwind.

---

## 6. Verification Gates

| Gate | Command | Must Pass |
|------|---------|-----------|
| G-1 | `npx tsc --noEmit` (in `frontend/`) | Zero TS errors |
| G-2 | `npx vitest run --no-coverage` (in `frontend/`) | Zero new failures |
| G-3 | `grep -r "useTimedPuzzles\|timed-loader\|daily-loader\|tag-loader\|dailyPath\|cdn\.ts" frontend/src/` | Zero results |

---

## 7. Documentation Plan

| doc_id | Action | File | Reason |
|--------|--------|------|--------|
| DOC-1 | Update | `frontend/src/AGENTS.md` | Remove entries for deleted files; update file count. Same commit per project policy. |

No user-facing docs affected — this is internal dead code removal with no behavior change.
