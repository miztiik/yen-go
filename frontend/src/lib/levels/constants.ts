/**
 * Level System Constants
 * @module lib/levels/constants
 *
 * Utility functions for the 9-level system.
 * Level data imported from config.ts (loaded from config/puzzle-levels.json via Vite JSON import).
 *
 * Constitution Compliance:
 * - VI. Type Safety: Strict TypeScript types
 * - VII. Format Pragmatism: Single source of truth from config
 */

import type { LevelId } from './types';
import { LEVELS, type LevelMeta } from './config';

/**
 * Get level definition by ID
 */
export function getLevelById(id: LevelId): LevelMeta | undefined {
  return LEVELS.find((l) => l.id === id);
}

/**
 * Get level display name with rank range
 * @example "Intermediate (15k-11k)"
 */
export function getLevelDisplayName(id: LevelId): string {
  const level = getLevelById(id);
  if (!level) return `Level ${id}`;
  return `${level.name} (${level.rankRange.min}-${level.rankRange.max})`;
}

/**
 * Get level short display name
 * @example "Int (15k-11k)"
 */
export function getLevelShortDisplayName(id: LevelId): string {
  const level = getLevelById(id);
  if (!level) return `L${id}`;
  return `${level.shortName} (${level.rankRange.min}-${level.rankRange.max})`;
}

/**
 * Get just the level name without rank range
 */
export function getLevelName(id: LevelId): string {
  const level = getLevelById(id);
  return level?.name ?? `Level ${id}`;
}

/**
 * Get all level IDs
 */
export function getAllLevelIds(): LevelId[] {
  return LEVELS.map((l) => l.id as LevelId);
}

/**
 * Check if a number is a valid level ID
 */
export function isValidLevelId(id: number): id is LevelId {
  return id >= 1 && id <= 9 && Number.isInteger(id);
}


