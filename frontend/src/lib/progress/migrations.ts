/**
 * Schema versioning and migrations for user progress.
 * @module lib/progress/migrations
 */

import type { UserProgress } from '../../types/progress';
import {
  createDefaultProgress,
  PROGRESS_SCHEMA_VERSION,
  DEFAULT_PREFERENCES,
  DEFAULT_STATISTICS,
  DEFAULT_STREAK_DATA,
} from '../../types/progress';

/**
 * Migration function type.
 */
export type MigrationFn = (data: Record<string, unknown>) => Record<string, unknown>;

/**
 * Migration definition.
 */
export interface Migration {
  /** Target version after migration */
  readonly toVersion: number;
  /** Description of the migration */
  readonly description: string;
  /** Migration function */
  readonly migrate: MigrationFn;
}

/**
 * Helper to safely extract an object field or use default.
 */
function safeObject<T extends Record<string, unknown>>(value: unknown, defaultValue: T): T {
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
    return value as T;
  }
  return defaultValue;
}

/**
 * Helper to safely extract an array field or use default.
 */
function safeArray<T>(value: unknown, defaultValue: T[]): T[] {
  if (Array.isArray(value)) {
    return value as T[];
  }
  return defaultValue;
}

/**
 * Registry of all migrations.
 * Key is the source version, value is the migration to apply.
 */
export const MIGRATIONS: ReadonlyMap<number, Migration> = new Map([
  // Migration from v0 (legacy/unknown) to v1
  [
    0,
    {
      toVersion: 1,
      description: 'Initialize v1 schema with all required fields',
      migrate: (data) => ({
        version: 1,
        completedPuzzles: safeObject(data.completedPuzzles, {}),
        unlockedLevels: safeArray(data.unlockedLevels, []),
        statistics: safeObject(
          data.statistics,
          DEFAULT_STATISTICS as unknown as Record<string, unknown>
        ),
        streakData: safeObject(
          data.streakData,
          DEFAULT_STREAK_DATA as unknown as Record<string, unknown>
        ),
        achievements: safeArray(data.achievements, []),
        preferences: safeObject(
          data.preferences,
          DEFAULT_PREFERENCES as unknown as Record<string, unknown>
        ),
      }),
    },
  ],
  // Future migrations would be added here:
  // [1, { toVersion: 2, description: '...', migrate: (data) => {...} }],
]);

/**
 * Result of a migration attempt.
 */
export interface MigrationResult {
  readonly success: boolean;
  readonly progress?: UserProgress | undefined;
  readonly error?: string | undefined;
  readonly migrationsApplied: readonly number[];
}

/**
 * Check if data needs migration.
 */
export function needsMigration(data: Record<string, unknown>): boolean {
  const version = typeof data.version === 'number' ? data.version : 0;
  return version < PROGRESS_SCHEMA_VERSION;
}

/**
 * Get the current version from data (0 if missing/invalid).
 */
export function getDataVersion(data: Record<string, unknown>): number {
  if (typeof data.version === 'number' && data.version > 0) {
    return data.version;
  }
  return 0;
}

/**
 * Apply all necessary migrations to bring data to current version.
 */
export function migrateProgress(data: Record<string, unknown>): MigrationResult {
  const migrationsApplied: number[] = [];
  let currentData = { ...data };
  let currentVersion = getDataVersion(currentData);

  try {
    // Handle future versions (higher than current schema)
    if (currentVersion > PROGRESS_SCHEMA_VERSION) {
      console.warn(
        `Data version ${currentVersion} is newer than current schema version ${PROGRESS_SCHEMA_VERSION}. Resetting to defaults.`
      );
      return {
        success: true,
        progress: createDefaultProgress(),
        migrationsApplied,
      };
    }

    // Apply migrations sequentially
    while (currentVersion < PROGRESS_SCHEMA_VERSION) {
      const migration = MIGRATIONS.get(currentVersion);

      if (!migration) {
        // No migration path available - reset to defaults
        console.warn(`No migration path from version ${currentVersion}. Resetting to defaults.`);
        return {
          success: true,
          progress: createDefaultProgress(),
          migrationsApplied,
        };
      }

      // Apply the migration
      currentData = migration.migrate(currentData);
      currentVersion = migration.toVersion;
      migrationsApplied.push(currentVersion);
    }

    // Validate final structure
    const validated = validateProgress(currentData);
    if (!validated.success) {
      return {
        success: false,
        error: validated.error,
        migrationsApplied,
      };
    }

    return {
      success: true,
      progress: currentData as unknown as UserProgress,
      migrationsApplied,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return {
      success: false,
      error: `Migration failed: ${message}`,
      migrationsApplied,
    };
  }
}

/**
 * Validation result.
 */
export interface ValidationResult {
  readonly success: boolean;
  readonly error?: string;
}

/**
 * Validate that data has all required UserProgress fields.
 */
export function validateProgress(data: Record<string, unknown>): ValidationResult {
  // Check version
  if (typeof data.version !== 'number') {
    return { success: false, error: 'Missing or invalid version' };
  }

  // Check completedPuzzles
  if (
    typeof data.completedPuzzles !== 'object' ||
    data.completedPuzzles === null ||
    Array.isArray(data.completedPuzzles)
  ) {
    return { success: false, error: 'Missing or invalid completedPuzzles' };
  }

  // Check unlockedLevels
  if (!Array.isArray(data.unlockedLevels)) {
    return { success: false, error: 'Missing or invalid unlockedLevels' };
  }

  // Check statistics
  if (typeof data.statistics !== 'object' || data.statistics === null) {
    return { success: false, error: 'Missing or invalid statistics' };
  }

  // Check streakData
  if (typeof data.streakData !== 'object' || data.streakData === null) {
    return { success: false, error: 'Missing or invalid streakData' };
  }

  // Check achievements
  if (!Array.isArray(data.achievements)) {
    return { success: false, error: 'Missing or invalid achievements' };
  }

  // Check preferences
  if (typeof data.preferences !== 'object' || data.preferences === null) {
    return { success: false, error: 'Missing or invalid preferences' };
  }

  return { success: true };
}

/**
 * Create a safe copy of progress with all required fields.
 * Used when loading potentially incomplete data.
 */
export function ensureComplete(partial: Partial<UserProgress>): UserProgress {
  const defaults = createDefaultProgress();

  return {
    version: partial.version ?? defaults.version,
    completedPuzzles: partial.completedPuzzles ?? defaults.completedPuzzles,
    unlockedLevels: partial.unlockedLevels ?? defaults.unlockedLevels,
    statistics: partial.statistics
      ? { ...defaults.statistics, ...partial.statistics }
      : defaults.statistics,
    streakData: partial.streakData
      ? { ...defaults.streakData, ...partial.streakData }
      : defaults.streakData,
    achievements: partial.achievements ?? defaults.achievements,
    preferences: partial.preferences
      ? { ...defaults.preferences, ...partial.preferences }
      : defaults.preferences,
  };
}
