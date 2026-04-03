# Charter — Frontend Cleanup Post-Recovery

**Initiative**: `20260324-1800-feature-frontend-cleanup-post-recovery`
**Last Updated**: 2026-03-24
**Correction Level**: Level 4 (Large Scale — 30+ file deletions, doc updates, quality config merge, AGENTS.md regen)

---

## Goals

1. **Delete all confirmed dead code** — 27 files + 2 directories (~3,000 lines) with verified 0 active imports, superseded by the SQLite architecture
2. **Delete all stale documentation** — 3 architecture docs describing the fully superseded shard/manifest system + fix 6 docs with factual errors
3. **Merge duplicate quality config** — Consolidate `services/qualityConfig.ts` (runtime fetch) into `lib/quality/config.ts` (build-time Vite import), update `QualityFilter.tsx`
4. **Fix README.md** — Rewrite sections describing wrong architecture (JSON shards → SQLite)
5. **Update CLAUDE.md** — Add missing services, pages, lib directories
6. **Regenerate AGENTS.md** — Full regeneration to cover the ~50% of missing file entries
7. **Clean service worker** — Remove stale `manifest.json` and `puzzles/` caching patterns from `sw.ts`

## Non-Goals

- **Timed-loader migration** — `useTimedPuzzles.ts` / `timed-loader.ts` / `daily-loader.ts` / `tag-loader.ts` chain is out of scope (separate initiative, see `10-clarifications.md §Q4-BRIEF`)
- **Solution verifier migration to SGF-native** — We delete the unused `sgfSolutionVerifier.ts` but do NOT rewrite `solutionVerifier.ts`
- **Refactoring active services** — No changes to `rulesEngine.ts`, `boardAnalysis.ts`, `puzzleGameState.ts` or other active services
- **Test infrastructure changes** — Delete tests for dead code only; no new test framework changes
- **Frontend feature work** — No behavioral changes to the app

## Constraints

- **No behavioral changes** — All deletions are 0-import files. The app must function identically before and after.
- **Git safety** — Never `git add .`, never `git stash`. Stage by explicit path only.
- **Test validation** — `npm test` must pass after every batch of deletions.
- **Build validation** — `npm run build` must succeed (TypeScript strict compilation).
- **Dead code policy** — "Delete, don't deprecate" per project CLAUDE.md.
- **Docs deletion** — Stale docs deleted outright (not archived). Git history preserves them.

## Acceptance Criteria

| AC-ID | Criterion | Verification |
|-------|-----------|-------------|
| AC-1 | All 27 dead files + 2 directories deleted | File system check |
| AC-2 | `npm test` passes (vitest) | Terminal output |
| AC-3 | `npm run build` succeeds (TypeScript strict) | Terminal output |
| AC-4 | 3 stale architecture docs deleted | File system check |
| AC-5 | 6 stale architecture docs factual errors fixed | Diff review |
| AC-6 | `frontend/README.md` Data Sources, Key Services, Routes sections rewritten for SQLite | Content review |
| AC-7 | `frontend/CLAUDE.md` missing sections added | Content review |
| AC-8 | `frontend/src/AGENTS.md` regenerated with all current files | Content review |
| AC-9 | `services/qualityConfig.ts` deleted, `QualityFilter.tsx` uses `lib/quality/config.ts` | Import check |
| AC-10 | `sw.ts` stale patterns removed | Grep for `manifest.json` pattern |
| AC-11 | No remaining imports to deleted files | `grep` verification |
| AC-12 | `types/index.ts` manifest comment cleaned | Content review |

## Scope Summary

| Category | File Count | Estimated Lines |
|----------|-----------|-----------------|
| Dead code deletion | 27 files + 2 dirs | ~3,000 removed |
| Quality config merge | 3 files modified | ~200 changed |
| Service worker fix | 1 file | ~10 changed |
| Stale docs deletion | 3 files | ~500 removed |
| Stale docs fixing | 6 files | ~300 changed |
| README.md rewrite | 1 file | ~200 changed |
| CLAUDE.md update | 1 file | ~100 added |
| AGENTS.md regen | 1 file | Full rewrite |
| **Total** | **~40 files touched** | **~4,000+ lines** |
