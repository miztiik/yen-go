/**
 * Puzzle Game State Service
 * @module services/puzzleGameState
 *
 * Provides game state interface and move validation logic.
 * Wraps functionality from rulesEngine and board models.
 */

import { isValidMove, placeStone, getNewKoState } from './rulesEngine';
import type { BoardSize, Coordinate, Stone } from '../models/puzzle';
import { BLACK, WHITE } from '../models/puzzle';
import type { KoState } from '../models/board';

// PuzzleBoard interface as requested
export interface PuzzleBoard {
  grid: Stone[][];
  size: number;
  sideToMove: 'black' | 'white';
  koState?: { position: Coordinate | null; capturedAt: number };
}

// Helper to convert 'black'|'white' to Stone
function sideToColor(side: 'black' | 'white'): Stone {
  return side === 'black' ? BLACK : WHITE;
}

/**
 * Check if a move is valid for the current puzzle state.
 */
export function isPuzzleMoveValid(board: PuzzleBoard, coord: Coordinate): boolean {
  return isValidMove(
    board.grid,
    coord,
    sideToColor(board.sideToMove),
    board.size as BoardSize,
    board.koState as KoState
  );
}

/**
 * Execute a move on the puzzle board.
 */
export function executePuzzleMove(
  board: PuzzleBoard,
  coord: Coordinate
): {
  success: boolean;
  newBoard?: PuzzleBoard;
  captures?: Coordinate[];
  error?: string;
} {
  const color = sideToColor(board.sideToMove);
  const result = placeStone(
    board.grid,
    coord,
    color,
    board.size as BoardSize,
    board.koState as KoState
  );

  if (!result.success) {
    return { success: false, error: result.error || 'Invalid move' };
  }

  const captures = result.capturedStones || [];

  // Calculate new Ko State. Logic from rulesEngine.getNewKoState
  // We use 0 as move number since PuzzleBoard doesn't track it,
  // and rulesEngine checks only depend on position equality.
  const nextKoState = getNewKoState(captures, coord, 0);

  const nextSide = board.sideToMove === 'black' ? 'white' : 'black';

  const newPuzzleBoard: PuzzleBoard = {
    grid: result.newBoard!,
    size: board.size,
    sideToMove: nextSide,
    koState: nextKoState,
  };

  return {
    success: true,
    newBoard: newPuzzleBoard,
    captures: captures ? [...captures] : [],
  };
}

/**
 * Get the reason why a move is invalid.
 */
export function getInvalidMoveReason(board: PuzzleBoard, coord: Coordinate): string | undefined {
  const color = sideToColor(board.sideToMove);
  const result = placeStone(
    board.grid,
    coord,
    color,
    board.size as BoardSize,
    board.koState as KoState
  );

  return result.success ? undefined : result.error;
}
