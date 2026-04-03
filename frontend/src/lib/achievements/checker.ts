/**
 * Achievement checker.
 * Evaluates conditions and awards achievements.
 * @module lib/achievements/checker
 */

import {
  ACHIEVEMENTS,
  ACHIEVEMENT_MAP,
  type AchievementDefinition,
} from './definitions';
import type { AchievementProgress } from './progress';

/**
 * Check result for an achievement.
 */
export interface AchievementCheckResult {
  /** Achievement ID */
  readonly achievementId: string;
  /** Whether achievement was just unlocked */
  readonly unlocked: boolean;
  /** Current progress value */
  readonly currentProgress: number;
  /** Required value */
  readonly requirement: number;
  /** Progress percentage (0-100) */
  readonly progressPercent: number;
}

/**
 * Batch check result for multiple achievements.
 */
export interface BatchCheckResult {
  /** All checked achievements */
  readonly results: readonly AchievementCheckResult[];
  /** Newly unlocked achievements */
  readonly newlyUnlocked: readonly AchievementDefinition[];
  /** Achievements that made progress */
  readonly progressed: readonly AchievementCheckResult[];
}

/**
 * Progress stats for checking achievements.
 */
export interface ProgressStats {
  /** Total puzzles solved */
  totalPuzzlesSolved: number;
  /** Puzzles solved without hints */
  puzzlesWithoutHints: number;
  /** Current streak length */
  currentStreak: number;
  /** Longest streak ever */
  longestStreak: number;
  /** Total rush sessions completed */
  rushSessionsCompleted: number;
  /** Best rush score */
  bestRushScore: number;
  /** Best rush streak */
  bestRushStreak: number;
  /** Had a perfect rush (no skips) */
  hadPerfectRush: boolean;
  /** Daily challenges completed */
  challengesCompleted: number;
  /** Had a perfect challenge (all puzzles) */
  hadPerfectChallenge: boolean;
  /** Easy puzzles solved */
  easyPuzzlesSolved: number;
  /** Hard puzzles solved */
  hardPuzzlesSolved: number;
  /** Expert puzzles solved */
  expertPuzzlesSolved: number;
}

/**
 * Get current value for an achievement based on stats.
 */
function getCurrentValue(
  achievement: AchievementDefinition,
  stats: ProgressStats
): number {
  switch (achievement.id) {
    // Puzzle count achievements
    case 'first_solve':
    case 'puzzles_10':
    case 'puzzles_50':
    case 'puzzles_100':
    case 'puzzles_500':
    case 'puzzles_1000':
      return stats.totalPuzzlesSolved;

    // No hints achievements
    case 'no_hints_10':
    case 'no_hints_50':
    case 'no_hints_100':
      return stats.puzzlesWithoutHints;

    // Streak achievements
    case 'streak_3':
    case 'streak_7':
    case 'streak_30':
    case 'streak_100':
    case 'streak_365':
      return Math.max(stats.currentStreak, stats.longestStreak);

    // Rush achievements
    case 'rush_first':
      return stats.rushSessionsCompleted;
    case 'rush_score_500':
    case 'rush_score_1000':
    case 'rush_score_2000':
      return stats.bestRushScore;
    case 'rush_perfect':
      return stats.hadPerfectRush ? 1 : 0;
    case 'rush_streak_10':
      return stats.bestRushStreak;

    // Challenge achievements
    case 'challenge_first':
    case 'challenge_10':
      return stats.challengesCompleted;
    case 'challenge_perfect':
      return stats.hadPerfectChallenge ? 1 : 0;

    // Difficulty achievements
    case 'difficulty_easy_10':
      return stats.easyPuzzlesSolved;
    case 'difficulty_hard_10':
      return stats.hardPuzzlesSolved;
    case 'difficulty_expert_10':
      return stats.expertPuzzlesSolved;

    default:
      return 0;
  }
}

/**
 * Check a single achievement.
 */
export function checkAchievement(
  achievementId: string,
  stats: ProgressStats,
  alreadyUnlocked: boolean
): AchievementCheckResult | null {
  const achievement = ACHIEVEMENT_MAP.get(achievementId);
  if (!achievement) {
    return null;
  }

  const currentProgress = getCurrentValue(achievement, stats);
  const progressPercent = Math.min(100, (currentProgress / achievement.requirement) * 100);
  const meetsRequirement = currentProgress >= achievement.requirement;
  const unlocked = meetsRequirement && !alreadyUnlocked;

  return {
    achievementId,
    unlocked,
    currentProgress,
    requirement: achievement.requirement,
    progressPercent,
  };
}

/**
 * Check all achievements.
 */
export function checkAllAchievements(
  stats: ProgressStats,
  currentProgress: AchievementProgress
): BatchCheckResult {
  const results: AchievementCheckResult[] = [];
  const newlyUnlocked: AchievementDefinition[] = [];
  const progressed: AchievementCheckResult[] = [];

  for (const achievement of ACHIEVEMENTS) {
    const alreadyUnlocked = currentProgress.unlockedIds.includes(achievement.id);
    const previousProgress = currentProgress.progressValues[achievement.id] ?? 0;

    const result = checkAchievement(achievement.id, stats, alreadyUnlocked);
    if (result) {
      results.push(result);

      if (result.unlocked) {
        newlyUnlocked.push(achievement);
      } else if (!alreadyUnlocked && result.currentProgress > previousProgress) {
        progressed.push(result);
      }
    }
  }

  return { results, newlyUnlocked, progressed };
}

/**
 * Check achievements for specific trigger.
 */
export type AchievementTrigger =
  | 'puzzle_solved'
  | 'streak_updated'
  | 'rush_completed'
  | 'challenge_completed';

/**
 * Get achievement IDs relevant to a trigger.
 */
export function getRelevantAchievements(trigger: AchievementTrigger): readonly string[] {
  switch (trigger) {
    case 'puzzle_solved':
      return [
        'first_solve', 'puzzles_10', 'puzzles_50', 'puzzles_100', 'puzzles_500', 'puzzles_1000',
        'no_hints_10', 'no_hints_50', 'no_hints_100',
        'difficulty_easy_10', 'difficulty_hard_10', 'difficulty_expert_10',
      ];

    case 'streak_updated':
      return ['streak_3', 'streak_7', 'streak_30', 'streak_100', 'streak_365'];

    case 'rush_completed':
      return [
        'rush_first', 'rush_score_500', 'rush_score_1000', 'rush_score_2000',
        'rush_perfect', 'rush_streak_10',
      ];

    case 'challenge_completed':
      return ['challenge_first', 'challenge_10', 'challenge_perfect'];

    default:
      return [];
  }
}

/**
 * Check only achievements relevant to a specific trigger.
 */
export function checkTriggeredAchievements(
  trigger: AchievementTrigger,
  stats: ProgressStats,
  currentProgress: AchievementProgress
): BatchCheckResult {
  const relevantIds = getRelevantAchievements(trigger);
  const results: AchievementCheckResult[] = [];
  const newlyUnlocked: AchievementDefinition[] = [];
  const progressed: AchievementCheckResult[] = [];

  for (const achievementId of relevantIds) {
    const achievement = ACHIEVEMENT_MAP.get(achievementId);
    if (!achievement) continue;

    const alreadyUnlocked = currentProgress.unlockedIds.includes(achievementId);
    const previousProgress = currentProgress.progressValues[achievementId] ?? 0;

    const result = checkAchievement(achievementId, stats, alreadyUnlocked);
    if (result) {
      results.push(result);

      if (result.unlocked) {
        newlyUnlocked.push(achievement);
      } else if (!alreadyUnlocked && result.currentProgress > previousProgress) {
        progressed.push(result);
      }
    }
  }

  return { results, newlyUnlocked, progressed };
}

/**
 * Create default progress stats.
 */
export function createDefaultStats(): ProgressStats {
  return {
    totalPuzzlesSolved: 0,
    puzzlesWithoutHints: 0,
    currentStreak: 0,
    longestStreak: 0,
    rushSessionsCompleted: 0,
    bestRushScore: 0,
    bestRushStreak: 0,
    hadPerfectRush: false,
    challengesCompleted: 0,
    hadPerfectChallenge: false,
    easyPuzzlesSolved: 0,
    hardPuzzlesSolved: 0,
    expertPuzzlesSolved: 0,
  };
}
