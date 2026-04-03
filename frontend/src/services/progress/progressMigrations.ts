/**
 * Progress Migrations
 * @module services/progress/progressMigrations
 *
 * Handles schema version migrations and data import/export.
 */

import type { UserProgress } from '../../models/progress';
import {
  DEFAULT_STATISTICS,
  DEFAULT_STREAK_DATA,
  DEFAULT_PREFERENCES,
  PROGRESS_SCHEMA_VERSION,
} from '../../models/progress';
import { runMigrationIfNeeded as runLevelMigration } from '../../lib/levels/migration';
import type { ProgressResult } from './storageOperations';
import { loadProgressRaw, saveProgress } from './storageOperations';

// ============================================================================
// Migration Logic
// ============================================================================

/**
 * Migrate progress from older schema versions
 */
export function migrateProgress(
  oldProgress: UserProgress
): ProgressResult<UserProgress> {
  try {
    let progress = { ...oldProgress } as Record<string, unknown>;

    // Migration from version 0 to 1 (example)
    if ((progress['version'] as number) < 1) {
      // Ensure all required fields exist with defaults
      progress = {
        ...progress,
        completedPuzzles: progress['completedPuzzles'] ?? {},
        unlockedLevels: progress['unlockedLevels'] ?? [],
        statistics: progress['statistics'] ?? { ...DEFAULT_STATISTICS },
        streakData: progress['streakData'] ?? { ...DEFAULT_STREAK_DATA },
        achievements: progress['achievements'] ?? [],
        preferences: progress['preferences'] ?? { ...DEFAULT_PREFERENCES },
        version: 1,
      };
    }

    // Migration to version 2: 9-level system
    // This is handled by the levels migration module separately
    // (runs on its own schema versioning for puzzleLevels data)

    return { success: true, data: progress as unknown as UserProgress };
  } catch {
    return {
      success: false,
      error: 'migration_failed',
      message: 'Failed to migrate progress data',
    };
  }
}

/**
 * Load progress with migration support
 */
export function loadProgress(): ProgressResult<UserProgress> {
  const result = loadProgressRaw();
  if (!result.success || !result.data) {
    return result;
  }

  const progress = result.data;

  // Run migrations if needed
  if (progress.version < PROGRESS_SCHEMA_VERSION) {
    const migrated = migrateProgress(progress);
    if (migrated.success && migrated.data) {
      // Save migrated data
      saveProgress(migrated.data);
      return migrated;
    }
    return migrated;
  }

  return { success: true, data: progress };
}

/**
 * Initialize progress system and run any pending migrations.
 * Call this once at app startup.
 */
export function initializeProgressSystem(): void {
  // Run level system migration (5-level to 9-level)
  const levelMigrationStats = runLevelMigration();
  if (levelMigrationStats) {
    console.info('[ProgressTracker] Level migration completed:', levelMigrationStats);
  }

  // Load and migrate main progress data
  const result = loadProgress();
  if (!result.success) {
    console.warn('[ProgressTracker] Failed to initialize:', result.message);
  }
}

// ============================================================================
// Import/Export
// ============================================================================

/**
 * Export progress data as JSON string (for backup)
 */
export function exportProgress(): string | null {
  const result = loadProgress();
  if (!result.success || !result.data) {
    return null;
  }
  return JSON.stringify(result.data, null, 2);
}

/**
 * Import progress data from JSON string (for restore)
 */
export function importProgress(jsonData: string): ProgressResult<UserProgress> {
  try {
    const data = JSON.parse(jsonData) as UserProgress;

    // Validate basic structure
    if (typeof data.version !== 'number') {
      return {
        success: false,
        error: 'parse_error',
        message: 'Invalid progress data format',
      };
    }

    // Migrate if needed
    const migrated = migrateProgress(data);
    if (!migrated.success || !migrated.data) {
      return migrated;
    }

    return saveProgress(migrated.data).success
      ? { success: true, data: migrated.data }
      : { success: false, error: 'save_failed' };
  } catch {
    return {
      success: false,
      error: 'parse_error',
      message: 'Failed to parse import data',
    };
  }
}
