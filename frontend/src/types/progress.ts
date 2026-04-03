/**
 * User Progress type definitions
 * User progress tracking for puzzle completion and settings
 * @module types/progress
 */

import type { SkillLevel } from './puzzle';
import { FIRST_LEVEL, FALLBACK_LEVEL, DEFAULT_LEVEL } from '../lib/levels/level-defaults';

/**
 * Board theme options
 */
export type BoardTheme = 'classic' | 'dark' | 'paper';

/**
 * User preferences for app behavior
 */
export interface UserPreferences {
  /** Whether hints are enabled */
  readonly hintsEnabled: boolean;
  /** Whether sound effects are enabled */
  readonly soundEnabled: boolean;
  /** Board color theme */
  readonly boardTheme: BoardTheme;
  /** Whether to show board coordinates */
  readonly coordinatesVisible: boolean;
}

/**
 * Completion record for a single puzzle
 */
export interface PuzzleCompletion {
  /** Puzzle ID */
  readonly puzzleId: string;
  /** ISO 8601 timestamp of completion */
  readonly completedAt: string;
  /** Time spent solving (milliseconds) */
  readonly timeSpentMs: number;
  /** Number of incorrect attempts before solving */
  readonly attempts: number;
  /** Number of hints used */
  readonly hintsUsed: number;
}

/**
 * Rush mode high score entry
 */
export interface RushScore {
  /** Number of puzzles solved */
  readonly score: number;
  /** ISO 8601 timestamp */
  readonly achievedAt: string;
  /** Duration in milliseconds */
  readonly durationMs: number;
}

/**
 * Average time by difficulty tier (3-tier grouping for daily challenges)
 */
export interface AvgTimeByDifficulty {
  readonly beginner: number;
  readonly intermediate: number;
  readonly advanced: number;
}

/**
 * Aggregated user statistics
 */
export interface Statistics {
  /** Total puzzles solved */
  readonly totalPuzzlesSolved: number;
  /** Total time spent (milliseconds) */
  readonly totalTimeSpentMs: number;
  /** Average time by difficulty tier */
  readonly avgTimeByDifficulty: AvgTimeByDifficulty;
  /** Total hints used across all puzzles */
  readonly totalHintsUsed: number;
  /** Puzzles solved without using hints */
  readonly puzzlesWithoutHints: number;
  /** Top rush mode scores (max 10) */
  readonly rushHighScores: readonly RushScore[];
}

/**
 * Statistics by skill level (5 levels)
 */
export interface StatisticsBySkillLevel {
  /** Puzzles solved per skill level */
  readonly puzzlesBySkillLevel: Record<SkillLevel, number>;
  /** Average time per skill level (milliseconds) */
  readonly avgTimeBySkillLevel: Record<SkillLevel, number>;
}

/**
 * Daily streak tracking data
 */
export interface StreakData {
  /** Current consecutive day streak */
  readonly currentStreak: number;
  /** Longest streak ever achieved */
  readonly longestStreak: number;
  /** Last date played (YYYY-MM-DD) */
  readonly lastPlayedDate: string;
  /** Date current streak started (YYYY-MM-DD) */
  readonly streakStartDate: string;
}

/**
 * Complete user progress state (stored in localStorage)
 */
export interface UserProgress {
  /** Schema version for migrations */
  readonly version: number;
  /** Completed puzzles indexed by puzzle ID */
  readonly completedPuzzles: Record<string, PuzzleCompletion>;
  /** Unlocked level dates (YYYY-MM-DD) */
  readonly unlockedLevels: readonly string[];
  /** Aggregated statistics */
  readonly statistics: Statistics;
  /** Daily streak data */
  readonly streakData: StreakData;
  /** Unlocked achievement IDs */
  readonly achievements: readonly string[];
  /** User preferences */
  readonly preferences: UserPreferences;
}

/**
 * Default user preferences
 */
export const DEFAULT_PREFERENCES: UserPreferences = {
  hintsEnabled: true,
  soundEnabled: true,
  boardTheme: 'classic',
  coordinatesVisible: true,
} as const;

/**
 * Default statistics
 */
export const DEFAULT_STATISTICS: Statistics = {
  totalPuzzlesSolved: 0,
  totalTimeSpentMs: 0,
  avgTimeByDifficulty: {
    beginner: 0,
    intermediate: 0,
    advanced: 0,
  },
  totalHintsUsed: 0,
  puzzlesWithoutHints: 0,
  rushHighScores: [],
} as const;

/**
 * Default streak data
 */
export const DEFAULT_STREAK_DATA: StreakData = {
  currentStreak: 0,
  longestStreak: 0,
  lastPlayedDate: '',
  streakStartDate: '',
} as const;

/**
 * Create default/initial user progress
 */
export function createDefaultProgress(): UserProgress {
  return {
    version: 1,
    completedPuzzles: {},
    unlockedLevels: [],
    statistics: DEFAULT_STATISTICS,
    streakData: DEFAULT_STREAK_DATA,
    achievements: [],
    preferences: DEFAULT_PREFERENCES,
  };
}

/**
 * Current schema version
 */
export const PROGRESS_SCHEMA_VERSION = 1;

// ============================================================================
// Collection Progress Types (added for Spec 021)
// ============================================================================

import type { SkillLevel as CollectionSkillLevel } from '../models/collection';

/**
 * User's progress within a single collection
 */
export interface CollectionProgress {
  /** Collection identifier this progress belongs to */
  readonly collectionId: string;
  /** IDs of completed puzzles in this collection */
  readonly completed: readonly string[];
  /** Current puzzle index (0-based) */
  readonly currentIndex: number;
  /** When user started this collection (ISO date) */
  readonly startedAt: string;
  /** Last activity timestamp (ISO date) */
  readonly lastActivity: string;
  /** Total puzzles in collection */
  readonly totalPuzzles: number;
  /** Aggregated stats for this collection */
  readonly stats?: CollectionStats;
}

/**
 * Stats for a collection attempt
 */
export interface CollectionStats {
  /** Puzzles solved correctly on first try */
  readonly correctFirstTry: number;
  /** Total hints used */
  readonly hintsUsed: number;
  /** Total time spent (milliseconds) */
  readonly totalTimeMs: number;
  /** Average time per puzzle (milliseconds) */
  readonly avgTimeMs: number;
}

/**
 * Collection status for UI display
 */
export type CollectionStatus = 'not-started' | 'in-progress' | 'completed';

/**
 * Summary view of collection progress for list display
 */
export interface CollectionProgressSummary {
  readonly collectionId: string;
  readonly status: CollectionStatus;
  readonly completedCount: number;
  readonly totalPuzzles: number;
  readonly percentComplete: number;
  readonly lastActivity?: string;
}

/**
 * User's progress on a specific daily challenge
 */
export interface DailyProgress {
  /** Challenge date (YYYY-MM-DD) */
  readonly date: string;
  /** IDs of completed puzzles */
  readonly completed: readonly string[];
  /** Current puzzle index (standard mode) */
  readonly currentIndex: number;
  /** When user started */
  readonly startedAt: string;
  /** Last activity */
  readonly lastActivity: string;
  /** Performance metrics */
  readonly performance?: DailyPerformanceData;
}

/**
 * Performance data for daily challenge
 */
export interface DailyPerformanceData {
  /** Accuracy by level: { "beginner": { correct: 5, total: 6 } } */
  readonly accuracyByLevel: Readonly<Record<string, { correct: number; total: number }>>;
  /** Total time in milliseconds */
  readonly totalTimeMs: number;
  /** Timed mode high score */
  readonly timedHighScore?: number;
}

/**
 * Technique-specific statistics
 */
export interface TechniqueStats {
  /** Technique tag (e.g., "ladder", "snapback") */
  readonly tag: string;
  /** Number of puzzles attempted */
  readonly attempted: number;
  /** Number of puzzles solved correctly */
  readonly solved: number;
  /** Accuracy percentage (0-100) */
  readonly accuracy: number;
  /** Last practiced timestamp (ISO date) */
  readonly lastPracticed: string;
}

/**
 * Extended user progress with collection tracking (Schema v3)
 */
export interface ExtendedUserProgress extends UserProgress {
  /** Collection progress indexed by collection ID */
  readonly collectionProgress: Record<string, CollectionProgress>;
  /** Daily challenge progress indexed by date (YYYY-MM-DD) */
  readonly dailyProgress: Record<string, DailyProgress>;
  /** Technique statistics indexed by tag */
  readonly techniqueStats: Record<string, TechniqueStats>;
  /** Training mode unlocked levels (by slug) */
  readonly unlockedTrainingLevels: readonly CollectionSkillLevel[];
  /** Estimated user skill level based on performance */
  readonly estimatedLevel: CollectionSkillLevel;
}

/**
 * Create default extended progress (Schema v3)
 */
export function createDefaultExtendedProgress(): ExtendedUserProgress {
  return {
    ...createDefaultProgress(),
    version: 3,
    collectionProgress: {},
    dailyProgress: {},
    techniqueStats: {},
    unlockedTrainingLevels: [FIRST_LEVEL, FALLBACK_LEVEL],
    estimatedLevel: DEFAULT_LEVEL,
  };
}
