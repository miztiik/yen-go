/**
 * Rush Mode Types
 * @module models/rush
 *
 * Types for Timed Puzzle Rush mode (US7, FR-039 to FR-041)
 */

import type { Puzzle } from '../types/puzzle';

/** Rush mode duration options (in seconds) */
export type RushDuration = 60 | 180 | 300; // 1 min, 3 min, 5 min

/** Rush mode difficulty filter */
export type RushDifficulty = 'mixed' | 'beginner' | 'intermediate' | 'advanced';

/** Rush mode configuration */
export interface RushConfig {
  /** Duration of the rush session in seconds */
  readonly duration: RushDuration;
  /** Difficulty filter for puzzles */
  readonly difficulty: RushDifficulty;
  /** Points deducted for skipping a puzzle */
  readonly skipPenalty: number;
  /** Maximum consecutive wrong moves before auto-skip */
  readonly maxConsecutiveWrong: number;
}

/** Default rush configuration */
export const DEFAULT_RUSH_CONFIG: RushConfig = {
  duration: 180, // 3 minutes
  difficulty: 'mixed',
  skipPenalty: 1,
  maxConsecutiveWrong: 3,
};

/** Available duration presets with labels */
export const RUSH_DURATION_OPTIONS: readonly { value: RushDuration; label: string }[] = [
  { value: 60, label: '1 minute' },
  { value: 180, label: '3 minutes' },
  { value: 300, label: '5 minutes' },
];

/** Rush session state */
export type RushSessionState = 'idle' | 'countdown' | 'playing' | 'paused' | 'finished';

/** Result for a single puzzle in rush mode */
export interface RushPuzzleResult {
  /** Puzzle ID */
  readonly puzzleId: string;
  /** Whether puzzle was solved correctly */
  readonly solved: boolean;
  /** Whether puzzle was skipped */
  readonly skipped: boolean;
  /** Number of wrong attempts before solving/skipping */
  readonly wrongAttempts: number;
  /** Time spent on this puzzle (ms) */
  readonly timeSpentMs: number;
}

/** Current rush session data */
export interface RushSession {
  /** Session configuration */
  readonly config: RushConfig;
  /** Current session state */
  readonly state: RushSessionState;
  /** Current score */
  readonly score: number;
  /** Remaining time in seconds */
  readonly timeRemainingSeconds: number;
  /** Session start timestamp */
  readonly startedAt: number | null;
  /** Results for completed puzzles */
  readonly puzzleResults: readonly RushPuzzleResult[];
  /** Current puzzle being solved */
  readonly currentPuzzle: Puzzle | null;
  /** Current puzzle index in queue */
  readonly currentPuzzleIndex: number;
  /** Consecutive wrong moves on current puzzle */
  readonly consecutiveWrong: number;
  /** Puzzles solved in this session */
  readonly puzzlesSolved: number;
  /** Puzzles skipped in this session */
  readonly puzzlesSkipped: number;
}

/** Rush session final result */
export interface RushResult {
  /** Final score */
  readonly score: number;
  /** Total puzzles solved */
  readonly puzzlesSolved: number;
  /** Total puzzles skipped */
  readonly puzzlesSkipped: number;
  /** Total puzzles attempted */
  readonly puzzlesAttempted: number;
  /** Duration setting used */
  readonly duration: RushDuration;
  /** Difficulty setting used */
  readonly difficulty: RushDifficulty;
  /** Results for each puzzle */
  readonly puzzleResults: readonly RushPuzzleResult[];
  /** Session finished timestamp */
  readonly finishedAt: string; // ISO 8601
  /** Whether this is a new personal best */
  readonly isNewHighScore: boolean;
  /** Previous high score for this duration (if any) */
  readonly previousHighScore: number | null;
}

/** Create initial rush session */
export function createRushSession(config: Partial<RushConfig> = {}): RushSession {
  const fullConfig = { ...DEFAULT_RUSH_CONFIG, ...config };
  return {
    config: fullConfig,
    state: 'idle',
    score: 0,
    timeRemainingSeconds: fullConfig.duration,
    startedAt: null,
    puzzleResults: [],
    currentPuzzle: null,
    currentPuzzleIndex: 0,
    consecutiveWrong: 0,
    puzzlesSolved: 0,
    puzzlesSkipped: 0,
  };
}

/** Calculate score change for solving a puzzle */
export function calculateSolveScore(_puzzle: Puzzle, wrongAttempts: number): number {
  // Base score of 1 point per puzzle solved
  // No penalty for wrong attempts during solving (only time cost)
  return wrongAttempts < 3 ? 1 : 1; // Could add bonus for perfect solves
}

/** Calculate score change for skipping a puzzle */
export function calculateSkipPenalty(config: RushConfig): number {
  return config.skipPenalty === 0 ? 0 : -config.skipPenalty;
}

/** Check if session should auto-skip due to consecutive wrong moves */
export function shouldAutoSkip(session: RushSession): boolean {
  return session.consecutiveWrong >= session.config.maxConsecutiveWrong;
}

/** Format time remaining for display */
export function formatTimeRemaining(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/** Get rush mode statistics summary */
export function getRushSummary(session: RushSession): string {
  const { puzzlesSolved, puzzlesSkipped, score } = session;
  const total = puzzlesSolved + puzzlesSkipped;
  return `Score: ${score} | Solved: ${puzzlesSolved}/${total}`;
}

export default {
  createRushSession,
  calculateSolveScore,
  calculateSkipPenalty,
  shouldAutoSkip,
  formatTimeRemaining,
  getRushSummary,
  DEFAULT_RUSH_CONFIG,
  RUSH_DURATION_OPTIONS,
};
