# Frontend

Preact + TypeScript web app for solving Go tsumego puzzles. See root `CLAUDE.md` for project-wide constraints and SGF schema.

## Stack

- **Language**: TypeScript 5.3+ (`strict: true`, ES2020 target)
- **Framework**: Preact 10.x (lightweight, React-compatible)
- **Build**: Vite 5.x
- **Styling**: Tailwind CSS 4.x (via `@tailwindcss/vite`) + CSS custom properties for theming
- **Board**: `goban` library (Canvas/SVG rendering with theme support)
- **Testing**: Vitest (unit), Playwright (E2E/visual)

## Commands

```bash
npm run dev          # Dev server at :5173/yen-go/
npm test             # Vitest unit tests
npm run lint         # ESLint
npm run build        # Production build
```

## Base Path & SPA Routing (GitHub Pages)

The app is deployed to GitHub Pages at `https://{user}.github.io/yen-go/`. All URLs use the `/yen-go/` base path — both locally and in production.

### How it works

| Concern               | Mechanism                                                                                           |
| --------------------- | --------------------------------------------------------------------------------------------------- |
| **Base path**         | `base: '/yen-go/'` in `vite.config.ts` → `import.meta.env.BASE_URL` = `'/yen-go/'`                  |
| **Asset URLs**        | Vite auto-prefixes built JS/CSS/HTML `href`/`src` with base                                         |
| **Data fetch URLs**   | `APP_CONSTANTS` in `config/constants.ts` derives paths from `import.meta.env.BASE_URL`              |
| **Route parsing**     | `parseRoute()` strips base prefix before matching; `serializeRoute()` prepends it                   |
| **SPA deep links**    | `public/404.html` redirects to `/?p=...`; inline script in `index.html` restores via `replaceState` |
| **In-app navigation** | `navigateTo()` uses `pushState` with base-prefixed URLs (client-side, no server)                    |

### Key files

| File                          | Role                                                                 |
| ----------------------------- | -------------------------------------------------------------------- |
| `vite.config.ts`              | `base: '/yen-go/'` — single source of truth for base path            |
| `src/config/constants.ts`     | All data/sound/config paths prefixed with `import.meta.env.BASE_URL` |
| `src/lib/routing/routes.ts`   | `parseRoute` strips base; `serializeRoute` prepends base             |
| `index.html`                  | SPA redirect receiver (reads `?p=` from 404 redirect, restores path) |
| `public/404.html`             | GitHub Pages SPA redirect (encodes path as `?p=` query param)        |
| `public/manifest.webmanifest` | PWA paths use `/yen-go/` prefix                                      |
| `src/sw.ts`                   | Service worker static assets use `/yen-go/` prefix                   |

### Adding the base path to new code

- **Fetch URLs**: Use `APP_CONSTANTS.paths.*` or `APP_CONSTANTS.config.*` — never hardcode `/config/...`
- **Route URLs**: Use `serializeRoute()` — never hardcode `/training` or `/contexts/...`
- **Static assets**: Use `import.meta.env.BASE_URL` prefix
- **HTML `<a>` tags**: Use `href={import.meta.env.BASE_URL}` not `href="/"`

## Key Directories

```
src/
  components/        # UI components (40+ dirs/files)
    GobanBoard/      # SVG/Canvas board rendering via goban library
    GobanContainer/  # Mounts goban's self-created DOM element (OGS pattern)
    Solver/          # Puzzle solving UI
    Transforms/      # Board transform controls
    shared/          # Shared icons, buttons, layout primitives
    ...              # Achievements, Collections, DailyChallenge, Hints, etc.
  pages/             # Route pages (30+ pages, see Pages section below)
  services/          # Business logic (25 files, see Services section below)
  lib/               # Core logic modules
    achievements/    # Achievement definitions and evaluation
    hints/           # Hint system (3-tier progressive reveal)
    levels/          # Level config (Vite JSON import - config/puzzle-levels.json)
    presentation/    # Display/formatting helpers
    progress/        # Progress tracking logic
    puzzle/          # Puzzle data structures and helpers
    quality/         # Quality config (Vite JSON import - config/puzzle-quality.json)
    review/          # Review mode logic
    routing/         # Client-side routing (parseRoute, serializeRoute)
    rush/            # Rush mode logic
    sgf/             # SGF format utilities
    solver/          # Solver engine logic
    streak/          # Streak calculation
    tags/            # Tag config (Vite JSON import - config/tags.json)
    tree/            # Move tree traversal and manipulation
  models/            # Data models / TypeScript types
  types/             # Additional type definitions
  hooks/             # Custom Preact hooks
  utils/             # Utility functions
  config/            # Frontend config (constants, paths)
  constants/         # App-wide constant values
  contexts/          # Preact context providers
  data/              # Static data files
  styles/            # Global styles
```

## Pages (by category)

| Category | Pages |
| --- | --- |
| Home | `HomePage.tsx`, `HomePageGrid.tsx` |
| Collections | `CollectionsBrowsePage.tsx`, `CollectionsPage.tsx`, `CollectionViewPage.tsx`, `MyCollectionsPage.tsx` |
| Daily | `DailyBrowsePage.tsx`, `DailyChallengePage.tsx` |
| Puzzle | `PuzzleSolvePage.tsx`, `PuzzleView.tsx`, `PuzzleView/` (directory) |
| Rush | `PuzzleRushPage.tsx`, `RushBrowsePage.tsx`, `RushPage.tsx` |
| Random | `RandomChallengePage.tsx`, `RandomPage.tsx` |
| Review | `ReviewPage.tsx` |
| Technique | `TechniqueBrowsePage.tsx`, `TechniqueFocusPage.tsx`, `TechniqueViewPage.tsx` |
| Training | `TrainingBrowsePage.tsx`, `TrainingPage.tsx`, `TrainingSelectionPage.tsx`, `TrainingViewPage.tsx` |
| Smart Practice | `SmartPracticePage.tsx` |
| Progress/Stats | `ProgressPage.tsx`, `StatsPage.tsx` |
| Achievements | `AchievementsPage.tsx` |
| Learning | `LearningPage.tsx`, `LearningTopicPage.tsx` |

## Services

| Category | File | Purpose |
| --- | --- | --- |
| Core data | `sqliteService.ts` | sql.js WASM DB initialization and query execution |
| Core data | `puzzleQueryService.ts` | SQL-based puzzle filtering (level, tag, collection) |
| Core data | `entryDecoder.ts` | Decode compact DB entries to puzzle metadata |
| Core data | `configService.ts` | Numeric ID to slug resolution facade |
| Daily | `dailyQueryService.ts` | Query daily_schedule/daily_puzzles tables |
| Daily | `dailyChallengeService.ts` | Daily challenge orchestration |
| Puzzle loading | `puzzleLoader.ts` | Single puzzle SGF fetch and parse |
| Puzzle loading | `puzzleLoaders.ts` | Batch/set puzzle loading strategies |
| Puzzle loading | `puzzleAdapter.ts` | Adapt raw puzzle data to UI format |
| Game logic | `solutionVerifier.ts` | Validate moves against solution tree |
| Game logic | `boardAnalysis.ts` | Board position analysis utilities |
| Game logic | `puzzleGameState.ts` | Puzzle session state machine |
| Game logic | `rulesEngine.ts` | Go rules enforcement |
| Rush | `puzzleRushService.ts` | Rush mode scoring and lifecycle |
| Progress | `progressTracker.ts` | localStorage progress read/write |
| Progress | `progressAnalytics.ts` | Progress statistics and trends |
| Progress | `streakManager.ts` | Daily streak tracking |
| Progress | `achievementEngine.ts` | Achievement evaluation and unlock |
| Collections | `collectionService.ts` | Collection browsing and membership |
| Other | `audioService.ts` | Sound playback |
| Other | `featureFlags.ts` | Feature flag checks |
| Other | `retryQueue.ts` | Failed operation retry |
| Other | `tagsService.ts` | Tag lookup and filtering |

## Config Architecture

Level, tag, and quality metadata is loaded from `config/*.json` via **Vite JSON imports** (build-time inlined, tree-shakeable). No code generation step required.

| Config File | Module | Provides |
|---|---|---|
| `config/puzzle-levels.json` | `lib/levels/config.ts` | `LEVELS`, `LevelSlug`, ID↔slug maps |
| `config/tags.json` | `lib/tags/config.ts` | `TAGS`, `TagSlug`, ID↔slug maps |
| `config/puzzle-quality.json` | `lib/quality/config.ts` | `QUALITIES`, `QualitySlug`, ID↔slug maps |

`services/configService.ts` is the single facade for numeric ID ↔ slug resolution (imports from the modules above).

**To add/change a level, tag, or quality**: edit the config JSON file, rebuild. No scripts to run.

## Runtime Constraints

- NO server API calls -- fetch static SGF/JSON files only
- NO AI or move computation -- validate against pre-computed solution trees
- NO blocking computation >100ms
- All user data in `localStorage` only
- Graceful degradation when localStorage unavailable

## Design Philosophy (Apple-Inspired Minimalism)

**Visual**: Content-first, minimal chrome. System fonts, muted earthy tones for board, subtle grays for UI. Generous whitespace. Soft shadows for depth.

**Interaction**: Direct manipulation (board, not dialogs). Immediate visual feedback (shake, glow). Progressive disclosure. Keyboard-accessible solution tree and puzzle controls. Responsive across desktop/tablet/mobile.

**Feedback Patterns**:

- Success: Subtle green indicators, no celebratory animations
- Incorrect: Brief shake animation, no intrusive popups
- Hints: Progressive system (Level 1: text, Level 2: area highlight, Level 3: exact coordinate)
- Loading: Skeleton states preferred over spinners

**Do NOT**:

- Use modal dialogs for simple feedback
- Use colored borders for error states
- Write text-heavy instructions
- Show multiple competing calls-to-action
- Use emoji in functional UI

## Board Rendering (Goban Integration)

Uses `goban` NPM library for all board rendering. **Zero modifications to the goban package** — all customization via callbacks, config, CSS, and the adapter layer.

### OGS-Native Puzzle Format

```
Raw SGF → sgfToPuzzle() → PuzzleObject (initial_state + move_tree) → goban
Raw SGF → parseSgfToTree() → metadata     (sidebar: level, tags, hints, collections)
```

SGF is converted to structured PuzzleObject via `sgfToPuzzle()`. Goban receives
`initial_state`, `move_tree`, `width`, `height`, `initial_player` — zero monkey-patches.
`correct_answer`/`wrong_answer` flags baked into MoveTreeJson from `C[]` comments.

### Key Files

| File                         | Purpose                                                         |
| ---------------------------- | --------------------------------------------------------------- |
| `lib/goban-init.ts`          | One-time goban callbacks (themes, sounds, CDN)                  |
| `lib/puzzle-config.ts`       | Build GobanConfig with PuzzleObject (initial_state + move_tree) |
| `lib/sgf-preprocessor.ts`    | SGF adaptation layer                                            |
| `lib/sgf-to-puzzle.ts`       | SGF→puzzle object adapter                                       |
| `hooks/useGoban.ts`          | Goban lifecycle hook (no boardRef)                              |
| `hooks/useBrowseParams.ts`   | URL param sync for browse pages (read-merge-write pattern)      |
| `components/GobanContainer/` | Mount goban's self-created div (OGS pattern)                    |

### Board Theme

- Board: `"Custom"` with `customBoardColor`/`customBoardLineColor` callbacks (no CDN texture)
- Stones: Shell (white) + Slate (black)
- Light mode board: `#E3C076`, dark mode: `#2a2520`
- Grid lines: `#4a3c28` (light), `#8b7355` (dark)

### Audio

Stone sounds handled by goban's built-in audio. `usePuzzleState` only plays correct/wrong/complete sounds.

### Goban Upgradability

Upgrading goban v8→v9 affects only 4 files: `puzzle-config.ts`, `useGoban.ts`, `goban-init.ts`, `types/goban.ts`.

## Puzzle Solver Architecture

### SolverView Sidebar Layout (top to bottom)

1. ProblemNav — puzzle dots + progress + streak
2. Metadata — level pills + technique tags + collection pills
3. TransformBar — 8 icon-only buttons (flip, rotate, swap, zoom, coords)
4. Hints — progressive reveal (3 tiers) + board marking on tier 3
5. Comments — root comment (initial) or move comment (after moves)
6. Action bar — Prev | Undo | Reset | Next | Review
7. Feedback — inline correct/wrong banner
8. Solution tree — visible only in review mode or after wrong answer

### Transform Pipeline

Transforms physically rewrite ALL SGF coordinates before passing to goban. Order: rotation→flip→color swap. The goban receives a self-consistent SGF.

### Design Decisions (Non-Negotiable)

1. **No emojis in production UI** — All icons are SVG components from `components/shared/icons/`
2. **No goban package modifications** — Customize via callbacks, config, CSS, events, adapter layer only
3. **OGS alignment** — Follow OGS patterns; deviate only with documented justification
4. **Solution tree gating** — Hidden until wrong move or explicit review. No spoilers.
5. **Action buttons are icon-only** with `aria-label` tooltips (except Review which has text)
6. **Dead code policy** — Delete, don't deprecate. Git history preserves everything.
7. **Visual regression testing** — Every UI change needs before/after Playwright screenshots
8. **Dirty text in comments** — Escape HTML, unescape SGF escapes, convert `\n` to `<br>`. Never render as markdown.
9. **Git safety** — Never `git add .`, never `git stash`, stage by explicit path only
10. **No Emdashes or non ascii characters in markdown** - For example use hyphens `-` instead of emdashes `—` to avoid encoding issues in markdown files (docs/, backend/puzzle_manager/AGENTS.md, etc.)


## Rush Play Mode

Timed challenge: solve as many puzzles as possible before time runs out or all 3 lives are lost.

### Architecture

- `RushBrowsePage` — Setup screen with duration cards, custom slider (1–30 min), level FilterBar, tag FilterDropdown, available count indicator
- `PuzzleRushPage` — Game mode: countdown → playing → finished states
- `useRushSession` — Timer, score, streak, lives management
- `RushOverlay` — In-game HUD (timer, lives, score, streak)
- `app.tsx::getNextPuzzle()` — Puzzle fetching with level/tag filtering

### Puzzle Loading Strategy

Puzzle queries are resolved via SQL against an in-memory SQLite database (`yengo-search.db`) loaded at startup via sql.js WASM.

| Filter      | SQL Pattern                                                        |
| ----------- | ------------------------------------------------------------------ |
| Level + Tag | `JOIN puzzle_tags WHERE level_id = ? AND tag_id = ?`               |
| Level only  | `WHERE level_id = ?`                                               |
| Tag only    | `JOIN puzzle_tags WHERE tag_id = ?`                                |
| Collection  | `JOIN puzzle_collections WHERE collection_id = ?`                  |
| Neither     | Random level from `SKILL_LEVELS`                                   |

### Key Decisions

- Rush does NOT use `PuzzleSetPlayer` — own state machine, timer, HUD
- `RushDuration` is `number` (seconds, 60–1800), not a fixed union
- Filters use `puzzleQueryService` for SQL-based queries
- Pool deduplication via `usedPuzzleIds` Set; resets when exhausted
- Custom duration: non-linear slider (30s steps 1–5 min, 60s steps 5–30 min)

## Puzzle Solving Flow

1. Fetch puzzle SGF from static files
2. Extract metadata via `preprocessSgf()` (tree parser, no regex), convert SGF to PuzzleObject via `sgfToPuzzle()`
3. Render board via goban (GobanContainer mounts goban's self-created div)
4. User places stone → validate against solution tree (deterministic tree traversal)
5. Show opponent response from solution tree
6. Track progress in localStorage

## Testing

- **Unit**: Vitest with jsdom. Tests in `tests/` directory.
- **E2E**: Playwright. Config at `playwright.config.ts`.
- Run `npm test` for unit tests before submitting changes.

---

*Last Updated: 2026-03-24*
