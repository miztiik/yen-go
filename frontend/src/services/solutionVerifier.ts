/**
 * Solution Verifier Service
 * @module services/solutionVerifier
 *
 * Validates player moves against precomputed solution trees.
 * Implements tree traversal for correct/incorrect move detection.
 *
 * Covers: FR-002 to FR-007, US1
 */

import type {
  Coordinate,
  Move,
  MoveValidationResult,
  Puzzle,
  SolutionNode,
  Explanation,
} from '../models/puzzle';
import { coordsEqual, BLACK, WHITE } from '../models/puzzle';

/**
 * Result of verifying a move against the solution tree
 */
export interface VerificationResult {
  /** Whether the move is valid according to Go rules */
  isLegal: boolean;
  /** Whether the move matches a correct continuation */
  isCorrect: boolean;
  /** The matched solution node if correct */
  matchedNode?: SolutionNode;
  /** Feedback message for the player */
  feedback: 'correct' | 'incorrect' | 'optimal' | 'suboptimal';
  /** Explanation text if available */
  explanation?: string;
  /** Whether this move completes the puzzle */
  isComplete: boolean;
  /** Response move from opponent (if any) */
  responseMove?: Coordinate;
}

/**
 * State of the solution verification
 */
export interface SolutionState {
  /** Current position in solution tree */
  currentNode: SolutionNode;
  /** Path of moves taken */
  moveHistory: Move[];
  /** Whether puzzle is complete */
  isComplete: boolean;
}

/**
 * Create initial solution state from puzzle
 */
export function createSolutionState(puzzle: Puzzle): SolutionState {
  return {
    currentNode: puzzle.solutionTree,
    moveHistory: [],
    isComplete: false,
  };
}

/**
 * Verify a move against the solution tree
 */
export function verifyMove(
  state: SolutionState,
  move: Coordinate,
  _playerColor: 'black' | 'white'
): VerificationResult {
  const { currentNode } = state;

  // Check if current node matches the move
  if (coordsEqual(currentNode.move, move)) {
    // This is the correct move
    const isComplete = !currentNode.branches || currentNode.branches.length === 0;
    const result: VerificationResult = {
      isLegal: true,
      isCorrect: true,
      matchedNode: currentNode,
      feedback: 'optimal',
      isComplete,
    };
    if (currentNode.response) {
      result.responseMove = currentNode.response;
    }
    return result;
  }

  // Check if move matches any branch
  const branches = currentNode.branches ?? [];
  for (const branch of branches) {
    if (coordsEqual(branch.move, move)) {
      const isComplete = !branch.branches || branch.branches.length === 0;
      const isOptimal = branches.indexOf(branch) === 0;
      const result: VerificationResult = {
        isLegal: true,
        isCorrect: true,
        matchedNode: branch,
        feedback: isOptimal ? 'optimal' : 'suboptimal',
        isComplete: isComplete || branch.isWinning === true,
      };
      if (branch.response) {
        result.responseMove = branch.response;
      }
      return result;
    }
  }

  // Move doesn't match
  return {
    isLegal: true,
    isCorrect: false,
    feedback: 'incorrect',
    isComplete: false,
  };
}

/**
 * Advance solution state after a correct move
 */
export function advanceSolutionState(
  state: SolutionState,
  matchedNode: SolutionNode,
  move: Coordinate
): SolutionState {
  const newMove: Move = {
    x: move.x,
    y: move.y,
    color: BLACK, // Assuming player is black
  };

  // Find the next node to continue from
  let nextNode = matchedNode;
  
  // If there's a response and branches, move to first branch after response
  if (matchedNode.response && matchedNode.branches && matchedNode.branches.length > 0) {
    nextNode = matchedNode.branches[0]!;
  }

  const isComplete = !nextNode.branches || nextNode.branches.length === 0;

  return {
    currentNode: nextNode,
    moveHistory: [...state.moveHistory, newMove],
    isComplete: isComplete || matchedNode.isWinning === true,
  };
}

/**
 * Find explanation for a move in the puzzle
 */
export function findExplanation(
  puzzle: Puzzle,
  move: Coordinate
): Explanation | undefined {
  return puzzle.explanations.find((e) => coordsEqual(e.move, move));
}

/**
 * Get all valid moves from current state
 */
export function getValidMoves(state: SolutionState): Coordinate[] {
  const { currentNode } = state;
  const moves: Coordinate[] = [currentNode.move];

  // Add branch moves
  const branches = currentNode.branches ?? [];
  for (const branch of branches) {
    moves.push(branch.move);
  }

  return moves;
}

/**
 * Get hint for current position (returns next correct move)
 */
export function getHint(
  state: SolutionState,
  _hintLevel: number
): Coordinate | null {
  return state.currentNode.move;
}

/** Solution marker type for UI display */
export interface SolutionMarkerData {
  coord: Coordinate;
  type: 'correct' | 'wrong' | 'optimal';
}

/**
 * Get solution markers showing correct and wrong moves for solution reveal
 * Returns markers for all possible next moves, categorized as:
 * - 'optimal': The best/primary correct move
 * - 'correct': Alternative correct moves (branches)
 * - 'wrong': Common wrong moves from refutations
 */
export function getSolutionMarkers(
  state: SolutionState,
  _boardSize: number
): SolutionMarkerData[] {
  const markers: SolutionMarkerData[] = [];
  const { currentNode } = state;
  const markedCoords = new Set<string>();

  // Mark the optimal (primary) move
  const optimalMove = currentNode.move;
  const optimalKey = `${optimalMove.x},${optimalMove.y}`;
  markers.push({ coord: optimalMove, type: 'optimal' });
  markedCoords.add(optimalKey);

  // Mark alternative correct moves (branches that lead to winning)
  const branches = currentNode.branches ?? [];
  for (const branch of branches) {
    const key = `${branch.move.x},${branch.move.y}`;
    if (!markedCoords.has(key)) {
      // Check if this branch is a winning line
      const isCorrect = branch.isWinning !== false;
      markers.push({ 
        coord: branch.move, 
        type: isCorrect ? 'correct' : 'wrong' 
      });
      markedCoords.add(key);
    }
  }

  return markers;
}

/**
 * Check if current state has any correct moves
 */
export function hasCorrectMoves(_state: SolutionState): boolean {
  return true; // Current node always has a move
}

/**
 * Get the solution path from current state to completion
 */
export function getSolutionPath(state: SolutionState): Move[] {
  const path: Move[] = [];
  let node: SolutionNode | undefined = state.currentNode;
  let moveNum = state.moveHistory.length + 1;

  while (node) {
    path.push({
      x: node.move.x,
      y: node.move.y,
      color: moveNum % 2 === 1 ? BLACK : WHITE,
    });
    moveNum++;

    // Move to next node via first branch
    if (node.branches && node.branches.length > 0) {
      node = node.branches[0];
    } else {
      break;
    }
  }

  return path;
}

/**
 * Validate move result combining rules engine and solution verification
 */
export function validateMove(
  puzzle: Puzzle,
  state: SolutionState,
  move: Coordinate,
  rulesValid: boolean
): MoveValidationResult {
  if (!rulesValid) {
    return {
      isCorrect: false,
      explanation: 'Invalid move according to Go rules',
    };
  }

  const verification = verifyMove(state, move, puzzle.sideToMove);

  if (!verification.isCorrect) {
    return {
      isCorrect: false,
      explanation: 'Incorrect - try a different move',
    };
  }

  // Find explanation if available
  const explanation = findExplanation(puzzle, move);
  const explanationText = explanation?.text ?? (verification.feedback === 'optimal'
    ? 'Correct!'
    : 'Correct, but there may be a better move');

  // Build result with conditional nextNode
  if (verification.matchedNode) {
    return {
      isCorrect: true,
      response: verification.responseMove ?? null,
      nextNode: verification.matchedNode,
      isWinning: verification.isComplete,
      explanation: explanationText,
    };
  }

  return {
    isCorrect: true,
    response: verification.responseMove ?? null,
    isWinning: verification.isComplete,
    explanation: explanationText,
  };
}
