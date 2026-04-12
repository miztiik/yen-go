/**
 * Board-related type definitions (Besogo Gold Standard)
 * @module types/board
 *
 * Spec 122 - Phase 4, T4.2 (Besogo Gold Standard)
 *
 * Key conventions:
 * - Stone values are integers: BLACK=-1, WHITE=1, EMPTY=0
 * - Board grid uses 1-indexed access: grid[y][x] where x,y ∈ 1..size
 * - Index 0 is unused padding to enable direct 1-indexed access
 * - Ko is computed from move history, NOT stored (Besogo pattern)
 * - Captures stored as count, not position array (Besogo pattern)
 */

import type { Coord } from './coordinate';

/**
 * Supported board sizes
 */
export type BoardSize = 9 | 13 | 19;

// =============================================================================
// Stone Values (Besogo convention from gameRoot.js)
// =============================================================================

/**
 * Stone values (Besogo convention).
 * Using integers for efficient comparison and board scoring.
 *
 * Benefits:
 * - Easy opponent calculation: nextColor = -currentColor
 * - Board scoring: sum(grid) gives territory difference
 * - Falsy empty check: if (stone) vs if (stone !== 'empty')
 */
export type Stone = -1 | 0 | 1;

/** Black stone (Besogo: BLACK = -1) */
export const BLACK: Stone = -1;

/** White stone (Besogo: WHITE = 1, equals -BLACK) */
export const WHITE: Stone = 1;

/** Empty intersection (Besogo: EMPTY = 0, any falsy value) */
export const EMPTY: Stone = 0;

/**
 * @deprecated Use 'black' | 'white' strings only for display.
 * For game logic, use Stone type (-1/0/1).
 */
export type StoneColor = 'black' | 'white';

// =============================================================================
// Board Grid (Besogo pattern with 1-indexed access)
// =============================================================================

/**
 * Board grid as 2D array with 1-indexed access.
 *
 * Access: grid[y][x] where x,y are 1-indexed (1 to size inclusive)
 * Index 0 is UNUSED padding to enable direct 1-indexed access.
 *
 * OFF-BY-ONE PREVENTION: NEVER do grid[y-1][x-1] — array is pre-padded!
 */
export type BoardGrid = Stone[][];

/**
 * Immutable board grid for read-only contexts.
 */
export type ReadonlyBoardGrid = readonly (readonly Stone[])[];

/**
 * @deprecated Use BoardGrid. Legacy type for backward compatibility.
 */
export type BoardState = BoardGrid;

/**
 * @deprecated Use ReadonlyBoardGrid.
 */
export type ReadonlyBoardState = ReadonlyBoardGrid;

// =============================================================================
// Move and Game State (Besogo pattern)
// =============================================================================

/**
 * Move record (Besogo pattern from gameRoot.js).
 *
 * Note: captures is a COUNT, not a position array.
 * If positions are needed for animation, compute from board diff.
 */
export interface Move {
  readonly x: number;          // 1-indexed column
  readonly y: number;          // 1-indexed row
  readonly color: Stone;       // BLACK (-1) or WHITE (1)
  readonly captures: number;   // Count only (Besogo pattern)
  readonly overwrite: boolean; // Was this move an overwrite?
}

/**
 * Complete board state for game logic.
 *
 * Note: Ko is computed from move history, NOT stored (Besogo pattern).
 * Use isKoViolation() function to check ko during move validation.
 */
export interface GameBoardState {
  /** Board size (9, 13, or 19) */
  readonly size: number;

  /** Stone grid: grid[y][x], 1-indexed (index 0 unused) */
  readonly grid: BoardGrid;

  /** Current side to move: BLACK (-1) or WHITE (1) */
  readonly sideToMove: Stone;

  // NO koPoint field - compute from previous move (Besogo pattern)
}

/**
 * @deprecated Use GameBoardState from board.ts. Legacy coordinate type.
 */
export interface Coordinate {
  readonly x: number;
  readonly y: number;
}

// =============================================================================
// Board Operations (1-indexed access)
// =============================================================================

/**
 * Create an empty board with 1-indexed padding.
 *
 * Creates grid of size (size+1) x (size+1) so that:
 * - grid[0][*] is unused padding
 * - grid[*][0] is unused padding
 * - Valid positions: grid[1..size][1..size]
 *
 * @param size - Board size (9, 13, or 19)
 * @returns Empty board grid with padding
 */
export function createEmptyGrid(size: number): BoardGrid {
  const grid: BoardGrid = [];
  for (let y = 0; y <= size; y++) {
    grid[y] = new Array<Stone>(size + 1).fill(EMPTY);
  }
  return grid;
}

/**
 * @deprecated Use createEmptyGrid. Legacy function name.
 */
export function createEmptyBoard(size: BoardSize): BoardGrid {
  return createEmptyGrid(size);
}

/**
 * Create initial board state.
 *
 * @param size - Board size (9, 13, or 19)
 * @param sideToMove - Starting side (default BLACK)
 */
export function createBoardState(size: number, sideToMove: Stone = BLACK): GameBoardState {
  return {
    size,
    grid: createEmptyGrid(size),
    sideToMove,
  };
}

/**
 * Clone a board grid (shallow copy of rows).
 */
export function cloneGrid(grid: BoardGrid): BoardGrid {
  return grid.map(row => [...row]);
}

/**
 * @deprecated Use cloneGrid.
 */
export function cloneBoard(board: ReadonlyBoardGrid): BoardGrid {
  return board.map((row) => [...row]);
}

/**
 * Check if coordinate is within board bounds (1-indexed).
 *
 * Besogo bounds: x >= 1 && y >= 1 && x <= size && y <= size
 */
export function isValidCoordinate(c: Coord, size: number): boolean {
  return c.x >= 1 && c.x <= size && c.y >= 1 && c.y <= size;
}

/**
 * Check if x,y values are within board bounds (1-indexed).
 */
export function isValidXY(x: number, y: number, size: number): boolean {
  return x >= 1 && x <= size && y >= 1 && y <= size;
}

/**
 * Get stone at coordinate (1-indexed).
 */
export function getStone(grid: ReadonlyBoardGrid, c: Coord): Stone {
  const row = grid[c.y];
  if (row === undefined) return EMPTY;
  return row[c.x] ?? EMPTY;
}

/**
 * Get stone at x,y position (1-indexed).
 */
export function getStoneAt(grid: ReadonlyBoardGrid, x: number, y: number): Stone {
  const row = grid[y];
  if (row === undefined) return EMPTY;
  return row[x] ?? EMPTY;
}

/**
 * Set stone at coordinate (mutates grid, 1-indexed).
 */
export function setStone(grid: BoardGrid, c: Coord, stone: Stone): void {
  const row = grid[c.y];
  if (row !== undefined) {
    row[c.x] = stone;
  }
}

/**
 * Set stone at x,y position (mutates grid, 1-indexed).
 */
export function setStoneAt(grid: BoardGrid, x: number, y: number, stone: Stone): void {
  const row = grid[y];
  if (row !== undefined) {
    row[x] = stone;
  }
}

/**
 * Get adjacent coordinates (orthogonal only, 1-indexed)
 */
export function getAdjacentCoords(c: Coord, size: number): readonly Coord[] {
  const deltas = [
    { x: -1, y: 0 },
    { x: 1, y: 0 },
    { x: 0, y: -1 },
    { x: 0, y: 1 },
  ];

  return deltas
    .map((d) => ({ x: c.x + d.x, y: c.y + d.y }))
    .filter((adj) => isValidCoordinate(adj, size));
}

// =============================================================================
// Stone Color Utilities
// =============================================================================

/**
 * Get opponent color.
 * Besogo pattern: opponent = -color
 */
export function opponent(color: Stone): Stone {
  return -color as Stone;
}

/**
 * Convert Stone integer to display color string.
 */
export function stoneToColor(stone: Stone): 'black' | 'white' | null {
  if (stone === BLACK) return 'black';
  if (stone === WHITE) return 'white';
  return null;
}

/**
 * Convert display color string to Stone integer.
 */
export function colorToStone(color: 'black' | 'white'): Stone {
  return color === 'black' ? BLACK : WHITE;
}

/**
 * Convert Side string ('B'/'W') to Stone integer.
 */
export function sideToStone(side: 'B' | 'W'): Stone {
  return side === 'B' ? BLACK : WHITE;
}

/**
 * Convert Stone integer to Side string.
 */
export function stoneToSide(stone: Stone): 'B' | 'W' {
  return stone === BLACK ? 'B' : 'W';
}

// =============================================================================
// Backward Compatibility (Legacy Types - Will Be Removed)
// =============================================================================

/**
 * @deprecated Use Coord from types/coordinate.ts.
 * Board position - alias for Coord.
 */
export type BoardPosition = Coord;

/**
 * @deprecated Use different representation.
 * Group of connected stones - legacy type for rules engine.
 */
export interface StoneGroup {
  /** Stone color */
  readonly color: Stone;
  /** Coordinates of stones in the group */
  readonly stones: readonly Coord[];
  /** Liberty count */
  readonly liberties: number;
  /** Coordinates of liberties */
  readonly libertyPoints: readonly Coord[];
}

/**
 * @deprecated Use different representation.
 * Result of placing a stone - legacy type.
 */
export interface MoveResult {
  /** Whether the move was valid */
  readonly valid: boolean;
  /** New board state after move */
  readonly newBoard?: BoardGrid;
  /** Number of captures */
  readonly captures?: number;
  /** Reason for invalid move */
  readonly error?: 'occupied' | 'suicide' | 'ko';
}

/**
 * @deprecated Ko is computed from move history, not stored (Besogo pattern).
 * Ko position tracking - legacy type.
 */
export interface KoState {
  /** Position that cannot be played (ko rule) */
  readonly forbidden: Coord | null;
  /** Last capture position (for ko detection) */
  readonly lastCapture: Coord | null;
  /** Number of stones captured in last move */
  readonly lastCaptureCount: number;
}

// Re-export coordinate functions for backward compatibility
export { coordToSgf, sgfToCoord } from './coordinate';
