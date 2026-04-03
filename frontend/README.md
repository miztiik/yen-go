# Yen-Go Frontend

A fully offline Go (Baduk/Weiqi) tsumego puzzle platform built with TypeScript, Preact, and Vite.

> **Full Documentation**:
>
> - [How-To: Local Development](../docs/how-to/frontend/local-development.md) — Dev server, testing
> - [How-To: Build & Deploy](../docs/how-to/frontend/build-deploy.md) — Production builds
> - [Architecture: Frontend](../docs/architecture/frontend/) — Design decisions

## Features

- 🎮 **Puzzle Solving** - Solve tsumego puzzles with immediate feedback
- 📊 **Progress Tracking** - All progress saved locally in localStorage
- 🔥 **Daily Streaks** - Track consecutive days of practice
- 💡 **Progressive Hints** - 3-tier hints (region → technique → text)
- 🔄 **Solution Tree** - Visual path through puzzle solution
- ⏱️ **Timed Challenges** - 3/5/10/15 minute puzzle rush modes
- 🏆 **Achievements** - Unlock badges for milestones
- 📱 **Responsive Design** - Desktop side panel, mobile bottom stack
- 🔄 **Board Rotation** - Rotate board 90° increments, persisted
- ♿ **Accessible** - WCAG 2.1 AA compliant, keyboard navigation

## Tech Stack

- **Framework**: Preact 10.x (lightweight React alternative)
- **Build Tool**: Vite 5.x
- **Language**: TypeScript 5.x (strict mode)
- **Go Board**: [OGS goban](https://github.com/online-go/goban) v8.3.147+ (SGF parsing, puzzle mode, variation trees)
- **Testing**: Vitest + Testing Library + Playwright (E2E)
- **Styling**: CSS with custom properties + Tailwind utilities
- **PWA**: Service worker for offline support

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test

# Type check
npm run typecheck

# Build for production
npm run build

# Preview production build locally (simulates GitHub Pages)
npm run preview
# → Open http://localhost:4173/yen-go/
```

> **Note**: For detailed documentation on building, previewing, and deploying, see [Development Setup](../docs/getting-started/develop.md#production-build--preview).

## Puzzle Data Sources

Puzzles are loaded from the **SQLite database** and **SGF files** in `yengo-puzzle-collections/`:

```
yengo-puzzle-collections/
├── yengo-search.db            # SQLite search/metadata index (~500 KB)
├── db-version.json            # Version pointer with puzzle count
└── sgf/                       # SGF files organized by batch
    ├── 0001/                  # Batch 0001 (up to 100 files)
    ├── 0002/                  # Batch 0002
    └── ...
```

**Bootstrap flow:**
1. Browser fetches `yengo-search.db` (~500 KB)
2. sql.js WASM loads DB into memory
3. All queries execute as SQL against in-memory DB
4. Individual SGF files fetched on demand: `sgf/{batch}/{content_hash}.sgf`

### SGF Custom Properties (Schema v15)

| Property | Description                                      | Example                                                                |
| -------- | ------------------------------------------------ | ---------------------------------------------------------------------- |
| `GN`     | Puzzle ID (set at publish)                        | `GN[YENGO-765f38a5196edb79]`                                           |
| `YV`     | Schema version                                    | `YV[15]`                                                               |
| `YG`     | Skill level slug                                  | `YG[intermediate]`                                                     |
| `YT`     | Tags (comma-separated, sorted)                    | `YT[ko,ladder,life-and-death]`                                         |
| `YH`     | Hints (pipe-delimited, max 3)                     | `YH[Corner focus\|Ladder pattern\|{!cg}]`                              |
| `YQ`     | Quality metrics                                   | `YQ[q:2;rc:0;hc:0;ac:1]`                                               |
| `YX`     | Complexity metrics                                | `YX[d:1;r:2;s:19;u:1;a:0]`                                             |
| `YK`     | Ko context                                        | `YK[none]`                                                             |
| `YO`     | Move order                                        | `YO[strict]`                                                           |
| `YL`     | Collection membership                             | `YL[cho-chikun-life-death-elementary:3/12]`                             |
| `YC`     | Corner position                                   | `YC[TL]`                                                               |
| `YR`     | Refutation moves                                  | `YR[cd,de,ef]`                                                         |
| `YM`     | Pipeline metadata JSON                            | `YM[{"t":"a1b2c3d4e5f67890","i":"20260220-abc12345"}]`                 |

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── GobanBoard/     # goban library wrapper (SVG/Canvas)
│   │   ├── Solver/         # SolverView, HintOverlay, MoveExplorer
│   │   ├── ProblemNav/     # Puzzle set navigation
│   │   ├── QuickControls/  # Rotate/undo/reset/hint
│   │   ├── Level/          # Level selection
│   │   ├── Progress/       # Stats & achievements
│   │   ├── Rush/           # Timed mode (overlay, setup)
│   │   ├── PuzzleSetPlayer/# Shared puzzle set player
│   │   ├── Transforms/     # Board flip/rotate/zoom controls
│   │   └── shared/         # RankBadge, SideToMove, etc.
│   ├── services/
│   │   ├── progressTracker.ts  # localStorage persistence
│   │   ├── streakManager.ts    # Daily streak logic
│   │   ├── achievementEngine.ts# Achievement tracking
│   │   ├── puzzleLoader.ts     # Load from SGF collections
│   │   ├── collectionService.ts# Collection browsing & progress
│   │   ├── dailyChallengeService.ts # Daily challenge modes
│   │   └── audioService.ts     # Sound effects
│   ├── lib/
│   │   ├── sgf-preprocessor.ts # YenGo SGF property extraction
│   │   ├── daily-challenge-loader.ts # Daily puzzle loading
│   │   ├── levels/         # Level config types
│   │   └── hints/          # Progressive hint mapper
│   ├── hooks/
│   │   ├── useGoban.ts     # goban lifecycle management
│   │   ├── usePuzzleState.ts # Puzzle solving state
│   │   ├── useTransforms.ts # Board flip/rotate/zoom
│   │   ├── useBoardMarkers.ts # Review mode markers
│   │   └── useRushSession.ts # Puzzle rush state
│   ├── pages/
│   │   ├── HomePage.tsx    # Home with 6 activity tiles
│   │   ├── CollectionViewPage.tsx # Collection browsing
│   │   ├── DailyChallengePage.tsx # Daily challenge
│   │   ├── TechniqueFocusPage.tsx # Practice by technique
│   │   ├── TrainingPage.tsx # Structured training levels
│   │   ├── PuzzleRushPage.tsx # Timed puzzle rush mode
│   │   └── RandomChallengePage.tsx # Random puzzles
│   └── styles/             # Global CSS
├── tests/
│   ├── unit/               # Unit tests
│   ├── e2e/                # Playwright E2E tests
│   └── visual/             # Visual regression tests
└── public/
    └── sounds/             # Sound effect files
```

## Architecture

### Zero Runtime Backend

The app runs entirely in the browser with no server communication:

- Puzzles are indexed in a SQLite database loaded via sql.js WASM; individual SGF files are static assets
- User progress is stored in localStorage
- Solution validation uses precomputed solution trees

### Key Services

| Service                    | Responsibility                                      |
| -------------------------- | --------------------------------------------------- |
| `sqliteService.ts`         | Load `yengo-search.db` via sql.js WASM, run SQL     |
| `puzzleQueryService.ts`    | Query puzzles from SQLite with filters/pagination    |
| `entryDecoder.ts`          | Decode compact DB rows into `DecodedEntry` objects   |
| `configService.ts`         | Load config (tags, levels) from SQLite               |
| `dailyQueryService.ts`     | Query daily challenge schedule from SQLite            |
| `dailyChallengeService.ts` | Daily challenge modes and streak tracking            |
| `puzzleLoader.ts`          | Fetch individual SGF files, convert to puzzle format |
| `solutionVerifier.ts`      | Validate moves against precomputed solution tree     |
| `boardAnalysis.ts`         | Board state analysis (liberties, captures)           |
| `puzzleGameState.ts`       | Manage puzzle solving state machine                  |
| `rulesEngine.ts`           | Enforce Go rules (captures, ko, suicide)             |
| `puzzleRushService.ts`     | Timed puzzle rush scoring and state                  |
| `progressAnalytics.ts`     | Progress statistics and analytics                    |
| `collectionService.ts`     | Collection browsing, filtering, progress             |
| `collectionQueryService.ts`| Query collections from SQLite                        |
| `audioService.ts`          | Play sound effects (respects mute setting)           |

### Solution Tree

The solution tree visualization uses the [goban](https://github.com/online-go/goban) library's built-in canvas tree renderer, displayed in the SolverView sidebar during review mode (Spec 125, 132).

### Routes

| Route                         | Route Type           | Description                              |
| ----------------------------- | -------------------- | ---------------------------------------- |
| `/`                           | `home`               | Activity tiles dashboard                 |
| `/collections`                | `collections-browse` | Browse puzzle collections                |
| `/collection/:slug`           | `context`            | Play puzzles from a collection           |
| `/modes/daily`                | `modes-daily`        | Daily challenge landing                  |
| `/modes/daily/:date`          | `modes-daily-date`   | Specific date's daily challenge          |
| `/modes/random`               | `modes-random`       | Random puzzle                            |
| `/modes/rush`                 | `modes-rush`         | Timed puzzle rush mode                   |
| `/technique`                  | `technique-browse`   | Browse techniques                        |
| `/technique/:tag`             | `context`            | Practice by technique/tag                |
| `/training`                   | `training-browse`    | Browse training levels                   |
| `/training/:level`            | `context`            | Structured level training                |
| `/learn`                      | `learning-browse`    | Browse learning content                  |
| `/progress`                   | `progress`           | View progress and statistics             |
| `/smart-practice`             | `smart-practice`     | AI-guided technique practice             |

### Performance Targets

- Move validation: <100ms (p95)
- Page load: <3s on 3G
- Bundle size: <500KB gzipped

## Scripts

| Script | Description |\n|--------|-------------|\n| `npm run dev` | Start dev server at http://localhost:5173 |\n| `npm run build` | Production build to `dist/` |\n| `npm run preview` | Preview production build at http://localhost:4173/yen-go/ |\n| `npm run build:preview` | Build + preview in one command |\n| `npm test` | Run all tests |\n| `npm run test:watch` | Run tests in watch mode |\n| `npm run test:coverage` | Run tests with coverage |\n| `npm run test:visual` | Run Playwright visual regression tests |\n| `npm run test:visual:update` | Update visual test baselines |\n| `npm run test:visual:ui` | Interactive visual test UI |\n| `npm run typecheck` | TypeScript type checking |\n| `npm run lint` | ESLint check |\n| `npm run lint:fix` | ESLint auto-fix |\n| `npm run format` | Prettier format |\n| `npm run format:check` | Prettier check |

## Testing

```bash
# Run all tests
npm test

# Run specific test file
npm test -- tests/unit/rulesEngine.test.ts

# Run with coverage
npm run test:coverage
```

**Test coverage:** 1073+ tests across unit and integration suites.

## Visual Regression Testing

Visual tests use Playwright to catch unintended UI changes. Screenshots are captured for Board, LevelCard, and FeedbackOverlay components across desktop, tablet, and mobile viewports.

```bash
# Run visual tests
npm run test:visual

# Update baselines after intentional changes
npm run test:visual:update

# Interactive UI for debugging
npm run test:visual:ui

# Run specific component tests
npm run test:visual -- --grep "Board"
```

**Test structure:**

```
tests/visual/
├── specs/           # Visual test specifications
├── baselines/       # Committed baseline screenshots
├── test-results/    # Diff images (gitignored)
└── README.md        # Visual testing guide
```

See [Visual Testing README](tests/visual/README.md) for detailed documentation.

## Accessibility

- Keyboard navigation: Arrow keys, Enter/Space, Escape
- ARIA labels on all interactive elements
- Minimum 44x44px touch targets
- Color contrast meets WCAG AA

### Keyboard Shortcuts

| Key | Action                     |
| --- | -------------------------- |
| `R` | Rotate board 90° clockwise |
| `Z` | Undo last move             |
| `X` | Reset puzzle               |
| `H` | Show next hint             |
| `←` | Previous puzzle            |
| `→` | Next puzzle                |

## Browser Support

- Chrome 88+
- Firefox 78+
- Safari 14+
- Edge 88+

Requires ES2020+ features (modern browsers only).

## Related Documentation

- [Architecture: Frontend Overview](../docs/architecture/frontend/overview.md)
- [Architecture: Goban Integration](../docs/architecture/frontend/goban-integration.md)
- [How-To: Local Development](../docs/how-to/frontend/local-development.md)
