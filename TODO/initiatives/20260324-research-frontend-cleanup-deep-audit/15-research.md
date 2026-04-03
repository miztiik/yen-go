# Research Brief: Frontend Cleanup — Deep Code Audit

**Initiative ID**: `20260324-research-frontend-cleanup-deep-audit`
**Date**: 2026-03-24
**Scope**: `frontend/src/` — dead code, duplicates, stale types, principle violations

---

## 1. Research Question and Boundaries

**Question**: After the repository recovery incident, what dead code, superseded modules, duplicate functionality, and SOLID/DRY/KISS/YAGNI violations exist in `frontend/src/`?

**Boundaries**:
- Only `frontend/src/` code; not test files used exclusively in test contexts
- "Dead" = zero imports from active (non-dead) code, or superseded by SQLite architecture
- "Active code" = files imported transitively by `app.tsx`, `main.tsx`, `boot.ts`
- Does not cover `frontend/tests/` or `frontend/playwright/`

**Success criteria**: Actionable file-by-file inventory with verified import counts and clear delete/merge/keep recommendations.

---

## 2. Internal Code Evidence

### 2a. Canonical Architecture (Active)

| R-1 | Component | File | Status |
|-----|-----------|------|--------|
| R-1.1 | SQLite init | `services/sqliteService.ts` | Active — imported by `app.tsx`, `boot.ts` |
| R-1.2 | SQL queries | `services/puzzleQueryService.ts` | Active — imported by `app.tsx`, pages |
| R-1.3 | Row decoder | `services/entryDecoder.ts` | Active — imported by `app.tsx`, `shardPageLoader` |
| R-1.4 | Config resolver | `services/configService.ts` | Active — imports from `lib/quality/config` |
| R-1.5 | Daily (SQL) | `services/dailyQueryService.ts` + `services/dailyChallengeService.ts` | Active — multiple page consumers |
| R-1.6 | Puzzle loaders | `services/puzzleLoaders.ts` + `services/puzzleLoaders/` | Active — 10 imports from pages/components |

### 2b. Old (Pre-SQLite) Architecture

| R-2 | Component | File(s) | Status |
|-----|-----------|---------|--------|
| R-2.1 | Shard loading | `services/shardPageLoader.ts` | Superseded — 0 imports from active code |
| R-2.2 | Snapshot/manifest | `services/snapshotService.ts` | Superseded — only imported by `shardPageLoader.ts` (itself dead) |
| R-2.3 | Query planning | `services/queryPlanner.ts` | Superseded — 0 imports from active code |
| R-2.4 | Shard key builder | `lib/shards/shard-key.ts` | Superseded — only imported by `queryPlanner.ts` (dead) |
| R-2.5 | Count tier display | `lib/shards/count-tier.ts` | Superseded — 0 imports from active code |
| R-2.6 | Snapshot types | `types/snapshot.ts` | Only imported by dead shard code |
| R-2.7 | Manifest types | `types/manifest.ts` | 0 imports from any code |

---

## 3. Dead Code Inventory

| R-3 | File | Purpose | Why Dead | Active Import Count | Recommendation |
|-----|------|---------|----------|---------------------|----------------|
| R-3.1 | `services/shardPageLoader.ts` | Fetch + decode shard page entries | Superseded by SQLite `puzzleQueryService` | **0** | **DELETE** |
| R-3.2 | `services/snapshotService.ts` | Manifest + shard meta loader | Superseded by SQLite; only importer is dead `shardPageLoader` | **0** (from active) | **DELETE** |
| R-3.3 | `services/queryPlanner.ts` | Deterministic shard fetch strategy | Superseded by SQL queries in `puzzleQueryService` | **0** | **DELETE** |
| R-3.4 | `services/schemaValidator.ts` | Runtime JSON validation for old Puzzle/Level/Progress models | No imports from active code; uses old `models/puzzle` coordinate Puzzle type | **0** | **DELETE** |
| R-3.5 | `lib/shards/shard-key.ts` | Shard key construction | Only imported by dead `queryPlanner.ts` | **0** (from active) | **DELETE** |
| R-3.6 | `lib/shards/count-tier.ts` | Count accuracy tier display | Imports `types/snapshot`; 0 imports from active | **0** | **DELETE** |
| R-3.7 | `lib/shards/` (directory) | Entire shard utility directory | Both files dead | — | **DELETE directory** |
| R-3.8 | `lib/rules/engine.ts` | Old Go rules engine (string-based `'B'/'W'/null` Stone type) | Marked `@deprecated` in source; superseded by `services/rulesEngine.ts` (integer Stone) | **0** | **DELETE** |
| R-3.9 | `lib/rules/index.ts` | Barrel for old rules | Exports from deprecated `engine.ts`; 0 imports from active code | **0** | **DELETE** |
| R-3.10 | `lib/rules/liberties.ts` | Liberty counting (old engine) | Only imported by dead `lib/rules/engine.ts` | **0** (from active) | **DELETE** |
| R-3.11 | `lib/rules/captures.ts` | Capture detection (old engine) | Only imported by dead `lib/rules/engine.ts` | **0** (from active) | **DELETE** |
| R-3.12 | `lib/rules/ko.ts` | Ko rule (old engine) | Only imported by dead `lib/rules/engine.ts` | **0** (from active) | **DELETE** |
| R-3.13 | `lib/rules/suicide.ts` | Suicide rule (old engine) | Only imported by dead `lib/rules/engine.ts` | **0** (from active) | **DELETE** |
| R-3.14 | `lib/rules/` (directory) | Entire deprecated rules directory | All files dead | — | **DELETE directory** |
| R-3.15 | `lib/config-loader.ts` | Loads `puzzle-levels.json` + `tags.json` at runtime | Marked `@deprecated`, replaced by `boot.ts` `getBootConfigs()`; 0 imports | **0** | **DELETE** |
| R-3.16 | `lib/daily-challenge-loader.ts` | Loads daily from JSON files | Superseded by SQL-based `dailyChallengeService.ts` + `dailyQueryService.ts`; 0 imports from active code | **0** | **DELETE** |
| R-3.17 | `lib/puzzle/manifest.ts` | Loads puzzle manifests (old system) | 0 imports from active code | **0** | **DELETE** |
| R-3.18 | `lib/puzzle/refresh.ts` | Auto-refresh manifest | 0 imports from active code; old manifest system | **0** | **DELETE** |
| R-3.19 | `lib/puzzle/level-loader.ts` | Barrel re-exporting from `puzzleLoader`; stub functions | 0 imports from active code | **0** | **DELETE** |
| R-3.20 | `lib/puzzle/compact-entry.ts` | Compact wire format decode | 0 imports from active code (entryDecoder.ts in services is the active version) | **0** | **DELETE** |
| R-3.21 | `lib/puzzle/_rewrite_pagination.py` | Python script — not frontend code | N/A | **DELETE** |
| R-3.22 | `types/manifest.ts` | Manifest/YearlyIndex types for old system | **0** imports from any code | **DELETE** |
| R-3.23 | `types/snapshot.ts` | Snapshot/shard/manifest types | Only imported by dead shard code (`shardPageLoader`, `snapshotService`, `queryPlanner`, `count-tier`) | **0** (from active) | **DELETE** |
| R-3.24 | `types/source-registry.ts` | Source registry types for puzzle import | **0** imports | **DELETE** |
| R-3.25 | `types/mastery.ts` | MasteryLevel + opacity map | 0 imports — `lib/mastery.ts` defines its own `MasteryLevel` type which is what active code uses | **DELETE** |
| R-3.26 | `app.tsx.new` | Stale copy of app.tsx (635 lines) | See §8 below for details. Uses old JSON shard imports, `useGoban`, `usePuzzleState` inline. Not imported by anything. | **0** | **DELETE** |

**Total dead files: 26 files + 2 directories**

---

## 4. Duplicate Functionality Map

| R-4 | Functionality | Implementation A (Canonical) | Implementation B (Duplicate) | Recommendation |
|-----|---------------|-------------------------------|------------------------------|----------------|
| R-4.1 | **Daily challenge loading** | `services/dailyChallengeService.ts` + `services/dailyQueryService.ts` (SQL-based) | `lib/daily-challenge-loader.ts` (JSON fetch) + `lib/puzzle/daily-loader.ts` (JSON fetch from views/) | **DELETE** both B files. A is canonical. |
| R-4.2 | **Go rules engine** | `services/rulesEngine.ts` (integer Stone: -1/0/1, Besogo pattern) | `lib/rules/engine.ts` (string Stone: 'B'/'W'/null, marked `@deprecated`) | **DELETE** B. A is canonical (used by `boardAnalysis`, `puzzleGameState`, `PuzzleView`, `ReviewMode`, `RushMode`). |
| R-4.3 | **Solution verification** | `services/sgfSolutionVerifier.ts` (SGF coords, `InternalPuzzle`) | `services/solutionVerifier.ts` (old `Puzzle` model, coordinate-based) | **INVESTIGATE**: `sgfSolutionVerifier` has 0 imports. `solutionVerifier` has 2 active imports (`PuzzleView.tsx`, `RushMode.tsx`). The "old" one is the active one. `sgfSolutionVerifier` may be dead. |
| R-4.4 | **MasteryLevel type** | `lib/mastery.ts` (6 levels: new→mastered, accuracy-based) | `types/mastery.ts` (5 levels: new→mastered, opacity-based) | **DELETE** `types/mastery.ts`. `lib/mastery.ts` is actively used (13 imports). |
| R-4.5 | **Progress tracking** | `services/progress/` dir (modular: storageOperations, calculations, migrations) | `services/progressTracker.ts` (re-export barrel) | **KEEP both**: `progressTracker.ts` is a re-export barrel for `progress/` and has 20+ active imports. The barrel pattern is intentional. |
| R-4.6 | **Streak management** | `lib/streak/` dir (calculator, reset, tolerance) | `services/streakManager.ts` | **KEEP both**: `streakManager.ts` adds daily-play recording + milestone logic on top of `lib/streak/` utilities, and has 7 active imports. `lib/streak/` has 3 direct imports. Different abstraction layers. |
| R-4.7 | **Quality config** | `lib/quality/config.ts` (Vite JSON import, build-time) | `services/qualityConfig.ts` (runtime fetch + fallback) | **INVESTIGATE**: Both have active imports (1 each from different consumers). Could be merged but serves different needs (build-time vs runtime). |
| R-4.8 | **Compact entry decode** | `services/entryDecoder.ts` (active, used in app.tsx) | `lib/puzzle/compact-entry.ts` (0 imports from active code) | **DELETE** `lib/puzzle/compact-entry.ts`. |
| R-4.9 | **Puzzle adapter** | `services/puzzleAdapter.ts` (`adaptToPagesPuzzle`) | Dead `adaptToLegacyPuzzle` function (removed per doc but imported by `useTimedPuzzles`) | **INVESTIGATE**: `useTimedPuzzles.ts` imports `adaptToLegacyPuzzle` which was documented as removed. Will cause runtime error if called. |

---

## 5. Stale Type Definitions

| R-5 | Type File | Types Defined | Active Import Count | Recommendation |
|-----|-----------|---------------|---------------------|----------------|
| R-5.1 | `types/manifest.ts` | `ManifestLevel`, `Manifest`, `YearlyIndex` | **0** | **DELETE** |
| R-5.2 | `types/snapshot.ts` | `ActiveSnapshotPointer`, `ShardManifestEntry`, `SnapshotManifest`, `ShardMeta`, `ShardPageDocument`, etc. | **0** from active code (only dead shard files) | **DELETE** |
| R-5.3 | `types/source-registry.ts` | `SourceLicense`, `SourceParser`, `SourceDefinition`, `SourceRegistry` | **0** | **DELETE** |
| R-5.4 | `types/mastery.ts` | `MasteryLevel`, `MASTERY_OPACITY` | **0** (superseded by `lib/mastery.ts`) | **DELETE** |
| R-5.5 | `types/indexes.ts` | `LevelEntry`, `TagEntry`, `CollectionEntry`, `DailyIndex`, `DailyPuzzleEntry`, master entries, etc. | **20+** imports | **KEEP** — actively used by pages, hooks, loaders |
| R-5.6 | `models/puzzle.ts` | `Puzzle`, `SolutionNode`, `Coordinate`, `Stone`, `BoardSize`, etc. | **20+** imports | **KEEP** — actively used by Board, Rush, visual-tests |
| R-5.7 | `models/board.ts` | `KoState`, `StoneGroup`, `getAdjacentCoords`, etc. | Active (used by `rulesEngine`, `boardAnalysis`) | **KEEP** |
| R-5.8 | `models/progress.ts` | `PuzzleCompletion`, `StreakData`, `UserProgress`, etc. | **20+** imports | **KEEP** |
| R-5.9 | `models/quality.ts` | `PuzzleQualityLevel`, `QualityMetrics`, etc. | Active (used by components) | **KEEP** |

---

## 6. Principle Violations

| R-6 | File | Violation | Description | Severity |
|-----|------|-----------|-------------|----------|
| R-6.1 | `app.tsx.new` | **YAGNI** | 635-line stale copy of `app.tsx` from recovery. Never used, never imported. Contains old JSON shard loading + inline `useGoban`/`usePuzzleState` rendering inside Rush. | **HIGH** |
| R-6.2 | `lib/rules/` | **DRY** | Entire Go rules engine duplicated: old string-based (`lib/rules/`) vs active integer-based (`services/rulesEngine.ts`). | **HIGH** |
| R-6.3 | `services/sgfSolutionVerifier.ts` | **YAGNI** | SGF-based solution verifier with 0 imports. Built for future use but never wired in; old `solutionVerifier.ts` is used instead. | **MEDIUM** |
| R-6.4 | `lib/puzzle/daily-loader.ts` | **DRY** | Duplicates daily loading that `dailyChallengeService` + `dailyQueryService` now handle via SQL. Has 2 indirect imports from `timed-loader` and `tag-loader`. | **MEDIUM** |
| R-6.5 | `lib/puzzle/tag-loader.ts` | **DRY** | Tag-based loading from JSON views; functionally replaced by `puzzleQueryService.getPuzzlesByTag()`. Still imported by `useTimedPuzzles` indirectly. | **MEDIUM** |
| R-6.6 | `services/schemaValidator.ts` | **YAGNI** | Runtime JSON validation for old models. Never imported by active code. Over-engineered for runtime validation that TypeScript covers at build time. | **MEDIUM** |
| R-6.7 | `lib/puzzle/manifest.ts` | **YAGNI** | Manifest loader for pre-SQLite architecture. 0 imports. | **LOW** |
| R-6.8 | `lib/puzzle/refresh.ts` | **YAGNI** | Auto-refresh for old manifest system. 0 imports. | **LOW** |
| R-6.9 | `lib/puzzle/level-loader.ts` | **YAGNI** | Barrel with stub functions that throw `NotImplementedError`. 0 imports. | **LOW** |
| R-6.10 | `services/qualityConfig.ts` | **DRY** | Runtime fetch of `puzzle-quality.json` + fallback defaults, while `lib/quality/config.ts` does build-time Vite JSON import. Both active (1 import each). | **LOW** |
| R-6.11 | `lib/puzzle/compact-entry.ts` | **DRY** | Duplicates `entryDecoder.ts` decode logic. 0 imports. | **LOW** |
| R-6.12 | `services/puzzleAdapter.ts` | **SOLID** (broken import) | `useTimedPuzzles.ts` imports `adaptToLegacyPuzzle` which docs say was removed in spec 115. Could cause runtime error or is a dead branch. | **MEDIUM** |

---

## 7. Service Worker Analysis

**File**: `frontend/src/sw.ts` (250+ lines)

### Obsolete Patterns Found

| R-7 | Pattern | Line | Status |
|-----|---------|------|--------|
| R-7.1 | `puzzles: /\/(puzzles\|yengo-puzzle-collections)\/.*\.json$/` | ~56 | **STALE** — `puzzles/` path prefix is from the old architecture. Only `yengo-puzzle-collections/` is current. The JSON index caching is still valid for SGF metadata. |
| R-7.2 | `manifest: /\/manifest\.json$/` | ~60 | **DEAD** — No manifest.json in the SQLite architecture. The active pointer is `db-version.json`. |
| R-7.3 | `db: /\.db$/` | ~58 | **CURRENT** — correctly caches `.db` files (yengo-search.db). |
| R-7.4 | `sgf: /\/yengo-puzzle-collections\/.*\.sgf$/` | ~57 | **CURRENT** — SGF files are still fetched individually. |
| R-7.5 | `wasm: /\.wasm$/` | ~59 | **CURRENT** — sql.js WASM binary. |

**Recommendation**: Update `puzzles` regex to remove dead `puzzles/` prefix. Remove `manifest` regex pattern — no manifest.json exists. Add `db-version.json` caching pattern. Severity: **LOW** (functional but contains dead patterns).

---

## 8. `app.tsx.new` Analysis

**File**: `frontend/src/app.tsx.new` — 635 lines

This is a **stale pre-recovery snapshot** of `app.tsx` from before the SQLite migration. Key differences from active `app.tsx` (460 lines):

| Aspect | `app.tsx` (active) | `app.tsx.new` (stale) |
|--------|-------------------|----------------------|
| Data layer | `sqliteService.init()`, `puzzleQueryService` | JSON shard fetching via `safeFetchJson` |
| Imports | `sqliteService`, `puzzleQueryService`, `puzzleRushService` | `useGoban`, `usePuzzleState`, `decodeEntries`, `decodeLevelEntry` |
| Rush mode | Delegates to `RushPuzzleRenderer` from `components/Rush` | Inline `RushPuzzleRenderer` + `InlinePuzzleSolver` (~100 lines) |
| Pages | Modern page components (browse, view pattern) | Older page names (`CollectionsPage`, `TrainingPage`, `TechniqueFocusPage`) |
| Lines | 460 | 635 |

**Recommendation**: **DELETE** — this is recovery debris. The active `app.tsx` is the canonical version.

---

## 9. `lib/puzzle/` Directory Risk Assessment

The `lib/puzzle/` directory contains a mix of active and dead files:

| R-9 | File | Status | Import Count | Recommendation |
|-----|------|--------|--------------|----------------|
| R-9.1 | `daily-loader.ts` | Partially dead | 2 internal (from `tag-loader`, `timed-loader`) | **DELETE** after removing dependents |
| R-9.2 | `tag-loader.ts` | Partially dead | 0 direct from active code; imports `daily-loader` internally | **INVESTIGATE** — may be used by `usePaginatedPuzzles` |
| R-9.3 | `timed-loader.ts` | Partially dead | 1 import from `useTimedPuzzles.ts` | **INVESTIGATE** — timed puzzles may still need JSON loading |
| R-9.4 | `manifest.ts` | Dead | 0 | **DELETE** |
| R-9.5 | `refresh.ts` | Dead | 0 | **DELETE** |
| R-9.6 | `compact-entry.ts` | Dead | 0 | **DELETE** |
| R-9.7 | `level-loader.ts` | Dead | 0 | **DELETE** |
| R-9.8 | `pagination.ts` | Active | 1 (`usePaginatedPuzzles`) | **KEEP** |
| R-9.9 | `loader.ts` | Active | 1 (`ReviewPage`) | **KEEP** |
| R-9.10 | `utils.ts` | Active | 4 imports | **KEEP** |
| R-9.11 | `index.ts` | Active (barrel) | — | **KEEP** |
| R-9.12 | `id-maps.ts` | Check | Used by `compact-entry.ts` | **INVESTIGATE** — may also be used by `configService` |
| R-9.13 | `_rewrite_pagination.py` | Not frontend code | N/A | **DELETE** |

---

## 10. External References

| R-10 | Reference | Relevance |
|------|-----------|-----------|
| R-10.1 | [Vite tree-shaking docs](https://vite.dev/guide/features#tree-shaking) | Dead imports won't affect production bundle if tree-shaken, but increase cognitive load and maintenance burden |
| R-10.2 | Dead code elimination best practices (Clean Code / Fowler refactoring patterns) | "Dead code is a breeding ground for bugs" — removing it improves codebase navigability |
| R-10.3 | TypeScript strict mode | With `strict: true`, dead type files contribute to slower type-checking across the project |
| R-10.4 | Service Worker best practices (web.dev) | Stale cache patterns in SW can cause unnecessary network requests or wrong caching strategies |

---

## 11. Risks, License/Compliance Notes, and Rejection Reasons

| R-11 | Risk | Mitigation |
|------|------|------------|
| R-11.1 | **Timed puzzles breakage**: `useTimedPuzzles.ts` imports from `timed-loader` → `daily-loader` → `types/indexes`. Removing `daily-loader` without migrating timed puzzle loading to SQL will break timed challenges. | **Phased approach**: Delete clearly dead files first (Phase 1), then migrate timed/tag paths to SQL (Phase 2). |
| R-11.2 | **`adaptToLegacyPuzzle` runtime error**: `useTimedPuzzles.ts` imports a function documented as removed. | Check if function still exists in `puzzleAdapter.ts` code or was actually deleted. If deleted, `useTimedPuzzles` has a latent crash. |
| R-11.3 | **Test coverage**: Some dead files may have tests that import them. Deleting files will break test compilation. | Delete tests alongside dead code in same commit. |
| R-11.4 | **Service Worker cache mismatch**: Updating SW patterns without version bump may cause stale caches. | Bump `CACHE_NAME` version when updating patterns. |

**License/Compliance**: No external code copying involved. All deletions are internal dead code removal.

**Rejection reasons**: None identified. All recommended deletions are supported by verified zero-import evidence.

---

## 12. Planner Recommendations

1. **Phase 1 — Safe Deletes (26 files, 2 dirs)**: Delete all R-3.x files immediately. These have verified 0 active imports. Includes: `shardPageLoader`, `snapshotService`, `queryPlanner`, `schemaValidator`, `lib/shards/`, `lib/rules/`, `lib/config-loader`, `lib/daily-challenge-loader`, `types/manifest`, `types/snapshot`, `types/source-registry`, `types/mastery`, `app.tsx.new`, `lib/puzzle/manifest.ts`, `lib/puzzle/refresh.ts`, `lib/puzzle/level-loader.ts`, `lib/puzzle/compact-entry.ts`, `lib/puzzle/_rewrite_pagination.py`. Estimated: ~3,000 lines removed.

2. **Phase 2 — Timed/Tag Loader Migration**: Before deleting `lib/puzzle/daily-loader.ts`, `lib/puzzle/timed-loader.ts`, `lib/puzzle/tag-loader.ts`, migrate `useTimedPuzzles.ts` and any remaining JSON-fetch paths to use `dailyQueryService` (SQL). This is a Level 3 change (2-3 files, UI + logic).

3. **Phase 3 — Solution Verifier Consolidation**: Decide between `sgfSolutionVerifier.ts` (0 imports, SGF-native) vs `solutionVerifier.ts` (2 imports, old model). If the app uses `solutionVerifier`, delete `sgfSolutionVerifier` as YAGNI. If moving to SGF-native format, wire in `sgfSolutionVerifier` and retire the old one.

4. **Phase 4 — Service Worker Update**: Remove stale `manifest` and `puzzles/` patterns from `sw.ts`. Add `db-version.json` caching. Bump cache version. Level 1 change.

---

## 13. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | **88** |
| `post_research_risk_level` | **low** |

**Confidence notes**: All import counts verified via grep. Phase 1 deletions are high-confidence (zero imports). Phase 2 requires deeper investigation of `useTimedPuzzles` data flow. Phase 3 requires a design decision on solution verification approach.

---

## 14. Summary Statistics

| Category | Count |
|----------|-------|
| Confirmed dead files | 26 |
| Dead directories | 2 (`lib/shards/`, `lib/rules/`) |
| Duplicate functionality pairs | 9 |
| Stale type files | 4 |
| Principle violations | 12 |
| Estimated lines removable (Phase 1) | ~3,000 |
| Files needing investigation before removal | 5 (`timed-loader`, `tag-loader`, `daily-loader`, `sgfSolutionVerifier`, `qualityConfig`) |

---

## 15. Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should timed puzzle loading be migrated to SQL (`dailyQueryService`) before deleting `lib/puzzle/timed-loader.ts`? | A: Yes, migrate first / B: Delete and accept timed puzzles are broken / C: Keep timed-loader as-is | A | | ❌ pending |
| Q2 | Which solution verifier should survive? | A: `solutionVerifier.ts` (old, currently active) / B: `sgfSolutionVerifier.ts` (SGF-native, unused) / C: Merge into one | A (delete unused B) | | ❌ pending |
| Q3 | Should `qualityConfig.ts` (runtime fetch) be merged into `lib/quality/config.ts` (build-time)? | A: Merge / B: Keep both / C: Delete qualityConfig.ts | A | | ❌ pending |
| Q4 | Is `puzzleAdapter.ts` still exporting `adaptToLegacyPuzzle` or was it actually deleted? If deleted, `useTimedPuzzles.ts` has a latent crash. | Verify in code | | | ❌ pending |
