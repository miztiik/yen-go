/**
 * Progress Calculations
 * @module services/progress/progressCalculations
 *
 * Business logic for calculating and updating user progress,
 * statistics, achievements, and preferences.
 *
 * Covers: FR-015 to FR-022, US3
 */

import type {
  UserProgress,
  PuzzleCompletion,
  UserStatistics,
  StreakData,
  UserPreferences,
  Achievement,
  RushScore,
} from '../../models/progress';
import {
  DEFAULT_STATISTICS,
  DEFAULT_STREAK_DATA,
  DEFAULT_PREFERENCES,
} from '../../models/progress';
import type { DailyChallengeGroup } from '../../models/level';
import type {
  CollectionProgress,
  CollectionStats,
  CollectionStatus,
  CollectionProgressSummary,
  DailyProgress,
  DailyPerformanceData,
} from '../../types/progress';
import type { ProgressResult } from './storageOperations';
import {
  saveProgress,
  loadCollectionProgress,
  saveCollectionProgress,
  loadDailyProgress,
  saveDailyProgress,
  failureResult,
} from './storageOperations';
import { loadProgress } from './progressMigrations';

// ============================================================================
// Puzzle Completion Input
// ============================================================================

/** Input for recording puzzle completion */
export interface PuzzleCompletionInput {
  timeSpentMs: number;
  attempts: number;
  hintsUsed: number;
  perfectSolve: boolean;
  difficulty: DailyChallengeGroup;
}

// ============================================================================
// Statistics Calculations
// ============================================================================

/**
 * Update statistics based on a puzzle completion
 */
function updateStatistics(
  stats: UserStatistics,
  completion: PuzzleCompletionInput
): UserStatistics {
  const diffStats = stats.byDifficulty[completion.difficulty];
  const newSolved = diffStats.solved + 1;
  const newTotalTime = diffStats.totalTimeMs + completion.timeSpentMs;

  return {
    ...stats,
    totalSolved: stats.totalSolved + 1,
    totalTimeMs: stats.totalTimeMs + completion.timeSpentMs,
    totalAttempts: stats.totalAttempts + completion.attempts,
    totalHintsUsed: stats.totalHintsUsed + completion.hintsUsed,
    perfectSolves: stats.perfectSolves + (completion.perfectSolve ? 1 : 0),
    byDifficulty: {
      ...stats.byDifficulty,
      [completion.difficulty]: {
        solved: newSolved,
        totalTimeMs: newTotalTime,
        avgTimeMs: Math.round(newTotalTime / newSolved),
        perfectSolves: diffStats.perfectSolves + (completion.perfectSolve ? 1 : 0),
      },
    },
  };
}

// ============================================================================
// Puzzle Completion
// ============================================================================

/**
 * Record a puzzle completion
 */
export function recordPuzzleCompletion(
  puzzleId: string,
  completion: PuzzleCompletionInput
): ProgressResult<UserProgress> {
  const loadResult = loadProgress();
  if (!loadResult.success || !loadResult.data) {
    return loadResult;
  }

  const progress = loadResult.data;
  const now = new Date().toISOString();

  // Create new completion record
  const puzzleCompletion: PuzzleCompletion = {
    puzzleId,
    completedAt: now,
    timeSpentMs: completion.timeSpentMs,
    attempts: completion.attempts,
    hintsUsed: completion.hintsUsed,
    perfectSolve: completion.perfectSolve,
  };

  // Update completed puzzles
  const newCompletedPuzzles = {
    ...progress.completedPuzzles,
    [puzzleId]: puzzleCompletion,
  };

  // Update statistics
  const newStatistics = updateStatistics(progress.statistics, completion);

  const updatedProgress: UserProgress = {
    ...progress,
    completedPuzzles: newCompletedPuzzles,
    statistics: newStatistics,
  };

  return saveProgress(updatedProgress).success
    ? { success: true, data: updatedProgress }
    : { success: false, error: 'save_failed' };
}

/**
 * Check if a puzzle is completed
 */
export function isPuzzleCompleted(puzzleId: string): boolean {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return false;
  }
  return puzzleId in result.data.completedPuzzles;
}

/**
 * Get completion data for a puzzle
 */
export function getPuzzleCompletion(puzzleId: string): PuzzleCompletion | undefined {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return undefined;
  }
  return result.data.completedPuzzles[puzzleId];
}

// ============================================================================
// Level Unlocks
// ============================================================================

/**
 * Unlock a level
 */
export function unlockLevel(levelId: string): ProgressResult<UserProgress> {
  const loadResult = loadProgress();
  if (!loadResult.success || !loadResult.data) {
    return loadResult;
  }

  const progress = loadResult.data;

  if (!progress.unlockedLevels.includes(levelId)) {
    const updatedProgress: UserProgress = {
      ...progress,
      unlockedLevels: [...progress.unlockedLevels, levelId],
    };
    return saveProgress(updatedProgress).success
      ? { success: true, data: updatedProgress }
      : { success: false, error: 'save_failed' };
  }

  return { success: true, data: progress };
}

/**
 * Check if a level is unlocked
 */
export function isLevelUnlocked(levelId: string): boolean {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return false;
  }
  return result.data.unlockedLevels.includes(levelId);
}

// ============================================================================
// Statistics
// ============================================================================

/**
 * Get user statistics
 */
export function getStatistics(): UserStatistics {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return { ...DEFAULT_STATISTICS };
  }
  return result.data.statistics;
}

// ============================================================================
// Streak Data
// ============================================================================

/**
 * Get streak data
 */
export function getStreakData(): StreakData {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return { ...DEFAULT_STREAK_DATA };
  }
  return result.data.streakData;
}

/**
 * Update streak data
 */
export function updateStreakData(streakData: StreakData): ProgressResult<UserProgress> {
  const loadResult = loadProgress();
  if (!loadResult.success || !loadResult.data) {
    return loadResult;
  }

  const progress = loadResult.data;
  const updatedProgress: UserProgress = {
    ...progress,
    streakData,
  };

  return saveProgress(updatedProgress).success
    ? { success: true, data: updatedProgress }
    : { success: false, error: 'save_failed' };
}

// ============================================================================
// Achievements
// ============================================================================

/**
 * Get achievements
 */
export function getAchievements(): readonly Achievement[] {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return [];
  }
  return result.data.achievements;
}

/**
 * Add an achievement
 */
export function addAchievement(
  achievement: Omit<Achievement, 'unlockedAt'>
): ProgressResult<UserProgress> {
  const loadResult = loadProgress();
  if (!loadResult.success || !loadResult.data) {
    return loadResult;
  }

  const progress = loadResult.data;

  // Check if already earned
  if (progress.achievements.some((a) => a.id === achievement.id)) {
    return { success: true, data: progress };
  }

  const newAchievement: Achievement = {
    ...achievement,
    unlockedAt: new Date().toISOString(),
  };

  const updatedProgress: UserProgress = {
    ...progress,
    achievements: [...progress.achievements, newAchievement],
  };

  return saveProgress(updatedProgress).success
    ? { success: true, data: updatedProgress }
    : { success: false, error: 'save_failed' };
}

// ============================================================================
// Rush Mode
// ============================================================================

/**
 * Update rush mode high score
 */
export function updateRushHighScore(score: number, duration: number): ProgressResult<UserProgress> {
  const loadResult = loadProgress();
  if (!loadResult.success || !loadResult.data) {
    return loadResult;
  }

  const progress = loadResult.data;
  const currentHighScores = progress.statistics.rushHighScores;
  const currentHigh = currentHighScores.length > 0 ? currentHighScores[0]!.score : 0;

  if (score > currentHigh) {
    const newScore: RushScore = {
      score,
      duration,
      achievedAt: new Date().toISOString(),
    };

    const updatedProgress: UserProgress = {
      ...progress,
      statistics: {
        ...progress.statistics,
        rushHighScores: [newScore, ...currentHighScores].slice(0, 10), // Keep top 10
      },
    };

    return saveProgress(updatedProgress).success
      ? { success: true, data: updatedProgress }
      : { success: false, error: 'save_failed' };
  }

  return { success: true, data: progress };
}

/**
 * Get rush mode high score
 */
export function getRushHighScore(): number {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return 0;
  }
  const scores = result.data.statistics.rushHighScores;
  return scores.length > 0 ? scores[0]!.score : 0;
}

/**
 * Get rush mode high score for a specific duration
 */
export function getRushHighScoreByDuration(duration: number): number {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return 0;
  }
  const scores = result.data.statistics.rushHighScores;
  const matchingScore = scores.find((s) => s.duration === duration);
  return matchingScore?.score ?? 0;
}

/**
 * Get all rush high scores
 */
export function getRushHighScores(): readonly RushScore[] {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return [];
  }
  return result.data.statistics.rushHighScores;
}

/**
 * Record a rush score (adds to history, updates high score if better)
 */
export function recordRushScore(
  score: number,
  duration: number
): ProgressResult<{ progress: UserProgress; isNewHighScore: boolean }> {
  const loadResult = loadProgress();
  if (!loadResult.success || !loadResult.data) {
    return {
      success: false,
      error: loadResult.error ?? 'storage_unavailable',
      message: loadResult.message ?? 'Failed to load progress',
    };
  }

  const progress = loadResult.data;
  const currentScores = [...progress.statistics.rushHighScores];

  // Find current high score for this duration
  const existingIndex = currentScores.findIndex((s) => s.duration === duration);
  const currentHighForDuration = existingIndex >= 0 ? currentScores[existingIndex]!.score : 0;
  const isNewHighScore = score > currentHighForDuration;

  // Create new score entry
  const newScore: RushScore = {
    score,
    duration,
    achievedAt: new Date().toISOString(),
  };

  // Update or add high score for this duration
  if (existingIndex >= 0) {
    if (isNewHighScore) {
      currentScores[existingIndex] = newScore;
    }
  } else {
    currentScores.push(newScore);
  }

  // Sort by score descending
  currentScores.sort((a, b) => b.score - a.score);

  // Keep top 10
  const topScores = currentScores.slice(0, 10);

  const updatedProgress: UserProgress = {
    ...progress,
    statistics: {
      ...progress.statistics,
      rushHighScores: topScores,
    },
  };

  const saveResult = saveProgress(updatedProgress);
  if (!saveResult.success) {
    return {
      success: false,
      error: 'save_failed',
      message: 'Failed to save rush score',
    };
  }

  return {
    success: true,
    data: { progress: updatedProgress, isNewHighScore },
  };
}

// ============================================================================
// Preferences
// ============================================================================

/**
 * Get user preferences
 */
export function getPreferences(): UserPreferences {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return { ...DEFAULT_PREFERENCES };
  }
  return result.data.preferences;
}

/**
 * Update user preferences
 */
export function updatePreferences(
  preferences: Partial<UserPreferences>
): ProgressResult<UserProgress> {
  const loadResult = loadProgress();
  if (!loadResult.success || !loadResult.data) {
    return loadResult;
  }

  const progress = loadResult.data;
  const updatedProgress: UserProgress = {
    ...progress,
    preferences: {
      ...progress.preferences,
      ...preferences,
    },
  };

  return saveProgress(updatedProgress).success
    ? { success: true, data: updatedProgress }
    : { success: false, error: 'save_failed' };
}

/**
 * Get count of completed puzzles in a level
 */
export function getLevelCompletionCount(levelId: string): number {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return 0;
  }

  return Object.keys(result.data.completedPuzzles).filter((puzzleId) =>
    puzzleId.startsWith(`${levelId}/`)
  ).length;
}

// ============================================================================
// Collection Progress (Spec 021)
// ============================================================================

/**
 * Get progress for a specific collection
 */
export function getCollectionProgress(
  collectionId: string
): ProgressResult<CollectionProgress | null> {
  const result = loadCollectionProgress();
  if (!result.success || !result.data) {
    return failureResult(result.error, result.message);
  }
  return { success: true, data: result.data[collectionId] ?? null };
}

/**
 * Update or create progress for a collection
 */
export function updateCollectionProgress(
  collectionId: string,
  update: Partial<CollectionProgress>
): ProgressResult<CollectionProgress> {
  const loadResult = loadCollectionProgress();
  if (!loadResult.success) {
    return failureResult(loadResult.error, loadResult.message);
  }

  const allProgress = loadResult.data ?? {};
  const existing = allProgress[collectionId];
  const now = new Date().toISOString();

  const statsValue = update.stats ?? existing?.stats;
  const updated: CollectionProgress = {
    collectionId,
    completed: update.completed ?? existing?.completed ?? [],
    currentIndex: update.currentIndex ?? existing?.currentIndex ?? 0,
    startedAt: existing?.startedAt ?? now,
    lastActivity: now,
    totalPuzzles: update.totalPuzzles ?? existing?.totalPuzzles ?? 0,
    ...(statsValue !== undefined && { stats: statsValue }),
  };

  allProgress[collectionId] = updated;
  const saveResult = saveCollectionProgress(allProgress);

  if (!saveResult.success) {
    return failureResult(saveResult.error, saveResult.message);
  }

  return { success: true, data: updated };
}

/**
 * Record completion of a puzzle in a collection
 */
export function recordCollectionPuzzleCompletion(
  collectionId: string,
  puzzleId: string,
  isCorrect: boolean,
  timeMs: number,
  hintsUsed: number
): ProgressResult<CollectionProgress> {
  const loadResult = loadCollectionProgress();
  if (!loadResult.success) {
    return failureResult(loadResult.error, loadResult.message);
  }

  const allProgress = loadResult.data ?? {};
  const existing = allProgress[collectionId];
  const now = new Date().toISOString();

  // Update completed list
  const completed = [...(existing?.completed ?? [])];
  if (!completed.includes(puzzleId)) {
    completed.push(puzzleId);
  }

  // Update stats
  const currentStats = existing?.stats ?? {
    correctFirstTry: 0,
    hintsUsed: 0,
    totalTimeMs: 0,
    avgTimeMs: 0,
  };

  const updatedStats: CollectionStats = {
    correctFirstTry: currentStats.correctFirstTry + (isCorrect ? 1 : 0),
    hintsUsed: currentStats.hintsUsed + hintsUsed,
    totalTimeMs: currentStats.totalTimeMs + timeMs,
    avgTimeMs: Math.round((currentStats.totalTimeMs + timeMs) / completed.length),
  };

  const updated: CollectionProgress = {
    collectionId,
    completed,
    currentIndex: completed.length,
    startedAt: existing?.startedAt ?? now,
    lastActivity: now,
    totalPuzzles: existing?.totalPuzzles ?? 0,
    stats: updatedStats,
  };

  allProgress[collectionId] = updated;
  const saveResult = saveCollectionProgress(allProgress);

  if (!saveResult.success) {
    return failureResult(saveResult.error, saveResult.message);
  }

  return { success: true, data: updated };
}

/**
 * Get collection status from progress
 */
export function getCollectionStatus(progress: CollectionProgress | null): CollectionStatus {
  if (!progress) return 'not-started';
  if (progress.completed.length >= progress.totalPuzzles) return 'completed';
  return 'in-progress';
}

/**
 * Get all collection progress summaries
 */
export function getAllCollectionProgress(): ProgressResult<CollectionProgressSummary[]> {
  const loadResult = loadCollectionProgress();
  if (!loadResult.success) {
    return failureResult(loadResult.error, loadResult.message);
  }

  const allProgress = loadResult.data ?? {};
  const summaries: CollectionProgressSummary[] = Object.values(allProgress).map((progress) => ({
    collectionId: progress.collectionId,
    status: getCollectionStatus(progress),
    completedCount: progress.completed.length,
    totalPuzzles: progress.totalPuzzles,
    percentComplete:
      progress.totalPuzzles > 0
        ? Math.round((progress.completed.length / progress.totalPuzzles) * 100)
        : 0,
    lastActivity: progress.lastActivity,
  }));

  return { success: true, data: summaries };
}

// ============================================================================
// Daily Progress (Spec 021)
// ============================================================================

/**
 * Get progress for a specific daily challenge
 */
export function getDailyProgress(date: string): ProgressResult<DailyProgress | null> {
  const result = loadDailyProgress();
  if (!result.success || !result.data) {
    return failureResult(result.error, result.message);
  }
  return { success: true, data: result.data[date] ?? null };
}

/**
 * Update or create progress for a daily challenge
 */
export function updateDailyProgress(
  date: string,
  update: Partial<DailyProgress>
): ProgressResult<DailyProgress> {
  const loadResult = loadDailyProgress();
  if (!loadResult.success) {
    return failureResult(loadResult.error, loadResult.message);
  }

  const allProgress = loadResult.data ?? {};
  const existing = allProgress[date];
  const now = new Date().toISOString();

  const performanceValue = update.performance ?? existing?.performance;
  const updated: DailyProgress = {
    date,
    completed: update.completed ?? existing?.completed ?? [],
    currentIndex: update.currentIndex ?? existing?.currentIndex ?? 0,
    startedAt: existing?.startedAt ?? now,
    lastActivity: now,
    ...(performanceValue !== undefined && { performance: performanceValue }),
  };

  allProgress[date] = updated;
  const saveResult = saveDailyProgress(allProgress);

  if (!saveResult.success) {
    return failureResult(saveResult.error, saveResult.message);
  }

  return { success: true, data: updated };
}

/**
 * Record completion of a puzzle in a daily challenge
 */
export function recordDailyPuzzleCompletion(
  date: string,
  puzzleId: string,
  level: string,
  isCorrect: boolean,
  timeMs: number
): ProgressResult<DailyProgress> {
  const loadResult = loadDailyProgress();
  if (!loadResult.success) {
    return failureResult(loadResult.error, loadResult.message);
  }

  const allProgress = loadResult.data ?? {};
  const existing = allProgress[date];
  const now = new Date().toISOString();

  // Update completed list — skip recording accuracy if already completed
  const completed = [...(existing?.completed ?? [])];
  const alreadyCompleted = completed.includes(puzzleId);
  if (!alreadyCompleted) {
    completed.push(puzzleId);
  }

  // Update performance — only increment accuracy for new completions
  const currentPerf = existing?.performance ?? {
    accuracyByLevel: {},
    totalTimeMs: 0,
  };

  let updatedPerf: DailyPerformanceData;
  if (alreadyCompleted) {
    // Puzzle already recorded — only add time, skip accuracy
    updatedPerf = {
      ...currentPerf,
      totalTimeMs: currentPerf.totalTimeMs + timeMs,
    };
  } else {
    const levelStats = currentPerf.accuracyByLevel[level] ?? { correct: 0, total: 0 };
    updatedPerf = {
      ...currentPerf,
      totalTimeMs: currentPerf.totalTimeMs + timeMs,
      accuracyByLevel: {
        ...currentPerf.accuracyByLevel,
        [level]: {
          correct: levelStats.correct + (isCorrect ? 1 : 0),
          total: levelStats.total + 1,
        },
      },
    };
  }

  const updated: DailyProgress = {
    date,
    completed,
    currentIndex: completed.length,
    startedAt: existing?.startedAt ?? now,
    lastActivity: now,
    performance: updatedPerf,
  };

  allProgress[date] = updated;
  const saveResult = saveDailyProgress(allProgress);

  if (!saveResult.success) {
    return failureResult(saveResult.error, saveResult.message);
  }

  return { success: true, data: updated };
}
