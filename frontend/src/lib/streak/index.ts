/**
 * Streak module - daily streak tracking functionality.
 * @module lib/streak
 *
 * Covers: US4 (Daily Streaks)
 */

export {
  // Calculator
  calculateStreakOnCompletion,
  getCurrentLocalDate,
  parseDateString,
  getDaysDifference,
  isYesterday,
  isToday,
  getStreakStatusMessage,
  getReachedMilestone,
  getMilestoneName,
  createDefaultStreakData,
  type StreakCalculationResult,
} from './calculator';

export {
  // Tolerance
  applyMidnightTolerance,
  shouldResetDueToClockJump,
  isInLateNightWindow,
  isInEarlyMorningWindow,
  getToleranceExplanation,
  DEFAULT_TOLERANCE,
  type ToleranceConfig,
  type ToleranceCheckResult,
} from './tolerance';

export {
  // Reset detection
  checkStreakResetStatus,
  getStreakResetNotification,
  isStreakAtRisk,
  getHoursUntilStreakEnds,
  type StreakResetReason,
  type StreakResetInfo,
} from './reset';
