# Tasks — Timed Puzzle JSON-to-SQL Migration

**Initiative**: `20260324-1900-feature-timed-puzzle-json-to-sql`
**Last Updated**: 2026-03-24
**Selected Option**: OPT-1 (Single-Commit Deletion)

---

## Task Graph

All tasks execute in a single commit. Tasks marked `[P]` can run in parallel within their group.

### Group 1: File Deletions (all parallel)

| task_id | title | file(s) | depends_on | parallel |
|---------|-------|---------|------------|----------|
| T1 | Delete `useTimedPuzzles.ts` | `frontend/src/hooks/useTimedPuzzles.ts` | — | [P] |
| T2 | Delete `timed-loader.ts` | `frontend/src/lib/puzzle/timed-loader.ts` | — | [P] |
| T3 | Delete `daily-loader.ts` | `frontend/src/lib/puzzle/daily-loader.ts` | — | [P] |
| T4 | Delete `tag-loader.ts` | `frontend/src/lib/puzzle/tag-loader.ts` | — | [P] |
| T5 | Delete `dailyPath.ts` | `frontend/src/utils/dailyPath.ts` | — | [P] |
| T6 | Delete `cdn.ts` | `frontend/src/config/cdn.ts` | — | [P] |

_D7 (`app.tsx.new`) dropped — file does not exist._

### Group 2: File Edits (all parallel, after Group 1)

| task_id | title | file(s) | depends_on | parallel | detail |
|---------|-------|---------|------------|----------|--------|
| T8 | Remove orphan functions from `indexes.ts` | `frontend/src/types/indexes.ts` | T1-T6 | [P] | Remove 2 orphan function exports: `isDailyIndexV2` (~15 lines) and `isTimedV2` (~5 lines). Keep ALL interface types (they're field types within active `DailyIndex`). |
| T9 | Remove `CollectionSummary.path` field | `frontend/src/models/collection.ts` | T1-T6 | [P] | Delete `readonly path: string` from `CollectionSummary` interface (~line 86). Keep `CollectionPuzzleEntry.path` (actively used). |
| T10 | Remove vestigial path strings from `collectionService.ts` | `frontend/src/services/collectionService.ts` | T9 | — | Remove 3 `path:` lines: `views/by-level/` (~line 345), `views/by-tag/` (~line 375), and `views/by-collection/` (~line 405). These lines produce TS errors once T9 removes the field. |
| T11 | Remove stale CDN comment from `loader.ts` | `frontend/src/lib/puzzle/loader.ts` | T6 | [P] | Remove comment at lines 35-36 referencing `@/config/cdn` and update line 40 comment. |
| T12 | Update `AGENTS.md` | `frontend/src/AGENTS.md` | T1-T6 | [P] | Remove entries for `config/cdn.ts`, `hooks/useTimedPuzzles.ts`, `lib/puzzle/timed-loader.ts`, `lib/puzzle/daily-loader.ts`, `lib/puzzle/tag-loader.ts`, `utils/dailyPath.ts`. Update file counts. |

### Group 3: Verification (sequential, after Group 2)

| task_id | title | command | depends_on | parallel |
|---------|-------|---------|------------|----------|
| T13 | TypeScript compilation check | `cd frontend && npx tsc --noEmit` | T8-T12 | — |
| T14 | Run vitest | `cd frontend && npx vitest run --no-coverage` | T13 | — |
| T15 | Grep verification (no stale refs) | `grep -r "useTimedPuzzles\|timed-loader\|daily-loader\|tag-loader\|dailyPath\|cdn\.ts" frontend/src/` → 0 results | T14 | — |

### Group 4: Commit (after verification)

| task_id | title | detail | depends_on | parallel |
|---------|-------|--------|------------|----------|
| T16 | Selective git stage | `git add` only the 6 deleted files + 5 edited files. Verify with `git diff --cached --name-only`. | T15 | — |
| T17 | Commit | `git commit -m "refactor: delete dead timed-puzzle JSON loading chain (6 files, ~1170 lines)"` | T16 | — |

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 17 (T7 dropped) |
| Files deleted | 6 |
| Files edited | 5 |
| Lines removed | ~1,170 + 2 orphan functions + vestigial strings |
| Lines added | 0 |
| Commits | 1 |
| Verification gates | 3 (tsc, vitest, grep) |
