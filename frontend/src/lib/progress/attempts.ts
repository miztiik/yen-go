/**
 * Attempt tracking for puzzle solving sessions.
 * @module lib/progress/attempts
 */

/**
 * Attempt state for tracking incorrect moves.
 */
export interface AttemptState {
  /** Puzzle ID being tracked */
  readonly puzzleId: string;
  /** Number of incorrect attempts */
  readonly incorrectAttempts: number;
  /** Timestamps of each incorrect attempt */
  readonly attemptTimes: readonly number[];
  /** Last move that was incorrect (for display) */
  readonly lastIncorrectMove?: string | undefined;
}

/**
 * Create a new attempt tracker for a puzzle.
 *
 * @param puzzleId - Puzzle ID being solved
 * @returns Initial attempt state
 */
export function createAttemptTracker(puzzleId: string): AttemptState {
  return {
    puzzleId,
    incorrectAttempts: 0,
    attemptTimes: [],
  };
}

/**
 * Record an incorrect attempt.
 *
 * @param state - Current attempt state
 * @param move - The incorrect move (optional, for display)
 * @returns Updated attempt state
 */
export function recordIncorrectAttempt(
  state: AttemptState,
  move?: string
): AttemptState {
  const now = performance.now();

  return {
    ...state,
    incorrectAttempts: state.incorrectAttempts + 1,
    attemptTimes: [...state.attemptTimes, now],
    lastIncorrectMove: move,
  };
}

/**
 * Get the number of incorrect attempts.
 *
 * @param state - Current attempt state
 * @returns Number of incorrect attempts
 */
export function getAttemptCount(state: AttemptState): number {
  return state.incorrectAttempts;
}

/**
 * Reset the attempt tracker.
 *
 * @param state - Current attempt state
 * @returns Reset attempt state
 */
export function resetAttempts(state: AttemptState): AttemptState {
  return {
    puzzleId: state.puzzleId,
    incorrectAttempts: 0,
    attemptTimes: [],
  };
}

/**
 * Check if user has made any incorrect attempts.
 *
 * @param state - Current attempt state
 * @returns True if there are incorrect attempts
 */
export function hasIncorrectAttempts(state: AttemptState): boolean {
  return state.incorrectAttempts > 0;
}

/**
 * Get time since last incorrect attempt (for cooldown).
 *
 * @param state - Current attempt state
 * @returns Milliseconds since last attempt, or null if no attempts
 */
export function getTimeSinceLastAttempt(state: AttemptState): number | null {
  if (state.attemptTimes.length === 0) {
    return null;
  }

  const lastAttempt = state.attemptTimes[state.attemptTimes.length - 1];
  if (lastAttempt === undefined) {
    return null;
  }
  return performance.now() - lastAttempt;
}

/**
 * AttemptTracker class for stateful attempt tracking.
 * Provides an object-oriented interface to attempt functions.
 */
export class AttemptTracker {
  private state: AttemptState;

  constructor(puzzleId: string) {
    this.state = createAttemptTracker(puzzleId);
  }

  /**
   * Record an incorrect attempt.
   *
   * @param move - The incorrect move (optional)
   */
  recordIncorrect(move?: string): void {
    this.state = recordIncorrectAttempt(this.state, move);
  }

  /**
   * Get the number of incorrect attempts.
   */
  getCount(): number {
    return getAttemptCount(this.state);
  }

  /**
   * Check if there are any incorrect attempts.
   */
  hasIncorrect(): boolean {
    return hasIncorrectAttempts(this.state);
  }

  /**
   * Get the last incorrect move.
   */
  getLastIncorrect(): string | undefined {
    return this.state.lastIncorrectMove;
  }

  /**
   * Reset the tracker.
   */
  reset(): void {
    this.state = resetAttempts(this.state);
  }

  /**
   * Get the current state (for serialization).
   */
  getState(): AttemptState {
    return this.state;
  }
}

/**
 * Calculate star rating based on attempts and hints.
 * 
 * - 3 stars: Perfect solve (0 incorrect, 0 hints)
 * - 2 stars: Good solve (1-2 incorrect OR 1 hint)
 * - 1 star: Completed with difficulty (3+ incorrect OR 2+ hints)
 *
 * @param attempts - Number of incorrect attempts
 * @param hintsUsed - Number of hints used
 * @returns Star rating (1-3)
 */
export function calculateStarRating(
  attempts: number,
  hintsUsed: number
): 1 | 2 | 3 {
  // Perfect solve
  if (attempts === 0 && hintsUsed === 0) {
    return 3;
  }

  // Good solve
  if ((attempts <= 2 && hintsUsed === 0) || (attempts === 0 && hintsUsed === 1)) {
    return 2;
  }

  // Completed with difficulty
  return 1;
}

/**
 * Get descriptive text for star rating.
 *
 * @param stars - Star rating (1-3)
 * @returns Description of the performance
 */
export function getStarRatingDescription(stars: 1 | 2 | 3): string {
  switch (stars) {
    case 3:
      return 'Perfect!';
    case 2:
      return 'Good job!';
    case 1:
      return 'Completed';
  }
}

/**
 * Format attempt count for display.
 *
 * @param attempts - Number of incorrect attempts
 * @returns Formatted string
 */
export function formatAttemptCount(attempts: number): string {
  if (attempts === 0) {
    return 'No mistakes';
  }
  if (attempts === 1) {
    return '1 incorrect attempt';
  }
  return `${attempts} incorrect attempts`;
}
