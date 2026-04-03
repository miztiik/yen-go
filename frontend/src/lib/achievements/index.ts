/**
 * Achievements module exports.
 * @module lib/achievements
 */

export {
  ACHIEVEMENTS,
  ACHIEVEMENT_MAP,
  getAchievement,
  getAchievementsByCategory,
  getAchievementsByTier,
  getTierColor,
  getTierName,
  type AchievementCategory,
  type AchievementTier,
  type AchievementDefinition,
} from './definitions';

export {
  checkAchievement,
  checkAllAchievements,
  checkTriggeredAchievements,
  getRelevantAchievements,
  createDefaultStats,
  type AchievementCheckResult,
  type BatchCheckResult,
  type ProgressStats,
  type AchievementTrigger,
} from './checker';

export {
  loadAchievementProgress,
  saveAchievementProgress,
  createAchievementProgress,
  unlockAchievement,
  unlockMultipleAchievements,
  updateProgressValue,
  updateMultipleProgressValues,
  markNotified,
  markAllNotified,
  isUnlocked,
  getUnlockRecord,
  getProgressValue,
  getUnlockedCount,
  getRecentUnlocks,
  clearAchievementProgress,
  AchievementProgressManager,
  createAchievementProgressManager,
  type AchievementProgress,
  type AchievementUnlock,
} from './progress';
