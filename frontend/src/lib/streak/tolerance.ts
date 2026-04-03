/**
 * Midnight tolerance logic - handles timezone edge cases for streaks.
 * @module lib/streak/tolerance
 *
 * Covers: US4 (Daily Streaks), Edge Case: "User changes device date"
 *
 * Per spec.md Edge Cases:
 * - A tolerance window of ±2 hours around midnight handles minor timezone drift.
 * - If the device clock jumps forward >48 hours, streak resets.
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Pure functions, no side effects
 * - IV. Local-First: All calculations based on local dates/times
 */

import { parseDateString, getDaysDifference } from './calculator';

/**
 * Tolerance configuration.
 */
export interface ToleranceConfig {
  /** Hours before midnight to count as "today" (default: 2) */
  readonly hoursBeforeMidnight: number;
  /** Hours after midnight to count as "yesterday" (default: 2) */
  readonly hoursAfterMidnight: number;
  /** Maximum days gap before forcing streak reset (default: 2 days = 48 hours) */
  readonly maxDaysGap: number;
}

/**
 * Default tolerance configuration per spec.md.
 */
export const DEFAULT_TOLERANCE: ToleranceConfig = {
  hoursBeforeMidnight: 2,
  hoursAfterMidnight: 2,
  maxDaysGap: 2,
} as const;

/**
 * Result of tolerance check.
 */
export interface ToleranceCheckResult {
  /** Effective date to use for streak calculation */
  readonly effectiveDate: string;
  /** Whether tolerance was applied */
  readonly toleranceApplied: boolean;
  /** Explanation of what happened */
  readonly reason: string;
}

/**
 * Get the hour of day (0-23) from a Date.
 *
 * @param date - Date object
 * @returns Hour of day
 */
export function getHourOfDay(date: Date): number {
  return date.getHours();
}

/**
 * Check if a time is within the late-night tolerance window.
 * Late night (10pm - midnight) might count as "next day" for players
 * who play late and want it to count for tomorrow.
 *
 * @param date - Current date/time
 * @param config - Tolerance configuration
 * @returns True if in late-night window
 */
export function isInLateNightWindow(
  date: Date,
  config: ToleranceConfig = DEFAULT_TOLERANCE
): boolean {
  const hour = getHourOfDay(date);
  // e.g., if hoursBeforeMidnight = 2, then 22:00-23:59 is late night
  return hour >= 24 - config.hoursBeforeMidnight;
}

/**
 * Check if a time is within the early-morning tolerance window.
 * Early morning (midnight - 2am) might count as "previous day" for players
 * who played late and crossed midnight.
 *
 * @param date - Current date/time
 * @param config - Tolerance configuration
 * @returns True if in early-morning window
 */
export function isInEarlyMorningWindow(
  date: Date,
  config: ToleranceConfig = DEFAULT_TOLERANCE
): boolean {
  const hour = getHourOfDay(date);
  // e.g., if hoursAfterMidnight = 2, then 0:00-1:59 is early morning
  return hour < config.hoursAfterMidnight;
}

/**
 * Apply tolerance rules to determine the effective date for streak calculation.
 *
 * Per spec: A tolerance window of ±2 hours around midnight handles minor timezone drift.
 *
 * Behavior:
 * - If playing at 11pm, treat as "today" (no special handling needed)
 * - If playing at 1am and last played was "yesterday" (before midnight), 
 *   this is still counted as continuing the streak
 *
 * @param now - Current date/time
 * @param lastPlayedDate - Last played date string (YYYY-MM-DD)
 * @param config - Tolerance configuration
 * @returns Tolerance check result
 */
export function applyMidnightTolerance(
  now: Date,
  lastPlayedDate: string,
  config: ToleranceConfig = DEFAULT_TOLERANCE
): ToleranceCheckResult {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const todayStr = `${year}-${month}-${day}`;

  // If no previous play, just return today
  if (!lastPlayedDate) {
    return {
      effectiveDate: todayStr,
      toleranceApplied: false,
      reason: 'First time playing',
    };
  }

  const lastPlayedDateObj = parseDateString(lastPlayedDate);
  if (!lastPlayedDateObj) {
    return {
      effectiveDate: todayStr,
      toleranceApplied: false,
      reason: 'Invalid last played date',
    };
  }

  const todayDateObj = new Date(year, now.getMonth(), now.getDate());
  const daysDiff = getDaysDifference(lastPlayedDateObj, todayDateObj);

  // Check for device clock jump (>48 hours forward)
  if (daysDiff > config.maxDaysGap) {
    return {
      effectiveDate: todayStr,
      toleranceApplied: false,
      reason: `Clock jumped forward ${daysDiff} days - streak will reset`,
    };
  }

  // Early morning tolerance: If it's 0:00-2:00 and last played was "yesterday"
  // (daysDiff === 1), and user is in early morning window, treat as still "yesterday"
  // for the purpose of not breaking streak
  if (isInEarlyMorningWindow(now, config) && daysDiff === 1) {
    // The player is in the early hours of "today" but may have played late "yesterday"
    // We don't change the effective date, but we note that tolerance applies
    // The streak calculator will see this as "yesterday" which is correct
    return {
      effectiveDate: todayStr,
      toleranceApplied: true,
      reason: 'Early morning window - streak continues from yesterday',
    };
  }

  // Late night tolerance: If it's 22:00-23:59, this is still "today"
  // No special handling needed as the date is already correct
  if (isInLateNightWindow(now, config)) {
    return {
      effectiveDate: todayStr,
      toleranceApplied: false,
      reason: 'Late night window - counting as today',
    };
  }

  return {
    effectiveDate: todayStr,
    toleranceApplied: false,
    reason: 'Normal play time',
  };
}

/**
 * Check if a clock jump requires streak reset.
 *
 * Per spec: If the device clock jumps forward >48 hours, streak resets.
 *
 * @param lastPlayedDate - Last played date string (YYYY-MM-DD)
 * @param now - Current date/time
 * @param config - Tolerance configuration
 * @returns True if streak should reset due to clock jump
 */
export function shouldResetDueToClockJump(
  lastPlayedDate: string,
  now: Date,
  config: ToleranceConfig = DEFAULT_TOLERANCE
): boolean {
  if (!lastPlayedDate) {
    return false;
  }

  const lastPlayedDateObj = parseDateString(lastPlayedDate);
  if (!lastPlayedDateObj) {
    return true; // Invalid date, reset to be safe
  }

  const todayDateObj = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const daysDiff = getDaysDifference(lastPlayedDateObj, todayDateObj);

  return daysDiff > config.maxDaysGap;
}

/**
 * Get a human-readable explanation of tolerance state.
 *
 * @param result - Tolerance check result
 * @returns User-friendly message
 */
export function getToleranceExplanation(result: ToleranceCheckResult): string {
  if (result.toleranceApplied) {
    return 'Playing in the early hours still counts for your streak!';
  }
  return '';
}
