/**
 * Progress Module
 * @module services/progress
 *
 * Re-exports all progress-related functionality for backward compatibility.
 * This is the public API for the progress system.
 */

// Storage operations
export {
  PROGRESS_STORAGE_KEY,
  COLLECTION_PROGRESS_KEY,
  DAILY_PROGRESS_KEY,
  type ProgressError,
  type ProgressResult,
  isStorageAvailable,
  saveProgress,
  resetProgress,
  loadCollectionProgress,
  saveCollectionProgress,
  loadDailyProgress,
  saveDailyProgress,
  PROGRESS_SCHEMA_VERSION,
} from './storageOperations';

// Migration operations
export {
  migrateProgress,
  loadProgress,
  initializeProgressSystem,
  exportProgress,
  importProgress,
} from './progressMigrations';

// Calculation operations
export {
  type PuzzleCompletionInput,
  recordPuzzleCompletion,
  isPuzzleCompleted,
  getPuzzleCompletion,
  unlockLevel,
  isLevelUnlocked,
  getStatistics,
  getStreakData,
  updateStreakData,
  getAchievements,
  addAchievement,
  updateRushHighScore,
  getRushHighScore,
  getRushHighScoreByDuration,
  getRushHighScores,
  recordRushScore,
  getPreferences,
  updatePreferences,
  getLevelCompletionCount,
  getCollectionProgress,
  updateCollectionProgress,
  recordCollectionPuzzleCompletion,
  getCollectionStatus,
  getAllCollectionProgress,
  getDailyProgress,
  updateDailyProgress,
  recordDailyPuzzleCompletion,
} from './progressCalculations';
