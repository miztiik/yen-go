# Frontend Overview

> **See also**:
>
> - [Architecture: Structure](./structure.md) — Component layout
> - [How-To: Frontend Development](../../how-to/frontend/) — Development guides
> - [Getting Started: Development](../../getting-started/develop.md) — Setup
> - [Concepts: Go Tips](../../concepts/go-tips.md) — GoTip schema and taxonomy

**Last Updated**: 2026-03-24

The Yen-Go frontend is a **static-first PWA** built with Preact + TypeScript + Vite.

---

## Technology Stack

| Layer     | Technology                       | Why                                                 |
| --------- | -------------------------------- | --------------------------------------------------- |
| Framework | Preact                           | React-compatible, ~3KB                              |
| Language  | TypeScript                       | Type safety, strict mode                            |
| Build     | Vite                             | Fast HMR, optimized builds                          |
| State     | `@preact/signals` + localStorage | Reactive settings, no backend                       |
| Styling   | Tailwind CSS v4                  | Utility-first, JIT compiled via `@tailwindcss/vite` |
| Go Board  | `goban` ^8.3.147                 | OGS Go library (untouched per FR-012)               |
| Testing   | Vitest + Playwright              | Unit + visual regression tests                      |

---

## Config Loading

Config data flows through two complementary paths:

### Build-Time (Vite JSON Imports)

Level, tag, and quality metadata is imported from `config/*.json` at build time via
Vite's `resolveJsonModule` support. This gives us compile-time type safety and zero
runtime overhead — the JSON is inlined into the bundle.

| Config File | Frontend Module | Provides |
|---|---|---|
| `config/puzzle-levels.json` | `lib/levels/config.ts` | `LEVELS`, `LevelSlug`, ID↔slug maps |
| `config/tags.json` | `lib/tags/config.ts` | `TAGS`, `TagSlug`, ID↔slug maps |
| `config/puzzle-quality.json` | `lib/quality/config.ts` | `QUALITIES`, `QualitySlug`, ID↔slug maps |

`services/configService.ts` is the single facade for numeric ID ↔ slug resolution.

### Runtime (Boot Sequence)

The application uses a **boot-before-render** pattern:

```
1. boot() runs 5 steps:
   ├── fetchConfigs   → levels + tags + tips (parallel)
   ├── cacheConfigs   → module-level singleton
   ├── cleanLegacy    → delete old localStorage keys (non-fatal)
   ├── initGoban      → theme callbacks, MutationObserver
   └── renderApp      → <App /> into #app
2. sqliteService.initDb() fetches yengo-search.db (~500 KB) via sql.js WASM
3. All puzzle queries resolve via SQL against in-memory SQLite (no JSON manifests)
4. GoTipDisplay shows random tips during boot loading
```

Key modules:

- `boot.ts` — 5-step boot sequence (fetchConfigs → cacheConfigs → cleanLegacy → initGoban → renderApp)
- `main.tsx` — Entry point, boot orchestration
- `services/configService.ts` — Numeric ID ↔ slug resolution facade

---

## Component Architecture

### PageLayout Composition Pattern

All pages use `PageLayout` for consistent structure:

```tsx
<PageLayout
  variant="puzzle" // Activates puzzle-layout CSS grid
  mode="collections" // Sets page accent color
>
  <PageLayout.Board>
    {" "}
    // 65% width on desktop
    <SolverView sgf={sgf} />
  </PageLayout.Board>
  <PageLayout.Sidebar>
    {" "}
    // 35% width, stacks on mobile
    <PuzzleSidebar />
  </PageLayout.Sidebar>
</PageLayout>
```

### SolverView — Core Puzzle Solving

`SolverView` is the shared puzzle-solving component used by all modes:

- Board div: `data-testid="goban-board"`, `role="application"`, `aria-label="Go puzzle board"`
- Sidebar: puzzle counter, transforms, hints, actions, solution tree

```
SolverView
├── useGoban()        — Board rendering via goban library (Canvas default)
├── usePuzzleState()  — Move validation, status tracking, audio feedback
├── auto-viewport     — YC-based corner puzzle auto-zoom
├── HintOverlay       — Progressive hint reveal (SVG icons, depletion)
├── SolutionReveal    — "Show Solution" + move stepper
├── MoveExplorer      — Move tree navigation
├── AnswerBanner      — Correct/incorrect feedback with forward nav
└── Coordinate Toggle — Show/hide board coordinates (SVG icon)
```

### Component Diagram

```
App
├── BootScreens (loading state)
│   └── GoTipDisplay
├── AppHeader (scrolls with content, non-sticky)
│   ├── YenGoLogo
│   ├── Navigation
│   └── UserProfile
├── PageLayout (CSS Grid slots, puzzle-layout aspect-ratio breakpoint)
│   └── Page Content
│       ├── HomePageGrid
│       ├── PuzzleSolvePage → SolverView + PuzzleSidebar
│       ├── CollectionViewPage → PuzzleSetPlayer → SolverView
│       ├── DailyChallengePage → PuzzleSetPlayer → SolverView
│       └── PuzzleRushPage → RushPuzzleRenderer
└── PuzzleSidebar (identity → tools → content)
    ├── Metadata (level, collection, tags, ko, corner)
    ├── TransformBar (SVG icon buttons)
    └── Solution Tree / Hints / Comments
```

---

## Directory Structure

```
frontend/
├── src/
│   ├── app.tsx               # App entry, routing
│   ├── boot.ts               # Config boot loader
│   ├── main.tsx              # Entry point
│   ├── components/           # Reusable UI components
│   │   ├── Board/            # Go board renderer (goban)
│   │   ├── Layout/           # PageLayout, AppHeader, YenGoLogo
│   │   ├── Solver/           # SolverView, HintOverlay, SolutionReveal, MoveExplorer
│   │   ├── Settings/         # SettingsPanel
│   │   ├── PuzzleSetPlayer/  # Shared puzzle set navigation
│   │   ├── DailyChallenge/   # Daily challenge cards
│   │   ├── TechniqueFocus/   # Technique browsing
│   │   ├── Training/         # Training mode
│   │   ├── Streak/           # Streak tracking
│   │   ├── shared/           # Modal, common components
│   │   └── Boot/             # BootScreens, GoTipDisplay, SkeletonLayout
│   ├── hooks/                # Custom hooks
│   │   ├── useSettings.ts    # Settings signal (coordinateLabels, theme, etc.)
│   │   ├── useGoban.ts       # Board rendering
│   │   ├── usePuzzleState.ts # Move validation
│   │   └── useBoardMarkers.ts# Board markers
│   ├── pages/                # Page components
│   ├── services/             # Data services
│   │   ├── puzzleLoader.ts   # SGF fetching
│   │   ├── puzzleLoaders.ts  # Collection & Daily loaders
│   │   └── audioService.ts   # Sound effects
│   ├── styles/
│   │   └── app.css           # Single Tailwind entry + all CSS vars
│   ├── lib/                  # Utility modules
│   │   ├── goban-init.ts     # Theme config, MutationObserver
│   │   ├── accuracy-color.ts # 3-tier accuracy coloring
│   │   └── slug-formatter.ts # URL slug → human label
│   ├── types/                # Shared TypeScript types
│   │   ├── page-mode.ts      # PageMode + PAGE_MODE_COLORS
│   │   └── mastery.ts        # MasteryLevel + MASTERY_OPACITY
│   └── constants.ts          # APP_CONSTANTS, paths, CDN URLs
├── public/                   # Static assets
│   └── img/kaya.jpg          # Self-hosted Kaya board texture
├── tests/                    # Test suites
│   ├── unit/                 # Vitest unit tests
│   └── visual/               # Playwright visual tests
└── index.html                # Entry HTML
```

---

## Routing

The app uses **path-based routing** in `app.tsx` via `parseRoute()`. No hash routing.

| Route                     | Type                | Page Component                                          |
| ------------------------- | ------------------- | ------------------------------------------------------- |
| `/`                       | `home`              | `HomePageGrid`                                          |
| `/collections`            | `collections`       | `CollectionsPage`                                       |
| `/collections/:id`        | `collection`        | `CollectionsPage` (detail)                              |
| `/collections/:id/:index` | `collection-puzzle` | `CollectionViewPage` → `PuzzleSetPlayer` → `SolverView` |
| `/daily`                  | `daily`             | `DailyBrowsePage`                                       |
| `/daily/:date`            | `daily-date`        | `DailyChallengePage`                                    |
| `/puzzle-rush`            | `puzzle-rush`       | `RushBrowsePage` (setup) / `PuzzleRushPage` (playing)   |
| `/technique/:tag`         | `technique`         | `TechniqueFocusPage`                                    |
| `/training`               | `training`          | `TrainingBrowsePage`                                    |
| `/training/:level`        | `training-level`    | `TrainingPage`                                          |
| `/random`                 | `random`            | `RandomPage`                                            |

### Collection ID Format

Collection IDs use prefixes to route the `CollectionPuzzleLoader` to the correct SQL query via `puzzleQueryService`:

- `curated-{slug}` → `getPuzzlesByCollection()` (curated collections)
- `level-{slug}` → `getPuzzlesByLevel()` (level-based)
- `tag-{slug}` → `getPuzzlesFiltered({ tagId })` (tag-based)
- Bare slug (e.g., `beginner`) → tries level query, then `curated-` fallback

The `CollectionsPage` always navigates with `curated-` prefix: `onNavigateToCollection('curated-' + slug)`.

---

## Goban Theme System (Spec 132)

The Go board uses the `goban` library with Canvas rendering and themed visuals:

| Theme Property | Light Mode           | Dark Mode         |
| -------------- | -------------------- | ----------------- |
| White stones   | Shell (Phong-shaded) | Shell             |
| Black stones   | Slate (Phong-shaded) | Slate             |
| Board surface  | Kaya (wood texture)  | Night Play (#444) |
| Stone shadows  | Default              | Default           |

**Theme switching**: A `MutationObserver` on `<html data-theme>` triggers live updates via `watchSelectedThemes` — no page reload needed.

**Self-hosted assets**: Board texture at `/img/kaya.jpg` (~50KB). The `getCDNReleaseBase` callback returns `""` for local asset resolution.

---

## Page Mode Color Identity (Spec 132)

Each page has a distinctive accent color set via `<PageLayout mode="...">`:

| Page             | Mode          | Accent Family |
| ---------------- | ------------- | ------------- |
| Daily Challenge  | `daily`       | Amber         |
| Puzzle Rush      | `rush`        | Rose          |
| Collections      | `collections` | Emerald       |
| Training         | `training`    | Blue          |
| Technique Focus  | `technique`   | Teal          |
| Random Challenge | `random`      | Indigo        |

The `data-mode` attribute on the layout wrapper activates a CSS cascade that sets `--color-accent` to that mode's text color. Dark mode overrides reduce saturation for each mode.

> **See also**: [Concepts: Design Tokens](../../concepts/design-tokens.md) — Full token reference

---

## Responsive Layout (Spec 132)

### Puzzle Layout Breakpoints

The `.puzzle-layout` CSS class uses aspect-ratio-aware media queries:

| Viewport                 | Condition                          | Layout                             |
| ------------------------ | ---------------------------------- | ---------------------------------- |
| Mobile                   | `< 768px width`                    | Stacked (board top, sidebar below) |
| Portrait tablet          | `>= 768px BUT aspect-ratio < 4/5`  | Stacked                            |
| Landscape tablet/desktop | `>= 768px AND aspect-ratio >= 4/5` | Side-by-side (65/35)               |
| Squashed landscape       | `height < 500px AND landscape`     | Board capped at 80vh               |

### Sidebar Architecture

PuzzleSidebar is structured in three sections:

1. **Identity**: Level (YG), collection link (YL), corner (YC), hints (YH), ko (YK), tags (YT)
2. **Tools**: TransformBar (SVG icon buttons for flip/rotate/swap/zoom)
3. **Content**: Solving mode shows comments + hints; review mode shows solution tree

Constrained to `max-width: 400px` on desktop. Empty fields are omitted (no "N/A" placeholders).

### Auto-Viewport

Corner puzzles (YC property) auto-zoom to the relevant quadrant on load via `auto-viewport.ts`. User manual zoom overrides take precedence.

---

## Core Responsibilities

### What the Frontend DOES

- Fetch static SGF/JSON from `yengo-puzzle-collections/`
- Parse SGF in browser (~5KB parser)
- Render Go board on Canvas
- Validate moves against solution trees
- Track progress in localStorage
- Work offline (PWA)

### What the Frontend DOES NOT

- Call backend APIs
- Calculate Go moves
- Run AI inference
- Store data on servers

---

## Data Flow

```
GitHub Pages              Browser
    │                        │
    │◀── GET /views/*.json ──┤ 1. Fetch puzzle index
    │                        │
    │◀── GET /sgf/*.sgf ─────┤ 2. Fetch puzzle SGF
    │                        │
    │                        ├── 3. Parse SGF
    │                        │
    │                        ├── 4. Render board
    │                        │
    │                        ├── 5. User plays move
    │                        │
    │                        ├── 6. Validate against tree
    │                        │
    │                        └── 7. Update localStorage
```

---

## Component Architecture

### Services Pattern

Services encapsulate data access:

```typescript
// services/puzzleService.ts
export async function fetchPuzzle(id: string): Promise<Puzzle> {
  const response = await fetch(`/sgf/${id}.sgf`);
  const sgf = await response.text();
  return parseSgf(sgf);
}
```

### Models

All data structures are typed:

```typescript
// models/puzzle.ts
export interface Puzzle {
  id: string;
  level: Level;
  position: Position;
  solution: MoveTree;
  tags: string[];
  hints: string[];
}
```

### State Management

- **No global state library** — Preact signals or prop drilling
- **localStorage** — User progress, preferences, achievements
- **Versioned schemas** — All localStorage data has version field

---

## Configuration

Frontend reads shared config:

```typescript
import levels from "../../../config/puzzle-levels.json";
import tags from "../../../config/tags.json";
```

Single source of truth shared with backend.

---

## PWA Features

- **Service Worker** — Offline puzzle solving
- **Manifest** — Installable as app
- **Cache Strategy** — Static assets cached, puzzles fetched on demand

---

## Build & Deploy

```bash
cd frontend
npm run build     # Generate dist/
npm run preview   # Preview at localhost:4173/yen-go/
```

Production builds deploy to GitHub Pages via CI.
