# SolverView Usage Guide

> **See also**:
>
> - [Architecture: UI Layout](../../architecture/frontend/ui-layout.md) — Component hierarchy
> - [Architecture: Puzzle Solving](../../architecture/frontend/puzzle-solving.md) — Move validation
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — YH, YG, YT properties

**Last Updated**: 2026-02-15

---

## Overview

`SolverView` is the shared puzzle-solving component used across all puzzle modes. It integrates the goban library, validates moves, and exposes progressive hints and solution reveal.

---

## Basic Usage

```tsx
import { SolverView } from "@components/Solver/SolverView";

function MyPuzzlePage() {
  return (
    <SolverView
      sgf={sgfString}
      level="beginner"
      onComplete={(result) => console.log("Puzzle complete:", result)}
      onNext={() => loadNextPuzzle()}
      onSkip={() => skipPuzzle()}
    />
  );
}
```

### Props

| Prop         | Type               | Required | Description                                       |
| ------------ | ------------------ | -------- | ------------------------------------------------- |
| `sgf`        | `string`           | Yes      | Raw SGF string for the puzzle                     |
| `level`      | `string`           | Yes      | Level slug (e.g., `'beginner'`, `'intermediate'`) |
| `onComplete` | `(result) => void` | No       | Called when puzzle is solved                      |
| `onNext`     | `() => void`       | No       | Handler for "Next puzzle" button                  |
| `onSkip`     | `() => void`       | No       | Handler for "Skip" button                         |

---

## Data Attributes (for testing)

| Attribute                          | Element          | Values                                    |
| ---------------------------------- | ---------------- | ----------------------------------------- |
| `data-component="solver-view"`     | Root             | —                                         |
| `data-status`                      | Root             | `waiting`, `correct`, `wrong`, `complete` |
| `data-component="hint-overlay"`    | Hints section    | —                                         |
| `data-component="solution-reveal"` | Solution section | —                                         |
| `data-component="move-explorer"`   | Explorer section | —                                         |

---

## Sub-Components

### HintOverlay

Reveals hints progressively from the SGF `YH` property:

```sgf
YH[Corner focus|Ladder pattern|Black lives]
```

Hints are pipe-delimited, max 3. HintOverlay shows them one at a time.

### SolutionReveal

Button to show the full solution. Once activated, shows a "Next Move" stepper through the solution tree.

### MoveExplorer

Navigates the move tree, showing variations and comments from the SGF `C[]` properties on moves.

---

## Coordinate Toggle

The coordinate toggle button persists its state via `useSettings()`:

```tsx
// Inside SolverView, the toggle is always visible:
<button
  aria-label="Toggle coordinates"
  aria-pressed={settings.coordinateLabels}
  onClick={() => updateSetting("coordinateLabels", !settings.coordinateLabels)}
/>
```

Settings are persisted to `localStorage:yengo:settings` via `@preact/signals`.

---

## Integration with PuzzleSetPlayer

For collection/daily pages, use `PuzzleSetPlayer` which wraps `SolverView`:

```tsx
import { PuzzleSetPlayer } from "@components/PuzzleSetPlayer";
import { CollectionPuzzleLoader } from "@services/puzzleLoaders";

function CollectionPage({ level }) {
  const loader = new CollectionPuzzleLoader(level);
  return (
    <PuzzleSetPlayer
      loader={loader}
      onBack={goHome}
      renderHeader={({ current, total }) => (
        <span>
          Puzzle {current} of {total}
        </span>
      )}
    />
  );
}
```

---

## useSettings() API

The `useSettings()` hook provides reactive settings via `@preact/signals`:

```tsx
import { useSettings } from "@hooks/useSettings";

function MyComponent() {
  const { settings, updateSetting, resetSettings } = useSettings();

  return (
    <div>
      <p>Theme: {settings.theme}</p>
      <p>Coordinates: {settings.coordinateLabels ? "on" : "off"}</p>
      <button onClick={() => updateSetting("theme", "dark")}>Dark Mode</button>
    </div>
  );
}
```

### Available Settings

| Key                | Type                | Default   | Description                 |
| ------------------ | ------------------- | --------- | --------------------------- |
| `theme`            | `'light' \| 'dark'` | `'light'` | UI theme                    |
| `coordinateLabels` | `boolean`           | `true`    | Show board coordinates      |
| `soundEnabled`     | `boolean`           | `true`    | Play move sounds            |
| `autoAdvance`      | `boolean`           | `false`   | Auto-advance to next puzzle |

---

## Tailwind Token Reference

All components use CSS custom properties from `app.css @theme`:

| Token        | CSS Variable           | Usage                         |
| ------------ | ---------------------- | ----------------------------- |
| Accent       | `--color-accent`       | Buttons, links, active states |
| Background   | `--color-bg-primary`   | Page background               |
| Secondary BG | `--color-bg-secondary` | Card backgrounds              |
| Primary text | `--color-text-primary` | Headings                      |
| Muted text   | `--color-text-muted`   | Labels, secondary text        |
| Success      | `--color-success`      | Correct answer, positive      |
| Error        | `--color-error`        | Wrong answer, negative        |
| Warning      | `--color-warning`      | Caution states                |

Use in Tailwind: `className="text-[--color-text-muted] bg-[--color-bg-secondary]"`
