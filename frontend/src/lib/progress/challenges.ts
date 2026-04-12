/**
 * Challenge unlock logic - determines which daily challenges are accessible.
 * @module lib/progress/challenges
 */

import type { UserProgress } from '../../types/progress';
import { getCompletionsForDate } from './puzzles';

/**
 * Number of puzzles needed to unlock subsequent challenges.
 * Users must complete at least this many puzzles from a day to unlock the next day.
 */
export const PUZZLES_TO_UNLOCK = 1;

/**
 * Maximum number of days that can be unlocked ahead of current date.
 * For future challenge support (e.g., preview content).
 */
export const MAX_FUTURE_DAYS = 0;

/**
 * Challenge unlock status.
 */
export interface ChallengeUnlockStatus {
  /** The challenge date (YYYY-MM-DD) */
  readonly date: string;
  /** Whether the challenge is unlocked */
  readonly isUnlocked: boolean;
  /** Whether this is today's challenge */
  readonly isToday: boolean;
  /** Whether this is a future challenge */
  readonly isFuture: boolean;
  /** Number of puzzles completed for this challenge */
  readonly completedCount: number;
  /** Reason why it's locked (if applicable) */
  readonly lockReason?: string;
}

/**
 * Get today's date in YYYY-MM-DD format (local timezone).
 */
export function getTodayDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Get yesterday's date in YYYY-MM-DD format (local timezone).
 */
export function getYesterdayDate(): string {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const year = yesterday.getFullYear();
  const month = String(yesterday.getMonth() + 1).padStart(2, '0');
  const day = String(yesterday.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Parse a date string and compare to another date.
 *
 * @param dateStr - Date string in YYYY-MM-DD format
 * @param referenceStr - Reference date string in YYYY-MM-DD format
 * @returns -1 if dateStr < referenceStr, 0 if equal, 1 if dateStr > referenceStr
 */
export function compareDates(dateStr: string, referenceStr: string): number {
  // Simple string comparison works for YYYY-MM-DD format
  if (dateStr < referenceStr) return -1;
  if (dateStr > referenceStr) return 1;
  return 0;
}

/**
 * Check if a date is in the future.
 *
 * @param dateStr - Date string in YYYY-MM-DD format
 * @returns True if date is after today
 */
export function isFutureDate(dateStr: string): boolean {
  return compareDates(dateStr, getTodayDate()) > 0;
}

/**
 * Check if a date is today.
 *
 * @param dateStr - Date string in YYYY-MM-DD format
 * @returns True if date is today
 */
export function isToday(dateStr: string): boolean {
  return dateStr === getTodayDate();
}

/**
 * Check if a challenge date is unlocked.
 * A challenge is unlocked if:
 * 1. It's today or in the past
 * 2. It's explicitly in the unlockedLevels list
 *
 * Note: For now, all past challenges are unlocked (no sequential requirements).
 *
 * @param _progress - User progress (reserved for future unlock logic)
 * @param date - Challenge date (YYYY-MM-DD)
 * @returns True if challenge is accessible
 */
export function isChallengeUnlocked(_progress: UserProgress, date: string): boolean {
  // Future dates are locked
  if (isFutureDate(date)) {
    return false;
  }

  // Today is always unlocked
  if (isToday(date)) {
    return true;
  }

  // Past dates are unlocked (could add sequential unlock logic here)
  return true;
}

/**
 * Get detailed unlock status for a challenge.
 *
 * @param progress - User progress
 * @param date - Challenge date (YYYY-MM-DD)
 * @param _totalPuzzles - Total puzzles in the challenge (reserved for future use)
 * @returns Detailed unlock status
 */
export function getChallengeUnlockStatus(
  progress: UserProgress,
  date: string,
  _totalPuzzles?: number
): ChallengeUnlockStatus {
  const completions = getCompletionsForDate(progress, date);
  const completedCount = completions.length;
  const dateIsToday = isToday(date);
  const dateIsFuture = isFutureDate(date);

  // Base status
  const status: ChallengeUnlockStatus = {
    date,
    isToday: dateIsToday,
    isFuture: dateIsFuture,
    completedCount,
    isUnlocked: false,
  };

  // Future dates are locked
  if (dateIsFuture) {
    return {
      ...status,
      lockReason: 'This challenge is not yet available.',
    };
  }

  // Today and past are unlocked
  return {
    ...status,
    isUnlocked: true,
  };
}

/**
 * Unlock a challenge explicitly (add to unlockedLevels).
 *
 * @param progress - Current user progress
 * @param date - Challenge date to unlock
 * @returns Updated user progress
 */
export function unlockChallenge(progress: UserProgress, date: string): UserProgress {
  // Already unlocked check
  if (progress.unlockedLevels.includes(date)) {
    return progress;
  }

  return {
    ...progress,
    unlockedLevels: [...progress.unlockedLevels, date],
  };
}

/**
 * Get all explicitly unlocked challenge dates.
 *
 * @param progress - User progress
 * @returns Array of unlocked date strings
 */
export function getUnlockedChallenges(progress: UserProgress): readonly string[] {
  return progress.unlockedLevels;
}

/**
 * Calculate challenge progress percentage.
 *
 * @param completedCount - Number of completed puzzles
 * @param totalPuzzles - Total puzzles in challenge
 * @returns Progress percentage (0-100)
 */
export function calculateChallengeProgress(completedCount: number, totalPuzzles: number): number {
  if (totalPuzzles === 0) return 0;
  return Math.round((completedCount / totalPuzzles) * 100);
}

/**
 * Check if a challenge is complete.
 *
 * @param progress - User progress
 * @param date - Challenge date
 * @param totalPuzzles - Total puzzles in challenge
 * @returns True if all puzzles are completed
 */
export function isChallengeComplete(
  progress: UserProgress,
  date: string,
  totalPuzzles: number
): boolean {
  const completions = getCompletionsForDate(progress, date);
  return completions.length >= totalPuzzles && totalPuzzles > 0;
}

/**
 * Get dates of all challenges with at least one completion.
 *
 * @param progress - User progress
 * @returns Array of unique challenge dates
 */
export function getStartedChallengeDates(progress: UserProgress): readonly string[] {
  const dates = new Set<string>();

  for (const puzzleId of Object.keys(progress.completedPuzzles)) {
    // Extract date from puzzle ID (format: YYYY-MM-DD-NNN)
    const parts = puzzleId.split('-');
    if (parts.length >= 3) {
      const date = `${parts[0]}-${parts[1]}-${parts[2]}`;
      dates.add(date);
    }
  }

  return Array.from(dates).sort().reverse(); // Most recent first
}

/**
 * Get the most recent challenge date the user has interacted with.
 *
 * @param progress - User progress
 * @returns Most recent date or null if no completions
 */
export function getMostRecentChallengeDate(progress: UserProgress): string | null {
  const dates = getStartedChallengeDates(progress);
  return dates[0] ?? null;
}
