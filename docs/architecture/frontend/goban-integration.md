# Goban Library Integration

> **See also**:
>
> - [Architecture: Board State & Coordinate System Design (Deprecated)](./board-state-design.md) — Historical pre-goban reference only
> - [Architecture: Go Rules Engine](./go-rules-engine.md) — Move validation and rules behavior

**Last Updated:** 2026-03-09  
**Spec:** 125 (Goban Library Migration), 132 (Board UI Visual Polish), UI Overhaul Phase 1-5

## Overview

This is the **canonical architecture document** for frontend board integration.

The legacy `board-state-design.md` document is deprecated and should not be used as implementation authority.

YenGo uses the [OGS goban library](https://github.com/online-go/goban) (v8.3.147+) for Go board rendering and puzzle interaction. The integration follows OGS patterns closely, with documented deviations.

## Why goban?

- **Battle-tested**: Powers yengo-source, handling millions of games
- **Full SGF support**: Native parsing, validation, and rendering
- **Puzzle mode**: Built-in move validation with correct/wrong feedback
- **Variation trees**: Native support for solution branches
- **Accessibility**: Keyboard navigation, screen reader support
- **Performance**: Canvas rendering with lazy updates
- **License**: MIT license

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    SolverView (memo-wrapped)                     │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐   │
│  │   GobanContainer        │  │    Sidebar                  │   │
│  │   ┌─────────────────┐   │  │    ┌─────────────────────┐  │   │
│  │   │  goban creates  │   │  │    │  ProblemNav          │  │   │
│  │   │  its own div    │   │  │    │  TransformBar        │  │   │
│  │   │  via gobanDiv   │   │  │    │  HintOverlay         │  │   │
│  │   └─────────────────┘   │  │    │  Solution Tree       │  │   │
│  └─────────────────────────┘  │    │  KBShortcut          │  │   │
│                               │    └─────────────────────┘  │   │
│                               └─────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │    Action bar: Prev | Undo | Reset | Next | Review      │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Design Decisions (Non-Negotiable)

1. **No modifications to goban NPM package** — Zero changes to `node_modules/goban/`. All customization via callbacks, config, CSS, events, and the adapter layer.
2. **Structured puzzle data** — SGF is converted to a structured `PuzzleObject` (`initial_state` + `move_tree`) via `sgfToPuzzle()`, then passed to goban via `buildPuzzleConfig()`. No `original_sgf` field is used. Metadata extracted separately via `parseSgfToTree()` (proper tree parser, no regex) for sidebar display.
3. **yengo-source alignment** — Deviate only with documented justification. Deviations: 3-tier hints, hook-based events, rotation buttons, dirty text comments, SGF preprocessing.
4. **Goban is drop-in replaceable** — Swapping the goban library affects only 5 files: `sgf-to-puzzle.ts`, `puzzle-config.ts`, `useGoban.ts`, `goban-init.ts`, `types/goban.ts`. The rest of the app uses `GobanInstance` and `GobanContainer` as opaque handles.

## Core Components

### GobanContainer (ported from OGS)

Manages goban's self-created DOM element. Uses `PersistentElement` to mount/unmount the goban div without destroying it.

```tsx
<GobanContainer gobanDiv={gobanDiv} />
```

**Key difference from old pattern**: No `boardRef` passed to useGoban. The goban library creates its own DOM element (`gobanDiv`), and GobanContainer mounts it with overflow:hidden + centering.

**Visual treatment** (CSS on `.goban-container`): Rounded corners (`border-radius: 12px`) with `overflow: hidden` to clip board content, an outer elevation `box-shadow`, and an inset `::after` pseudo-element for subtle 3D board-edge depth. Dark mode uses a stronger inset shadow for contrast.

### useGoban Hook

Manages goban lifecycle. Creates goban instance programmatically — no boardRef needed:

```tsx
const { gobanRef, isReady, boardMessage, gobanDiv } = useGoban(
  rawSgf, // Transformed SGF string
  treeRef, // Ref for variation tree (optional)
  transformSettings, // Flip/rotate/zoom settings
  bounds, // Auto-zoom viewport bounds
  labelPosition, // 'all' | 'none' coordinate labels
);
```

Key responsibilities:

- Extract metadata via `preprocessSgf()`, pass raw SGF to goban via `buildPuzzleConfig()`
- Create goban instance with correct puzzle mode config
- Return `gobanDiv` for GobanContainer to mount
- Handle cleanup on unmount
- Apply label positions via `setLabelPosition()` API

### usePuzzleState Hook

Manages puzzle solving lifecycle:

```tsx
const {
  state, // { status, moveCount, wrongAttempts, ... }
  onGobanReady, // Call when goban is mounted
  requestHint, // Request hint tier 1-3
  revealSolution, // Show full solution
  reset, // Reset puzzle to start
  undo, // Undo last move
  elapsedMs, // Time tracking
} = usePuzzleState(goban, { moveOrder });
```

### useTransforms Hook

Manages board transforms for practice variety:

```tsx
const {
  settings,
  toggleFlipH,
  toggleFlipV,
  toggleFlipDiagonal,
  toggleSwapColors,
  toggleZoom,
  randomize,
  reset,
  applyTransforms,
  getZoomBounds,
} = useTransforms();
```

## Rendering

### SVG Renderer (Default)

YenGo defaults to `SVGRenderer` from the goban library (with Shadow DOM). Users can switch to `GobanCanvas` via `localStorage` key `"yengo-renderer-preference"` (`"svg"` | `"canvas"` | `"auto"`).

- `"svg"` (default) — SVG-based rendering. Flat stone appearance (no Phong shading).
- `"canvas"` — Canvas rendering with Phong-shaded stones (Shell/Slate themes, specular highlights, drop shadows).
- `"auto"` — Tries SVG first, falls back to Canvas on failure.

Both renderers support:

- **Custom board color** — Flat kaya wood color via `customBoardColor` callback (no CDN texture)
- **Custom line color** — Darker, more visible grid lines via `customBoardLineColor` callback
- Native ghost stone hover preview on empty intersections

The renderer preference constant is `RENDERER_PREFERENCE_KEY` in `types/goban.ts`.

## Theme Configuration

### `getSelectedThemes` Callback

Configured in `frontend/src/lib/goban-init.ts` via `setGobanCallbacks()`:

```typescript
getSelectedThemes: () => ({
  white: "Shell", // White stones with shell-grain texture
  black: "Slate", // Black stones with slate-like surface
  board: "Custom", // Custom board for full control (UI-017)
  "removal-graphic": "square",
  "removal-scale": 1.0,
  "stone-shadows": "default",
});
```

### Custom Board Theme Callbacks (UI-017)

Instead of using goban's built-in Kaya theme, YenGo uses custom callbacks for full visual control:

```typescript
customBoardColor: () => isDarkMode() ? "#2a2520" : "#E3C076",
customBoardLineColor: () => isDarkMode() ? "#8b7355" : "#4a3c28",
customBoardUrl: () => isDarkMode() ? "" : "/img/kaya.jpg",
```

Light mode uses a kaya wood grain texture (`public/img/kaya.jpg`) for a realistic board surface. Dark mode uses a solid color with no texture.

### `watchSelectedThemes` — Live Theme Switching

Uses `MutationObserver` on `<html>` element to detect `data-theme` attribute changes:

```typescript
watchSelectedThemes: (cb) => {
  const observer = new MutationObserver(() => {
    cb(getSelectedThemes());
  });
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  return { remove: () => observer.disconnect() };
};
```

This enables real-time board theme switching without page reload or goban instance recreation.

## Audio (UI-035)

Stone placement sounds are handled entirely by the goban library's sound events — `usePuzzleState` does NOT play stone sounds. It only plays:

- `audioService.play('correct')` on correct answer
- `audioService.play('wrong')` on wrong answer
- `audioService.play('complete')` on puzzle completion

## Puzzle Mode

goban's puzzle mode validates moves against the solution tree:

1. User plays a move
2. goban checks if move exists in solution tree
3. Events fired:
   - `puzzle-correct-answer`: Move is on the correct path
   - `puzzle-wrong-answer`: Move is not in solution tree
   - `puzzle-correct-answer-is-end`: Puzzle completed successfully

## Transforms

Transforms modify the SGF before passing to goban:

| Transform      | Effect                                       |
| -------------- | -------------------------------------------- |
| `flipH`        | Mirror board horizontally                    |
| `flipV`        | Mirror board vertically                      |
| `flipDiagonal` | Transpose coordinates (matrix transposition) |
| `rotateCCW`    | Rotate board 90° counter-clockwise           |
| `rotateCW`     | Rotate board 90° clockwise                   |
| `swapColors`   | Swap black/white stones + text               |
| `zoom`         | Auto-detect minimal bounds                   |

Rotation safety: Transforms physically rewrite ALL coordinates in the SGF (setup stones, moves, variations, labels) before passing to goban. The goban receives a self-consistent SGF.

## File Structure

```text
frontend/src/
├── components/
│   ├── GobanContainer/
│   │   ├── GobanContainer.tsx   # Mount goban's self-created div
│   │   ├── PersistentElement.tsx # DOM node persistence
│   │   └── index.ts
│   ├── Solver/
│   │   └── SolverView.tsx       # Main puzzle UI (sidebar + board)
│   ├── Transforms/
│   │   └── TransformBar.tsx     # Transform toolbar (8 buttons)
│   ├── ProblemNav/              # Puzzle set navigation dots
│   └── shared/
│       ├── KBShortcut.tsx       # Declarative keyboard shortcuts
│       └── icons/               # All SVG icon components
├── hooks/
│   ├── useGoban.ts              # goban lifecycle (no boardRef)
│   ├── usePuzzleState.ts        # Puzzle solving state
│   ├── useTransforms.ts         # Board transforms
│   └── useHints.ts              # Hint progression
├── lib/
│   ├── goban-init.ts            # One-time goban callbacks
│   ├── puzzle-config.ts         # GobanConfig builder
│   ├── sgf-preprocessor.ts      # SGF adaptation layer
│   └── sgf-to-puzzle.ts         # SGF→puzzle object adapter
└── pages/
    ├── CollectionViewPage.tsx   # Uses PuzzleSetPlayer→SolverView
    ├── DailyChallengePage.tsx   # Uses SolverView
    └── PuzzleRushPage.tsx       # Uses SolverView
```

## Troubleshooting

### Goban Not Rendering

1. **Check refs**: Ensure the container element is visible and has non-zero width/height
2. **Check SGF**: Validate the SGF string is not empty and parseable
3. **Check container size**: goban needs a non-zero-dimension parent

### Puzzle State Not Updating

1. **Check onGobanReady**: Ensure it's called after `isReady` is true
2. **Check goban instance**: Ensure `gobanRef.current` is not null

### Transform Issues

1. **Key changes**: If transforms don't apply, ensure the component re-mounts (key prop)
2. **Zoom bounds**: Call `getZoomBounds()` after transforms are applied

## See Also

- [Puzzle Solving Architecture](./puzzle-solving.md) — Solving lifecycle
- [Board Rendering Architecture](./svg-board.md) — Canvas vs SVG decision
- [Concepts: Dark Mode](../../concepts/dark-mode.md) — Dark mode theming strategy
- [State Management](./state-management.md) — Frontend state patterns
- [Testing](./testing.md) — E2E and visual testing
