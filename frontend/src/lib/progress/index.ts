/**
 * Progress tracking module - complete user progress management.
 * @module lib/progress
 */

// Storage
export {
  ProgressStorageService,
  getProgressStorage,
  resetProgressStorage,
  isLocalStorageAvailable,
  isSessionStorageAvailable,
  STORAGE_KEY,
  type StorageMode,
  type StorageResult,
  type ProgressStorage,
} from './storage';

// Migrations
export {
  migrateProgress,
  validateProgress,
  needsMigration,
  getDataVersion,
  ensureComplete,
  MIGRATIONS,
  type MigrationFn,
  type Migration,
  type MigrationResult,
  type ValidationResult,
} from './migrations';

// Puzzle completion
export {
  isPuzzleCompleted,
  getPuzzleCompletion,
  getCompletedPuzzleIds,
  getCompletedCount,
  getCompletionsForDate,
  getCompletionsBySkillLevel,
  recordCompletion,
  recordCompletionWithStreak,
  clearCompletion,
  getDateCompletionStats,
  getRecentCompletions,
  getAverageSolveTime,
  getTodayCompletions,
  type CompletionData,
  type CompletionResult,
} from './puzzles';

// Challenge unlock
export {
  isChallengeUnlocked,
  getChallengeUnlockStatus,
  unlockChallenge,
  getUnlockedChallenges,
  calculateChallengeProgress,
  isChallengeComplete,
  getStartedChallengeDates,
  getMostRecentChallengeDate,
  getTodayDate,
  getYesterdayDate,
  compareDates,
  isFutureDate,
  isToday,
  PUZZLES_TO_UNLOCK,
  MAX_FUTURE_DAYS,
  type ChallengeUnlockStatus,
} from './challenges';

// Statistics
export {
  calculateStatsBySkillLevel,
  recalculateStatistics,
  updateStatisticsAfterCompletion,
  addRushHighScore,
  getBestRushScore,
  getAverageTimePerPuzzle,
  getHintUsageRate,
  formatDuration,
  formatAverageTime,
  getStatisticsSummary,
  SKILL_LEVEL_NAMES,
  SKILL_LEVEL_RANKS,
  MAX_RUSH_HIGH_SCORES,
} from './statistics';

// Timing
export {
  PuzzleTimer,
  createTimer,
  pauseTimer,
  resumeTimer,
  stopTimer,
  getElapsedTime,
  resetTimer,
  formatElapsedTime,
  formatElapsedTimePrecise,
  parseTimeString,
  type TimerState,
} from './timing';

// Attempts
export {
  AttemptTracker,
  createAttemptTracker,
  recordIncorrectAttempt,
  getAttemptCount,
  resetAttempts,
  hasIncorrectAttempts,
  getTimeSinceLastAttempt,
  calculateStarRating,
  getStarRatingDescription,
  formatAttemptCount,
  type AttemptState,
} from './attempts';

// Fallback
export {
  SessionOnlyStorage,
  MemoryOnlyStorage,
  getStorageWarning,
  isPersistentStorage,
  survivesTabClose,
  getStorageStatus,
  createBestAvailableStorage,
  exportProgress,
  importProgress,
  SESSION_ONLY_WARNING,
  MEMORY_ONLY_WARNING,
  type StorageStatus,
} from './fallback';

// Recovery
export {
  recoverProgress,
  loadAndRecoverProgress,
  safeJsonParse,
  createBackup,
  restoreFromBackup,
  checkDataIntegrity,
  repairDataIntegrity,
  type RecoveryAction,
  type RecoveryResult,
  type StorageRecoveryResult,
} from './recovery';
