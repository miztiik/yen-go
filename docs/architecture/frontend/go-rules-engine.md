# Go Rules Engine

**Last Updated**: 2026-03-24

> **See also**:
>
> - [Architecture: Puzzle Solving](./puzzle-solving.md) — How rules integrate with puzzles
> - [Architecture: Board State Design](./board-state-design.md) — Coordinate system

## Overview

The Go rules engine (`services/rulesEngine.ts`) validates moves, calculates captures, and enforces ko rules. It runs entirely in the browser with no server-side computation.

**Note**: The previous `lib/rules/` directory (engine.ts, liberties.ts, captures.ts, ko.ts, suicide.ts) was deleted. All rules logic now lives in `services/rulesEngine.ts`.

## Design Principles

1. **Pure Functions**: All rules functions are pure with no side effects
2. **Immutable State**: Board state is never mutated; new state is computed
3. **No External Dependencies**: Standard library only

## Core Data Structures

### Stone Type (Integer-Based, from `models/puzzle.ts`)

```typescript
export const BLACK = -1 as const;
export const WHITE = 1 as const;
export const EMPTY = 0 as const;
type Stone = typeof BLACK | typeof WHITE | typeof EMPTY;
```

This uses the Besogo integer pattern where `WHITE === -BLACK` for easy color inversion.

### Board Representation

```typescript
type BoardState = Stone[][];        // 2D array of Stone values
interface Coordinate { x: number; y: number; }
```

### Supporting Types (from `models/board.ts`)

- `StoneGroup` — Connected stones with liberties list
- `KoState` — Tracks ko position for simple ko enforcement
- `PlaceStoneResult` — Result of placing a stone (captures, new board, ko)

## Key Functions

### `findGroup(board, start, boardSize)`

Flood-fill to find all connected stones of the same color, plus their liberties. Returns a `StoneGroup` with stones array and liberties array.

### `findCaptures(board, coord, boardSize)`

After placing a stone, checks all four neighbors for opponent chains with zero liberties.

### `placeStone(board, coord, color, boardSize, koState)`

Full move validation pipeline:
1. Check bounds and occupation
2. Place stone on board copy
3. Find and remove opponent captures
4. Check for ko violation
5. Check for suicide (if no captures)
6. Return `PlaceStoneResult` with new board state

## Integration

- `services/solutionVerifier.ts` uses the rules engine for legality checks
- `services/puzzleGameState.ts` manages the solving state machine
- Board rendering is handled by the `goban` library (untouched external dependency)

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Place stone | O(1) | Array write |
| Find group (flood fill) | O(n) | n = board cells (max 361) |
| Find captures | O(4n) | Check 4 neighbors |
| Ko check | O(1) | Compare previous position |

## See Also

- [Puzzle Solving Flow](./puzzle-solving.md) - How rules integrate with puzzles
- [Board State Design](./board-state-design.md) - Coordinate system
