/**
 * Puzzle completion detection
 * @module lib/solver/completion
 *
 * Covers: FR-016 (Puzzle completion)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Completion logic separate from UI
 * - V. No Browser AI: Solution tree traversal only
 */

import type { Puzzle } from '../../types';
import type { TraversalState } from './traversal';
import { getProgress } from './traversal';

/**
 * Completion status of a puzzle
 */
export type CompletionStatus =
  | 'not_started'
  | 'in_progress'
  | 'failed'
  | 'complete';

/**
 * Completion result with details
 */
export interface CompletionResult {
  /** Status of the puzzle */
  status: CompletionStatus;
  /** Is the puzzle complete? */
  isComplete: boolean;
  /** Was the puzzle failed? */
  isFailed: boolean;
  /** Number of moves made */
  movesPlayed: number;
  /** Total moves in solution */
  totalMoves: number;
  /** Percentage complete */
  percentComplete: number;
  /** Number of wrong attempts */
  wrongAttempts: number;
  /** Time taken (if tracking) */
  timeTaken?: number;
  /** Whether hints were used */
  hintsUsed?: number;
}

/**
 * Completion event data
 */
export interface CompletionEvent {
  /** Type of completion */
  type: 'complete' | 'failed';
  /** Puzzle ID */
  puzzleId: string;
  /** Final result */
  result: CompletionResult;
  /** Timestamp */
  timestamp: number;
}

/**
 * Completion tracking configuration
 */
export interface CompletionConfig {
  /** Maximum wrong attempts before failure */
  maxWrongAttempts: number;
  /** Whether to track time */
  trackTime: boolean;
  /** Whether to track hints */
  trackHints: boolean;
}

/** Default completion configuration */
export const DEFAULT_COMPLETION_CONFIG: CompletionConfig = {
  maxWrongAttempts: 5,
  trackTime: true,
  trackHints: true,
};

/**
 * Check if a puzzle is complete
 *
 * @param traversalState - Current traversal state
 * @returns true if puzzle is complete
 */
export function isPuzzleComplete(traversalState: TraversalState): boolean {
  return traversalState.complete;
}

/**
 * Check if a puzzle is failed (too many wrong attempts)
 *
 * @param traversalState - Current traversal state
 * @param maxAttempts - Maximum allowed wrong attempts
 * @returns true if puzzle is failed
 */
export function isPuzzleFailed(
  traversalState: TraversalState,
  maxAttempts: number = DEFAULT_COMPLETION_CONFIG.maxWrongAttempts
): boolean {
  return traversalState.wrongAttempts >= maxAttempts;
}

/**
 * Get completion status from traversal state
 *
 * @param traversalState - Current traversal state
 * @param config - Completion configuration
 * @returns Completion status
 */
export function getCompletionStatus(
  traversalState: TraversalState,
  config: CompletionConfig = DEFAULT_COMPLETION_CONFIG
): CompletionStatus {
  if (traversalState.complete) {
    return 'complete';
  }

  if (isPuzzleFailed(traversalState, config.maxWrongAttempts)) {
    return 'failed';
  }

  if (traversalState.history.length === 0) {
    return 'not_started';
  }

  return 'in_progress';
}

/**
 * Get detailed completion result
 *
 * @param traversalState - Current traversal state
 * @param config - Completion configuration
 * @param timeTaken - Time taken in milliseconds
 * @param hintsUsed - Number of hints used
 * @returns Completion result
 */
export function getCompletionResult(
  traversalState: TraversalState,
  config: CompletionConfig = DEFAULT_COMPLETION_CONFIG,
  timeTaken?: number,
  hintsUsed?: number
): CompletionResult {
  const status = getCompletionStatus(traversalState, config);
  const progress = getProgress(traversalState);

  const result: CompletionResult = {
    status,
    isComplete: status === 'complete',
    isFailed: status === 'failed',
    movesPlayed: progress.movesPlayed,
    totalMoves: progress.totalMoves,
    percentComplete: progress.percentComplete,
    wrongAttempts: traversalState.wrongAttempts,
  };

  if (config.trackTime && timeTaken !== undefined) {
    result.timeTaken = timeTaken;
  }
  if (config.trackHints && hintsUsed !== undefined) {
    result.hintsUsed = hintsUsed;
  }

  return result;
}

/**
 * Completion tracker for managing puzzle completion state
 */
export interface CompletionTracker {
  /** Start tracking a puzzle */
  start: (puzzleId: string) => void;
  /** Record a move */
  recordMove: (correct: boolean) => void;
  /** Record hint usage */
  recordHint: () => void;
  /** Get current result */
  getResult: (traversalState: TraversalState) => CompletionResult;
  /** Check if complete */
  isComplete: (traversalState: TraversalState) => boolean;
  /** Check if failed */
  isFailed: (traversalState: TraversalState) => boolean;
  /** Reset tracker */
  reset: () => void;
}

/**
 * Create a completion tracker
 *
 * @param config - Completion configuration
 * @param onComplete - Callback when puzzle is completed
 * @returns Completion tracker
 */
export function createCompletionTracker(
  config: CompletionConfig = DEFAULT_COMPLETION_CONFIG,
  onComplete?: (event: CompletionEvent) => void
): CompletionTracker {
  let puzzleId: string | null = null;
  let startTime: number | null = null;
  let hintsUsed = 0;

  return {
    start(id: string): void {
      puzzleId = id;
      startTime = Date.now();
      hintsUsed = 0;
    },

    recordMove(_correct: boolean): void {
      // Move recording handled by traversal state
    },

    recordHint(): void {
      hintsUsed++;
    },

    getResult(traversalState: TraversalState): CompletionResult {
      const timeTaken = startTime ? Date.now() - startTime : undefined;
      return getCompletionResult(traversalState, config, timeTaken, hintsUsed);
    },

    isComplete(traversalState: TraversalState): boolean {
      const complete = isPuzzleComplete(traversalState);
      if (complete && puzzleId && onComplete) {
        const result = this.getResult(traversalState);
        onComplete({
          type: 'complete',
          puzzleId,
          result,
          timestamp: Date.now(),
        });
      }
      return complete;
    },

    isFailed(traversalState: TraversalState): boolean {
      const failed = isPuzzleFailed(traversalState, config.maxWrongAttempts);
      if (failed && puzzleId && onComplete) {
        const result = this.getResult(traversalState);
        onComplete({
          type: 'failed',
          puzzleId,
          result,
          timestamp: Date.now(),
        });
      }
      return failed;
    },

    reset(): void {
      puzzleId = null;
      startTime = null;
      hintsUsed = 0;
    },
  };
}

/**
 * Calculate score for a completed puzzle
 *
 * @param result - Completion result
 * @param puzzle - Puzzle definition
 * @returns Score (0-100)
 */
export function calculateScore(
  result: CompletionResult,
  puzzle: Puzzle
): number {
  if (!result.isComplete) {
    return 0;
  }

  let score = 100;

  // Deduct for wrong attempts
  score -= result.wrongAttempts * 10;

  // Deduct for hints (if used)
  if (result.hintsUsed) {
    score -= result.hintsUsed * 5;
  }

  // Bonus for speed (if under par time)
  // Par time based on difficulty: level 1 = 60s, level 5 = 180s
  const parTimeMs = 60000 + (puzzle.rank ? getDifficultyFactor(puzzle.rank) : 0) * 30000;
  if (result.timeTaken && result.timeTaken < parTimeMs) {
    const speedBonus = Math.round((1 - result.timeTaken / parTimeMs) * 10);
    score += speedBonus;
  }

  return Math.max(0, Math.min(100, score));
}

/**
 * Get difficulty factor from rank string
 */
function getDifficultyFactor(rank: string): number {
  // kyu ranks: 30k = 0, 1k = 29
  // dan ranks: 1d = 30, 9d = 38
  const kyuMatch = rank.match(/(\d+)k/i);
  if (kyuMatch?.[1]) {
    return 30 - parseInt(kyuMatch[1], 10);
  }

  const danMatch = rank.match(/(\d+)d/i);
  if (danMatch?.[1]) {
    return 29 + parseInt(danMatch[1], 10);
  }

  return 15; // Default to middle
}

/**
 * Get rating change for completed puzzle
 *
 * @param result - Completion result
 * @param puzzleRating - Puzzle rating
 * @param playerRating - Player rating
 * @returns Rating change
 */
export function calculateRatingChange(
  result: CompletionResult,
  puzzleRating: number,
  playerRating: number
): number {
  if (!result.isComplete) {
    // Small penalty for failed puzzles
    return -2;
  }

  // ELO-style calculation
  const expected = 1 / (1 + Math.pow(10, (puzzleRating - playerRating) / 400));
  const actual = 1; // Won

  const k = 32; // K-factor
  let change = Math.round(k * (actual - expected));

  // Reduce gain if hints were used
  if (result.hintsUsed && result.hintsUsed > 0) {
    change = Math.max(1, Math.round(change * 0.5));
  }

  // Reduce gain if many wrong attempts
  if (result.wrongAttempts >= 3) {
    change = Math.max(1, Math.round(change * 0.75));
  }

  return change;
}
