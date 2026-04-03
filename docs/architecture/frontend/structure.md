# Frontend Structure

> **See also**:
>
> - [Architecture: Frontend Overview](./overview.md) — Technology stack, PWA
> - [Architecture: State Management](./state-management.md) — localStorage patterns
> - [Architecture: Puzzle Solving](./puzzle-solving.md) — Move validation

**Last Updated**: 2026-03-24

## Directory Layout

```
frontend/src/
├── app.tsx               # App entry, routing
├── components/           # Reusable UI components
│   ├── GobanContainer/   # Mounts goban's self-created DOM element
│   ├── Achievements/     # Achievement display
│   ├── DailyChallenge/   # Daily challenge mode
│   ├── Rush/             # Puzzle rush mode
│   ├── Layout/           # PageLayout (with mode prop)
│   ├── shared/           # ProgressBar, Button, FilterBar, GoQuote, ErrorState
│   └── ...
├── lib/                  # Core business logic
│   ├── levels/           # Level config (Vite JSON import from config/puzzle-levels.json)
│   ├── tags/             # Tag config (Vite JSON import from config/tags.json)
│   ├── quality/          # Quality config (Vite JSON import from config/puzzle-quality.json)
│   ├── puzzle/           # Puzzle utilities
│   ├── goban-init.ts     # goban callbacks (themes, CDN)
│   ├── sgf/              # SGF parser, types, coordinates, solution-tree
│   ├── sgf-preprocessor.ts # Extract YenGo metadata from SGF
│   ├── sgf-metadata.ts   # Canonical tree parser (parseSgfToTree)
│   ├── sgf-solution.ts   # SolutionNode tree builder
│   ├── sgf-to-puzzle.ts  # SGF → PuzzleObject (initial_state + move_tree)
│   ├── puzzle-config.ts  # PuzzleObject → GobanConfig
│   ├── accuracy-color.ts # 3-tier accuracy coloring
│   ├── progress/         # Progress tracking
│   └── achievements/     # Achievement system
├── hooks/                # Custom hooks
│   └── useGoban.ts       # goban lifecycle hook
├── pages/                # Page components (with PageLayout mode)
├── services/             # Data services
│   ├── sqliteService.ts  # SQLite DB init (sql.js WASM)
│   ├── puzzleQueryService.ts # Puzzle search/filter queries
│   ├── puzzleLoader.ts   # SGF fetching
│   ├── configService.ts  # Numeric ID ↔ slug resolution
│   ├── solutionVerifier.ts # Move validation vs solution tree
│   ├── rulesEngine.ts    # Go rules (captures, ko, legality)
│   ├── puzzleGameState.ts # Puzzle solving state machine
│   └── ...               # daily, collection, rush, analytics services
├── models/               # TypeScript interfaces
├── types/                # Shared type definitions
│   ├── page-mode.ts      # PageMode type + PAGE_MODE_COLORS
│   └── mastery.ts        # MasteryLevel + MASTERY_OPACITY
└── styles/               # CSS files + design tokens
```

## Services Pattern

Services encapsulate data access. Key services:

- `sqliteService.ts` — Initializes sql.js WASM, loads `yengo-search.db`
- `puzzleQueryService.ts` — SQL queries for puzzle search/filtering
- `configService.ts` — Numeric ID ↔ slug resolution facade
- `solutionVerifier.ts` — Validates moves against precomputed solution trees
- `rulesEngine.ts` — Go rules: captures, ko, suicide, legality

## Models

All data structures are typed. Key types from `models/puzzle.ts`:

- `Stone` — Integer type: `BLACK = -1`, `WHITE = 1`, `EMPTY = 0`
- `SolutionNode` — Tree node with `move`, `branches`, `isWinning`
- `Puzzle` — Full puzzle: `boardSize`, `initialState`, `solutionTree`, `hints`, `metadata`
- `Move` — `{ x, y, color }`
- `MoveValidationResult` — `{ isCorrect, nextNode?, isWinning? }`

## State Management

- **No global state library** — Preact signals or prop drilling
- **localStorage** — User progress, preferences, achievements
- **Versioned schemas** — All localStorage data has version field

## Board Rendering

- **goban library** — SVG/Canvas rendering with theme support (Shell/Slate stones, custom board color)
- **SVG default** — SVGRenderer is the default; Canvas (with Phong-shaded stones) is opt-in via `localStorage`
- **Dark mode** — Custom dark board color via `customBoardColor` callback, live switching via MutationObserver on `data-theme`
- **Touch support** — Mobile-first design
- **Keyboard navigation** — Full WCAG 2.1 AA compliance

## Page Mode Color Identity

Each page has a distinctive accent color set via `PageLayout` `mode` prop:

| Page             | Mode          | Color   |
| ---------------- | ------------- | ------- |
| Daily Challenge  | `daily`       | Amber   |
| Puzzle Rush      | `rush`        | Rose    |
| Collections      | `collections` | Purple  |
| Training         | `training`    | Blue    |
| Technique Focus  | `technique`   | Emerald |
| Random Challenge | `random`      | Indigo  |

## Configuration Loading

### Dev Server Path Mounting

The Vite dev server uses a custom plugin `serveRootStaticFiles()` in `vite.config.ts` to mount parent-directory paths into the dev server:

| URL Path                     | Maps To                        |
| ---------------------------- | ------------------------------ |
| `/yengo-puzzle-collections/` | `../yengo-puzzle-collections/` |
| `/config/`                   | `../config/`                   |

This avoids Vite's default restriction against serving files outside the project root. Content types are set for `.json` and `.sgf` files. Path traversal (`..`) is blocked.

### Shared Config

Frontend reads from `config/`:

```typescript
import levels from "../../../config/puzzle-levels.json";
import tags from "../../../config/tags.json";
```

Single source of truth shared with backend.
