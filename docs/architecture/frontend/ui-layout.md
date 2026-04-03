# UI Layout Architecture (Spec 127)

> **See also**:
>
> - [Architecture: Frontend Overview](./overview.md) — Technology stack
> - [Architecture: Frontend Structure](./structure.md) — Directory layout
> - [How-To: SolverView Usage](../../how-to/frontend/solver-view.md) — Integration guide
> - [Concepts: Go Tips](../../concepts/go-tips.md) — Tip system schema

**Last Updated**: 2026-02-11

---

## Component Hierarchy

```
App
├── AppHeader (scrolls with content, flex-shrink-0)
│   ├── YenGoLogo
│   ├── Navigation links
│   └── SettingsPanel (slide-over)
│
├── PageLayout (CSS Grid composition wrapper)
│   ├── slot: Board      → Goban container (~65% desktop)
│   ├── slot: Sidebar    → puzzle info, hints, solution tree (~35% desktop)
│   ├── slot: Controls   → action buttons overlay
│   ├── slot: Navigation → prev/next puzzle navigation
│   └── slot: Content    → full-width (single-column variant)
│
└── Page Components
    ├── HomePageGrid        → PageLayout(single-column) + tile grid
    ├── PuzzleSolvePage     → PageLayout(puzzle) + GobanRenderer + PuzzleChrome
    ├── CollectionViewPage  → PuzzleSetPlayer + SolverView
    ├── DailyChallengePage  → PuzzleSetPlayer + SolverView
    ├── PuzzleRushPage      → PageLayout(puzzle) + rush-specific UI
    └── UserProfile         → stats, streaks, achievements
```

---

## Boot Sequence

```
main.tsx
  ↓
boot() — parallel fetch of 3 configs:
  ├── config/puzzle-levels.json  → LevelConfig[]
  ├── config/tags.json (v6)      → TagDefinition[]
  └── config/go-tips.json        → GoTip[]
  ↓
getBootConfigs() available globally
  ↓
App renders with <BootScreens> wrapper
  ├── idle/loading → GoTipDisplay (random tip + skeleton)
  ├── error → BootError (retry button)
  └── ready → full app renders
```

### Boot State Machine

| State     | UI                                | Transition                   |
| --------- | --------------------------------- | ---------------------------- |
| `idle`    | Nothing                           | → `loading` on `boot()` call |
| `loading` | `GoTipDisplay` + `SkeletonLayout` | → `ready` or `error`         |
| `ready`   | Full app                          | Terminal                     |
| `error`   | `BootError` with retry            | → `loading` on retry         |

---

## PageLayout Composition

`PageLayout` uses a compound component pattern with named slots:

```tsx
// Puzzle variant — 2-column 65/35 split on desktop, stacked on mobile
<PageLayout variant="puzzle">
  <PageLayout.Board>
    <GobanRenderer boardRef={boardRef} />
    <PageLayout.Controls>
      <PuzzleChrome status={status} onHint={handleHint} />
    </PageLayout.Controls>
    <PageLayout.Navigation>
      <ProblemNav totalProblems={10} currentIndex={3} />
    </PageLayout.Navigation>
  </PageLayout.Board>
  <PageLayout.Sidebar>
    <PuzzleSidebar status={status} />
  </PageLayout.Sidebar>
</PageLayout>

// Single-column variant — full-width content
<PageLayout variant="single-column">
  <PageLayout.Content>
    <HomeGrid>{/* tile cards */}</HomeGrid>
  </PageLayout.Content>
</PageLayout>
```

### Responsive Behavior

| Viewport          | Layout                      | Sidebar        |
| ----------------- | --------------------------- | -------------- |
| < 768px (mobile)  | Single column, stacked      | Below board    |
| ≥ 768px (desktop) | Two-column grid (65fr/35fr) | Right of board |

---

## SolverView Architecture

`SolverView` is the central puzzle-solving component:

```
SolverView (props: sgf, level, onComplete, onNext, onSkip)
  ├── useGoban()         → goban library integration
  ├── usePuzzleState()   → move validation, solution tracking
  ├── useBoardMarkers()  → stone markers, last-move indicator
  │
  ├── Board container    → goban renders here (ref-based)
  ├── Coordinate toggle  → aria-pressed, persisted via useSettings
  ├── HintOverlay        → progressive hint reveal from YH property
  ├── SolutionReveal     → "Show Solution" + "Next Move" stepper
  └── MoveExplorer       → variation tree navigation
```

### Data Attributes

| Attribute                          | Element          | Values                                    |
| ---------------------------------- | ---------------- | ----------------------------------------- |
| `data-component="solver-view"`     | Root div         | —                                         |
| `data-status`                      | Root div         | `waiting`, `correct`, `wrong`, `complete` |
| `data-component="hint-overlay"`    | Hint section     | —                                         |
| `data-component="solution-reveal"` | Solution section | —                                         |
| `data-component="move-explorer"`   | Explorer section | —                                         |

---

## Hint Progression (HintOverlay)

The progressive hint system follows a **vague → precise** pedagogical funnel:

| Level | Source                                | Visual                       | Pedagogical Purpose                                  |
| ----- | ------------------------------------- | ---------------------------- | ---------------------------------------------------- |
| 1     | `YH` property text (1st pipe segment) | `💡 {text}` overlay          | Guides **thinking** — describes technique or concept |
| 2     | Computed from correct move coordinate | "Look at the {quadrant}"     | Narrows **spatial search** (361 → ~90 intersections) |
| 3     | Exact correct move coordinate         | Green circle marker on board | **Last resort** — reveals precise location           |

**Fallback behavior**: If a puzzle has no `YH` data, the system skips directly to coordinate marker (Level 3) as the sole hint. If `YH` has only 1 entry, levels compress proportionally.

> **Note**: This differs from Constitution Principle X (v2.0.0) which specified "stone shadow → technique badge → text." The current 3-tier hint system (text → quadrant → coordinate) was validated by 1P Go player and expert panel.

---

## Styling Strategy

**Tailwind CSS v4** is the sole styling approach:

- All component styles use Tailwind utility classes
- CSS custom properties defined in `app.css` `@theme` block for token values
- Board/SVG styles merged into `app.css` (formerly separate CSS files)
- No inline `style={}` except for dynamic values (e.g., `fontSize` from props)
- Color tokens: `--color-accent`, `--color-bg-primary`, `--color-text-muted`, etc.

### Token Reference

| Token                  | Usage                                 |
| ---------------------- | ------------------------------------- |
| `--color-accent`       | Primary action color (buttons, links) |
| `--color-bg-primary`   | Main background                       |
| `--color-bg-secondary` | Card/section background               |
| `--color-text-primary` | Headings, important text              |
| `--color-text-muted`   | Secondary text, labels                |
| `--color-success`      | Correct answers, positive             |
| `--color-error`        | Wrong answers, errors                 |
| `--color-warning`      | Caution states                        |

---

## State Management

| Concern      | Mechanism                                | Persistence                   |
| ------------ | ---------------------------------------- | ----------------------------- |
| Settings     | `useSettings()` hook + `@preact/signals` | `localStorage:yengo:settings` |
| Boot configs | `getBootConfigs()` singleton             | Memory (re-fetched on boot)   |
| Route        | `useState` + `history.pushState`         | URL                           |
| Puzzle state | `usePuzzleState()` per-puzzle            | Memory                        |
| Progress     | `localStorage` direct                    | `localStorage`                |

---

## PuzzleSetPlayer Pattern

Shared puzzle-solving wrapper for collection and daily pages:

```tsx
<PuzzleSetPlayer
  loader={new CollectionPuzzleLoader("beginner")}
  onBack={handleBack}
  renderHeader={({ current, total }) => <Header />}
  renderNavigation={({ onPrev, onNext }) => <Nav />}
  renderSummary={({ solved, total }) => <Summary />}
/>
```

States: `idle` → `loading` → `ready` / `error` / `empty` → `allComplete`
