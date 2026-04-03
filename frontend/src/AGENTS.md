# Frontend (`frontend/src/`) — Agent Architecture Map

> Agent-facing reference. NOT user documentation. Dense structural facts only.
> _Last updated: 2026-03-29 | Trigger: Playing Modes DRY Compliance — migrated Rush and Random to PuzzleSetPlayer + SolverView, deleted InlineSolver/RushPuzzleRenderer/RushMode/5 dead pages_

---

## 1. Directory Structure

### Top-Level Files

| Path | Purpose |
|------|---------|
| `main.tsx` | Entry point — imports `boot()` |
| `boot.ts` | 5-step boot: fetchConfigs → cacheConfigs → cleanLegacy → initGoban → renderApp |
| `app.tsx` | Root `<App>` component — route state machine, renders pages based on `Route` union |
| `sw.ts` | Service worker registration |
| `vite-env.d.ts` | Vite type shims |

### `config/`

| Path | Purpose |
|------|---------|
| `config/constants.ts` | `APP_CONSTANTS` — all runtime paths, sounds, breakpoints |

### `constants/`

| Path | Purpose |
|------|---------|
| `constants/goQuotes.ts` | Random Go proverbs/tips for UI display |

### `contexts/`

| Path | Purpose |
|------|---------|
| `contexts/ThemeContext.tsx` | Preact context for dark/light theme |
| `contexts/index.ts` | Re-exports |

### `data/`

| Path | Purpose |
|------|---------|
| `data/learning-topics.ts` | Static learning topic definitions |

### `models/`

| Path | Purpose |
|------|---------|
| `models/puzzle.ts` | Legacy Puzzle/SolutionNode/Coordinate types (Besogo integer pattern) |
| `models/board.ts` | Board-related model types |
| `models/level.ts` | Level model types |
| `models/rush.ts` | Rush mode model types |
| `models/collection.ts` | Collection model types, `SkillLevel` |
| `models/dailyChallenge.ts` | Daily challenge mode types |
| `models/achievement.ts` | Achievement model types |
| `models/progress.ts` | Progress model types |
| `models/SolutionPresentation.ts` | Solution display model |

### `types/`

| Path | Purpose |
|------|---------|
| `types/puzzle-internal.ts` | `InternalPuzzle`, `SolutionNode` (SGF coord strings, 1-indexed), `Position` = `Coord` |
| `types/puzzle.ts` | Frontend puzzle display types (`Side`, `BoardRegion`, `PuzzleTag`) |
| `types/indexes.ts` | `LevelEntry`, `TagEntry`, `CollectionEntry`, `DailySchedule`, `DailyPuzzleEntry` |
| `types/progress.ts` | `UserPreferences`, `PuzzleCompletion`, `RushScore`, `AvgTimeByDifficulty` |
| `types/coordinate.ts` | `Coord` type (1-indexed x,y) |
| `types/goban.ts` | Goban-related types: `TransformSettings`, `RushDuration`, `RushPuzzle`, `RendererPreference` |
| `types/sgf.ts` | `ParsedSGF`, `SGFNode`, `SGFProperties`, `GameInfo`, `ISGFParser` |
| `types/tree.ts` | Solution tree view types |
| `types/board.ts` | Board display types |
| `types/level.ts` | Level types |
| `types/storage.ts` | localStorage schema types |
| `types/page-mode.ts` | Page mode discriminator types |
| `types/common.ts` | Shared utility types |
| `types/index.ts` | Re-exports |

### `services/` (25 files)

| Path | Purpose |
|------|---------|
| `services/sqliteService.ts` | `init()` fetches yengo-search.db → sql.js WASM, `query<T>()` executes SQL |
| `services/puzzleQueryService.ts` | SQL queries against DB-1: `getPuzzlesByLevel()`, `getPuzzlesFiltered()`, `getEditionCollections()`, `PuzzleRow`; all collection queries filter `parent_id IS NULL` |
| `services/entryDecoder.ts` | `DecodedEntry` type, `decodePuzzleRow()`, `expandPath()` |
| `services/puzzleLoader.ts` | `fetchSGFContent()` from CDN, `loadPuzzleFromPath()` → `InternalPuzzle` |
| `services/puzzleLoaders.ts` | `PuzzleSetLoader` interface + `StreamingPuzzleSetLoader`, 5 loaders: `CollectionPuzzleLoader`, `TrainingPuzzleLoader`, `DailyPuzzleLoader`, `RushPuzzleLoader`, `RandomPuzzleLoader` |
| `services/puzzleAdapter.ts` | `adaptToPagesPuzzle()` — InternalPuzzle → display Puzzle. **`adaptToLegacyPuzzle` removed** |
| `services/configService.ts` | ID↔slug resolution for levels, tags, quality. Re-exports from `lib/` configs |
| `services/solutionVerifier.ts` | `verifyMove()` — validates player moves against precomputed SolutionNode tree |
| `services/collectionService.ts` | Collection metadata queries against DB-1 |
| `services/dailyChallengeService.ts` | Daily challenge loading from `daily_schedule`/`daily_puzzles` tables |
| `services/dailyQueryService.ts` | SQL queries for daily challenge data |
| `services/puzzleGameState.ts` | Puzzle solving state machine |
| `services/puzzleRushService.ts` | Rush mode puzzle selection (`getNextRushPuzzle()`) |
| `services/progressTracker.ts` | Re-exports from `progress/` submodule |
| `services/progress/` | `storageOperations.ts`, `progressCalculations.ts`, `progressMigrations.ts` |
| `services/streakManager.ts` | Daily streak tracking |
| `services/achievementEngine.ts` | Achievement unlock logic |
| `services/tagsService.ts` | Tag definitions (`TagDefinition`) |
| `services/boardAnalysis.ts` | Board position analysis utilities |
| `services/audioService.ts` | Sound effects playback |
| `services/featureFlags.ts` | Feature flag checks |
| `services/retryQueue.ts` | Failed operation retry queue |
| `services/rulesEngine.ts` | Go rules validation |
| `services/progressAnalytics.ts` | Cross-references localStorage progress with SQLite tags for stats |

### `lib/` (15 subdirectories + standalone files)

| Path | Purpose |
|------|---------|
| `lib/sgf-parser.ts` | `parseSGF()` — FF4 SGF parser → `ParsedSGF` |
| `lib/sgf-solution.ts` | `buildSolutionTree()` — SGF → `SolutionNode` tree |
| `lib/sgf-to-puzzle.ts` | `sgfToPuzzle()` — SGF → OGS `PuzzleObject` (initial_state + move_tree) |
| `lib/sgf-metadata.ts` | `parseSgfToTree()` — canonical recursive-descent parser; metadata extraction |
| `lib/sgf-preprocessor.ts` | `preprocessSgf()` — clean/normalize raw SGF before parsing |
| `lib/puzzle-config.ts` | `buildPuzzleConfig()` — PuzzleObject → GobanConfig for renderer |
| `lib/goban-init.ts` | `initGoban()` — one-time goban library initialization |
| `lib/sgf/` | `coordinates.ts`, `parser.ts`, `solution-tree.ts`, `types.ts` |
| `lib/solver/` | `completion.ts`, `history.ts`, `parser.ts`, `traversal.ts`, `validator.ts` |
| `lib/routing/` | `routes.ts` (`Route` union, `parseRoute()`, `navigateTo()`), `canonicalUrl.ts` |
| `lib/quality/` | `config.ts` (`QualityMeta`, `QUALITIES`, `PuzzleQualityLevel`, parsers) |
| `lib/levels/` | `config.ts`, `types.ts`, `mapping.ts`, `migration.ts`, `constants.ts`, etc. |
| `lib/tags/` | `config.ts` — tag metadata from config JSON |
| `lib/hints/` | `progressive.ts`, `sgf-mapper.ts`, `sgf-progressive.ts`, `token-resolver.ts` |
| `lib/progress/` | `attempts.ts`, `challenges.ts`, `puzzles.ts`, `rush.ts`, `statistics.ts`, `timing.ts`, etc. |
| `lib/puzzle/` | `loader.ts`, `pagination.ts`, `utils.ts` |
| `lib/achievements/` | `checker.ts`, `definitions.ts`, `progress.ts` |
| `lib/rush/` | `queue.ts`, `scoring.ts`, `skip.ts`, `timer.ts`, `visibility.ts` |
| `lib/streak/` | `calculator.ts`, `reset.ts`, `tolerance.ts` |
| `lib/review/` | `controller.ts` |
| `lib/tree/` | `constants.ts`, `layout.ts`, `navigation.ts`, `svg-utils.ts` |
| `lib/presentation/` | `exploreHints.ts`, `numberedSolution.ts`, `viewportCalculator.ts` |
| `lib/auto-viewport.ts` | Auto-viewport calculation for board display |
| `lib/mark-tree.ts` | Move tree marking utilities |
| `lib/mastery.ts` | Mastery level calculation |
| `lib/accent-palette.ts` | UI accent color palette |
| `lib/accuracy-color.ts` | Accuracy → color mapping |
| `lib/getBoundsFromPuzzle.ts` | Board bounds extraction from puzzle data |
| `lib/levelRanks.ts` | Level rank display helpers |
| `lib/sanitizeComment.ts` | SGF comment sanitization |
| `lib/slug-formatter.ts` | Slug → display name formatting |

### `hooks/` (30+ hooks)

| Path | Purpose |
|------|---------|
| `hooks/useGoban.ts` | **Core**: SGF → sgfToPuzzle → buildPuzzleConfig → instantiate goban renderer |
| `hooks/usePuzzleState.ts` | Puzzle solving state management |
| `hooks/useTransforms.ts` | Board rotation/flip transforms |
| `hooks/useBoardMarkers.ts` | Board marker overlays |
| `hooks/useBoardViewport.ts` | Viewport/zoom controls |
| `hooks/useHints.ts` | Progressive hint reveal |
| `hooks/useRushSession.ts` | Rush mode session management |
| `hooks/useExploreMode.ts` | Post-solve free exploration |
| `hooks/useSolutionAnimation.ts` | Animated solution playback |
| `hooks/useSolutionTreeKeyboard.ts` | Keyboard nav for solution tree view |
| `hooks/useTreeKeyboard.ts` | General tree keyboard navigation |
| `hooks/useTreeNavigation.ts` | Tree node navigation |
| `hooks/useFilterParams.ts` | URL filter parameter sync |
| `hooks/useFilterState.ts` | Filter state management |
| `hooks/usePuzzleFilters.ts` | Puzzle filter composition |
| `hooks/useBrowseParams.ts` | Browse page URL params |
| `hooks/usePaginatedPuzzles.ts` | Paginated puzzle list loading |
| `hooks/useProgressTracker.ts` | Progress tracking hook |
| `hooks/useStreak.ts` | Streak tracking hook |
| `hooks/useAutoAdvance.ts` | Auto-advance to next puzzle |
| `hooks/useCanonicalUrl.ts` | Canonical URL management |
| `hooks/useContentType.ts` | Content type filters |
| `hooks/useDebounce.ts` | Debounce utility hook |
| `hooks/useMediaQuery.ts` | Responsive breakpoint hook |
| `hooks/useNavigationContext.ts` | Navigation context data |
| `hooks/usePrefetch.ts` | Prefetch SGF for next puzzle |
| `hooks/useSettings.ts` | User settings (also exports `cleanLegacyKeys` for boot) |
| `hooks/useShardFilters.ts` | Shard-based filter state |
| `hooks/useMasterIndexes.ts` | Master index data loading |

### `components/` (40 directories/files)

| Path | Purpose |
|------|---------|
| `components/GobanContainer/` | Mounts goban's self-created DOM element via `PersistentElement` |
| `components/GobanBoard/` | `GobanBoard.tsx`, `GobanRenderer.tsx` — board display wrapper |
| `components/Solver/` | `SolverView.tsx` (supports `minimal` mode: board-only, no sidebar), `HintOverlay.tsx`, `MoveExplorer.tsx`, `SolutionReveal.tsx` |
| `components/PuzzleView/` | `HintButton.tsx`, `Success.tsx` |
| `components/Hints/` | `HintPanel.tsx` |
| `components/SolutionTree/` | Solution tree visualization |
| `components/Review/` | Post-solve review UI |
| `components/Board/` | Board-related sub-components |
| `components/PuzzleList/` | Puzzle list display |
| `components/PuzzleNavigation/` | Prev/next puzzle navigation |
| `components/ProblemNav/` | Problem navigation controls |
| `components/QuickControls/` | Transform/zoom quick action bar |
| `components/Transforms/` | Rotation/flip UI controls |
| `components/Rush/` | `RushOverlay.tsx` — HUD overlay (timer, lives, score). RushMode.tsx and RushPuzzleRenderer.tsx deleted; Rush uses PuzzleSetPlayer now |
| `components/PuzzleRush/` | Rush mode wrapper (legacy, mostly unused — page logic moved to PuzzleRushPage thin wrapper) |
| `components/PuzzleSetPlayer/` | Unified sequential puzzle player — used by Collection, Daily, Training, Rush, Random, Technique, Smart Practice, Quality modes. Supports `StreamingPuzzleSetLoader`, `failOnWrongDelayMs`, `autoAdvanceEnabled`, `minimal` props |
| `components/DailyChallenge/` | Daily challenge UI |
| `components/ChallengeList/` | Challenge listing |
| `components/RandomChallenge/` | Random puzzle challenge UI (legacy — page logic now in RandomChallengePage thin wrapper) |
| `components/Collections/` | Collection browsing UI; includes `EditionPicker` for multi-source collection editions |
| `components/TechniqueFocus/` | Technique-focused practice UI |
| `components/Training/` | Training mode UI |
| `components/Achievements/` | Achievement display |
| `components/Streak/` | Streak display |
| `components/Progress/` | Progress visualization |
| `components/Stats/` | Statistics display |
| `components/Level/` | Level selector/display |
| `components/Home/` | Home page components |
| `components/Layout/` | `AppHeader` and layout shells |
| `components/Boot/` | `BootLoading`, `BootError` screens |
| `components/Loading/` | Loading spinners/skeletons |
| `components/Feedback/` | User feedback UI |
| `components/Settings/` | Settings panel |
| `components/shared/` | Reusable: `Button`, `Modal`, `FilterBar`, `ErrorBoundary`, `AnswerBanner`, etc. |
| `components/shared/icons/` | 47 SVG icon components (no emojis in production UI) |
| `components/ComplexityIndicator.tsx` | Complexity badge |
| `components/QualityBadge.tsx` | Quality star badge |
| `components/QualityBreakdown.tsx` | Quality detail breakdown |
| `components/QualityFilter.tsx` | Quality filter dropdown |

### `pages/` (28 files)

| Path | Purpose |
|------|---------|
| `pages/HomePage.tsx` | Home page |
| `pages/HomePageGrid.tsx` | Grid layout for home |
| `pages/PuzzleView.tsx` | Puzzle view wrapper |
| `pages/PuzzleView/` | Puzzle view sub-components |
| `pages/CollectionViewPage.tsx` | Single collection view; detects parent collections with editions → shows EditionPicker |
| `pages/CollectionsBrowsePage.tsx` | Browse all collections; editions hidden via `parent_id IS NULL` filter |
| `pages/DailyChallengePage.tsx` | Daily challenge solving |
| `pages/DailyBrowsePage.tsx` | Browse daily challenges |
| `pages/PuzzleRushPage.tsx` | Rush mode — thin wrapper around PuzzleSetPlayer with RushPuzzleLoader, useRushSession, RushOverlay, countdown/finished screens |
| `pages/RushBrowsePage.tsx` | Browse rush modes |
| `pages/TechniqueFocusPage.tsx` | Technique practice |
| `pages/TechniqueBrowsePage.tsx` | Browse techniques |
| `pages/TechniqueViewPage.tsx` | Single technique view |
| `pages/TrainingBrowsePage.tsx` | Browse training levels |
| `pages/TrainingSelectionPage.tsx` | Training selection |
| `pages/TrainingViewPage.tsx` | Single training view |
| `pages/RandomPage.tsx` | Random puzzle page |
| `pages/RandomChallengePage.tsx` | Random challenge — thin wrapper around PuzzleSetPlayer with RandomPuzzleLoader |
| `pages/SmartPracticePage.tsx` | AI-free smart practice (weakness targeting) |
| `pages/ProgressPage.tsx` | Progress overview |
| `pages/StatsPage.tsx` | Statistics page |
| `pages/AchievementsPage.tsx` | Achievements page |
| `pages/LearningPage.tsx` | Learning topics |
| `pages/LearningTopicPage.tsx` | Single learning topic |
| `pages/MyCollectionsPage.tsx` | User collections |

### `styles/` (15 CSS files)

Global CSS: `app.css`, `global.css`, `theme.css`, `colors.css`, `responsive.css`, `board.css`, `board-svg.css`, `buttons.css`, `focus.css`, `level.css`, `presentation.css`, `progress.css`, `scrollbars.css`, `tailwind.css`, `touch.css`.

### `utils/`

| Path | Purpose |
|------|---------|
| `utils/coordinates.ts` | SGF ↔ grid coordinate conversions (`sgfToPosition`, `positionToSgf`) |
| `utils/storage.ts` | localStorage wrappers with error handling |
| `utils/sanitize.ts` | Input sanitization |
| `utils/safeFetchJson.ts` | fetch() wrapper with error handling |
| `utils/accessibility.ts` | ARIA/a11y helpers |
| `utils/sound.ts` | Sound playback utilities |
| `utils/statusMapping.ts` | Puzzle status → display mapping |

---

## 2. Core Entities

| Type | Location | Key Fields | Represents |
|------|----------|-----------|------------|
| `DecodedEntry` | `services/entryDecoder.ts` | `path`, `level`, `tags`, `complexity`, `quality`, `contentType`, `ac` | Decoded puzzle metadata from SQLite row |
| `PuzzleRow` | `services/puzzleQueryService.ts` | `content_hash`, `batch`, `level_id`, `quality`, `cx_*`, `ac` | Raw row from `puzzles` table |
| `InternalPuzzle` | `types/puzzle-internal.ts` | `size`, `blackStones`, `whiteStones`, `solutionTree`, `sideToMove` | Parsed puzzle after SGF processing |
| `SolutionNode` | `types/puzzle-internal.ts` | `move`, `player`, `isCorrect`, `isUserMove`, `children`, `comment` | Node in precomputed solution tree |
| `PuzzleObject` | `lib/sgf-to-puzzle.ts` | `initial_state`, `move_tree`, `width`, `height`, `initial_player` | OGS-compatible format for goban |
| `MoveTreeJson` | `lib/sgf-to-puzzle.ts` | `x`, `y`, `trunk_next`, `branches`, `correct_answer`, `wrong_answer` | Recursive move tree for goban |
| `Route` | `lib/routing/routes.ts` | Discriminated union: `home`, `context`, `modes-*`, `progress`, etc. | All app URLs as typed union |
| `QualityMeta` | `lib/quality/config.ts` | `id`, `slug`, `stars`, `description`, `selectionWeight` | Quality level metadata |
| `LevelMeta` | `lib/levels/config.ts` | `id`, `slug`, `name`, `rankRange`, `order` | Difficulty level metadata |
| `TagMeta` | `lib/tags/config.ts` | `id`, `slug`, `name`, `category` | Technique tag metadata |
| `ParsedSGF` | `types/sgf.ts` | `root`, `gameInfo`, `nodes` | Result of SGF parsing |
| `SgfNode` | `lib/sgf-metadata.ts` | `properties`, `children` | Internal SGF tree node (canonical parser) |
| `BootConfigs` | `boot.ts` | `levels`, `tags`, `tips` | Cached config data from boot |
| `UserPreferences` | `types/progress.ts` | `hintsEnabled`, `soundEnabled`, `boardTheme`, `coordinatesVisible` | User settings in localStorage |
| `PuzzleCompletion` | `types/progress.ts` | `puzzleId`, `completedAt`, `timeSpentMs`, `attempts`, `hintsUsed` | Single puzzle completion record |
| `GobanInstance` | `hooks/useGoban.ts` | Union of `SVGRenderer` / `GobanCanvas` | Active goban renderer instance |
| `VerificationResult` | `services/solutionVerifier.ts` | `isCorrect`, `isComplete`, `feedback`, `responseMove` | Move validation result |

---

## 3. Key Methods & Call Sites

| Function | Location | Called By |
|----------|----------|-----------|
| `boot()` | `boot.ts` | `main.tsx` (entry point) |
| `sqliteService.init()` | `services/sqliteService.ts` | `app.tsx` on mount |
| `query<T>(sql, params)` | `services/sqliteService.ts` | `puzzleQueryService`, `dailyQueryService`, `collectionService` |
| `getPuzzlesByLevel()` | `services/puzzleQueryService.ts` | `app.tsx`, `usePaginatedPuzzles` |
| `getPuzzlesFiltered()` | `services/puzzleQueryService.ts` | `app.tsx`, filter hooks |
| `decodePuzzleRow()` | `services/entryDecoder.ts` | `puzzleLoaders.ts` |
| `expandPath()` | `services/entryDecoder.ts` | `puzzleLoaders.ts`, puzzle loading |
| `fetchSGFContent(path)` | `services/puzzleLoader.ts` | `puzzleLoaders.ts`, `lib/puzzle/loader.ts` |
| `parseSGF(sgf)` | `lib/sgf-parser.ts` | `puzzleLoader.ts` |
| `buildSolutionTree(root, side)` | `lib/sgf-solution.ts` | `puzzleLoader.ts` |
| `parseSgfToTree(sgf)` | `lib/sgf-metadata.ts` | `sgf-to-puzzle.ts`, `sgf-preprocessor.ts` |
| `sgfToPuzzle(sgf)` | `lib/sgf-to-puzzle.ts` | `useGoban` hook |
| `preprocessSgf(rawSgf)` | `lib/sgf-preprocessor.ts` | `useGoban` hook |
| `buildPuzzleConfig(puzzle)` | `lib/puzzle-config.ts` | `useGoban` hook |
| `verifyMove(state, move, color)` | `services/solutionVerifier.ts` | `usePuzzleState`, `Solver` components |
| `parseRoute(pathname, search)` | `lib/routing/routes.ts` | `app.tsx` (route state machine) |
| `navigateTo(route)` | `lib/routing/routes.ts` | Pages, navigation components |
| `recordPuzzleCompletion()` | `services/progressTracker.ts` | `usePuzzleState`, solve handlers |
| `initializeProgressSystem()` | `services/progressTracker.ts` | `app.tsx` useEffect |
| `adaptToPagesPuzzle()` | `services/puzzleAdapter.ts` | Page components |

---

## 4. Data Flow

### Boot Sequence
```
main.tsx → boot()
  1. fetchConfigs  → fetch puzzle-levels.json, tags.json, go-tips.json
  2. cacheConfigs  → store in module-level singleton
  3. cleanLegacy   → delete old localStorage keys (non-fatal)
  4. initGoban     → initialize goban library callbacks
  5. renderApp     → render <App /> into #app
```

### Database Initialization
```
App mount → sqliteService.init()
  → fetch yengo-search.db (~500KB static file)
  → initSqlJs({ locateFile: () => sql-wasm.wasm })
  → new SQL.Database(buffer)
  → in-memory SQLite ready for queries
```

### Puzzle Discovery (SQL Path)
```
User navigates to level/tag/collection
  → puzzleQueryService.getPuzzlesByLevel(levelId)
  → sqliteService.query<PuzzleRow>(SQL)
  → decodePuzzleRow(row) → DecodedEntry { path, level, tags, complexity }
  → UI renders puzzle list
```

### Puzzle Loading & Solving
```
User clicks puzzle
  → expandPath("0001/abc123") → "sgf/0001/abc123.sgf"
  → fetchSGFContent(path) → fetch from CDN → raw SGF string
  → Two parallel paths:
     A) Board: preprocessSgf() → sgfToPuzzle() → PuzzleObject → buildPuzzleConfig() → goban
     B) Meta: parseSgfToTree() → extract YG/YT/YH/YC → sidebar display
  → useGoban: instantiate SVGRenderer/GobanCanvas with GobanConfig
  → GobanContainer mounts goban's self-created DOM element
  → User plays move → verifyMove() against SolutionNode tree
  → Correct: animate response, advance tree
  → Wrong: show wrong banner, allow retry
  → Complete: recordPuzzleCompletion() → localStorage
```

### Data Flow Summary
```
yengo-search.db ──→ sql.js WASM ──→ SQL queries ──→ DecodedEntry[]
                                                         │
                     CDN: sgf/{batch}/{hash}.sgf ◄───────┘
                          │
                          ▼
                    Raw SGF string
                     ┌────┴────┐
                     ▼         ▼
              sgfToPuzzle()  parseSgfToTree()
                     │         │
                     ▼         ▼
              PuzzleObject   Metadata (level, tags, hints)
                     │
                     ▼
              GobanConfig → goban renderer → DOM
                                    │
                          user move ─┘
                                    │
                          verifyMove() ← SolutionNode tree
                                    │
                          progressTracker → localStorage
```

---

## 5. External Dependencies

| Library | Used For |
|---------|----------|
| `goban` | OGS Go board library — SVG/Canvas rendering, puzzle mode, move tree |
| `sql.js` | SQLite compiled to WASM — in-browser SQL queries against yengo-search.db |
| `preact` | UI framework (h, render, hooks) |
| `preact/hooks` | useState, useEffect, useRef, useCallback, useMemo |
| `vite` | Build tool, dev server, JSON imports, `import.meta.env` |

---

## 6. Known Gotchas

- **GobanContainer pattern**: Goban creates its own DOM element internally. `GobanContainer` mounts it via `PersistentElement` — never pass a ref to goban for rendering. See `components/GobanContainer/`.
- **Read-only SQLite**: Browser never writes to yengo-search.db. All user data goes to localStorage only.
- **Two SGF parsers**: `lib/sgf-parser.ts` (`parseSGF()`) produces `ParsedSGF` for solution tree building. `lib/sgf-metadata.ts` (`parseSgfToTree()`) produces `SgfNode` for metadata extraction and PuzzleObject conversion. They serve different purposes — don't unify.
- **Coordinate systems**: Goban uses (x,y) 0-indexed. SGF uses letter pairs `aa`-`ss`. `types/coordinate.ts` `Coord` is 1-indexed (Besogo pattern). Use `utils/coordinates.ts` for conversions.
- **Quality scale**: Stars 1=unassigned (worst) → 5=premium (best). IDs are numeric in DB, slugs in display.
- **Level IDs**: Numeric 110–230 in SQLite, slugs ("novice"→"expert") in display. Resolution only via `configService.ts`.
- **Config is build-time**: Level/tag/quality configs imported from JSON via Vite — inlined at build, not fetched at runtime. Boot fetches `puzzle-levels.json`, `tags.json`, `go-tips.json` separately for display names/tips.
- **Route-based puzzle solving**: App uses a single `<App>` component with `Route` union state machine — no router library. `parseRoute()` + `popstate` listener handles navigation.
- **PuzzleSetPlayer is the universal puzzle player**: All 8 playing modes (Collection, Daily, Training, Rush, Random, Technique, Smart Practice, Quality) use PuzzleSetPlayer. Pages are thin wrappers providing `renderHeader`, `renderSummary`, and a `PuzzleSetLoader` (or `StreamingPuzzleSetLoader` for infinite modes like Rush/Random). Rush uses `minimal=true` + `failOnWrongDelayMs=100` + `autoAdvanceEnabled=false`. InlineSolver was deleted — do not recreate separate board rendering.
- **CollectionsBrowsePage v2**: 3 sections (Learning Paths, Practice, Books) configured via `SECTION_DEFS` in `constants/collectionConfig.ts`. Shuffle policy per section via `SHUFFLE_POLICY`. In-section search uses `searchCollectionsByTypes()` from `puzzleQueryService` (DB-scoped FTS). Collections with <15 puzzles are filtered. Sections require ≥2 collections to be visible. Hover treatment uses ring-based color instead of translateY bounce.
- **Sound preloading**: `audioService.preload()` runs at module load in `app.tsx` — before any user interaction. Uses `AudioContext` which may require user gesture on some browsers.
- **Progress system init**: `initializeProgressSystem()` runs in a `useEffect` inside `<App>`, not at module scope, to avoid boot ordering issues.
- **SGF preprocessing**: `preprocessSgf()` must run before `sgfToPuzzle()`. It normalizes encoding, strips problematic properties, and ensures valid FF4 format.
- **CDN path**: All SGF/DB fetches use `APP_CONSTANTS.paths.cdnBase` (derived from `import.meta.env.BASE_URL`). In dev: `/yen-go/yengo-puzzle-collections/`. In prod: same via GitHub Pages base path.
