/**
 * Streak Manager Service
 * @module services/streakManager
 *
 * Handles daily streak tracking, reset logic, and milestone detection.
 *
 * Covers: FR-023 to FR-026, US4
 */

import type { StreakData } from '@/models/progress';
import { getStreakData, updateStreakData, type ProgressResult } from '@services/progressTracker';

/** Streak milestones for achievements */
export const STREAK_MILESTONES = [3, 7, 14, 30, 60, 100, 365] as const;
export type StreakMilestone = (typeof STREAK_MILESTONES)[number];

/** Result of a streak update */
export interface StreakUpdateResult {
  readonly streakData: StreakData;
  readonly streakContinued: boolean;
  readonly streakBroken: boolean;
  readonly milestonesReached: readonly StreakMilestone[];
}

/**
 * Get today's date in YYYY-MM-DD format using UTC timezone
 *
 * Using UTC ensures consistent streak tracking across all timezones
 * and prevents issues with daylight saving time transitions.
 */
export function getUTCDateString(date: Date = new Date()): string {
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** @deprecated Use getUTCDateString instead */
export const getLocalDateString = getUTCDateString;

/**
 * Parse a date string (YYYY-MM-DD) into a Date object (midnight UTC)
 */
export function parseDateString(dateStr: string): Date {
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(Date.UTC(year!, month! - 1, day));
}

/**
 * Calculate the difference in days between two date strings
 * Returns positive if date1 is after date2
 */
export function daysDifference(date1: string, date2: string): number {
  const d1 = parseDateString(date1);
  const d2 = parseDateString(date2);
  const diffTime = d1.getTime() - d2.getTime();
  return Math.round(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * Check if a date is yesterday relative to another date
 */
export function isYesterday(checkDate: string, relativeToDate: string): boolean {
  return daysDifference(relativeToDate, checkDate) === 1;
}

/**
 * Check if a date is today relative to another date
 */
export function isToday(checkDate: string, relativeToDate: string): boolean {
  return checkDate === relativeToDate;
}

/**
 * Check if a streak milestone has been reached
 */
export function checkMilestones(
  streak: number,
  previousStreak: number
): readonly StreakMilestone[] {
  return STREAK_MILESTONES.filter((milestone) => streak >= milestone && previousStreak < milestone);
}

/**
 * Helper to create error result from updateStreakData failure
 */
function createErrorResult(result: ProgressResult<unknown>): ProgressResult<StreakUpdateResult> {
  return {
    success: false,
    error: result.error ?? 'save_failed',
    message: result.message ?? 'Failed to save streak data',
  };
}

/**
 * Record a play activity and update the streak accordingly
 *
 * Streak logic:
 * - If this is the first play, start a new streak
 * - If played yesterday, increment streak
 * - If played today, no change
 * - If more than 1 day since last play, reset streak to 1
 */
export function recordPlay(today: string = getUTCDateString()): ProgressResult<StreakUpdateResult> {
  const streakData = getStreakData();

  const { lastPlayedDate, currentStreak, longestStreak, streakStartDate } = streakData;

  // First time playing
  if (lastPlayedDate === null) {
    const newStreakData: StreakData = {
      currentStreak: 1,
      longestStreak: 1,
      lastPlayedDate: today,
      streakStartDate: today,
    };

    const result = updateStreakData(newStreakData);
    if (!result.success) {
      return createErrorResult(result);
    }

    return {
      success: true,
      data: {
        streakData: newStreakData,
        streakContinued: true,
        streakBroken: false,
        milestonesReached: checkMilestones(1, 0),
      },
    };
  }

  // Already played today
  if (isToday(lastPlayedDate, today)) {
    return {
      success: true,
      data: {
        streakData,
        streakContinued: false,
        streakBroken: false,
        milestonesReached: [],
      },
    };
  }

  // Played yesterday - continue streak
  if (isYesterday(lastPlayedDate, today)) {
    const newStreak = currentStreak + 1;
    const newLongest = Math.max(longestStreak, newStreak);

    const newStreakData: StreakData = {
      currentStreak: newStreak,
      longestStreak: newLongest,
      lastPlayedDate: today,
      streakStartDate,
    };

    const result = updateStreakData(newStreakData);
    if (!result.success) {
      return createErrorResult(result);
    }

    return {
      success: true,
      data: {
        streakData: newStreakData,
        streakContinued: true,
        streakBroken: false,
        milestonesReached: checkMilestones(newStreak, currentStreak),
      },
    };
  }

  // More than 1 day since last play - streak broken, start new
  const newStreakData: StreakData = {
    currentStreak: 1,
    longestStreak, // Keep the longest streak
    lastPlayedDate: today,
    streakStartDate: today,
  };

  const result = updateStreakData(newStreakData);
  if (!result.success) {
    return createErrorResult(result);
  }

  return {
    success: true,
    data: {
      streakData: newStreakData,
      streakContinued: false,
      streakBroken: true,
      milestonesReached: [],
    },
  };
}

/**
 * Check if the current streak is at risk (no play today, but played yesterday)
 */
export function isStreakAtRisk(today: string = getLocalDateString()): boolean {
  const streakData = getStreakData();

  if (streakData.lastPlayedDate === null) {
    return false;
  }

  if (streakData.currentStreak === 0) {
    return false;
  }

  // Not played today and played yesterday means at risk
  return (
    !isToday(streakData.lastPlayedDate, today) && isYesterday(streakData.lastPlayedDate, today)
  );
}

/**
 * Check if the streak is currently active (played today or yesterday)
 */
export function isStreakActive(today: string = getLocalDateString()): boolean {
  const streakData = getStreakData();

  if (streakData.lastPlayedDate === null) {
    return false;
  }

  return isToday(streakData.lastPlayedDate, today) || isYesterday(streakData.lastPlayedDate, today);
}

/**
 * Get the number of days until a milestone
 */
export function daysUntilMilestone(currentStreak: number): number | null {
  const nextMilestone = STREAK_MILESTONES.find((m) => m > currentStreak);
  return nextMilestone ? nextMilestone - currentStreak : null;
}

/**
 * Get the next milestone target
 */
export function getNextMilestone(currentStreak: number): StreakMilestone | null {
  return STREAK_MILESTONES.find((m) => m > currentStreak) ?? null;
}

/**
 * Calculate streak statistics
 */
export interface StreakStats {
  readonly currentStreak: number;
  readonly longestStreak: number;
  readonly isActive: boolean;
  readonly isAtRisk: boolean;
  readonly nextMilestone: StreakMilestone | null;
  readonly daysUntilNextMilestone: number | null;
  readonly streakStartDate: string | null;
  readonly lastPlayedDate: string | null;
}

export function getStreakStats(today: string = getLocalDateString()): StreakStats {
  const streakData = getStreakData();
  const isActive = isStreakActive(today);
  const isAtRisk = isStreakAtRisk(today);

  // If streak is broken (not active and not at risk), current streak is 0
  const effectiveStreak = isActive || isAtRisk ? streakData.currentStreak : 0;

  return {
    currentStreak: effectiveStreak,
    longestStreak: streakData.longestStreak,
    isActive,
    isAtRisk,
    nextMilestone: getNextMilestone(effectiveStreak),
    daysUntilNextMilestone: daysUntilMilestone(effectiveStreak),
    streakStartDate: streakData.streakStartDate,
    lastPlayedDate: streakData.lastPlayedDate,
  };
}
