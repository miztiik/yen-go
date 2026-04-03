/**
 * Board state types for runtime Go board manipulation
 * @module models/board
 *
 * Spec 122 - Phase 4: Updated to use Besogo integer Stone type
 */

import type { BoardSize, Coordinate, Move, Stone } from './puzzle';
import { EMPTY } from './puzzle';

/** A group of connected stones */
export interface StoneGroup {
  readonly color: Stone;  // Now uses integer Stone (-1 or 1)
  readonly stones: readonly Coordinate[];
  readonly liberties: readonly Coordinate[];
}

/** Result of placing a stone on the board */
export interface PlaceStoneResult {
  readonly success: boolean;
  readonly error?: 'occupied' | 'suicide' | 'ko';
  readonly capturedStones?: readonly Coordinate[];
  readonly newBoard?: Stone[][];
}

/** Ko state tracking */
export interface KoState {
  readonly position: Coordinate | null;
  readonly capturedAt: number; // Move number when ko was created
}

/** Complete board state for game tracking */
export interface GameBoardState {
  readonly board: Stone[][];
  readonly boardSize: BoardSize;
  readonly currentPlayer: Stone;  // Now uses integer Stone
  readonly moveNumber: number;
  readonly koState: KoState;
  readonly capturedByBlack: number;
  readonly capturedByWhite: number;
  readonly moveHistory: readonly Move[];
}

/** Direction offsets for adjacent positions */
export const DIRECTIONS: readonly Coordinate[] = [
  { x: 0, y: -1 }, // up
  { x: 0, y: 1 },  // down
  { x: -1, y: 0 }, // left
  { x: 1, y: 0 },  // right
];

/** Get adjacent coordinates (1-indexed per Besogo pattern) */
export function getAdjacentCoords(coord: Coordinate, boardSize: BoardSize): Coordinate[] {
  return DIRECTIONS.map(({ x, y }) => ({ x: coord.x + x, y: coord.y + y })).filter(
    ({ x, y }) => x >= 1 && x <= boardSize && y >= 1 && y <= boardSize
  );
}

/** Get stone at position (returns EMPTY=0 if out of bounds) */
export function getStone(board: readonly (readonly Stone[])[], coord: Coordinate): Stone {
  const row = board[coord.y];
  if (row === undefined) return EMPTY;
  return row[coord.x] ?? EMPTY;
}

/**
 * Create empty board with 1-indexed access (Besogo pattern).
 * Grid is (size+1)x(size+1), with row/col 0 unused padding.
 * Valid positions: grid[1..size][1..size]
 */
export function createEmptyBoard(size: BoardSize): Stone[][] {
  const grid: Stone[][] = [];
  for (let y = 0; y <= size; y++) {
    grid[y] = new Array(size + 1).fill(EMPTY);
  }
  return grid;
}

/** Get opponent color (Besogo pattern: -color) */
export function getOpponent(color: Stone): Stone {
  return -color as Stone;
}

/** Star point (hoshi) positions for each board size (1-indexed per Besogo) */
export const STAR_POINTS: Record<BoardSize, readonly Coordinate[]> = {
  9: [
    { x: 3, y: 3 }, { x: 7, y: 3 },
    { x: 5, y: 5 }, // tengen
    { x: 3, y: 7 }, { x: 7, y: 7 },
  ],
  13: [
    { x: 4, y: 4 }, { x: 10, y: 4 },
    { x: 7, y: 7 }, // tengen
    { x: 4, y: 10 }, { x: 10, y: 10 },
  ],
  19: [
    { x: 4, y: 4 }, { x: 10, y: 4 }, { x: 16, y: 4 },
    { x: 4, y: 10 }, { x: 10, y: 10 }, { x: 16, y: 10 }, // tengen at 10,10
    { x: 4, y: 16 }, { x: 10, y: 16 }, { x: 16, y: 16 },
  ],
};
