/**
 * Puzzle completion tracking - records when puzzles are solved.
 * @module lib/progress/puzzles
 */

import type { PuzzleCompletion, UserProgress } from '../../types/progress';
import type { SkillLevel } from '../../types/puzzle';
import { calculateStreakOnCompletion, type StreakCalculationResult } from '../streak';
import {
  loadAchievementProgress,
  saveAchievementProgress,
  unlockMultipleAchievements,
  updateMultipleProgressValues,
  // AchievementProgress imported but used for type reference only
} from '../achievements/progress';

import {
  checkTriggeredAchievements,
  type ProgressStats,
  type AchievementTrigger,
} from '../achievements/checker';
import type { AchievementDefinition } from '../achievements/definitions';

/**
 * Data required to record a puzzle completion.
 */
export interface CompletionData {
  /** Puzzle ID */
  readonly puzzleId: string;
  /** Time spent solving (milliseconds) */
  readonly timeSpentMs: number;
  /** Number of incorrect attempts */
  readonly attempts: number;
  /** Number of hints used */
  readonly hintsUsed: number;
  /** Skill level of the puzzle (1-5) */
  readonly skillLevel: SkillLevel;
}

/**
 * Result of recording a puzzle completion.
 * Includes both the updated progress and streak calculation results.
 */
export interface CompletionResult {
  /** Updated user progress */
  readonly progress: UserProgress;
  /** Whether this was a new completion (false if already completed) */
  readonly wasNewCompletion: boolean;
  /** Streak calculation result (if new completion) */
  readonly streakResult: StreakCalculationResult | null;
  /** Milestone reached (7, 30, 100, 365) or null */
  readonly milestoneReached: number | null;
  /** Newly unlocked achievements */
  readonly newlyUnlockedAchievements: readonly AchievementDefinition[];
}

/**
 * Check if a puzzle has been completed.
 *
 * @param progress - Current user progress
 * @param puzzleId - Puzzle ID to check
 * @returns True if puzzle is completed
 */
export function isPuzzleCompleted(
  progress: UserProgress,
  puzzleId: string
): boolean {
  return puzzleId in progress.completedPuzzles;
}

/**
 * Get completion data for a specific puzzle.
 *
 * @param progress - Current user progress
 * @param puzzleId - Puzzle ID to get
 * @returns PuzzleCompletion if found, undefined otherwise
 */
export function getPuzzleCompletion(
  progress: UserProgress,
  puzzleId: string
): PuzzleCompletion | undefined {
  return progress.completedPuzzles[puzzleId];
}

/**
 * Get all completed puzzle IDs.
 *
 * @param progress - Current user progress
 * @returns Array of completed puzzle IDs
 */
export function getCompletedPuzzleIds(progress: UserProgress): readonly string[] {
  return Object.keys(progress.completedPuzzles);
}

/**
 * Get count of completed puzzles.
 *
 * @param progress - Current user progress
 * @returns Number of completed puzzles
 */
export function getCompletedCount(progress: UserProgress): number {
  return Object.keys(progress.completedPuzzles).length;
}

/**
 * Get completions for a specific date (challenge).
 *
 * @param progress - Current user progress
 * @param date - Date string (YYYY-MM-DD)
 * @returns Array of completions for that date
 */
export function getCompletionsForDate(
  progress: UserProgress,
  date: string
): readonly PuzzleCompletion[] {
  return Object.values(progress.completedPuzzles).filter((completion) =>
    completion.puzzleId.startsWith(date)
  );
}

/**
 * Get completions by skill level.
 *
 * @param progress - Current user progress
 * @param _skillLevel - Skill level (1-5) - reserved for future use
 * @returns Array of completions for that skill level
 */
export function getCompletionsBySkillLevel(
  progress: UserProgress,
  _skillLevel: SkillLevel
): readonly PuzzleCompletion[] {
  // Note: PuzzleCompletion doesn't store skillLevel directly in the schema
  // We would need to look up the puzzle to get its level
  // For now, filter by examining puzzle IDs or return all
  // This is a limitation of the current schema
  return Object.values(progress.completedPuzzles);
}

/**
 * Record a puzzle completion.
 * Returns a new UserProgress with the completion added.
 *
 * @param progress - Current user progress
 * @param data - Completion data
 * @returns Updated user progress (immutable)
 * @deprecated Use recordCompletionWithStreak for streak support
 */
export function recordCompletion(
  progress: UserProgress,
  data: CompletionData
): UserProgress {
  const { puzzleId, timeSpentMs, attempts, hintsUsed } = data;

  // Don't overwrite existing completion (first completion wins)
  if (isPuzzleCompleted(progress, puzzleId)) {
    return progress;
  }

  const completion: PuzzleCompletion = {
    puzzleId,
    completedAt: new Date().toISOString(),
    timeSpentMs,
    attempts,
    hintsUsed,
  };

  return {
    ...progress,
    completedPuzzles: {
      ...progress.completedPuzzles,
      [puzzleId]: completion,
    },
  };
}

/**
 * MILESTONE_THRESHOLDS - recognized streak milestones
 */
const MILESTONE_THRESHOLDS = [7, 30, 100, 365] as const;

/**
 * Check if a milestone was just reached.
 *
 * @param previousStreak - Streak count before completion
 * @param currentStreak - Streak count after completion
 * @returns Milestone number if just reached, null otherwise
 */
function checkMilestoneReached(
  previousStreak: number,
  currentStreak: number
): number | null {
  for (const milestone of MILESTONE_THRESHOLDS) {
    if (currentStreak >= milestone && previousStreak < milestone) {
      return milestone;
    }
  }
  return null;
}

/**
 * Record a puzzle completion with streak update.
 * Returns both the updated progress and streak calculation details.
 * This is the primary function for recording completions.
 *
 * @param progress - Current user progress
 * @param data - Completion data
 * @returns CompletionResult with progress and streak info
 */
export function recordCompletionWithStreak(
  progress: UserProgress,
  data: CompletionData
): CompletionResult {
  const { puzzleId, timeSpentMs, attempts, hintsUsed, skillLevel } = data;

  // Check if already completed
  if (isPuzzleCompleted(progress, puzzleId)) {
    return {
      progress,
      wasNewCompletion: false,
      streakResult: null,
      milestoneReached: null,
      newlyUnlockedAchievements: [],
    };
  }

  // Create completion record
  const completion: PuzzleCompletion = {
    puzzleId,
    completedAt: new Date().toISOString(),
    timeSpentMs,
    attempts,
    hintsUsed,
  };

  // Calculate streak update
  // Note: progress.streakData uses types/progress which requires non-null dates
  // We need to handle conversion from models/progress which allows null
  const previousStreak = progress.streakData.currentStreak;
  const streakResult = calculateStreakOnCompletion({
    currentStreak: progress.streakData.currentStreak,
    longestStreak: progress.streakData.longestStreak,
    lastPlayedDate: progress.streakData.lastPlayedDate || null,
    streakStartDate: progress.streakData.streakStartDate || null,
  });

  // Check for milestone
  const milestoneReached = checkMilestoneReached(
    previousStreak,
    streakResult.streakData.currentStreak
  );

  // Build updated progress
  const updatedProgress: UserProgress = {
    ...progress,
    completedPuzzles: {
      ...progress.completedPuzzles,
      [puzzleId]: completion,
    },
    streakData: {
      currentStreak: streakResult.streakData.currentStreak,
      longestStreak: streakResult.streakData.longestStreak,
      lastPlayedDate: streakResult.streakData.lastPlayedDate ?? progress.streakData.lastPlayedDate,
      streakStartDate: streakResult.streakData.streakStartDate ?? progress.streakData.streakStartDate,
    },
  };

  // Check and update achievements
  const newlyUnlockedAchievements = checkAndUpdateAchievements(
    updatedProgress,
    hintsUsed,
    skillLevel,
    'puzzle_solved'
  );

  // Also check streak achievements if streak was updated
  if (streakResult.isFirstPuzzleToday || milestoneReached) {
    const streakUnlocks = checkAndUpdateAchievements(
      updatedProgress,
      hintsUsed,
      skillLevel,
      'streak_updated'
    );
    newlyUnlockedAchievements.push(...streakUnlocks);
  }

  return {
    progress: updatedProgress,
    wasNewCompletion: true,
    streakResult,
    milestoneReached,
    newlyUnlockedAchievements,
  };
}

/**
 * Clear a specific puzzle completion (for testing/admin).
 *
 * @param progress - Current user progress
 * @param puzzleId - Puzzle ID to clear
 * @returns Updated user progress
 */
export function clearCompletion(
  progress: UserProgress,
  puzzleId: string
): UserProgress {
  if (!isPuzzleCompleted(progress, puzzleId)) {
    return progress;
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { [puzzleId]: _, ...remaining } = progress.completedPuzzles;

  return {
    ...progress,
    completedPuzzles: remaining,
  };
}

/**
 * Get completion statistics for a specific date.
 *
 * @param progress - Current user progress
 * @param date - Date string (YYYY-MM-DD)
 * @param totalPuzzles - Total puzzles for that date
 * @returns Completion stats
 */
export function getDateCompletionStats(
  progress: UserProgress,
  date: string,
  totalPuzzles: number
): {
  readonly completed: number;
  readonly total: number;
  readonly percentage: number;
  readonly isComplete: boolean;
} {
  const completions = getCompletionsForDate(progress, date);
  const completed = completions.length;
  const percentage = totalPuzzles > 0 ? (completed / totalPuzzles) * 100 : 0;

  return {
    completed,
    total: totalPuzzles,
    percentage,
    isComplete: completed >= totalPuzzles && totalPuzzles > 0,
  };
}

/**
 * Get recent completions sorted by date.
 *
 * @param progress - Current user progress
 * @param limit - Maximum number to return
 * @returns Array of recent completions (most recent first)
 */
export function getRecentCompletions(
  progress: UserProgress,
  limit: number = 10
): readonly PuzzleCompletion[] {
  return Object.values(progress.completedPuzzles)
    .sort((a, b) => {
      // Sort by completedAt descending
      return new Date(b.completedAt).getTime() - new Date(a.completedAt).getTime();
    })
    .slice(0, limit);
}

/**
 * Calculate average solve time for all completed puzzles.
 *
 * @param progress - Current user progress
 * @returns Average time in milliseconds, 0 if no completions
 */
export function getAverageSolveTime(progress: UserProgress): number {
  const completions = Object.values(progress.completedPuzzles);
  if (completions.length === 0) {
    return 0;
  }

  const totalTime = completions.reduce((sum, c) => sum + c.timeSpentMs, 0);
  return totalTime / completions.length;
}

/**
 * Get puzzle IDs completed today.
 *
 * @param progress - Current user progress
 * @returns Array of puzzle IDs completed today
 */
export function getTodayCompletions(progress: UserProgress): readonly string[] {
  const today = new Date().toISOString().split('T')[0] ?? '';

  return Object.values(progress.completedPuzzles)
    .filter((c) => c.completedAt.startsWith(today))
    .map((c) => c.puzzleId);
}

/**
 * Count puzzles solved without hints.
 *
 * @param progress - User progress
 * @returns Count of puzzles with 0 hints used
 */
export function countPuzzlesWithoutHints(progress: UserProgress): number {
  return Object.values(progress.completedPuzzles)
    .filter((c) => c.hintsUsed === 0)
    .length;
}

/**
 * Build progress stats for achievement checking.
 *
 * @param progress - User progress
 * @param hintsUsedThisPuzzle - Hints used for the current puzzle
 * @param skillLevel - Skill level of the current puzzle
 * @returns Progress stats for achievement checker
 */
function buildProgressStats(
  progress: UserProgress,
  _hintsUsedThisPuzzle: number,
  skillLevel: SkillLevel
): ProgressStats {
  const completions = Object.values(progress.completedPuzzles);
  const totalPuzzlesSolved = completions.length;
  const puzzlesWithoutHints = countPuzzlesWithoutHints(progress);

  // Count by difficulty (skill level ranges)
  // Level 1-2 = easy, 3 = medium, 4 = hard, 5 = expert
  const _easyPuzzles = completions.filter(() => {
    // We'd need puzzle metadata to check skill level
    // For now, estimate based on puzzle ID patterns or default
    return true; // Placeholder - would need puzzle lookup
  }).length;
  void _easyPuzzles; // Suppress unused warning

  // Map skill level slugs to difficulty categories
  const easyLevels: readonly SkillLevel[] = ['novice', 'beginner', 'elementary'];
  const hardLevels: readonly SkillLevel[] = ['advanced', 'low-dan', 'high-dan'];
  const expertLevels: readonly SkillLevel[] = ['expert'];

  return {
    totalPuzzlesSolved,
    puzzlesWithoutHints,
    currentStreak: progress.streakData.currentStreak,
    longestStreak: progress.streakData.longestStreak,
    rushSessionsCompleted: 0, // Would need to load from rush progress
    bestRushScore: 0,
    bestRushStreak: 0,
    hadPerfectRush: false,
    challengesCompleted: 0, // Would need separate tracking
    hadPerfectChallenge: false,
    easyPuzzlesSolved: easyLevels.includes(skillLevel) ? totalPuzzlesSolved : 0,
    hardPuzzlesSolved: hardLevels.includes(skillLevel) ? totalPuzzlesSolved : 0,
    expertPuzzlesSolved: expertLevels.includes(skillLevel) ? totalPuzzlesSolved : 0,
  };
}

/**
 * Check achievements and update progress.
 *
 * @param progress - User progress after completion
 * @param hintsUsed - Hints used for this puzzle
 * @param skillLevel - Skill level of the puzzle
 * @param trigger - What triggered this check
 * @returns Array of newly unlocked achievements
 */
function checkAndUpdateAchievements(
  progress: UserProgress,
  hintsUsed: number,
  skillLevel: SkillLevel,
  trigger: AchievementTrigger
): AchievementDefinition[] {
  // Load current achievement progress
  let achievementProgress = loadAchievementProgress();

  // Build stats for checking
  const stats = buildProgressStats(progress, hintsUsed, skillLevel);

  // Check achievements
  const result = checkTriggeredAchievements(trigger, stats, achievementProgress);

  // If any achievements were unlocked, update and save
  if (result.newlyUnlocked.length > 0) {
    achievementProgress = unlockMultipleAchievements(
      achievementProgress,
      result.newlyUnlocked.map((a) => a.id)
    );
  }

  // Update progress values for tracking
  const progressUpdates: Record<string, number> = {};
  for (const r of result.results) {
    if (r.currentProgress > (achievementProgress.progressValues[r.achievementId] ?? 0)) {
      progressUpdates[r.achievementId] = r.currentProgress;
    }
  }
  if (Object.keys(progressUpdates).length > 0) {
    achievementProgress = updateMultipleProgressValues(achievementProgress, progressUpdates);
  }

  // Save updated progress
  saveAchievementProgress(achievementProgress);

  return [...result.newlyUnlocked];
}
