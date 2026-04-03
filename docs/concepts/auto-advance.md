# Auto-Advance

Last Updated: 2026-02-25

## Overview

Auto-Advance automatically moves to the next puzzle after a correct solve, with a configurable delay. This creates a smooth flow-state experience when working through puzzle sets.

## How It Works

1. **Enable** the "Auto-Advance" toggle in Settings (gear icon, top-right)
2. **Configure delay** (1–5 seconds) using the stepper that appears when the toggle is ON
3. **Solve a puzzle correctly** — a countdown ring replaces the Next button
4. After the delay expires, the next puzzle loads automatically
5. **Cancel** at any time by clicking the countdown ring or pressing `Escape`

## Where It Applies

Auto-Advance works in all puzzle-solving contexts that use the PuzzleSetPlayer:

| Context          | Route                         |         Auto-Advance         |
| ---------------- | ----------------------------- | :--------------------------: |
| Training sets    | `/contexts/training/{slug}`   |             Yes              |
| Technique focus  | `/contexts/technique/{slug}`  |             Yes              |
| Collections      | `/contexts/collection/{slug}` |             Yes              |
| Daily challenges | `/modes/daily/{date}`         |             Yes              |
| Puzzle Rush      | `/modes/rush`                 | No (has own instant advance) |
| Random puzzles   | `/modes/random`               |   No (single puzzle flow)    |

## Behavior Details

- **Correct answers only**: Auto-advance never triggers on wrong answers. Users stay on the puzzle to retry or review.
- **Cancel is per-puzzle**: Cancelling the countdown for one puzzle doesn't disable auto-advance globally. The next correct solve will start a new countdown.
- **Settings persist**: Auto-advance preference is stored in `localStorage` alongside theme and sound settings.
- **Default: OFF**: Users must opt-in. Default delay is 3 seconds.

## Keyboard Shortcuts

| Key      | Action                                         |
| -------- | ---------------------------------------------- |
| `A`      | Toggle auto-advance on/off (shows brief toast) |
| `Escape` | Cancel active countdown                        |

## Technical Architecture

- **Settings**: `autoAdvance` (boolean) and `autoAdvanceDelay` (number, 1–5) in `AppSettings` interface ([useSettings.ts](../../frontend/src/hooks/useSettings.ts))
- **Core hook**: `useAutoAdvance` ([useAutoAdvance.ts](../../frontend/src/hooks/useAutoAdvance.ts)) — reusable countdown timer with start/cancel/cleanup
- **Integration**: `PuzzleSetPlayer` wires `useAutoAdvance` between `handleComplete` (trigger) and `handleNext` (advance)
- **UI**: Countdown ring SVG in `SolverView` replaces the Next button during active countdown

## Accessibility

- Countdown button has `role="timer"` and descriptive `aria-label`
- Toast messages use `aria-live="polite"` for screen reader announcements
- Escape key always cancels active countdowns
- Delay stepper values announced via `aria-live="polite"`

> **See also**:
>
> - [Architecture: Frontend](../architecture/frontend/) — Component structure
> - [Reference: Settings](../reference/) — All configurable options
