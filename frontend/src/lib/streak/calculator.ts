/**
 * Streak calculation logic - determines streak state from dates.
 * @module lib/streak/calculator
 *
 * Covers: US4 (Daily Streaks), FR-023 to FR-025
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Pure functions, no side effects
 * - IV. Local-First: All calculations based on local dates
 */

import type { StreakData } from '../../models/progress';
import { DEFAULT_STREAK_DATA } from '../../models/progress';

/**
 * Result of a streak calculation.
 */
export interface StreakCalculationResult {
  /** Updated streak data */
  readonly streakData: StreakData;
  /** Whether the streak was broken */
  readonly wasStreakBroken: boolean;
  /** Whether this was the first puzzle of the day */
  readonly isFirstPuzzleToday: boolean;
  /** Whether a new streak was started */
  readonly isNewStreak: boolean;
  /** Days missed (0 if streak continues) */
  readonly daysMissed: number;
}

/**
 * Get current local date as YYYY-MM-DD string.
 *
 * @param now - Optional Date object (for testing)
 * @returns Date string in YYYY-MM-DD format
 */
export function getCurrentLocalDate(now: Date = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Parse a YYYY-MM-DD date string to a Date object (midnight local time).
 *
 * @param dateStr - Date string in YYYY-MM-DD format
 * @returns Date object or null if invalid
 */
export function parseDateString(dateStr: string): Date | null {
  if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    return null;
  }

  const parts = dateStr.split('-').map(Number);
  const year = parts[0];
  const month = parts[1];
  const day = parts[2];
  
  if (year === undefined || month === undefined || day === undefined) {
    return null;
  }

  const date = new Date(year, month - 1, day);

  // Validate the date is valid (e.g., not 2024-02-30)
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null;
  }

  return date;
}

/**
 * Calculate the number of calendar days between two dates.
 * Ignores time, only considers calendar dates.
 *
 * @param date1 - First date
 * @param date2 - Second date
 * @returns Number of calendar days (positive if date2 > date1)
 */
export function getDaysDifference(date1: Date, date2: Date): number {
  // Reset to midnight to compare calendar days only
  const d1 = new Date(date1.getFullYear(), date1.getMonth(), date1.getDate());
  const d2 = new Date(date2.getFullYear(), date2.getMonth(), date2.getDate());

  const msPerDay = 24 * 60 * 60 * 1000;
  return Math.round((d2.getTime() - d1.getTime()) / msPerDay);
}

/**
 * Check if a date is "yesterday" relative to today.
 *
 * @param dateStr - Date string in YYYY-MM-DD format
 * @param today - Today's date string in YYYY-MM-DD format
 * @returns True if dateStr is exactly one day before today
 */
export function isYesterday(dateStr: string, today: string): boolean {
  const lastPlayed = parseDateString(dateStr);
  const todayDate = parseDateString(today);

  if (!lastPlayed || !todayDate) {
    return false;
  }

  return getDaysDifference(lastPlayed, todayDate) === 1;
}

/**
 * Check if a date is "today".
 *
 * @param dateStr - Date string in YYYY-MM-DD format
 * @param today - Today's date string in YYYY-MM-DD format
 * @returns True if dateStr equals today
 */
export function isToday(dateStr: string, today: string): boolean {
  return dateStr === today;
}

/**
 * Calculate streak state when a puzzle is completed.
 *
 * State transitions per data-model.md:
 * - If lastPlayedDate == today: no change
 * - If lastPlayedDate == yesterday: increment streak
 * - Otherwise: reset streak to 1
 *
 * @param currentStreak - Current streak data
 * @param now - Current date/time (for testing)
 * @returns Calculation result with updated streak data
 */
export function calculateStreakOnCompletion(
  currentStreak: StreakData,
  now: Date = new Date()
): StreakCalculationResult {
  const today = getCurrentLocalDate(now);
  const { lastPlayedDate, currentStreak: streak, longestStreak, streakStartDate } = currentStreak;

  // Case 1: First time playing ever
  if (!lastPlayedDate) {
    const newStreakData: StreakData = {
      currentStreak: 1,
      longestStreak: 1,
      lastPlayedDate: today,
      streakStartDate: today,
    };
    return {
      streakData: newStreakData,
      wasStreakBroken: false,
      isFirstPuzzleToday: true,
      isNewStreak: true,
      daysMissed: 0,
    };
  }

  // Case 2: Already played today - no change
  if (isToday(lastPlayedDate, today)) {
    return {
      streakData: currentStreak,
      wasStreakBroken: false,
      isFirstPuzzleToday: false,
      isNewStreak: false,
      daysMissed: 0,
    };
  }

  // Case 3: Played yesterday - continue streak
  if (isYesterday(lastPlayedDate, today)) {
    const newStreak = streak + 1;
    const newStreakData: StreakData = {
      currentStreak: newStreak,
      longestStreak: Math.max(longestStreak, newStreak),
      lastPlayedDate: today,
      streakStartDate: streakStartDate || today,
    };
    return {
      streakData: newStreakData,
      wasStreakBroken: false,
      isFirstPuzzleToday: true,
      isNewStreak: false,
      daysMissed: 0,
    };
  }

  // Case 4: Missed one or more days - break streak
  const lastPlayedDateObj = parseDateString(lastPlayedDate);
  const todayObj = parseDateString(today);
  const daysMissed = lastPlayedDateObj && todayObj
    ? getDaysDifference(lastPlayedDateObj, todayObj) - 1
    : 0;

  const newStreakData: StreakData = {
    currentStreak: 1,
    longestStreak: longestStreak, // Keep the record
    lastPlayedDate: today,
    streakStartDate: today,
  };

  return {
    streakData: newStreakData,
    wasStreakBroken: streak > 0,
    isFirstPuzzleToday: true,
    isNewStreak: true,
    daysMissed: Math.max(0, daysMissed),
  };
}

/**
 * Get streak status message for display.
 *
 * @param result - Streak calculation result
 * @returns User-friendly status message
 */
export function getStreakStatusMessage(result: StreakCalculationResult): string {
  if (result.wasStreakBroken) {
    const days = result.daysMissed;
    const dayWord = days === 1 ? 'day' : 'days';
    return `Streak broken after missing ${days} ${dayWord}. Starting fresh!`;
  }

  if (result.isNewStreak && !result.wasStreakBroken) {
    return 'Welcome! Your first puzzle starts a new streak.';
  }

  if (!result.isFirstPuzzleToday) {
    return 'Already played today. Keep it up!';
  }

  return `Streak continued! Day ${result.streakData.currentStreak}.`;
}

/**
 * Check if current streak has reached a milestone.
 *
 * @param currentStreak - Current streak count
 * @param previousStreak - Previous streak count (before completion)
 * @returns Milestone number if reached, null otherwise
 */
export function getReachedMilestone(
  currentStreak: number,
  previousStreak: number
): number | null {
  const milestones = [7, 30, 100, 365];

  for (const milestone of milestones) {
    if (currentStreak >= milestone && previousStreak < milestone) {
      return milestone;
    }
  }

  return null;
}

/**
 * Get milestone name for display.
 *
 * @param milestone - Milestone number
 * @returns Milestone name or null
 */
export function getMilestoneName(milestone: number): string | null {
  const names: Record<number, string> = {
    7: 'Weekly Warrior',
    30: 'Monthly Master',
    100: 'Century Solver',
    365: 'Year of Dedication',
  };
  return names[milestone] ?? null;
}

/**
 * Create initial/default streak data.
 */
export function createDefaultStreakData(): StreakData {
  return { ...DEFAULT_STREAK_DATA };
}
