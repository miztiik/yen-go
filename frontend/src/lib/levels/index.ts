/**
 * Level System Module
 * @module lib/levels
 *
 * Unified exports for the 9-level difficulty system.
 * Level data is loaded from config/puzzle-levels.json via Vite JSON import (no codegen step).
 */

// Types
export type {
  LevelId,
  LevelName,
  LevelShortName,
  RankRange,
  LevelDefinition,
  LevelConfig,
  LevelProgress,
} from './types';

export { LEVEL_SCHEMA_VERSION } from './types';

// Config types (source of truth from config/puzzle-levels.json via Vite JSON import)
export type { LevelSlug, LevelMeta } from './config';
export { LEVELS, LEVEL_SLUGS, LEVEL_COUNT, isValidLevel, getLevelId } from './config';

// Constants and utilities
export {
  getLevelById,
  getLevelDisplayName,
  getLevelShortDisplayName,
  getLevelName,
  getAllLevelIds,
  isValidLevelId,
} from './constants';

// Rank mapping (config-derived, no hardcoded values)
export {
  normalizeRank,
  rankToLevel,
  resolveRankRange,
  rankStringToLevel,
  getRanksForLevel,
} from './mapping';

// Migration
export {
  needsMigration,
  getCurrentSchemaVersion,
  mapOldToNewLevel,
  backupProgressData,
  restoreFromBackup,
  migrateProgressData,
  runMigrationIfNeeded,
} from './migration';

export type { MigrationStats } from './migration';
