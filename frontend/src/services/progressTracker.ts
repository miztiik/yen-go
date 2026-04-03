/**
 * Progress Tracker Service
 * @module services/progressTracker
 *
 * Re-exports from the modular progress system for backward compatibility.
 * The actual implementation has been split into:
 * - progress/storageOperations.ts (storage CRUD)
 * - progress/progressCalculations.ts (business logic)
 * - progress/progressMigrations.ts (migrations, import/export)
 *
 * Covers: FR-015 to FR-022, US3
 */

// Re-export everything from the progress module
export {
  // Storage keys
  PROGRESS_STORAGE_KEY,
  COLLECTION_PROGRESS_KEY,
  DAILY_PROGRESS_KEY,
  PROGRESS_SCHEMA_VERSION,
  // Types
  type ProgressError,
  type ProgressResult,
  type PuzzleCompletionInput,
  // Storage operations
  isStorageAvailable,
  saveProgress,
  resetProgress,
  loadCollectionProgress,
  saveCollectionProgress,
  loadDailyProgress,
  saveDailyProgress,
  // Migration operations
  migrateProgress,
  loadProgress,
  initializeProgressSystem,
  exportProgress,
  importProgress,
  // Calculation operations
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
} from './progress';
