# Research Brief: Frontend Documentation & Architecture Docs Gap Audit

**Initiative**: `frontend-docs-gap-audit`
**Research Date**: 2026-03-24
**Research Question**: What frontend documentation is stale, incorrect, or missing after the JSON→SQLite migration and repository recovery?
**Success Criteria**: Every claim in CLAUDE.md, AGENTS.md, README.md, and docs/ verified against actual code; gaps classified and prioritized.

---

## 1. Research Boundaries

**In scope**: All frontend-facing documentation files — `frontend/CLAUDE.md`, `frontend/src/AGENTS.md`, `frontend/README.md`, `docs/architecture/frontend/*`, `docs/concepts/*` (frontend-relevant), `docs/how-to/frontend/*`, `docs/reference/frontend/*`, `frontend/TESTING.md`, `frontend/HARDCODED-COLORS-AUDIT.md`, `frontend/src/visual-tests.tsx`.

**Out of scope**: Backend docs (except cross-references), spec archive, TODO plans.

---

## 2. Internal Code Evidence — Dead Code Inventory

### Confirmed Dead Files (exist, 0 active imports)

| R-ID | File | Evidence |
|------|------|----------|
| R-1 | `services/shardPageLoader.ts` | Only imports from dead `snapshotService.ts` |
| R-2 | `services/snapshotService.ts` | Only imported by R-1 and dead `shards/count-tier.ts` |
| R-3 | `services/queryPlanner.ts` | Imports from dead `types/snapshot.ts` + `shards/shard-key.ts` |
| R-4 | `services/schemaValidator.ts` | Imports from old `models/level` types |
| R-5 | `lib/shards/count-tier.ts` | Imports from dead `types/snapshot.ts` |
| R-6 | `lib/shards/shard-key.ts` | Only imported by dead R-3 |
| R-7 | `types/snapshot.ts` | Only imported by R-2, R-3, R-5 (all dead) |
| R-8 | `types/manifest.ts` | 0 imports anywhere in `src/` |
| R-9 | `types/source-registry.ts` | 0 imports anywhere in `src/` |
| R-10 | `lib/config-loader.ts` | Marked `@deprecated`; 0 imports anywhere |
| R-11 | `lib/daily-challenge-loader.ts` | 0 imports; superseded by `lib/puzzle/daily-loader.ts` + `services/dailyChallengeService.ts` |
| R-12 | `lib/puzzle/compact-entry.ts` | 0 active imports |
| R-13 | `lib/puzzle/level-loader.ts` | 0 active imports |
| R-14 | `lib/puzzle/manifest.ts` | 0 active imports |
| R-15 | `lib/puzzle/refresh.ts` | 0 active imports |
| R-16 | `lib/rules/*` (entire directory) | 0 imports from anywhere in `src/`; active rules engine is `services/rulesEngine.ts` |
| R-17 | `app.tsx.new` | Recovery debris — 0 imports |
| R-18 | `types/mastery.ts` | 0 imports; active mastery code is in `lib/mastery.ts` |
| R-19 | `lib/puzzle/_rewrite_pagination.py` | Script artifact; not frontend code |

### Alive Files Often Confused With Dead

| R-ID | File | Status | Evidence |
|------|------|--------|----------|
| R-20 | `services/rulesEngine.ts` | **ACTIVE** | Imported by PuzzleView, ReviewMode, RushMode, boardAnalysis, puzzleGameState |
| R-21 | `services/boardAnalysis.ts` | **ACTIVE** | Imported by PuzzleView/useGameState |
| R-22 | `services/puzzleGameState.ts` | **ACTIVE** | Imported by solver/validator, solver/history, PuzzleView/useGameState |
| R-23 | `services/featureFlags.ts` | **ACTIVE** | Imported by boardAnalysis, PuzzleView/useGameState |
| R-24 | `services/puzzleAdapter.ts` | **ACTIVE** | Imported by useTimedPuzzles |
| R-25 | `services/solutionVerifier.ts` | **ACTIVE** | Imported by PuzzleView, RushMode |
| R-26 | `services/qualityConfig.ts` | **ACTIVE** | Imported by QualityFilter |
| R-27 | `lib/mastery.ts` | **ACTIVE** | Imported by TechniqueCard, CollectionsBrowsePage, PuzzleCollectionCard, TrainingBrowsePage, TrainingSelectionPage |
| R-28 | `types/indexes.ts` | **ACTIVE** | Imported by 15+ files (pagination, daily-loader, tag-loader, useMasterIndexes, etc.) |
| R-29 | `lib/puzzle/pagination.ts` | **ACTIVE** | Imported by usePaginatedPuzzles |
| R-30 | `lib/puzzle/daily-loader.ts` | **ACTIVE** | Imports from types/indexes (likely imported by dailyChallengeService) |
| R-31 | `lib/puzzle/timed-loader.ts` | **ACTIVE** | Imported by useTimedPuzzles |
| R-32 | `lib/puzzle/tag-loader.ts` | **ACTIVE** | Imports types/indexes |
| R-33 | `lib/puzzle/loader.ts` | **ACTIVE** | Imported by ReviewPage |
| R-34 | `components/GobanBoard/` | **ACTIVE** | GobanRenderer imported by PuzzleSolvePage |

---

## 3. CLAUDE.md Gaps

### File: `frontend/CLAUDE.md`

| G-ID | Section/Line | Issue Type | Description | Fix Needed |
|------|-------------|------------|-------------|------------|
| G-1 | "Key Directories" `lib/` listing | **Missing** | Many existing lib/ subdirs missing: `achievements/`, `presentation/`, `progress/`, `review/`, `rush/`, `sgf/`, `solver/`, `tree/` | Add missing directories to listing |
| G-2 | "Key Directories" `lib/` listing | **Missing** | Lists `quality/` which exists, but misses `mastery.ts` which is actively used | Add `mastery.ts` mention |
| G-3 | "Key Directories" | **Missing** | Missing `constants/` directory (contains `goQuotes.ts`) | Add directory |
| G-4 | "Key Directories" | **Missing** | Missing `contexts/` directory (contains `ThemeContext.tsx`) | Add directory |
| G-5 | "Key Directories" | **Missing** | Missing `data/` directory (contains `learning-topics.ts`) | Add directory |
| G-6 | "Board Rendering" Key Files table | **Stale** | Lists `lib/sgf-preprocessor.ts` as "SGF adaptation layer" but actual purpose now is metadata extraction + SGF cleaning for goban. The architecture doc `sgf-processing.md` describes it more accurately. | Update description |
| G-7 | "Rush Play Mode" Architecture | **Incomplete** | Lists 5 components but doesn't mention `RushPage.tsx`, `RushPage.css`, or distinguish that `RushBrowsePage` is the setup AND pre-game browse | Add RushPage references |
| G-8 | Section absent | **Missing** | No mention of `GobanBoard/` component directory (contains `GobanBoard.tsx`, `GobanRenderer.tsx`) — distinct from `GobanContainer/` | Add section or mention in Board Rendering |
| G-9 | Section absent | **Missing** | No mention of the many active pages that exist beyond what's listed: `AchievementsPage`, `CollectionsPage`, `DailyBrowsePage`, `LearningPage`, `LearningTopicPage`, `MyCollectionsPage`, `PuzzleSolvePage`, `PuzzleView/`, `RandomPage`, `ReviewPage`, `RushPage`, `StatsPage`, `TechniqueFocusPage`, `TechniqueViewPage`, `TrainingBrowsePage`, `TrainingSelectionPage` | Add page inventory |
| G-10 | Section absent | **Missing** | No mention of critical active services: `boardAnalysis.ts`, `puzzleGameState.ts`, `solutionVerifier.ts`, `featureFlags.ts`, `puzzleAdapter.ts`, `qualityConfig.ts` | Document undocumented services |
| G-11 | Config Architecture section | **Incomplete** | `configService.ts` is correctly documented, but doesn't mention `qualityConfig.ts` as a parallel quality config service | Add reference |
| G-12 | "Puzzle Solving Flow" step 2 | **Minor inaccuracy** | Says "Extract metadata via `preprocessSgf()` (tree parser, no regex)" but `sgf-preprocessor.ts` actually DOES use regex (confirmed by `sgf-processing.md` architecture doc) | Fix: regex-based extraction, not tree parser |
| G-13 | Section absent | **Missing** | No mention of `visual-tests.tsx` — a specialized Playwright visual test fixture renderer | Add note about visual test infrastructure |
| G-14 | "Goban Upgradability" | **Potentially stale** | Says upgrading v8→v9 affects "only 4 files" but GobanBoard/ directory is separate from GobanContainer/ and may also be affected | Verify and update |

### Severity: 6 missing sections, 4 incomplete, 2 stale, 2 minor

---

## 4. AGENTS.md Gaps

### File: `frontend/src/AGENTS.md`

| A-ID | Section | Issue Type | Description | Fix Needed |
|------|---------|------------|-------------|------------|
| A-1 | §1 Directory Structure | **Missing entries** | ~20+ hooks missing: `useAutoAdvance`, `useBoardViewport`, `useCanonicalUrl`, `useContentType`, `useDebounce`, `useExploreMode`, `useFilterParams`, `useFilterState`, `useMediaQuery`, `useNavigationContext(.tsx)`, `usePaginatedPuzzles`, `usePrefetch`, `useShardFilters`, `useSolutionAnimation`, `useSolutionTreeKeyboard`, `useTimedPuzzles`, `useTreeKeyboard`, `useTreeNavigation` | Add all hooks |
| A-2 | §1 Directory Structure | **Missing entries** | Missing services: `boardAnalysis.ts`, `puzzleGameState.ts`, `solutionVerifier.ts`, `featureFlags.ts`, `puzzleAdapter.ts`, `qualityConfig.ts`, `puzzleLoaders/` directory | Add services |
| A-3 | §1 Directory Structure | **Missing entries** | Missing pages: 20+ pages exist but only ~14 are listed. Missing: `AchievementsPage`, `CollectionsPage`, `DailyBrowsePage`, `HomePage`, `LearningPage`, `LearningTopicPage`, `MyCollectionsPage`, `PuzzleSolvePage`, `PuzzleView/`, `RandomPage`, `ReviewPage`, `RushPage`, `StatsPage`, `TechniqueFocusPage`, `TechniqueViewPage`, `TrainingBrowsePage`, `TrainingSelectionPage` | Add pages |
| A-4 | §1 Directory Structure | **Missing entries** | Missing components: `Achievements/`, `Board/`, `ChallengeList/`, `Collections/`, `ComplexityIndicator`, `DailyChallenge/`, `Feedback/`, `GobanBoard/`, `Home/`, `Loading/`, `PuzzleList/`, `PuzzleNavigation/`, `PuzzleRush/`, `PuzzleView/`, `QualityBadge`, `QualityBreakdown`, `QualityFilter`, `RandomChallenge/`, `Review/`, `Settings/`, `SolutionTree/`, `Stats/`, `Streak/`, `TechniqueFocus/`, `Training/` | Add components |
| A-5 | §1 Directory Structure | **Missing entries** | Missing lib/ subdirs: `achievements/`, `presentation/`, `progress/`, `review/`, `rush/`, `sgf/`, `solver/`, `tree/`, `mastery.ts`, `accent-palette.ts`, `accuracy-color.ts`, `colorTextTransform.ts`, `getBoundsFromPuzzle.ts`, `levelRanks.ts`, `mark-tree.ts`, `sanitizeComment.ts`, `slug-formatter.ts` | Add lib entries |
| A-6 | §1 Directory Structure | **Missing entries** | Missing `models/` entries: `achievement.ts`, `board.ts`, `dailyChallenge.ts`, `progress.ts`, `quality.ts`, `rush.ts`, `SolutionPresentation.ts`, `level.ts` | Add models |
| A-7 | §1 Directory Structure | **Missing entries** | Missing `types/` entries: `achievement.ts`, `board.ts`, `common.ts`, `coordinate.ts`, `goban.ts`, `json-modules.d.ts`, `level.ts`, `page-mode.ts`, `preact-iso.d.ts`, `progress.ts`, `sgf.ts`, `tree.ts` | Add types |
| A-8 | §1 Directory Structure | **Lists dead files** | Does NOT list any dead files — the current listings are all accurate. However, the map is severely incomplete. | N/A (positive) |
| A-9 | §2 Core Entities | **Missing** | Missing entities: `PuzzleBoard` (from puzzleGameState), `RetryEntry` and `AchievementNotification` ARE listed ✓, but missing `GobanConfig` (from goban.ts types), `BoardState`, `StoneGroup`, `KoState` (from board.ts model), `QualityMetrics`, `ComplexityMetrics` | Add missing entities |
| A-10 | §3 Key Methods | **Missing** | Missing key method call sites for `boardAnalysis.ts` (isMoveLegal, isSelfAtari), `puzzleGameState.ts` (createPuzzleBoardFromData, executePuzzleMove, isPuzzleMoveValid), `solutionVerifier.ts` | Add methods |
| A-11 | §4 Data Flow | **Accurate** | The BOOT, PAGE LOAD, PUZZLE PLAY, MOVE, PROGRESS, SMART PRACTICE flows are accurate. The SQLite-based architecture is correctly documented | No fix needed ✓ |
| A-12 | §5 External Dependencies | **Minor** | Version info is vague (all "~10.x", "—"). Package.json versions should be pinned | Update with actual versions |
| A-13 | §6 Known Gotchas | **Accurate** | All 14 gotchas are still valid. No stale entries found. | No fix needed ✓ |
| A-14 | §7 Decommission Notes | **Accurate** | The Adaptive Learning decommission plan is still valid. All listed files exist and the integration points are correct. | No fix needed ✓ |
| A-15 | §1 Directory Structure | **Missing** | Entire `constants/`, `contexts/`, `data/` directories not listed | Add directories |
| A-16 | §1 Directory Structure | **Missing** | `utils/` directory not listed (contains accessibility.ts, coordinates.ts, dailyPath.ts, safeFetchJson.ts, sanitize.ts, sound.ts, statusMapping.ts, storage.ts) | Add utils directory |

### Severity: 8 missing sections/entries, 1 minor, 3 accurate (no fix needed)

---

## 5. README.md Gaps

### File: `frontend/README.md`

| RM-ID | Section | Issue Type | Description | Fix Needed |
|-------|---------|------------|-------------|------------|
| RM-1 | "Puzzle Data Sources" | **STALE (Critical)** | Describes old JSON shard directory structure: `manifest.json`, `sgf/beginner/`, `views/by-level/`, `views/by-tag/`, `views/daily/{YYYY-MM-DD}.json`. This is completely wrong. Current system uses SQLite `yengo-search.db` + `sgf/{NNNN}/` batch dirs. | **Rewrite entirely** to describe SQLite architecture |
| RM-2 | "SGF Custom Properties" table | **Stale** | Shows `YV[8]` — actual schema version is 15. Missing properties: `YC`, `YK`, `YO`, `YL`, `YR`, `YM`, `YX`. `YQ` example is simplified/wrong | Update to schema v15 with all properties |
| RM-3 | "Project Structure" | **Stale** | Lists `GobanBoard/` as "goban library wrapper (SVG/Canvas)" but actual purpose is GobanBoard+GobanRenderer components. Doesn't list `GobanContainer/` which is the OGS-ported board wrapper | Fix component descriptions |
| RM-4 | "Project Structure" `lib/` | **Stale** | Lists `lib/daily-challenge-loader.ts` — this is dead code (R-11) | Remove dead file reference |
| RM-5 | "Project Structure" `pages/` | **Stale** | Lists `HomePage.tsx` but actual home page is `HomePageGrid.tsx` (both exist but HomePageGrid is the main one). Lists `TechniqueFocusPage.tsx` (exists). Lists `TrainingPage.tsx` (exists). Lists `CollectionViewPage.tsx` (exists). Missing 20+ other pages | Update page listing |
| RM-6 | "Key Services" table | **Stale** | Lists `rulesEngine.ts` as "Enforce Go rules (captures, ko, suicide)" — this is now a secondary module; goban handles primary move validation. Also `sgfSolutionVerifier.ts` listed but the actual filename is `solutionVerifier.ts` | Fix service names and descriptions |
| RM-7 | "Key Services" table | **Missing** | Missing services: `sqliteService.ts`, `puzzleQueryService.ts`, `entryDecoder.ts`, `configService.ts`, `dailyQueryService.ts`, `boardAnalysis.ts`, `puzzleGameState.ts`, `progressAnalytics.ts` | Add critical SQLite-era services |
| RM-8 | "Architecture → Zero Runtime Backend" | **Stale** | Says "Puzzles are pre-generated static JSON files" — puzzles are SGF files, metadata is in SQLite | Fix description |
| RM-9 | "Routes" table | **Stale/Wrong** | Component names don't match actual files: `CollectionsPage` (actual: `CollectionsBrowsePage`), `CollectionPlayPage` (actual: `CollectionViewPage`), `DailyChallengeView` (actual: `DailyChallengePage`), `TechniqueFocusPage` (OK), `TrainingPage` (OK), `PuzzleView` (actual: `PuzzleSolvePage` or `PuzzleView/`). Missing routes: `/progress`, `/smart-practice`, `/rush-browse`, `/achievements`, `/learning`, `/stats`, `/random-page`, `/review` | Fix component names, add missing routes |
| RM-10 | "Solution Tree" section | **Minor** | References "(Spec 125, 132)" — spec references may confuse readers | Remove spec references or add context |
| RM-11 | "Features" list | **Uses emojis** | Uses emojis (🎮📊🔥💡🔄⏱️🏆📱♿) — project rule says "No emojis in production UI" but README is docs, so technically OK. But inconsistent with project tone. | Low priority: remove emojis for consistency |
| RM-12 | "Test structure" | **Outdated** | Test count "1073+" may be outdated. `TESTING.md` says "900+" | Verify and update test count |
| RM-13 | Cross-reference links | **Potentially broken** | Links to `../docs/how-to/frontend/local-development.md`, `../docs/how-to/frontend/build-deploy.md`, `../docs/architecture/frontend/` — need verification | Verify all cross-links |

### Severity: **Critical** — README is the most severely outdated document. 5 stale sections, 2 missing, multiple wrong names.

---

## 6. Docs Directory Audit

### `docs/architecture/frontend/`

| D-ID | File | Relevance | Status | Description |
|------|------|-----------|--------|-------------|
| D-1 | `overview.md` | High | **Partially stale** | Boot sequence section references `config-loader.ts` (R-10, dead). Says boot fetches 3 configs via `config-loader.ts` but actual boot is in `boot.ts` using Vite JSON imports + `configService.ts`. | 
| D-2 | `structure.md` | High | **Stale** | Lists `services/puzzleService.ts` (doesn't exist — actual is `puzzleLoader.ts`). Lists `services/progressService.ts` (doesn't exist — actual is `progressTracker.ts`). Lists `lib/puzzle.ts` (doesn't exist). Lists `lib/progress.ts` (doesn't exist). Lists `lib/achievements.ts` (doesn't exist). `constants.ts` listed at top level but actual location is `config/constants.ts`. |
| D-3 | `goban-integration.md` | High | **Accurate** | Well-maintained, correctly describes GobanContainer, useGoban, design decisions. Last updated 2026-03-09. |
| D-4 | `puzzle-solving.md` | Medium | **Stale** | Describes `MoveNode` type and `lookupMove()` function. Actual implementation uses goban's built-in puzzle mode for move validation + `SolutionNode` type from `lib/sgf-solution.ts`. The custom `MoveNode` interface shown doesn't match code. |
| D-5 | `state-management.md` | Medium | **Partially stale** | Storage prefix shown as `yengo:` but actual prefix uses `yen-go-` (e.g., `yen-go-retry-queue`, `yen-go-achievement-progress`). Interface shapes may not match current code. |
| D-6 | `puzzle-modes.md` | Medium | **Stale** | Mode table lists "Survival" mode (doesn't exist). Daily challenge "Puzzle Selection" shows old JSON format with sgfPath structure. Implementation section shows `practiceModeReducer` which doesn't exist in code. |
| D-7 | `go-rules-engine.md` | Medium | **Stale/Misleading** | Documents a detailed Go rules engine implementation. Actual frontend has TWO: `services/rulesEngine.ts` (active, imported by components) and `lib/rules/*` (dead, 0 imports). The doc describes the `lib/rules/` version's interfaces (`BoardState`, `Move` with 1-indexed coords) which don't match the active `rulesEngine.ts`. |
| D-8 | `sgf-processing.md` | High | **Partially stale** | Describes `sgf-preprocessor.ts` as "single SGF parser" with regex extraction. But actual codebase ALSO has `lib/sgf-parser.ts` (tree parser) and `lib/sgf-metadata.ts` (canonical tree parser). The "single-parser" claim is wrong — there are at least 3 SGF-related parsers. |
| D-9 | `testing.md` | Medium | **Partially stale** | Test count may be outdated. Structure is accurate. References `playwright.investigation.config.ts` — need to verify existence. |
| D-10 | `board-state-design.md` | Low | **Deprecated (OK)** | Correctly marked as deprecated with pointer to `goban-integration.md`. |
| D-11 | `svg-board.md` | Medium | **Conflicting** | Title says "Canvas rendering (default)" per Spec 132 but `renderer-canvas-vs-svg-analysis.md` says SVG is now the default. These docs contradict each other. |
| D-12 | `renderer-canvas-vs-svg-analysis.md` | Medium | **OK but contradicts D-11** | Header says "SVG is now the default renderer" — this supersedes svg-board.md. One of these needs updating. |
| D-13 | `view-index-types.md` | High | **Stale (Critical)** | Describes the OLD compact entry / JSON shard pagination system (`CompactEntry` with `p`, `l`, `t`, `c`, `x` wire format). Current system uses SQLite queries via `puzzleQueryService.ts`. The entire document describes a superseded architecture. |
| D-14 | `ui-layout.md` | Medium | **Partially accurate** | Component hierarchy is mostly correct. Boot sequence correctly describes 3-config parallel fetch. But lists `UserProfile` as a page component which may not match actual code. |
| D-15 | `exploration-besogo-tree-swap.md` | Low | **Historical (OK)** | Correctly positioned as exploration/research doc, not prescriptive. |

### `docs/concepts/`

| D-ID | File | Relevance | Status | Description |
|------|------|-----------|--------|-------------|
| D-16 | `sqlite-index-architecture.md` | **Critical** | **Accurate ✓** | Well-maintained, correctly describes DB-1 schema, bootstrap sequence, depth presets, path reconstruction. Last updated 2026-03-20. Legacy term mapping table is helpful. |
| D-17 | `snapshot-shard-terminology.md` | High | **STALE (Critical)** | Defines canonical terminology for the OLD snapshot/shard system (manifests, shard keys, query planners, dimension prefixes). Entire document describes superseded architecture. Should be moved to archive or marked deprecated. |
| D-18 | `mastery.md` | Medium | **Needs verification** | Mastery concept — actual mastery code is in `lib/mastery.ts` (active). Verify doc matches code. |
| D-19 | `auto-advance.md` | Low | **Needs verification** | Auto-advance concept — `useAutoAdvance.ts` hook exists. |
| D-20 | `dark-mode.md` | Low | **Needs verification** | Dark mode — ThemeContext.tsx exists. |
| D-21 | `design-tokens.md` | Low | **Needs verification** | Design tokens — HARDCODED-COLORS-AUDIT.md exists suggesting ongoing token work. |

### `docs/architecture/` (top-level)

| D-ID | File | Relevance | Status | Description |
|------|------|-----------|--------|-------------|
| D-22 | `snapshot-deployment-topology.md` | High | **STALE (Critical)** | Full ADR for snapshot deployment. Describes `active-snapshot.json`, manifest bootstrap, shard fetching — all superseded by SQLite. ADR status "DECIDED" but architecture was later replaced. |
| D-23 | `database-deployment-topology.md` | High | **Needs verification** | Likely the SQLite replacement ADR. Verify accuracy. |

### `docs/how-to/frontend/`

| D-ID | File | Relevance | Status | Description |
|------|------|-----------|--------|-------------|
| D-24 | `add-components.md` | Medium | **Needs verification** | Component creation guide |
| D-25 | `build-deploy.md` | Medium | **Needs verification** | Build/deploy guide |
| D-26 | `local-development.md` | Medium | **Needs verification** | Dev setup guide |
| D-27 | `goban-integration.md` | Medium | **Needs verification** | Duplicate of architecture doc? |
| D-28 | `rush-mode.md` | Low | **Needs verification** | Rush mode how-to |
| D-29 | `solver-view.md` | Medium | **Needs verification** | Solver integration guide |
| D-30 | `progress-page.md` | Low | **Needs verification** | Progress page guide |
| D-31 | `filtering-ux-implementation-roadmap.md` | Low | **Likely historic** | Roadmap doc in how-to |

### `docs/reference/frontend/`

| D-ID | File | Relevance | Status | Description |
|------|------|-----------|--------|-------------|
| D-32 | `collections-filtering-audit-gaps-2026-02-25.md` | Low | **Needs verification** | Audit/gap doc |

### `docs/reference/` (top-level, frontend-relevant)

| D-ID | File | Relevance | Status | Description |
|------|------|-----------|--------|-------------|
| D-33 | `view-index-schema.md` | High | **Likely stale** | Referenced by stale `view-index-types.md`. Describes JSON shard schema. |
| D-34 | `hint-system.md` | Medium | **Needs verification** | Hint system reference |

---

## 7. Standalone File Audit

### `frontend/TESTING.md`
- **Status**: Mostly accurate. Well-structured with correct framework split (Vitest/Playwright), grouped test commands, timeout configuration, AI agent guidelines.
- **Issues**: Test count discrepancy (README says "1073+", TESTING.md says "900+"). Directory structure is accurate. Commands are correct.

### `frontend/HARDCODED-COLORS-AUDIT.md`
- **Status**: Active audit artifact. Lists 58 component files with hardcoded hex colors mapped to theme token replacements. Contains a complete token reference table.
- **Assessment**: Useful working document for ongoing theming work. Not stale but should not be confused with architecture docs.

### `frontend/src/visual-tests.tsx`
- **Status**: Active Playwright visual test fixture file. Renders component fixtures (Board, LevelCard) in isolation for screenshot testing.
- **Issues**: Imports `Board` from `./components/Board` and `LevelCard` from `./components/Level/LevelCard` — both active components. References `STREAK_MILESTONES` from `services/streakManager` — active. References `BoardSize`, `Stone`, `SolutionMarker` types — need to verify all still match actual interfaces.

---

## 8. Cross-Reference Issues

| X-ID | Source Doc | Target Doc | Issue |
|------|-----------|------------|-------|
| X-1 | `README.md` → `docs/architecture/frontend/overview.md` | Target references deprecated `config-loader.ts` | Both need updating |
| X-2 | `README.md` → `docs/how-to/frontend/local-development.md` | Link exists | Verify target accuracy |
| X-3 | `README.md` → `docs/how-to/frontend/build-deploy.md` | Link exists | Verify target accuracy |
| X-4 | `CLAUDE.md` has no cross-references to `docs/` | Missing linkage | CLAUDE.md should reference architecture docs |
| X-5 | `overview.md` references `config-loader.ts` | Dead file (R-10) | Remove reference |
| X-6 | `sgf-processing.md` claims "single SGF parser" | Contradicted by `AGENTS.md` which correctly lists 3 SGF modules | Update sgf-processing.md |
| X-7 | `svg-board.md` says Canvas=default | `renderer-canvas-vs-svg-analysis.md` says SVG=default | Reconcile — one must be updated |
| X-8 | `sqlite-index-architecture.md` → "See also" references `system-overview.md` | Need to verify path | Verify link |
| X-9 | `snapshot-shard-terminology.md` → references `plan-composable-fragments-architecture.md` | May not exist (archived?) | Verify/remove |
| X-10 | `view-index-types.md` → references `view-index-schema.md` | Both may be stale | Both need review |

---

## 9. Missing Documentation

| M-ID | Topic | Current State | Priority |
|------|-------|---------------|----------|
| M-1 | SQLite data flow (boot → query → decode) | Only in AGENTS.md §4 and `sqlite-index-architecture.md`. Not in README or CLAUDE.md in sufficient detail | High |
| M-2 | `puzzleQueryService.ts` API reference | No dedicated doc. This is the primary query interface. | High |
| M-3 | `entryDecoder.ts` decode pipeline | Documented in AGENTS.md but not in architecture docs | Medium |
| M-4 | New page inventory (30+ pages exist) | AGENTS.md lists ~14, CLAUDE.md lists ~5 | High |
| M-5 | `GobanBoard/` vs `GobanContainer/` distinction | Neither CLAUDE.md nor README explains the two separate board component directories | Medium |
| M-6 | `PuzzleView/` directory (page + hooks) | Undocumented multi-file page pattern | Low |
| M-7 | Filter system (`usePuzzleFilters`, `useFilterState`, `useBrowseParams`) | Not documented in architecture docs | Medium |
| M-8 | `puzzleLoaders/` directory (separate from `puzzleLoaders.ts`) | Directory exists but no docs | Low |
| M-9 | Active `services/rulesEngine.ts` vs dead `lib/rules/` | Confusing dual existence not documented | Medium |
| M-10 | Feature flags system (`featureFlags.ts`) | Undocumented | Low |

---

## 10. External References

| R-ID | Source | Relevance |
|------|--------|-----------|
| E-1 | [OGS goban library](https://github.com/online-go/goban) | Core dependency — goban-integration.md is well-aligned |
| E-2 | [sql.js documentation](https://sql.js.org/) | WASM SQLite — sqlite-index-architecture.md covers this well |
| E-3 | Preact docs (preactjs.com) | Framework — no specific doc gaps |
| E-4 | Vite docs (vitejs.dev) | Build tool — JSON import pattern documented in overview.md |

---

## 11. Priority Ranking

| Priority | Action | Documents Affected | Effort |
|----------|--------|-------------------|--------|
| **P0** | **Rewrite README.md "Puzzle Data Sources"** — currently describes completely wrong architecture (JSON shards vs SQLite) | `frontend/README.md` | Medium |
| **P0** | **Rewrite README.md "Routes" table** — wrong component names throughout | `frontend/README.md` | Small |
| **P0** | **Rewrite README.md "Key Services"** — missing all SQLite services, has wrong filenames | `frontend/README.md` | Medium |
| **P1** | **Archive or deprecate `snapshot-shard-terminology.md`** — describes superseded architecture, will confuse agents | `docs/concepts/` | Small |
| **P1** | **Archive or deprecate `snapshot-deployment-topology.md`** — full ADR for replaced architecture | `docs/architecture/` | Small |
| **P1** | **Archive or deprecate `view-index-types.md`** — describes old JSON pagination system | `docs/architecture/frontend/` | Small |
| **P1** | **Fix `structure.md`** — references files that don't exist (`puzzleService.ts`, `progressService.ts`, `puzzle.ts`, `progress.ts`, `achievements.ts`) | `docs/architecture/frontend/` | Medium |
| **P1** | **Fix `overview.md` boot sequence** — references dead `config-loader.ts` | `docs/architecture/frontend/` | Small |
| **P2** | **Update AGENTS.md §1** — missing ~50% of actual files/directories | `frontend/src/AGENTS.md` | Large |
| **P2** | **Reconcile SVG vs Canvas default** — `svg-board.md` and `renderer-canvas-vs-svg-analysis.md` contradict | `docs/architecture/frontend/` | Small |
| **P2** | **Fix `puzzle-solving.md`** — describes non-existent interfaces, pre-goban validation flow | `docs/architecture/frontend/` | Medium |
| **P2** | **Fix `puzzle-modes.md`** — lists non-existent "Survival" mode, shows old JSON format | `docs/architecture/frontend/` | Medium |
| **P2** | **Fix `sgf-processing.md`** — "single parser" claim is wrong | `docs/architecture/frontend/` | Small |
| **P2** | **Fix `go-rules-engine.md`** — describes dead `lib/rules/` implementation | `docs/architecture/frontend/` | Medium |
| **P3** | **Update CLAUDE.md** — add missing sections for undocumented services, pages, lib dirs | `frontend/CLAUDE.md` | Medium |
| **P3** | **Update README.md "Project Structure"** — missing many directories and files | `frontend/README.md` | Medium |
| **P3** | **Verify `state-management.md`** — storage prefix may be wrong | `docs/architecture/frontend/` | Small |
| **P4** | **Add missing AGENTS.md entities/methods** (§2, §3) | `frontend/src/AGENTS.md` | Medium |
| **P4** | **Verify all how-to/frontend/ docs** — D-24 through D-31 | `docs/how-to/frontend/` | Medium |
| **P4** | **Verify reference docs** — D-32 through D-34 | `docs/reference/` | Small |

---

## 12. Planner Recommendations

1. **Batch P0 fixes immediately** — README.md is the most dangerous document. It describes a completely wrong architecture (JSON shards + manifest) that will mislead any agent or developer. The "Puzzle Data Sources", "Key Services", and "Routes" sections need full rewrites. Estimated: 3 files, ~200 lines changed.

2. **Archive 3 stale architecture docs in one pass** — `snapshot-shard-terminology.md`, `snapshot-deployment-topology.md`, and `view-index-types.md` all describe the pre-SQLite architecture. Move to `docs/archive/` or add prominent "SUPERSEDED" headers with pointers to `sqlite-index-architecture.md`. This prevents agent confusion without losing historical context.

3. **Schedule AGENTS.md refresh as a separate task** — AGENTS.md is missing ~50% of actual files but its existing content is accurate. This is a "completeness gap" not a "correctness crisis". Regenerate using `.github/prompts/regen-agents-map.prompt.md` as described in CLAUDE.md.

4. **Batch fix 6 stale architecture/frontend/ docs** — `structure.md`, `overview.md`, `puzzle-solving.md`, `puzzle-modes.md`, `sgf-processing.md`, `go-rules-engine.md` all have factual errors referencing non-existent files or describing wrong interfaces. Fix per P1-P2 priority.

---

## 13. Confidence and Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 88 |
| `post_research_risk_level` | medium |

**Confidence rationale**: High confidence on dead code identification (verified via grep), document accuracy assessment (read every referenced file), and priority ranking. Medium uncertainty on: how-to docs (D-24 through D-31 not yet read in detail), reference docs (D-32 through D-34), and some cross-reference link validity.

**Risk rationale**: Medium risk because README.md actively misleads with completely wrong architecture description. Any new contributor or agent reading it will assume JSON shards, manifest.json, and directory-based SGF organization — all of which are wrong. Until P0 items are fixed, documentation is a source of bugs, not prevention.

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/frontend-docs-gap-audit/
artifact: 15-research.md
top_recommendations:
  - "P0: Rewrite README.md (Puzzle Data Sources, Key Services, Routes) — describes completely wrong architecture"
  - "P1: Archive 3 stale pre-SQLite docs (snapshot-shard-terminology, snapshot-deployment-topology, view-index-types)"
  - "P1: Fix structure.md and overview.md — reference non-existent files"
  - "P2: Regenerate AGENTS.md — missing ~50% of actual file entries"
open_questions:
  - "Q1: Should stale docs be archived to docs/archive/ or marked deprecated in-place?"
  - "Q2: Should view-index-types.md be fully deleted or kept with deprecation notice (it documents JSON wire format still used by lib/puzzle/ loaders)?"
  - "Q3: Which docs/how-to/frontend/ guides need detailed audit (not yet read in full)?"
post_research_confidence_score: 88
post_research_risk_level: medium
```
