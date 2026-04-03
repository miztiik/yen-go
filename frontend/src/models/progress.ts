/**
 * Progress types for user puzzle completion tracking
 * @module models/progress
 */

import type { DailyChallengeGroup } from './level';

/** Completion record for a single puzzle */
export interface PuzzleCompletion {
  readonly puzzleId: string;
  readonly completedAt: string; // ISO 8601
  readonly timeSpentMs: number;
  readonly attempts: number;
  readonly hintsUsed: number;
  readonly perfectSolve: boolean;
}

/** Statistics for a daily challenge group */
export interface GroupStats {
  readonly solved: number;
  readonly totalTimeMs: number;
  readonly avgTimeMs: number;
  readonly perfectSolves: number;
}

/** Statistics by daily challenge group */
export type DifficultyStats = Record<DailyChallengeGroup, GroupStats>;

/** Rush mode high score */
export interface RushScore {
  readonly score: number;
  readonly achievedAt: string; // ISO 8601
  readonly duration: number; // seconds
}

/** Aggregated user statistics */
export interface UserStatistics {
  readonly totalSolved: number;
  readonly totalTimeMs: number;
  readonly totalAttempts: number;
  readonly totalHintsUsed: number;
  readonly perfectSolves: number;
  readonly byDifficulty: DifficultyStats;
  readonly rushHighScores: readonly RushScore[];
}

/** Daily streak tracking */
export interface StreakData {
  readonly currentStreak: number;
  readonly longestStreak: number;
  readonly lastPlayedDate: string | null; // YYYY-MM-DD
  readonly streakStartDate: string | null; // YYYY-MM-DD
}

/** Achievement definition */
export interface Achievement {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly unlockedAt?: string; // ISO 8601
  readonly progress?: number;
  readonly target: number;
}

/** User preferences */
export interface UserPreferences {
  readonly hintsEnabled: boolean;
  readonly soundEnabled: boolean;
  readonly theme: 'dark' | 'light' | 'system';
  readonly boardStyle: 'classic' | 'modern';
}

/** Complete user progress state */
export interface UserProgress {
  readonly version: number; // Schema version for migrations
  readonly completedPuzzles: Record<string, PuzzleCompletion>;
  readonly unlockedLevels: readonly string[];
  readonly statistics: UserStatistics;
  readonly streakData: StreakData;
  readonly achievements: readonly Achievement[];
  readonly preferences: UserPreferences;
  readonly lastUpdated: string; // ISO 8601
}

/** Default initial statistics */
export const DEFAULT_STATISTICS: UserStatistics = {
  totalSolved: 0,
  totalTimeMs: 0,
  totalAttempts: 0,
  totalHintsUsed: 0,
  perfectSolves: 0,
  byDifficulty: {
    beginner: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 },
    intermediate: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 },
    advanced: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 },
  },
  rushHighScores: [],
};

/** Default initial streak data */
export const DEFAULT_STREAK_DATA: StreakData = {
  currentStreak: 0,
  longestStreak: 0,
  lastPlayedDate: null,
  streakStartDate: null,
};

/** Default user preferences */
export const DEFAULT_PREFERENCES: UserPreferences = {
  hintsEnabled: true,
  soundEnabled: true,
  theme: 'system',
  boardStyle: 'classic',
};

/** Create initial empty progress */
export function createInitialProgress(): UserProgress {
  return {
    version: 1,
    completedPuzzles: {},
    unlockedLevels: [],
    statistics: DEFAULT_STATISTICS,
    streakData: DEFAULT_STREAK_DATA,
    achievements: [],
    preferences: DEFAULT_PREFERENCES,
    lastUpdated: new Date().toISOString(),
  };
}

/** Current schema version */
export const PROGRESS_SCHEMA_VERSION = 1;
