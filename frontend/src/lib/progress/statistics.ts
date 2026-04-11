/**
 * Statistics aggregation - calculates and updates user statistics.
 * @module lib/progress/statistics
 *
 * Constitution Compliance:
 * - Single source of truth: Uses config/puzzle-levels.json via Vite JSON import
 */

import type {
  UserProgress,
  Statistics,
  PuzzleCompletion,
  RushScore,
  StatisticsBySkillLevel,
} from '../../types/progress';
import { LEVELS, LEVEL_SLUGS, type LevelSlug } from '../levels/config';

/** Re-export for backward compatibility */
export type SkillLevel = LevelSlug;

/**
 * Maximum number of rush high scores to keep.
 */
export const MAX_RUSH_HIGH_SCORES = 10;

/**
 * Skill level names for display (derived from config).
 */
export const SKILL_LEVEL_NAMES: Record<LevelSlug, string> = Object.fromEntries(
  LEVELS.map((lvl) => [lvl.slug, lvl.name])
) as Record<LevelSlug, string>;

/**
 * Skill level rank ranges for display (derived from config).
 */
export const SKILL_LEVEL_RANKS: Record<LevelSlug, string> = Object.fromEntries(
  LEVELS.map((lvl) => [lvl.slug, `${lvl.rankRange.min}-${lvl.rankRange.max}`])
) as Record<LevelSlug, string>;

/**
 * Initialize empty skill level stats.
 */
function createEmptySkillLevelStats(): Record<LevelSlug, number> {
  return Object.fromEntries(LEVEL_SLUGS.map((slug) => [slug, 0])) as Record<LevelSlug, number>;
}

/**
 * Calculate statistics by skill level.
 * Since PuzzleCompletion doesn't store skill level, we need a puzzle lookup function.
 *
 * @param completions - Array of puzzle completions
 * @param getSkillLevel - Function to get skill level for a puzzle ID
 * @returns Statistics by skill level
 */
export function calculateStatsBySkillLevel(
  completions: readonly PuzzleCompletion[],
  getSkillLevel: (puzzleId: string) => LevelSlug | undefined
): StatisticsBySkillLevel {
  const puzzlesByLevel = createEmptySkillLevelStats();
  const totalTimeByLevel = createEmptySkillLevelStats();
  const countByLevel = createEmptySkillLevelStats();

  for (const completion of completions) {
    const level = getSkillLevel(completion.puzzleId);
    if (level !== undefined) {
      puzzlesByLevel[level] = (puzzlesByLevel[level] ?? 0) + 1;
      totalTimeByLevel[level] = (totalTimeByLevel[level] ?? 0) + completion.timeSpentMs;
      countByLevel[level] = (countByLevel[level] ?? 0) + 1;
    }
  }

  // Calculate averages
  const avgTimeBySkillLevel: Record<LevelSlug, number> = Object.fromEntries(
    LEVEL_SLUGS.map((slug) => [
      slug,
      countByLevel[slug] ?? 0 > 0 ? (totalTimeByLevel[slug] ?? 0) / (countByLevel[slug] ?? 1) : 0,
    ])
  ) as Record<LevelSlug, number>;

  return {
    puzzlesBySkillLevel: puzzlesByLevel,
    avgTimeBySkillLevel,
  };
}

/**
 * Recalculate all statistics from completions.
 * Call this when rebuilding stats from scratch.
 *
 * @param progress - Current user progress
 * @returns Updated statistics object
 */
export function recalculateStatistics(progress: UserProgress): Statistics {
  const completions = Object.values(progress.completedPuzzles);

  if (completions.length === 0) {
    return progress.statistics;
  }

  // Calculate totals
  const totalPuzzlesSolved = completions.length;
  const totalTimeSpentMs = completions.reduce((sum, c) => sum + c.timeSpentMs, 0);
  const totalHintsUsed = completions.reduce((sum, c) => sum + c.hintsUsed, 0);
  const puzzlesWithoutHints = completions.filter((c) => c.hintsUsed === 0).length;

  // Keep existing rush scores and difficulty averages
  return {
    ...progress.statistics,
    totalPuzzlesSolved,
    totalTimeSpentMs,
    totalHintsUsed,
    puzzlesWithoutHints,
  };
}

/**
 * Update statistics after a puzzle completion.
 * Incremental update for efficiency.
 *
 * @param progress - Current user progress
 * @param completion - New puzzle completion
 * @returns Updated user progress
 */
export function updateStatisticsAfterCompletion(
  progress: UserProgress,
  completion: PuzzleCompletion
): UserProgress {
  const stats = progress.statistics;

  const updatedStats: Statistics = {
    ...stats,
    totalPuzzlesSolved: stats.totalPuzzlesSolved + 1,
    totalTimeSpentMs: stats.totalTimeSpentMs + completion.timeSpentMs,
    totalHintsUsed: stats.totalHintsUsed + completion.hintsUsed,
    puzzlesWithoutHints:
      stats.puzzlesWithoutHints + (completion.hintsUsed === 0 ? 1 : 0),
  };

  return {
    ...progress,
    statistics: updatedStats,
  };
}

/**
 * Add a rush mode high score.
 * Keeps only top scores up to MAX_RUSH_HIGH_SCORES.
 *
 * @param progress - Current user progress
 * @param score - Rush score to add
 * @returns Updated user progress
 */
export function addRushHighScore(
  progress: UserProgress,
  score: RushScore
): UserProgress {
  const currentScores = [...progress.statistics.rushHighScores];

  // Add new score
  currentScores.push(score);

  // Sort by score descending
  currentScores.sort((a, b) => b.score - a.score);

  // Keep only top scores
  const topScores = currentScores.slice(0, MAX_RUSH_HIGH_SCORES);

  return {
    ...progress,
    statistics: {
      ...progress.statistics,
      rushHighScores: topScores,
    },
  };
}

/**
 * Get the best rush high score.
 *
 * @param progress - User progress
 * @returns Best rush score or undefined
 */
export function getBestRushScore(progress: UserProgress): RushScore | undefined {
  const scores = progress.statistics.rushHighScores;
  return scores.length > 0 ? scores[0] : undefined;
}

/**
 * Calculate average time per puzzle.
 *
 * @param progress - User progress
 * @returns Average time in milliseconds
 */
export function getAverageTimePerPuzzle(progress: UserProgress): number {
  const { totalPuzzlesSolved, totalTimeSpentMs } = progress.statistics;
  if (totalPuzzlesSolved === 0) return 0;
  return totalTimeSpentMs / totalPuzzlesSolved;
}

/**
 * Calculate hint usage rate.
 *
 * @param progress - User progress
 * @returns Percentage of puzzles solved with hints (0-100)
 */
export function getHintUsageRate(progress: UserProgress): number {
  const { totalPuzzlesSolved, puzzlesWithoutHints } = progress.statistics;
  if (totalPuzzlesSolved === 0) return 0;

  const withHints = totalPuzzlesSolved - puzzlesWithoutHints;
  return (withHints / totalPuzzlesSolved) * 100;
}

/**
 * Format time duration for display.
 *
 * @param ms - Time in milliseconds
 * @returns Formatted string (e.g., "2h 30m", "45s", "1m 30s")
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return '< 1s';

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    const remainingMinutes = minutes % 60;
    if (remainingMinutes > 0) {
      return `${hours}h ${remainingMinutes}m`;
    }
    return `${hours}h`;
  }

  if (minutes > 0) {
    const remainingSeconds = seconds % 60;
    if (remainingSeconds > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${minutes}m`;
  }

  return `${seconds}s`;
}

/**
 * Format average time for display.
 *
 * @param ms - Average time in milliseconds
 * @returns Formatted string with context (e.g., "~45s", "~2m")
 */
export function formatAverageTime(ms: number): string {
  if (ms === 0) return '—';
  return `~${formatDuration(ms)}`;
}

/**
 * Get a summary of all statistics for display.
 *
 * @param progress - User progress
 * @returns Summary object with formatted values
 */
export function getStatisticsSummary(progress: UserProgress): {
  readonly puzzlesSolved: number;
  readonly totalTime: string;
  readonly averageTime: string;
  readonly hintsUsed: number;
  readonly hintFreePercentage: number;
  readonly bestRushScore: number | null;
} {
  const stats = progress.statistics;
  const bestRush = getBestRushScore(progress);

  return {
    puzzlesSolved: stats.totalPuzzlesSolved,
    totalTime: formatDuration(stats.totalTimeSpentMs),
    averageTime: formatAverageTime(getAverageTimePerPuzzle(progress)),
    hintsUsed: stats.totalHintsUsed,
    hintFreePercentage: Math.round(
      (stats.puzzlesWithoutHints / Math.max(stats.totalPuzzlesSolved, 1)) * 100
    ),
    bestRushScore: bestRush?.score ?? null,
  };
}
