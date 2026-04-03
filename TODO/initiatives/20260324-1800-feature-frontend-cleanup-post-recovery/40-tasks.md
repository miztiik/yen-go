# Tasks — Frontend Cleanup Post-Recovery

**Initiative**: `20260324-1800-feature-frontend-cleanup-post-recovery`
**Selected Option**: OPT-1 — Category-Ordered Batches
**Last Updated**: 2026-03-24

---

## Task Legend

- `[P]` = Can be executed in parallel with other `[P]`-marked tasks in same batch
- `[S]` = Sequential — must complete before next task
- `[D:Tn]` = Depends on task Tn completing first

---

## Batch 1: Dead Services (D: none)

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T1 | Grep for test files importing from `shardPageLoader`, `snapshotService`, `queryPlanner`, `schemaValidator`, `sgfSolutionVerifier`. List all test files to delete alongside. | `frontend/src/services/__tests__/` | [S] |
| T2 | Delete `frontend/src/services/shardPageLoader.ts` | — | [P] D:T1 |
| T3 | Delete `frontend/src/services/snapshotService.ts` | — | [P] D:T1 |
| T4 | Delete `frontend/src/services/queryPlanner.ts` | — | [P] D:T1 |
| T5 | Delete `frontend/src/services/schemaValidator.ts` | — | [P] D:T1 |
| T6 | Delete `frontend/src/services/sgfSolutionVerifier.ts` | — | [P] D:T1 |
| T7 | Delete all test files identified in T1 | — | [P] D:T1 |
| T8 | Run `npm test` + `npm run build` — must pass | — | [S] D:T2-T7 |

## Batch 2: Dead Lib Directories + Standalone Loaders (D: T8)

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T9 | Delete entire `frontend/src/lib/shards/` directory (2 files: `shard-key.ts`, `count-tier.ts`) | — | [P] |
| T10 | Delete entire `frontend/src/lib/rules/` directory (6 files: `engine.ts`, `index.ts`, `liberties.ts`, `captures.ts`, `ko.ts`, `suicide.ts`) | — | [P] |
| T11 | Delete `frontend/src/lib/config-loader.ts` | — | [P] |
| T12 | Delete `frontend/src/lib/daily-challenge-loader.ts` | — | [P] |
| T13 | Grep for test files importing from deleted modules. Delete them. | — | [P] |
| T14 | Run `npm test` + `npm run build` — must pass | — | [S] D:T9-T13 |

## Batch 3: Dead lib/puzzle Files (D: T14)

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T15 | Delete `frontend/src/lib/puzzle/manifest.ts` | — | [P] |
| T16 | Delete `frontend/src/lib/puzzle/refresh.ts` | — | [P] |
| T17 | Delete `frontend/src/lib/puzzle/level-loader.ts` | — | [P] |
| T18 | Delete `frontend/src/lib/puzzle/compact-entry.ts` | — | [P] |
| T19 | Delete `frontend/src/lib/puzzle/_rewrite_pagination.py` | — | [P] |
| T20 | Grep for test files importing from deleted modules. Delete them. | — | [P] |
| T21 | Run `npm test` + `npm run build` — must pass | — | [S] D:T15-T20 |

## Batch 4: Dead Types + Recovery Debris (D: T21)

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T22 | Delete `frontend/src/types/manifest.ts` | — | [P] |
| T23 | Delete `frontend/src/types/snapshot.ts` | — | [P] |
| T24 | Delete `frontend/src/types/source-registry.ts` | — | [P] |
| T25 | Delete `frontend/src/types/mastery.ts` | — | [P] |
| T26 | Delete `frontend/src/app.tsx.new` | — | [P] |
| T27 | Clean stale comment in `frontend/src/types/index.ts` (line 25: manifest types comment) | `types/index.ts` | [P] |
| T28 | Grep for test files importing from deleted types. Delete them. | — | [P] |
| T29 | Run `npm test` + `npm run build` — must pass | — | [S] D:T22-T28 |

## Batch 5: Service Worker Cleanup (D: T29)

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T30 | Remove `manifest: /\/manifest\.json$/` regex pattern from `frontend/src/sw.ts` | `sw.ts` | [S] |
| T31 | Update `puzzles` regex to remove stale `puzzles/` prefix in `frontend/src/sw.ts` | `sw.ts` | [S] D:T30 |
| T32 | Remove any fetch handler references to the deleted `manifest` pattern | `sw.ts` | [S] D:T31 |
| T33 | Run `npm test` + `npm run build` — must pass | — | [S] D:T32 |

## Batch 6: Quality Config Merge (D: T33)

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T34 | Read `config/puzzle-quality.json` to identify all fields available at build time (stars, selectionWeight, requirements, display colors) | — | [S] |
| T35 | Extend `QualityMeta` in `frontend/src/lib/quality/config.ts` to include `selectionWeight`, `requirements` (minRefutationCount, requiresComments), and `displayColor` from JSON | `lib/quality/config.ts` | [S] D:T34 |
| T36 | Rewrite `frontend/src/components/QualityFilter.tsx` to import from `@/lib/quality/config` instead of `services/qualityConfig`. Remove async `loadQualityConfig()` call and `isConfigLoaded` state. Use synchronous `QUALITIES` array. | `QualityFilter.tsx` | [S] D:T35 |
| T37 | Delete `frontend/src/services/qualityConfig.ts` | — | [S] D:T36 |
| T38 | Update comment in `frontend/src/config/cdn.ts` (line 18) to remove `qualityConfig.ts` reference | `cdn.ts` | [P] D:T37 |
| T39 | Grep for any remaining imports of `qualityConfig` — must be 0 | — | [S] D:T37 |
| T40 | Run `npm test` + `npm run build` — must pass | — | [S] D:T39 |

## Batch 7: Stale Docs Deletion (D: T40) — No test gate

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T41 | Delete `docs/archive/snapshot-shard-terminology.md` | — | [P] |
| T42 | Delete `docs/archive/snapshot-deployment-topology.md` | — | [P] |
| T43 | Delete `docs/architecture/frontend/view-index-types.md` | — | [P] |

## Batch 8: Docs Factual Fixes (D: T43) — No test gate

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T44 | Fix `docs/architecture/frontend/structure.md` — remove references to non-existent `puzzleService.ts`, `progressService.ts`, `puzzle.ts`, `progress.ts`, `achievements.ts`. Replace with actual file names (`puzzleLoader.ts`, `progressTracker.ts`, etc.) | `structure.md` | [P] |
| T45 | Fix `docs/architecture/frontend/overview.md` — remove `config-loader.ts` reference, update boot sequence to `boot.ts` + `configService.ts` | `overview.md` | [P] |
| T46 | Fix `docs/architecture/frontend/puzzle-solving.md` — update `MoveNode` type to match actual `SolutionNode` from `lib/sgf-solution.ts` | `puzzle-solving.md` | [P] |
| T47 | Fix `docs/architecture/frontend/puzzle-modes.md` — remove "Survival" mode, update daily challenge format to SQLite tables | `puzzle-modes.md` | [P] |
| T48 | Fix `docs/architecture/frontend/sgf-processing.md` — fix "single SGF parser" claim, document all 3 SGF modules | `sgf-processing.md` | [P] |
| T49 | Fix `docs/architecture/frontend/go-rules-engine.md` — update to document active `services/rulesEngine.ts`, remove dead `lib/rules/` description | `go-rules-engine.md` | [P] |

## Batch 9: README.md Rewrite (D: T49) — No test gate

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T50 | Rewrite "Puzzle Data Sources" section — from JSON shards to SQLite (`yengo-search.db` + `sgf/{NNNN}/` batch dirs) | `README.md` | [S] |
| T51 | Rewrite "Key Services" table — replace with current SQLite-era services | `README.md` | [S] D:T50 |
| T52 | Rewrite "Routes" table — fix component names, add missing routes | `README.md` | [S] D:T51 |
| T53 | Update "SGF Custom Properties" table to schema v15 (currently shows v8) | `README.md` | [S] D:T52 |

## Batch 10: CLAUDE.md Update (D: T53) — No test gate

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T54 | Add missing `lib/` subdirectories to "Key Directories" section | `CLAUDE.md` | [S] |
| T55 | Add missing `constants/`, `contexts/`, `data/` directories | `CLAUDE.md` | [P] D:T54 |
| T56 | Add `GobanBoard/` vs `GobanContainer/` distinction | `CLAUDE.md` | [P] D:T54 |
| T57 | Add active pages inventory (30+ pages exist, only ~5 listed) | `CLAUDE.md` | [P] D:T54 |
| T58 | Add undocumented active services | `CLAUDE.md` | [P] D:T54 |

## Batch 11: AGENTS.md Regeneration (D: T58) — MUST BE LAST

| Task | Description | Files | Parallel |
|------|-------------|-------|----------|
| T59 | Use `.github/prompts/regen-agents-map.prompt.md` to regenerate `frontend/src/AGENTS.md` from current codebase state | `AGENTS.md` | [S] |
| T60 | Review generated AGENTS.md — verify all sections (Directory Structure, Core Entities, Key Methods, Data Flow, Dependencies, Gotchas, Decommission Notes) are complete and accurate | — | [S] D:T59 |

---

## Final Verification (D: T60)

| Task | Description | Parallel |
|------|-------------|----------|
| T61 | Final `npm test` — all tests pass | [S] |
| T62 | Final `npm run build` — TypeScript strict compilation succeeds | [S] D:T61 |
| T63 | Grep for any imports to deleted files — must be 0 results | [S] D:T62 |
| T64 | Verify no `@deprecated` annotations remain for deleted modules | [S] D:T63 |

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 64 |
| Code batches (with test gates) | 6 (B1–B6) |
| Docs batches (no test gates) | 5 (B7–B11) |
| Files deleted | 27 files + 2 directories |
| Files modified | ~12 |
| Files created | 0 (AGENTS.md is rewritten in place) |
| Estimated removable lines | ~3,000 |
