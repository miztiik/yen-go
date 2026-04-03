/**
 * Solution traversal - navigates through puzzle solutions.
 *
 * Handles:
 * - Tracking player progress through solution tree
 * - Determining correct/incorrect moves
 * - Providing opponent responses
 * - Solution completion detection
 */

import type { SgfCoord, Side } from '../../types';
import {
  parseSolution,
  isCorrectFirstMove,
  getResponses,
  getMatchingLines,
  isSolutionComplete,
  getRemainingMoves,
  type ParsedSolution,
  type SolutionMove,
} from './parser';

/**
 * Result of checking a move against the solution.
 */
export interface MoveCheckResult {
  /** Is the move correct? */
  correct: boolean;
  /** Is this the final move of a correct line? */
  isComplete: boolean;
  /** Opponent's response (if correct and not complete) */
  response?: SgfCoord;
  /** Hint for wrong moves */
  hint?: string;
}

/**
 * Current state of solution traversal.
 */
export interface TraversalState {
  /** Parsed solution tree */
  solution: ParsedSolution;
  /** Moves made so far */
  history: SgfCoord[];
  /** Player side */
  playerSide: Side;
  /** Is the puzzle complete? */
  complete: boolean;
  /** Number of wrong attempts */
  wrongAttempts: number;
}

/**
 * Create a new traversal state for a puzzle.
 *
 * @param solutions - Raw solution data from puzzle
 * @param playerSide - Side the player is playing
 * @returns Initial traversal state
 */
export function createTraversal(
  solutions: readonly (readonly string[])[],
  playerSide: Side
): TraversalState {
  return {
    solution: parseSolution(solutions, playerSide),
    history: [],
    playerSide,
    complete: false,
    wrongAttempts: 0,
  };
}

/**
 * Check if a move is correct and advance the state.
 *
 * @param state - Current traversal state
 * @param move - Player's move
 * @returns Result of the move check and new state
 */
export function checkMove(
  state: TraversalState,
  move: SgfCoord
): { result: MoveCheckResult; newState: TraversalState } {
  if (state.complete) {
    return {
      result: { correct: false, isComplete: true, hint: 'Puzzle already complete' },
      newState: state,
    };
  }

  // Check if this is a valid move in any solution line
  const isFirstMove = state.history.length === 0;
  let isCorrect = false;

  if (isFirstMove) {
    isCorrect = isCorrectFirstMove(state.solution, move);
  } else {
    // Check if move continues any valid line
    const testHistory = [...state.history, move];
    const matchingLines = getMatchingLines(state.solution, testHistory);
    isCorrect = matchingLines.length > 0;
  }

  if (!isCorrect) {
    // Wrong move
    return {
      result: {
        correct: false,
        isComplete: false,
        hint: getHint(state),
      },
      newState: {
        ...state,
        wrongAttempts: state.wrongAttempts + 1,
      },
    };
  }

  // Correct move - update history
  const newHistory = [...state.history, move];

  // Check for completion
  const isComplete = isSolutionComplete(state.solution, newHistory);

  if (isComplete) {
    return {
      result: {
        correct: true,
        isComplete: true,
      },
      newState: {
        ...state,
        history: newHistory,
        complete: true,
      },
    };
  }

  // Get opponent response
  const responses = getResponses(state.solution, newHistory);

  if (responses.length === 0) {
    // No opponent response needed - puzzle complete
    return {
      result: {
        correct: true,
        isComplete: true,
      },
      newState: {
        ...state,
        history: newHistory,
        complete: true,
      },
    };
  }

  // Pick best response (first one for simplicity)
  const response = responses[0];
  
  // If no response, puzzle is complete
  if (!response) {
    return {
      result: {
        correct: true,
        isComplete: true,
      },
      newState: {
        ...state,
        history: newHistory,
        complete: true,
      },
    };
  }
  
  const historyWithResponse: SgfCoord[] = [...newHistory, response];

  return {
    result: {
      correct: true,
      isComplete: false,
      response,
    },
    newState: {
      ...state,
      history: historyWithResponse,
    },
  };
}

/**
 * Get a hint for the current position.
 *
 * @param state - Traversal state
 * @returns Hint string
 */
export function getHint(state: TraversalState): string {
  if (state.wrongAttempts === 0) {
    return 'Try again';
  }

  if (state.wrongAttempts === 1) {
    return 'Think about liberties and capturing';
  }

  if (state.wrongAttempts >= 2) {
    // Give more specific hint
    const remaining = getRemainingMoves(state.solution, state.history);
    const firstRemaining = remaining[0];
    if (remaining.length > 0 && firstRemaining?.isPlayerMove) {
      const nextMove = firstRemaining.coord;
      const col = nextMove.charCodeAt(0) - 'a'.charCodeAt(0);
      const row = nextMove.charCodeAt(1) - 'a'.charCodeAt(0);

      // Give approximate location
      const colHint = col < 9 ? 'left side' : col > 9 ? 'right side' : 'center';
      const rowHint = row < 9 ? 'upper' : row > 9 ? 'lower' : 'middle';

      return `Try the ${rowHint} ${colHint}`;
    }
  }

  return 'Focus on the key stones';
}

/**
 * Get the correct first move(s) - for showing solution.
 *
 * @param state - Traversal state
 * @returns Array of correct first moves
 */
export function getCorrectFirstMoves(state: TraversalState): SgfCoord[] {
  return [...state.solution.correctFirstMoves];
}

/**
 * Get the full solution from current position.
 *
 * @param state - Traversal state
 * @returns Remaining moves to complete the puzzle
 */
export function getSolution(state: TraversalState): SolutionMove[] {
  return getRemainingMoves(state.solution, state.history);
}

/**
 * Reset traversal state to beginning.
 *
 * @param state - Current state
 * @returns Reset state
 */
export function resetTraversal(state: TraversalState): TraversalState {
  return {
    ...state,
    history: [],
    complete: false,
    wrongAttempts: 0,
  };
}

/**
 * Undo the last move pair (player + opponent).
 *
 * @param state - Current state
 * @returns State with last move pair undone
 */
export function undoMove(state: TraversalState): TraversalState {
  if (state.history.length === 0) {
    return state;
  }

  // Remove last two moves (player + response) or just one if at start
  const removeCount = state.history.length >= 2 ? 2 : 1;
  const newHistory = state.history.slice(0, -removeCount);

  return {
    ...state,
    history: newHistory,
    complete: false,
  };
}

/**
 * Get progress through the puzzle.
 *
 * @param state - Traversal state
 * @returns Progress object
 */
export function getProgress(state: TraversalState): {
  movesPlayed: number;
  totalMoves: number;
  percentComplete: number;
} {
  const playerMoves = state.history.filter((_, i) => i % 2 === 0).length;
  const totalPlayerMoves = Math.ceil(state.solution.maxDepth / 2);

  return {
    movesPlayed: playerMoves,
    totalMoves: totalPlayerMoves,
    percentComplete: totalPlayerMoves > 0
      ? Math.round((playerMoves / totalPlayerMoves) * 100)
      : 100,
  };
}

/**
 * Check if player is on a correct path.
 *
 * @param state - Traversal state
 * @returns true if current history matches a valid solution line
 */
export function isOnCorrectPath(state: TraversalState): boolean {
  if (state.history.length === 0) {
    return true;
  }

  const matching = getMatchingLines(state.solution, state.history);
  return matching.length > 0;
}

/**
 * Get number of valid continuations from current position.
 *
 * @param state - Traversal state
 * @returns Number of valid next moves
 */
export function getValidContinuations(state: TraversalState): number {
  if (state.complete) {
    return 0;
  }

  const matching = getMatchingLines(state.solution, state.history);

  // Get unique next player moves
  const nextMoves = new Set<string>();
  const nextIndex = state.history.length;

  for (const line of matching) {
    if (nextIndex < line.moves.length) {
      const move = line.moves[nextIndex];
      if (move?.isPlayerMove) {
        nextMoves.add(move.coord);
      }
    }
  }

  return nextMoves.size;
}
