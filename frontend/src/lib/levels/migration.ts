/**
 * Level System Migration
 * @module lib/levels/migration
 *
 * Handles migration from old 5-level system to new 9-level system.
 * Preserves user progress data during transition.
 *
 * This module intentionally inlines its own constants because:
 * 1. LevelId (1-9) is the OLD numbering scheme, not the current sparse IDs.
 * 2. The migration defaults and rank table are frozen for this migration.
 * 3. No other code should use these values — they exist only here.
 */

import { normalizeRank } from './mapping';

/** Old 5/9 level numbering (NOT the current sparse IDs 110-230). */
type LevelId = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;

/** Schema version for level progress data in localStorage. */
const LEVEL_SCHEMA_VERSION = 2;

/** Old 5-level system → new 9-level system defaults. */
const MIGRATION_DEFAULTS: Record<number, LevelId> = {
  1: 2, 2: 4, 3: 5, 4: 7, 5: 9,
};

/** Rank → old level ID table (frozen for migration). */
const RANK_TO_LEVEL: Record<string, LevelId> = {
  '30k': 1, '29k': 1, '28k': 1, '27k': 1, '26k': 1,
  '25k': 2, '24k': 2, '23k': 2, '22k': 2, '21k': 2,
  '20k': 3, '19k': 3, '18k': 3, '17k': 3, '16k': 3,
  '15k': 4, '14k': 4, '13k': 4, '12k': 4, '11k': 4,
  '10k': 5, '9k': 5, '8k': 5, '7k': 5, '6k': 5,
  '5k': 6, '4k': 6, '3k': 6, '2k': 6, '1k': 6,
  '1d': 7, '2d': 7, '3d': 7,
  '4d': 8, '5d': 8, '6d': 8,
  '7d': 9, '8d': 9, '9d': 9,
};

function rankToLevel(normalizedRank: string): LevelId | null {
  if (!normalizedRank) return null;
  return RANK_TO_LEVEL[normalizedRank.toLowerCase()] ?? null;
}

/**
 * Progress data structure (pre-migration)
 */
interface LegacyProgressData {
  schemaVersion?: number;
  solvedPuzzles?: Record<string, boolean>;
  puzzleLevels?: Record<string, number>; // puzzleId -> old level (1-5)
  lastUpdated?: string;
}

/**
 * Progress data structure (post-migration)
 */
interface MigratedProgressData {
  schemaVersion: number;
  solvedPuzzles: Record<string, boolean>;
  puzzleLevels: Record<string, LevelId>; // puzzleId -> new level (1-9)
  lastUpdated: string;
  migrationLog?: MigrationLog;
}

/**
 * Migration statistics
 */
export interface MigrationStats {
  totalPuzzles: number;
  puzzlesMigrated: number;
  levelChanges: Record<string, number>; // "1->2": count
  errors: string[];
}

/**
 * Migration log for auditing
 */
interface MigrationLog {
  migratedAt: string;
  fromVersion: number;
  toVersion: number;
  stats: MigrationStats;
}

/**
 * Storage keys
 */
const PROGRESS_KEY = 'yengo_progress';
const BACKUP_KEY = 'yengo_progress_backup';

/**
 * Check if migration is needed
 */
export function needsMigration(): boolean {
  try {
    const data = localStorage.getItem(PROGRESS_KEY);
    if (!data) return false;

    const parsed = JSON.parse(data) as LegacyProgressData;
    const currentVersion = parsed.schemaVersion ?? 1;

    return currentVersion < LEVEL_SCHEMA_VERSION;
  } catch {
    return false;
  }
}

/**
 * Get current schema version from localStorage
 */
export function getCurrentSchemaVersion(): number {
  try {
    const data = localStorage.getItem(PROGRESS_KEY);
    if (!data) return 0;

    const parsed = JSON.parse(data) as LegacyProgressData;
    return parsed.schemaVersion ?? 1;
  } catch {
    return 0;
  }
}

/**
 * Map old level (1-5) to new level (1-9)
 *
 * @param oldLevel - Old level ID (1-5)
 * @param rank - Optional rank for more precise mapping
 * @returns New level ID (1-9)
 */
export function mapOldToNewLevel(oldLevel: number, rank?: string): LevelId {
  // If we have a rank, use it for precise mapping
  if (rank) {
    const normalized = normalizeRank(rank);
    const levelFromRank = rankToLevel(normalized);
    if (levelFromRank !== null) {
      return levelFromRank;
    }
  }

  // Use default mapping
  const defaultLevel = MIGRATION_DEFAULTS[oldLevel];
  if (defaultLevel) {
    return defaultLevel;
  }

  // Fallback: return middle level
  return 5;
}

/**
 * Backup current progress data
 */
export function backupProgressData(): boolean {
  try {
    const data = localStorage.getItem(PROGRESS_KEY);
    if (data) {
      localStorage.setItem(BACKUP_KEY, data);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Restore progress data from backup
 */
export function restoreFromBackup(): boolean {
  try {
    const backup = localStorage.getItem(BACKUP_KEY);
    if (backup) {
      localStorage.setItem(PROGRESS_KEY, backup);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Migrate progress data from old 5-level to new 9-level system
 *
 * @returns Migration statistics
 */
export function migrateProgressData(): MigrationStats {
  const stats: MigrationStats = {
    totalPuzzles: 0,
    puzzlesMigrated: 0,
    levelChanges: {},
    errors: [],
  };

  try {
    // Load current data
    const rawData = localStorage.getItem(PROGRESS_KEY);
    if (!rawData) {
      return stats;
    }

    const data = JSON.parse(rawData) as LegacyProgressData;
    const fromVersion = data.schemaVersion ?? 1;

    // Already migrated?
    if (fromVersion >= LEVEL_SCHEMA_VERSION) {
      return stats;
    }

    // Backup before migration
    backupProgressData();

    // Migrate puzzle levels
    const newPuzzleLevels: Record<string, LevelId> = {};
    const puzzleLevels = data.puzzleLevels ?? {};

    for (const [puzzleId, oldLevel] of Object.entries(puzzleLevels)) {
      stats.totalPuzzles++;

      try {
        const newLevel = mapOldToNewLevel(oldLevel);
        newPuzzleLevels[puzzleId] = newLevel;

        // Track level change
        const changeKey = `${oldLevel}->${newLevel}`;
        stats.levelChanges[changeKey] = (stats.levelChanges[changeKey] ?? 0) + 1;

        stats.puzzlesMigrated++;
      } catch (error) {
        stats.errors.push(`Failed to migrate puzzle ${puzzleId}: ${String(error)}`);
      }
    }

    // Create migrated data
    const migratedData: MigratedProgressData = {
      schemaVersion: LEVEL_SCHEMA_VERSION,
      solvedPuzzles: data.solvedPuzzles ?? {},
      puzzleLevels: newPuzzleLevels,
      lastUpdated: new Date().toISOString(),
      migrationLog: {
        migratedAt: new Date().toISOString(),
        fromVersion,
        toVersion: LEVEL_SCHEMA_VERSION,
        stats,
      },
    };

    // Save migrated data
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(migratedData));

    // Log migration stats
    console.info('[YenGo Migration] Completed:', stats);

    return stats;
  } catch (error) {
    stats.errors.push(`Migration failed: ${String(error)}`);
    console.error('[YenGo Migration] Failed:', error);
    return stats;
  }
}

/**
 * Run migration on app startup if needed
 */
export function runMigrationIfNeeded(): MigrationStats | null {
  if (!needsMigration()) {
    return null;
  }

  console.info('[YenGo Migration] Starting migration to schema version', LEVEL_SCHEMA_VERSION);
  return migrateProgressData();
}
