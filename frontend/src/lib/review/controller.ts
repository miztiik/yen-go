/**
 * Review mode controller for solution playback.
 * Manages stepping through solution moves.
 * @module lib/review/controller
 */

import type { PuzzleWithId, SgfCoord } from '../../types/puzzle';
import { sgfToPoint, type Point } from '../sgf/coordinates';

/**
 * Move in the solution with additional metadata.
 */
export interface ReviewMove {
  /** Move index (0-based) */
  readonly index: number;
  /** SGF coordinate */
  readonly coord: SgfCoord;
  /** Board point */
  readonly point: Point;
  /** Stone color */
  readonly color: 'B' | 'W';
  /** Optional explanation text */
  readonly explanation?: string;
}

/**
 * Review state at any point in the playback.
 */
export interface ReviewState {
  /** All moves in the solution */
  readonly moves: readonly ReviewMove[];
  /** Current move index (-1 = initial position, 0 = first move, etc.) */
  readonly currentIndex: number;
  /** Moves played so far (up to and including currentIndex) */
  readonly playedMoves: readonly ReviewMove[];
  /** Can go to previous move? */
  readonly canGoBack: boolean;
  /** Can go to next move? */
  readonly canGoForward: boolean;
  /** Is at the end of the solution? */
  readonly isComplete: boolean;
  /** Total number of moves */
  readonly totalMoves: number;
}

/**
 * Default explanations for common move types.
 * Note: Currently unused but kept for future implementation.
 *
 * Possible values:
 * - atari: 'This move puts the opponent in atari.'
 * - capture: 'This move captures stones.'
 * - connect: 'This move connects groups.'
 * - cut: 'This move cuts the opponent.'
 * - eye: 'This move makes or destroys eye space.'
 * - ko: 'This move starts or resolves a ko.'
 * - tesuji: 'This is a key tesuji move.'
 */

/**
 * Generate explanation for a move based on puzzle tags.
 */
function generateExplanation(
  _move: ReviewMove,
  moveNumber: number,
  totalMoves: number,
  tags: readonly string[] = []
): string | undefined {
  // First move often has a special explanation
  if (moveNumber === 0) {
    if (tags.includes('capturing')) return 'The key move to capture.';
    if (tags.includes('life')) return 'The vital point for life.';
    if (tags.includes('death')) return 'The killing move.';
    if (tags.includes('ko')) return 'This move initiates the ko.';
    if (tags.includes('tesuji')) return 'The tesuji move.';
    return 'The first move of the solution.';
  }

  // Last move
  if (moveNumber === totalMoves - 1) {
    return 'The final move completes the solution.';
  }

  // Response moves (odd indices are opponent responses in typical puzzles)
  if (moveNumber % 2 === 1) {
    return "The opponent's best response.";
  }

  return undefined;
}

/**
 * Review mode controller for stepping through solutions.
 */
export class ReviewController {
  private puzzle: PuzzleWithId;
  private solutionIndex: number;
  private moves: ReviewMove[];
  private currentIndex: number;

  /**
   * Create a new review controller.
   * @param puzzle - The puzzle to review
   * @param solutionIndex - Which solution path to use (default: 0)
   */
  constructor(puzzle: PuzzleWithId, solutionIndex = 0) {
    this.puzzle = puzzle;
    this.solutionIndex = Math.min(solutionIndex, puzzle.sol.length - 1);
    this.moves = this.buildMoves();
    this.currentIndex = -1; // Start at initial position
  }

  /**
   * Build the move list from the solution.
   */
  private buildMoves(): ReviewMove[] {
    const solution = this.puzzle.sol[this.solutionIndex];
    if (!solution || solution.length === 0) {
      return [];
    }

    // Determine starting color
    let currentColor: 'B' | 'W' = this.puzzle.side;
    const moves: ReviewMove[] = [];

    for (let index = 0; index < solution.length; index++) {
      const coord = solution[index];
      if (!coord) continue;
      const point = sgfToPoint(coord);
      if (!point) continue;

      const explanation = generateExplanation(
        { index, coord, point, color: currentColor },
        index,
        solution.length,
        this.puzzle.tags || []
      );

      const move: ReviewMove = {
        index,
        coord,
        point,
        color: currentColor,
        ...(explanation !== undefined && { explanation }),
      };

      moves.push(move);
      // Alternate colors
      currentColor = currentColor === 'B' ? 'W' : 'B';
    }

    return moves;
  }

  /**
   * Get the current review state.
   */
  getState(): ReviewState {
    return {
      moves: this.moves,
      currentIndex: this.currentIndex,
      playedMoves: this.moves.slice(0, this.currentIndex + 1),
      canGoBack: this.currentIndex >= 0,
      canGoForward: this.currentIndex < this.moves.length - 1,
      isComplete: this.currentIndex === this.moves.length - 1,
      totalMoves: this.moves.length,
    };
  }

  /**
   * Get the current move (or null if at initial position).
   */
  getCurrentMove(): ReviewMove | null {
    if (this.currentIndex < 0) return null;
    return this.moves[this.currentIndex] ?? null;
  }

  /**
   * Go to the next move.
   * @returns The new state
   */
  next(): ReviewState {
    if (this.currentIndex < this.moves.length - 1) {
      this.currentIndex++;
    }
    return this.getState();
  }

  /**
   * Go to the previous move.
   * @returns The new state
   */
  previous(): ReviewState {
    if (this.currentIndex >= 0) {
      this.currentIndex--;
    }
    return this.getState();
  }

  /**
   * Go to a specific move index.
   * @param index - Move index (-1 for initial position)
   * @returns The new state
   */
  goTo(index: number): ReviewState {
    this.currentIndex = Math.max(-1, Math.min(index, this.moves.length - 1));
    return this.getState();
  }

  /**
   * Go to the beginning (initial position).
   * @returns The new state
   */
  toBeginning(): ReviewState {
    this.currentIndex = -1;
    return this.getState();
  }

  /**
   * Go to the end (last move).
   * @returns The new state
   */
  toEnd(): ReviewState {
    this.currentIndex = this.moves.length - 1;
    return this.getState();
  }

  /**
   * Reset to initial position.
   */
  reset(): void {
    this.currentIndex = -1;
  }

  /**
   * Get the puzzle being reviewed.
   */
  getPuzzle(): PuzzleWithId {
    return this.puzzle;
  }

  /**
   * Get all available solution paths.
   */
  getSolutionCount(): number {
    return this.puzzle.sol.length;
  }

  /**
   * Switch to a different solution path.
   */
  switchSolution(index: number): ReviewState {
    if (index >= 0 && index < this.puzzle.sol.length) {
      this.solutionIndex = index;
      this.moves = this.buildMoves();
      this.currentIndex = -1;
    }
    return this.getState();
  }
}

/**
 * Create a review controller for a puzzle.
 */
export function createReviewController(puzzle: PuzzleWithId, solutionIndex = 0): ReviewController {
  return new ReviewController(puzzle, solutionIndex);
}
