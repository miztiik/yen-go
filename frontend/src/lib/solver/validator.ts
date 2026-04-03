/**
 * Move validation against solution tree
 * @module lib/solver/validator
 *
 * Covers: FR-011 (Move validation), FR-013 (Correct feedback), FR-014 (Incorrect feedback)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Validation separate from rendering
 * - V. No Browser AI: Uses precomputed solution tree, not AI analysis
 */

import type { SgfCoord, Puzzle } from '../../types';
import type { PuzzleBoard } from '../../services/puzzleGameState';
import { isPuzzleMoveValid, executePuzzleMove, getInvalidMoveReason } from '../../services/puzzleGameState';
import { checkMove, type TraversalState } from './traversal';
import { positionToSgf } from '../sgf/coordinates';
import { sgfToCoord, coordToSgf } from '../../types/coordinate';

/**
 * Validation result for a move
 */
export interface ValidationResult {
  /** Is the move valid according to Go rules? */
  isLegal: boolean;
  /** Is the move correct according to the solution? */
  isCorrect: boolean;
  /** Is this the final correct move (puzzle complete)? */
  isComplete: boolean;
  /** Opponent's response (if correct and not complete) */
  opponentResponse?: SgfCoord;
  /** Captured stones from this move */
  captures?: readonly SgfCoord[];
  /** Error message if move is invalid */
  error?: string;
  /** Hint for incorrect moves */
  hint?: string;
}

/**
 * Validator configuration
 */
export interface ValidatorConfig {
  /** Current puzzle */
  puzzle: Puzzle;
  /** Current board state */
  boardState: PuzzleBoard;
  /** Current traversal state */
  traversalState: TraversalState;
  /** Allow playing on even if move is incorrect */
  allowIncorrect?: boolean;
}

/**
 * Validate a move at given coordinates
 *
 * @param x - Column (0-indexed)
 * @param y - Row (0-indexed)
 * @param config - Validator configuration
 * @returns Validation result
 */
export function validateMove(
  x: number,
  y: number,
  config: ValidatorConfig
): ValidationResult {
  const { boardState, traversalState } = config;

  // Convert to SGF coordinate (0-indexed x,y → SGF)
  const coord = positionToSgf(x, y);
  if (!coord) {
    return {
      isLegal: false,
      isCorrect: false,
      isComplete: false,
      error: 'Invalid coordinate',
    };
  }

  // Check Go rules first
  if (!isPuzzleMoveValid(boardState, sgfToCoord(coord))) {
    const reason = getInvalidMoveReason(boardState, sgfToCoord(coord));
    return {
      isLegal: false,
      isCorrect: false,
      isComplete: false,
      ...(reason && { error: reason }),
    };
  }

  // Check against solution tree
  const { result } = checkMove(traversalState, coord);

  const validationResult: ValidationResult = {
    isLegal: true,
    isCorrect: result.correct,
    isComplete: result.isComplete,
  };

  if (result.response) {
    validationResult.opponentResponse = result.response;
  }
  if (result.hint) {
    validationResult.hint = result.hint;
  }

  return validationResult;
}

/**
 * Validate a move using SGF coordinate
 *
 * @param coord - SGF coordinate
 * @param config - Validator configuration
 * @returns Validation result
 */
export function validateMoveCoord(
  coord: SgfCoord,
  config: ValidatorConfig
): ValidationResult {
  const { boardState, traversalState } = config;

  // Check Go rules first
  if (!isPuzzleMoveValid(boardState, sgfToCoord(coord))) {
    const reason = getInvalidMoveReason(boardState, sgfToCoord(coord));
    return {
      isLegal: false,
      isCorrect: false,
      isComplete: false,
      ...(reason && { error: reason }),
    };
  }

  // Check against solution tree
  const { result } = checkMove(traversalState, coord);

  const validationResult: ValidationResult = {
    isLegal: true,
    isCorrect: result.correct,
    isComplete: result.isComplete,
  };

  if (result.response) {
    validationResult.opponentResponse = result.response;
  }
  if (result.hint) {
    validationResult.hint = result.hint;
  }

  return validationResult;
}

/**
 * Execute a validated move and get the new states
 *
 * @param coord - SGF coordinate
 * @param config - Validator configuration
 * @returns New board and traversal states, or null if invalid
 */
export function executeMove(
  coord: SgfCoord,
  config: ValidatorConfig
): {
  newBoardState: PuzzleBoard;
  newTraversalState: TraversalState;
  captures: readonly SgfCoord[];
  opponentCaptures: readonly SgfCoord[];
} | null {
  const { boardState, traversalState } = config;

  // Try to make the move
  const moveResult = executePuzzleMove(boardState, sgfToCoord(coord));
  if (!moveResult.success || !moveResult.newBoard) {
    return null;
  }

  // Check against solution
  const { result, newState: newTraversal } = checkMove(traversalState, coord);
  if (!result.correct && !config.allowIncorrect) {
    return null;
  }

  let finalBoardState = moveResult.newBoard;
  let opponentCaptures: readonly SgfCoord[] = [];

  // If there's an opponent response, make that move too
  if (result.response) {
    const opponentMoveResult = executePuzzleMove(finalBoardState, sgfToCoord(result.response));
    if (opponentMoveResult.success && opponentMoveResult.newBoard) {
      finalBoardState = opponentMoveResult.newBoard;
      opponentCaptures = (opponentMoveResult.captures ?? []).map(coordToSgf);
    }
  }

  return {
    newBoardState: finalBoardState,
    newTraversalState: newTraversal,
    captures: (moveResult.captures ?? []).map(coordToSgf),
    opponentCaptures,
  };
}

/**
 * Check if the puzzle is in a failed state
 * (too many wrong attempts without progress)
 */
export function isPuzzleFailed(
  traversalState: TraversalState,
  maxAttempts: number = 5
): boolean {
  return traversalState.wrongAttempts >= maxAttempts;
}

/**
 * Validate state consistency between board and solution
 *
 * @param boardState - Current board state
 * @param traversalState - Current traversal state
 * @param puzzle - Puzzle definition
 * @returns true if states are consistent
 */
export function validateStateConsistency(
  boardState: PuzzleBoard,
  traversalState: TraversalState,
  puzzle: Puzzle
): boolean {
  // Check board size matches (use full boardSize if available, fallback to region.w)
  const expectedSize = puzzle.boardSize ?? puzzle.region.w;
  if (boardState.size !== expectedSize) {
    return false;
  }

  // Check side to move matches
  if (traversalState.complete) {
    return true; // Completed puzzles can have any side
  }

  // Player side should match history parity
  const isPlayerTurn = traversalState.history.length % 2 === 0;
  const puzzleSide = puzzle.side === 'B' ? 'black' : 'white';
  const expectedSide = isPlayerTurn ? puzzleSide : (puzzleSide === 'black' ? 'white' : 'black');
  if (boardState.sideToMove !== expectedSide) {
    return false;
  }

  return true;
}

/**
 * Create a validator function for use in components
 */
export function createMoveValidator(
  config: ValidatorConfig
): (x: number, y: number) => ValidationResult {
  return (x: number, y: number) => validateMove(x, y, config);
}

/**
 * Get all valid moves for current position
 * Useful for hint generation
 */
export function getValidMoves(config: ValidatorConfig): SgfCoord[] {
  const { boardState, traversalState } = config;
  const validMoves: SgfCoord[] = [];

  for (let y = 0; y < boardState.size; y++) {
    for (let x = 0; x < boardState.size; x++) {
      const coord = positionToSgf(x, y);
      if (coord && isPuzzleMoveValid(boardState, sgfToCoord(coord))) {
        const { result } = checkMove(traversalState, coord);
        if (result.correct) {
          validMoves.push(coord);
        }
      }
    }
  }

  return validMoves;
}

/**
 * Get hint level based on wrong attempts
 */
export function getHintLevel(wrongAttempts: number): 'none' | 'subtle' | 'moderate' | 'strong' {
  if (wrongAttempts === 0) return 'none';
  if (wrongAttempts === 1) return 'subtle';
  if (wrongAttempts === 2) return 'moderate';
  return 'strong';
}
