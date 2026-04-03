# Clarifications — Frontend Cleanup Post-Recovery

**Initiative**: `20260324-1800-feature-frontend-cleanup-post-recovery`
**Last Updated**: 2026-03-24

---

## Research Summary

Two comprehensive research passes were completed:

1. **Code Audit** (`20260324-research-frontend-cleanup-deep-audit/15-research.md`):
   - 26 confirmed dead files + 2 dead directories
   - 9 duplicate functionality pairs
   - 4 stale type files
   - 12 principle violations (YAGNI/DRY/KISS/SOLID)
   - ~3,000 lines removable in Phase 1 safe deletes
   - Service worker has 2 stale caching patterns

2. **Docs/README/AGENTS.md Audit** (`frontend-docs-gap-audit/15-research.md`):
   - README.md is severely broken (describes old JSON shard architecture)
   - 3 architecture docs describe fully superseded system
   - 6 architecture/frontend/ docs have factual errors
   - AGENTS.md missing ~50% of actual file entries
   - CLAUDE.md missing ~15 services, 20+ pages
   - 14 CLAUDE.md gaps, 16 AGENTS.md gaps, 13 README.md gaps

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | **88** |
| Risk Level | **low** |

Score breakdown:
- Architecture seams clear (SQLite is canonical, JSON shards are dead): -0
- Two clear approaches (phased delete vs big-bang): -5
- No external precedent needed: -0
- Quality/performance impact negligible (removing dead code): -0
- Test strategy clear (delete dead tests with dead code): -0
- Rollout/rollback straightforward (git revert): -7

Research NOT triggered (score >= 70, risk = low, no external patterns needed). Research was already conducted upfront via Feature-Researcher.

---

## Clarification Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? | A: No / B: Some compat | A | **A** — "code is in git history, we don't need it" | ✅ resolved |
| Q2 | Should old code be removed? | A: Yes / B: Deprecate / C: Selective | A | **A** — "remove it" | ✅ resolved |
| Q3 | Stale docs: archive or delete? | A: Archive / B: Deprecate in-place / C: Delete | A | **C** — "Delete. No need for archive." | ✅ resolved |
| Q4 | Timed-loader migration: in-scope or separate? | A: In-scope / B: Separate initiative | B | **B** — Separate. See §Q4-BRIEF below. | ✅ resolved |
| Q5 | Which solution verifier survives? | A: Keep active / B: Migrate to SGF-native / C: Defer | A | **A** — after investigation (§Q5-ANALYSIS). Delete unused. | ✅ resolved |
| Q6 | Merge qualityConfig into lib/quality/config? | A: Merge / B: Keep both / C: Defer | C | **A** — "Yes, mash them." | ✅ resolved |
| Q7 | AGENTS.md: full regen or incremental? | A: Full regen / B: Incremental / C: Defer | A | **A** — "full regeneration is better" | ✅ resolved |
| Q8 | Combined initiative or split? | A: Combined / B: Split | A | **A** — "combined" | ✅ resolved |

---

## §Q4-BRIEF: Timed Puzzle JSON-to-SQL Migration (Separate Initiative)

### Problem Statement

The timed puzzle loading path still uses the **old JSON file-based architecture** (`views/by-tag/`, `views/daily/{YYYY-MM-DD}.json`) instead of the canonical **SQLite architecture** (`yengo-search.db` via `sqliteService` + `puzzleQueryService` + `dailyQueryService`). This is a **Level 3 change** (2-3 files, UI + logic) that carries behavioral risk because it changes how timed/rush puzzles are actually fetched and loaded.

### What Is Currently Broken

1. **`hooks/useTimedPuzzles.ts`** imports `adaptToLegacyPuzzle` from `services/puzzleAdapter.ts`, but **this function was deleted** in spec 115. The hook has a **latent runtime crash** — if the timed puzzle path is ever invoked, it will throw an import error.

2. **`hooks/useTimedPuzzles.ts`** imports from `lib/puzzle/timed-loader.ts`, which imports from `lib/puzzle/daily-loader.ts`, which fetches JSON from `views/daily/{YYYY}/{MM}/{YYYY-MM-DD}-{NNN}.json` — these JSON files **may not exist** in the new SQLite-based publish pipeline.

### Full Dependency Chain

```
hooks/useTimedPuzzles.ts
  → imports from lib/puzzle/timed-loader.ts (TimedChallengeConfig, loadTimedQueue, etc.)
  → imports adaptToLegacyPuzzle from services/puzzleAdapter.ts  ← DELETED FUNCTION (crash)
  
lib/puzzle/timed-loader.ts
  → imports from lib/puzzle/daily-loader.ts (loadDailyIndex, loadPuzzle, getTimedPuzzlePaths, etc.)
  
lib/puzzle/daily-loader.ts
  → fetches from views/daily/{YYYY}/{MM}/{YYYY-MM-DD}-{NNN}.json ← OLD JSON FORMAT
  → imports from types/indexes.ts (DailyIndex, DailyStandard, DailyTimed, etc.)
  → imports from lib/sgf-parser, lib/sgf-solution, utils/coordinates, etc.
  
lib/puzzle/tag-loader.ts
  → imports loadPuzzle from daily-loader.ts
  → fetches from views/by-tag/ ← OLD JSON FORMAT
  → imports from types/indexes.ts, services/entryDecoder, services/configService
```

### Who Uses These Files

| File | Imported By | Status |
|------|------------|--------|
| `hooks/useTimedPuzzles.ts` | **0 page/component imports found** | Likely dead |
| `lib/puzzle/timed-loader.ts` | Only by `useTimedPuzzles.ts` | Dead if hook is dead |
| `lib/puzzle/daily-loader.ts` | By `timed-loader.ts` and `tag-loader.ts` only | Dead if both consumers dead |
| `lib/puzzle/tag-loader.ts` | **0 imports** outside chain | Likely dead |

### Canonical Replacement Services (already exist and are active)

| Old (JSON) | New (SQL) | Status |
|-----------|-----------|--------|
| `lib/puzzle/daily-loader.ts` → `loadDailyIndex()` | `services/dailyQueryService.ts` → `getDailySchedule()` | Active |
| `lib/puzzle/daily-loader.ts` → `loadPuzzle()` | `services/puzzleLoader.ts` → `loadPuzzle()` | Active |
| `lib/puzzle/tag-loader.ts` → tag loading | `services/puzzleQueryService.ts` → `getPuzzlesByTag()` | Active |
| `lib/puzzle/timed-loader.ts` → timed queue | `services/puzzleRushService.ts` → `getNextRushPuzzle()` | Active |

### What The New Initiative Should Do

1. **Verify** whether `useTimedPuzzles` is actually imported by any page/component. If 0 consumers → entire chain is dead → just delete all 4 files.

2. **If alive**: Rewrite `useTimedPuzzles.ts` to use `dailyQueryService` + `puzzleQueryService`. Replace `adaptToLegacyPuzzle` (deleted) with `adaptToPagesPuzzle` (exists).

3. **Delete** after migration: `lib/puzzle/timed-loader.ts`, `lib/puzzle/daily-loader.ts`, `lib/puzzle/tag-loader.ts`

4. **Clean up** `types/indexes.ts` to remove types only used by deleted loaders.

### Acceptance Criteria

- No JSON fetches to `views/daily/` or `views/by-tag/`
- If hook is alive: timed puzzles load from SQLite
- All deleted files have 0 remaining imports
- Tests pass; new tests if hook was rewritten

### Risk: Medium (Level 3 if alive, Level 1 if dead)

---

## §Q5-ANALYSIS: Solution Verifier Comparison

| Aspect | `solutionVerifier.ts` (ACTIVE) | `sgfSolutionVerifier.ts` (UNUSED) |
|--------|-------------------------------|-----------------------------------|
| **Import count** | **2 active** (`PuzzleView.tsx`, `RushMode.tsx`) | **0** |
| **Model** | `Puzzle` + `Coordinate` from `models/puzzle.ts` | `InternalPuzzle` + `Position` from `types/puzzle-internal.ts` |
| **Coordinate format** | `Coordinate` object (x, y) with `coordsEqual()` | SGF string coords via `positionToSgf()` |
| **Tree traversal** | `currentNode.move` + `currentNode.branches[]` | `findMove()` / `findMoveDeep()` from `lib/sgf/solution-tree.ts` |
| **State type** | `SolutionState { currentNode, moveHistory[], isComplete }` | `SGFSolutionState { currentNode, movePath[], isComplete, allCorrect }` |
| **Result type** | `VerificationResult { isLegal, isCorrect, matchedNode, feedback, isComplete, responseMove? }` | `SGFVerificationResult { isCorrect, matchedNode, feedback, isComplete, responseMoves[], error? }` |
| **Response** | Single `responseMove?: Coordinate` | Array `responseMoves: string[]` |
| **Call sites** | `PuzzleView.tsx` (4 sites), `RushMode.tsx` (4 sites) | None |

**Decision**: Delete `sgfSolutionVerifier.ts` — 0 consumers, YAGNI violation.

---

## §Q6-ANALYSIS: Quality Config Merge

| Aspect | `lib/quality/config.ts` (BUILD-TIME) | `services/qualityConfig.ts` (RUNTIME) |
|--------|--------------------------------------|---------------------------------------|
| **Approach** | Vite JSON import — inlined at build time | Runtime `fetch()` + fallback defaults |
| **Import count** | 1 (`configService.ts`) | 1 (`QualityFilter.tsx`) |
| **Exports** | `QUALITIES`, `QUALITY_ID_MAP`, `getQualitySlug()`, etc. | `loadQualityConfig()` async, `QualityConfig` type |
| **Unique data (build-time)** | id, slug, name, stars, description | — |
| **Unique data (runtime)** | — | selectionWeight, requirements, display colors |
| **Loading** | Synchronous (module-level constants) | Async (fetch + cache + promise) |

**Merge plan**: Extend `lib/quality/config.ts` to include selectionWeight, requirements, and display colors from the JSON (already available at build time). Rewrite `QualityFilter.tsx` to import synchronously from `lib/quality/config.ts`. Delete `services/qualityConfig.ts`.
