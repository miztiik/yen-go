# Rush Play Mode

**Last Updated**: 2026-02-21

Puzzle Rush is a timed challenge where you solve as many Go puzzles as possible before time runs out or you lose all your lives.

## Features

### Duration Selection

Choose from preset durations or set a custom time:

| Preset | Duration | Description                       |
| ------ | -------- | --------------------------------- |
| 3 min  | 180s     | Quick sprint — warm-ups           |
| 5 min  | 300s     | Classic challenge — balanced pace |
| 10 min | 600s     | Marathon — test endurance         |
| Custom | 1–30 min | Any duration via slider           |

Custom duration uses 30-second steps from 1–5 min, then 60-second steps from 5–30 min.

### Level & Technique Filtering

Optionally filter puzzles by:

- **Difficulty Level** — All, Novice, Beginner, Elementary, ..., Expert (from level master index)
- **Technique** — All, Life & Death, Ladder, Ko, etc. (from tag master index)

Cascading counts update in real-time: selecting a level shows how many puzzles of each technique exist at that level, and vice versa.

The "~N puzzles available" indicator shows the intersection count. A warning appears if fewer than 20 puzzles match.

### Gameplay

1. Puzzles are served one after another
2. Each wrong answer costs 1 life (3 lives total)
3. Skipping costs 1 life
4. Build streaks for bonus points (1.5× multiplier at 5-streak)
5. Game ends when time runs out or all lives are lost

### Scoring

- Base: 100 points per correct puzzle
- Streak bonus: 1.5× at 5+ consecutive correct answers
- Best score saved to `localStorage`

## Architecture

```
RushBrowsePage (setup screen)
  → useMasterIndexes() — loads level + tag master indexes
  → useFilterState() — cascading filter state
  → FilterBar (level pills) + FilterDropdown (technique)
  → user picks duration + optional filters → onStartRush(duration, levelId, tagId)

App (state owner)
  → rushDuration, rushLevelId, rushTagId state
  → getNextPuzzle() — uses rushLevelId/rushTagId from closure
    → Level selected: loadLevelIndex(slug), filter by tag if needed
    → Tag only: loadRushTagEntries(tagId)
    → Neither: random level from SKILL_LEVELS
  → RushPuzzleRenderer → InlinePuzzleSolver → GobanContainer

PuzzleRushPage (game mode)
  → states: countdown → playing → finished
  → useRushSession(duration) — timer, score, streak, lives
  → RushOverlay — HUD (timer, lives, score, streak)
  → loadNextPuzzle() → getNextPuzzle() → renders puzzle
```

### Key Files

| File                              | Purpose                                             |
| --------------------------------- | --------------------------------------------------- |
| `pages/RushBrowsePage.tsx`        | Setup screen with duration, level, tag selection    |
| `pages/PuzzleRushPage.tsx`        | Game mode with countdown, board, HUD                |
| `hooks/useRushSession.ts`         | Timer, lives, score, streak management              |
| `components/rush/RushOverlay.tsx` | In-game HUD overlay                                 |
| `app.tsx`                         | `getNextPuzzle()`, Rush state, `RushPuzzleRenderer` |

### Puzzle Loading Strategy

| Filter Combination | Data Source                                                           |
| ------------------ | --------------------------------------------------------------------- |
| Level + Tag        | SQLite query: `getPuzzlesFiltered({ levelId, tagIds })` (AND semantics) |
| Level only         | SQLite query: `getPuzzlesByLevel(levelId)`                             |
| Tag only           | SQLite query: `getPuzzlesByTag(tagId)`                                 |
| Neither            | Random level from `SKILL_LEVELS`                                       |

Deduplication: `usedPuzzleIds` Set tracks loaded puzzles by hash ID. Pool resets when exhausted.

> **See also**:
>
> - [Architecture: Puzzle Modes](../../architecture/frontend/puzzle-modes.md) — All game modes overview
> - [Architecture: State Management](../../architecture/frontend/state-management.md) — App state patterns
