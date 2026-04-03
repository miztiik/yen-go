/**
 * Streak reset detection - determines when and why streaks are broken.
 * @module lib/streak/reset
 *
 * Covers: US4 (Daily Streaks), FR-025 (Streak reset detection)
 *
 * Per spec.md US4-Scenario 3:
 * "Given I missed a day, When I play again, Then my streak resets to 1 
 *  with a message about the broken streak"
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Pure functions, no side effects
 * - IV. Local-First: All calculations based on local dates
 */

import type { StreakData } from '../../models/progress';
import {
  getCurrentLocalDate,
  parseDateString,
  getDaysDifference,
  isToday,
  isYesterday,
} from './calculator';
import {
  shouldResetDueToClockJump,
  DEFAULT_TOLERANCE,
  type ToleranceConfig,
} from './tolerance';

/**
 * Reason why a streak was or will be reset.
 */
export type StreakResetReason =
  | 'missed_day'
  | 'missed_multiple_days'
  | 'clock_jump'
  | 'corrupted_data'
  | 'first_time'
  | 'none';

/**
 * Detailed information about a streak reset.
 */
export interface StreakResetInfo {
  /** Whether streak will be reset */
  readonly willReset: boolean;
  /** Reason for reset */
  readonly reason: StreakResetReason;
  /** Number of days missed (if applicable) */
  readonly daysMissed: number;
  /** Previous streak count that was lost */
  readonly previousStreak: number;
  /** Human-readable message */
  readonly message: string;
}

/**
 * Check if a streak will be reset on next puzzle completion.
 * This is a preview check - does not modify state.
 *
 * @param streakData - Current streak data
 * @param now - Current date/time (for testing)
 * @param config - Tolerance configuration
 * @returns Reset information
 */
export function checkStreakResetStatus(
  streakData: StreakData,
  now: Date = new Date(),
  config: ToleranceConfig = DEFAULT_TOLERANCE
): StreakResetInfo {
  const today = getCurrentLocalDate(now);
  const { lastPlayedDate, currentStreak } = streakData;

  // First time playing - not technically a "reset"
  if (!lastPlayedDate) {
    return {
      willReset: false,
      reason: 'first_time',
      daysMissed: 0,
      previousStreak: 0,
      message: 'Welcome! Complete a puzzle to start your streak.',
    };
  }

  // Already played today - streak continues
  if (isToday(lastPlayedDate, today)) {
    return {
      willReset: false,
      reason: 'none',
      daysMissed: 0,
      previousStreak: currentStreak,
      message: 'Streak continues! You already played today.',
    };
  }

  // Played yesterday - streak will continue
  if (isYesterday(lastPlayedDate, today)) {
    return {
      willReset: false,
      reason: 'none',
      daysMissed: 0,
      previousStreak: currentStreak,
      message: `Great! Continue your ${currentStreak}-day streak by playing today.`,
    };
  }

  // Check for clock jump
  if (shouldResetDueToClockJump(lastPlayedDate, now, config)) {
    return {
      willReset: true,
      reason: 'clock_jump',
      daysMissed: 0,
      previousStreak: currentStreak,
      message: 'Your device clock changed significantly. Streak will restart.',
    };
  }

  // Calculate days missed
  const lastPlayedDateObj = parseDateString(lastPlayedDate);
  const todayObj = parseDateString(today);

  if (!lastPlayedDateObj || !todayObj) {
    return {
      willReset: true,
      reason: 'corrupted_data',
      daysMissed: 0,
      previousStreak: currentStreak,
      message: 'Streak data was corrupted. Starting fresh.',
    };
  }

  const daysDiff = getDaysDifference(lastPlayedDateObj, todayObj);
  const daysMissed = daysDiff - 1;

  if (daysMissed === 1) {
    return {
      willReset: true,
      reason: 'missed_day',
      daysMissed: 1,
      previousStreak: currentStreak,
      message: currentStreak > 0
        ? `You missed a day. Your ${currentStreak}-day streak has ended.`
        : 'You missed a day. Starting a new streak!',
    };
  }

  return {
    willReset: true,
    reason: 'missed_multiple_days',
    daysMissed,
    previousStreak: currentStreak,
    message: currentStreak > 0
      ? `You missed ${daysMissed} days. Your ${currentStreak}-day streak has ended.`
      : `It's been ${daysMissed} days. Starting a new streak!`,
  };
}

/**
 * Get a notification-style message for streak reset.
 *
 * @param info - Reset info from checkStreakResetStatus
 * @returns Object with title and body for notification
 */
export function getStreakResetNotification(info: StreakResetInfo): {
  readonly title: string;
  readonly body: string;
  readonly type: 'info' | 'warning' | 'error';
} {
  if (!info.willReset) {
    if (info.reason === 'first_time') {
      return {
        title: 'Welcome!',
        body: 'Start your journey by solving your first puzzle.',
        type: 'info',
      };
    }
    return {
      title: 'Keep Going!',
      body: info.message,
      type: 'info',
    };
  }

  if (info.previousStreak === 0) {
    return {
      title: 'New Start',
      body: 'Begin your streak today!',
      type: 'info',
    };
  }

  if (info.reason === 'clock_jump') {
    return {
      title: 'Streak Reset',
      body: 'Device clock change detected. Your streak has been reset.',
      type: 'warning',
    };
  }

  if (info.previousStreak >= 7) {
    return {
      title: 'Streak Ended',
      body: `Your impressive ${info.previousStreak}-day streak has ended. Time to start a new one!`,
      type: 'warning',
    };
  }

  return {
    title: 'Streak Reset',
    body: info.message,
    type: 'info',
  };
}

/**
 * Check if the user is at risk of losing their streak today.
 * Useful for showing reminders.
 *
 * @param streakData - Current streak data
 * @param now - Current date/time (for testing)
 * @returns True if user hasn't played today and has an active streak
 */
export function isStreakAtRisk(
  streakData: StreakData,
  now: Date = new Date()
): boolean {
  const today = getCurrentLocalDate(now);
  const { lastPlayedDate, currentStreak } = streakData;

  // No active streak - nothing at risk
  if (currentStreak === 0) {
    return false;
  }

  // No play history - nothing at risk (new user)
  if (!lastPlayedDate) {
    return false;
  }

  // Played yesterday but not today - at risk
  if (isYesterday(lastPlayedDate, today)) {
    return true;
  }

  // Haven't played today and have a streak from before yesterday
  if (!isToday(lastPlayedDate, today) && currentStreak > 0) {
    return true;
  }

  return false;
}

/**
 * Get hours remaining until streak is at risk of ending.
 * Returns null if already played today or no active streak.
 *
 * @param streakData - Current streak data
 * @param now - Current date/time (for testing)
 * @returns Hours remaining, or null
 */
export function getHoursUntilStreakEnds(
  streakData: StreakData,
  now: Date = new Date()
): number | null {
  if (!isStreakAtRisk(streakData, now)) {
    return null;
  }

  // Calculate hours until midnight
  const midnight = new Date(now);
  midnight.setHours(24, 0, 0, 0);

  const msRemaining = midnight.getTime() - now.getTime();
  const hoursRemaining = Math.floor(msRemaining / (1000 * 60 * 60));

  return hoursRemaining;
}
