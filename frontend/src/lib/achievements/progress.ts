/**
 * Achievement progress tracking.
 * Persists achievement state to localStorage.
 * @module lib/achievements/progress
 */

/**
 * Storage key for achievements.
 */
const STORAGE_KEY = 'yen-go-achievements';

/**
 * Achievement unlock record.
 */
export interface AchievementUnlock {
  /** Achievement ID */
  readonly achievementId: string;
  /** ISO timestamp when unlocked */
  readonly unlockedAt: string;
  /** Whether user has seen the notification */
  readonly notified: boolean;
}

/**
 * Achievement progress data structure.
 */
export interface AchievementProgress {
  /** Version for migrations */
  readonly version: number;
  /** List of unlocked achievement IDs */
  readonly unlockedIds: readonly string[];
  /** Unlock records with timestamps */
  readonly unlocks: readonly AchievementUnlock[];
  /** Current progress values by achievement ID */
  readonly progressValues: { readonly [key: string]: number };
  /** Achievements pending notification */
  readonly pendingNotifications: readonly string[];
}

/**
 * Current progress version.
 */
const CURRENT_VERSION = 1;

/**
 * Create initial achievement progress.
 */
export function createAchievementProgress(): AchievementProgress {
  return {
    version: CURRENT_VERSION,
    unlockedIds: [],
    unlocks: [],
    progressValues: {},
    pendingNotifications: [],
  };
}

/**
 * Load achievement progress from storage.
 */
export function loadAchievementProgress(): AchievementProgress {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return createAchievementProgress();
    }

    const parsed = JSON.parse(stored) as AchievementProgress;

    // Handle version migrations
    if (parsed.version !== CURRENT_VERSION) {
      return migrateProgress(parsed);
    }

    return parsed;
  } catch (error) {
    console.warn('Failed to load achievement progress:', error);
    return createAchievementProgress();
  }
}

/**
 * Save achievement progress to storage.
 */
export function saveAchievementProgress(progress: AchievementProgress): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch (error) {
    console.error('Failed to save achievement progress:', error);
  }
}

/**
 * Migrate progress from older version.
 */
function migrateProgress(progress: AchievementProgress): AchievementProgress {
  // Currently only version 1 exists
  return {
    ...progress,
    version: CURRENT_VERSION,
    pendingNotifications: progress.pendingNotifications ?? [],
  };
}

/**
 * Unlock an achievement.
 */
export function unlockAchievement(
  progress: AchievementProgress,
  achievementId: string
): AchievementProgress {
  // Already unlocked
  if (progress.unlockedIds.includes(achievementId)) {
    return progress;
  }

  const unlock: AchievementUnlock = {
    achievementId,
    unlockedAt: new Date().toISOString(),
    notified: false,
  };

  return {
    ...progress,
    unlockedIds: [...progress.unlockedIds, achievementId],
    unlocks: [...progress.unlocks, unlock],
    pendingNotifications: [...progress.pendingNotifications, achievementId],
  };
}

/**
 * Unlock multiple achievements.
 */
export function unlockMultipleAchievements(
  progress: AchievementProgress,
  achievementIds: readonly string[]
): AchievementProgress {
  let updated = progress;
  for (const id of achievementIds) {
    updated = unlockAchievement(updated, id);
  }
  return updated;
}

/**
 * Update progress value for an achievement.
 */
export function updateProgressValue(
  progress: AchievementProgress,
  achievementId: string,
  value: number
): AchievementProgress {
  return {
    ...progress,
    progressValues: {
      ...progress.progressValues,
      [achievementId]: value,
    },
  };
}

/**
 * Update multiple progress values.
 */
export function updateMultipleProgressValues(
  progress: AchievementProgress,
  updates: { readonly [key: string]: number }
): AchievementProgress {
  return {
    ...progress,
    progressValues: {
      ...progress.progressValues,
      ...updates,
    },
  };
}

/**
 * Mark achievement as notified.
 */
export function markNotified(
  progress: AchievementProgress,
  achievementId: string
): AchievementProgress {
  return {
    ...progress,
    unlocks: progress.unlocks.map(u =>
      u.achievementId === achievementId ? { ...u, notified: true } : u
    ),
    pendingNotifications: progress.pendingNotifications.filter(id => id !== achievementId),
  };
}

/**
 * Mark all achievements as notified.
 */
export function markAllNotified(progress: AchievementProgress): AchievementProgress {
  return {
    ...progress,
    unlocks: progress.unlocks.map(u => ({ ...u, notified: true })),
    pendingNotifications: [],
  };
}

/**
 * Check if achievement is unlocked.
 */
export function isUnlocked(
  progress: AchievementProgress,
  achievementId: string
): boolean {
  return progress.unlockedIds.includes(achievementId);
}

/**
 * Get unlock record for achievement.
 */
export function getUnlockRecord(
  progress: AchievementProgress,
  achievementId: string
): AchievementUnlock | undefined {
  return progress.unlocks.find(u => u.achievementId === achievementId);
}

/**
 * Get progress value for achievement.
 */
export function getProgressValue(
  progress: AchievementProgress,
  achievementId: string
): number {
  return progress.progressValues[achievementId] ?? 0;
}

/**
 * Get count of unlocked achievements.
 */
export function getUnlockedCount(progress: AchievementProgress): number {
  return progress.unlockedIds.length;
}

/**
 * Get recent unlocks (most recent first).
 */
export function getRecentUnlocks(
  progress: AchievementProgress,
  limit: number = 5
): readonly AchievementUnlock[] {
  return [...progress.unlocks]
    .sort((a, b) => new Date(b.unlockedAt).getTime() - new Date(a.unlockedAt).getTime())
    .slice(0, limit);
}

/**
 * Clear all achievement progress (for testing/reset).
 */
export function clearAchievementProgress(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Achievement progress manager for convenient usage.
 */
export class AchievementProgressManager {
  private progress: AchievementProgress;

  constructor() {
    this.progress = loadAchievementProgress();
  }

  /**
   * Get current progress.
   */
  getProgress(): AchievementProgress {
    return this.progress;
  }

  /**
   * Unlock achievements and save.
   */
  unlock(achievementIds: readonly string[]): void {
    this.progress = unlockMultipleAchievements(this.progress, achievementIds);
    saveAchievementProgress(this.progress);
  }

  /**
   * Update progress values and save.
   */
  updateProgress(updates: { readonly [key: string]: number }): void {
    this.progress = updateMultipleProgressValues(this.progress, updates);
    saveAchievementProgress(this.progress);
  }

  /**
   * Mark achievement as notified and save.
   */
  markNotified(achievementId: string): void {
    this.progress = markNotified(this.progress, achievementId);
    saveAchievementProgress(this.progress);
  }

  /**
   * Get pending notifications.
   */
  getPendingNotifications(): readonly string[] {
    return this.progress.pendingNotifications;
  }

  /**
   * Check if achievement is unlocked.
   */
  isUnlocked(achievementId: string): boolean {
    return isUnlocked(this.progress, achievementId);
  }

  /**
   * Reload from storage.
   */
  reload(): void {
    this.progress = loadAchievementProgress();
  }
}

/**
 * Create achievement progress manager.
 */
export function createAchievementProgressManager(): AchievementProgressManager {
  return new AchievementProgressManager();
}
