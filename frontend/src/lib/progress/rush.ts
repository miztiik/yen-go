/**
 * Rush mode progress and high score tracking.
 * Persists rush results to localStorage.
 * @module lib/progress/rush
 */

import type { RushResult, RushDuration } from '@models/rush';

/**
 * Storage key for rush progress.
 */
const STORAGE_KEY = 'yen-go-rush-progress';

/**
 * Stored rush result with metadata.
 */
export interface StoredRushResult extends RushResult {
  /** Unique result ID */
  readonly id: string;
  /** ISO timestamp when result was recorded */
  readonly recordedAt: string;
}

/**
 * Rush progress data structure.
 */
export interface RushProgress {
  /** Version for migrations */
  readonly version: number;
  /** High scores by duration */
  readonly highScores: {
    readonly [key in RushDuration]?: number;
  };
  /** All rush results (most recent first) */
  readonly results: readonly StoredRushResult[];
  /** Total rush sessions played */
  readonly totalSessions: number;
  /** Total puzzles solved across all sessions */
  readonly totalPuzzlesSolved: number;
  /** Best streak achieved */
  readonly bestStreak: number;
}

/**
 * Current progress version.
 */
const CURRENT_VERSION = 1;

/**
 * Maximum results to store (prevent unbounded growth).
 */
const MAX_STORED_RESULTS = 100;

/**
 * Create initial rush progress.
 */
export function createRushProgress(): RushProgress {
  return {
    version: CURRENT_VERSION,
    highScores: {},
    results: [],
    totalSessions: 0,
    totalPuzzlesSolved: 0,
    bestStreak: 0,
  };
}

/**
 * Generate a unique ID for a result.
 */
function generateResultId(): string {
  return `rush-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Calculate best consecutive streak from puzzle results.
 */
function calculateBestStreak(puzzleResults: readonly { solved: boolean }[]): number {
  let best = 0;
  let current = 0;
  for (const result of puzzleResults) {
    if (result.solved) {
      current++;
      best = Math.max(best, current);
    } else {
      current = 0;
    }
  }
  return best;
}

/**
 * Load rush progress from storage.
 */
export function loadRushProgress(): RushProgress {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return createRushProgress();
    }

    const parsed = JSON.parse(stored) as RushProgress;

    // Handle version migrations if needed
    if (parsed.version !== CURRENT_VERSION) {
      return migrateProgress(parsed);
    }

    return parsed;
  } catch (error) {
    console.warn('Failed to load rush progress:', error);
    return createRushProgress();
  }
}

/**
 * Save rush progress to storage.
 */
export function saveRushProgress(progress: RushProgress): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch (error) {
    console.error('Failed to save rush progress:', error);
  }
}

/**
 * Migrate progress from older version.
 */
function migrateProgress(progress: RushProgress): RushProgress {
  // Currently only version 1 exists, so just return as-is with updated version
  return {
    ...progress,
    version: CURRENT_VERSION,
  };
}

/**
 * Record a new rush result.
 */
export function recordRushResult(
  progress: RushProgress,
  result: RushResult
): {
  newProgress: RushProgress;
  isNewHighScore: boolean;
  previousHighScore: number | null;
} {
  const storedResult: StoredRushResult = {
    ...result,
    id: generateResultId(),
    recordedAt: new Date().toISOString(),
  };

  // Check for new high score
  const currentHighScore = progress.highScores[result.duration] ?? null;
  const isNewHighScore = currentHighScore === null || result.score > currentHighScore;

  // Update high scores
  const newHighScores = {
    ...progress.highScores,
    [result.duration]: isNewHighScore ? result.score : currentHighScore,
  };

  // Add result and trim to max
  const newResults = [storedResult, ...progress.results].slice(0, MAX_STORED_RESULTS);

  // Calculate best streak from puzzle results
  const sessionStreak = calculateBestStreak(result.puzzleResults);
  const newBestStreak = Math.max(progress.bestStreak, sessionStreak);

  const newProgress: RushProgress = {
    ...progress,
    highScores: newHighScores,
    results: newResults,
    totalSessions: progress.totalSessions + 1,
    totalPuzzlesSolved: progress.totalPuzzlesSolved + result.puzzlesSolved,
    bestStreak: newBestStreak,
  };

  return {
    newProgress,
    isNewHighScore,
    previousHighScore: currentHighScore,
  };
}

/**
 * Get high score for a specific duration.
 */
export function getHighScore(
  progress: RushProgress,
  duration: RushDuration
): number | null {
  return progress.highScores[duration] ?? null;
}

/**
 * Get all high scores.
 */
export function getAllHighScores(
  progress: RushProgress
): { duration: RushDuration; score: number }[] {
  const durations: RushDuration[] = [60, 180, 300];
  return durations
    .filter((d): d is RushDuration => progress.highScores[d] !== undefined)
    .map((duration) => ({ duration, score: progress.highScores[duration]! }))
    .sort((a, b) => b.score - a.score);
}

/**
 * Get recent rush results.
 */
export function getRecentResults(
  progress: RushProgress,
  limit: number = 10
): readonly StoredRushResult[] {
  return progress.results.slice(0, limit);
}

/**
 * Get results filtered by duration.
 */
export function getResultsByDuration(
  progress: RushProgress,
  duration: RushDuration,
  limit: number = 10
): readonly StoredRushResult[] {
  return progress.results
    .filter(r => r.duration === duration)
    .slice(0, limit);
}

/**
 * Get rush statistics summary.
 */
export function getRushStatistics(progress: RushProgress): {
  totalSessions: number;
  totalPuzzlesSolved: number;
  bestStreak: number;
  averageScore: number | null;
  averagePuzzlesPerSession: number | null;
  bestRank: string | null;
} {
  const { results, totalSessions, totalPuzzlesSolved, bestStreak } = progress;

  if (totalSessions === 0) {
    return {
      totalSessions: 0,
      totalPuzzlesSolved: 0,
      bestStreak: 0,
      averageScore: null,
      averagePuzzlesPerSession: null,
      bestRank: null,
    };
  }

  const totalScore = results.reduce((sum, r) => sum + r.score, 0);
  const averageScore = Math.round(totalScore / results.length);
  const averagePuzzlesPerSession = Math.round(totalPuzzlesSolved / totalSessions);

  // Determine best rank from high scores
  const allScores = Object.values(progress.highScores).filter((s): s is number => s !== undefined);
  const maxScore = allScores.length > 0 ? Math.max(...allScores) : 0;
  const bestRank = calculateRankFromScore(maxScore);

  return {
    totalSessions,
    totalPuzzlesSolved,
    bestStreak,
    averageScore,
    averagePuzzlesPerSession,
    bestRank,
  };
}

/**
 * Calculate rank from score.
 */
function calculateRankFromScore(score: number): string {
  if (score >= 2000) return 'S';
  if (score >= 1500) return 'A';
  if (score >= 1000) return 'B';
  if (score >= 500) return 'C';
  if (score >= 200) return 'D';
  return 'F';
}

/**
 * Clear all rush progress (for testing/reset).
 */
export function clearRushProgress(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Rush progress manager class for convenient usage.
 */
export class RushProgressManager {
  private progress: RushProgress;

  constructor() {
    this.progress = loadRushProgress();
  }

  /**
   * Get current progress.
   */
  getProgress(): RushProgress {
    return this.progress;
  }

  /**
   * Record a result and save.
   */
  recordResult(result: RushResult): {
    isNewHighScore: boolean;
    previousHighScore: number | null;
  } {
    const { newProgress, isNewHighScore, previousHighScore } = recordRushResult(
      this.progress,
      result
    );
    this.progress = newProgress;
    saveRushProgress(this.progress);
    return { isNewHighScore, previousHighScore };
  }

  /**
   * Get high score for duration.
   */
  getHighScore(duration: RushDuration): number | null {
    return getHighScore(this.progress, duration);
  }

  /**
   * Get statistics.
   */
  getStatistics() {
    return getRushStatistics(this.progress);
  }

  /**
   * Get recent results.
   */
  getRecentResults(limit?: number) {
    return getRecentResults(this.progress, limit);
  }

  /**
   * Reload progress from storage.
   */
  reload(): void {
    this.progress = loadRushProgress();
  }
}

/**
 * Create a rush progress manager.
 */
export function createRushProgressManager(): RushProgressManager {
  return new RushProgressManager();
}
