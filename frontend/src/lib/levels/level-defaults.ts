/**
 * Derived level constants from config data.
 * @module lib/levels/level-defaults
 *
 * Named constants for common level references, derived from LEVEL_SLUGS
 * (imported from config/puzzle-levels.json via Vite JSON import).
 *
 * Usage: Import these instead of accessing LEVEL_SLUGS by index.
 */

import { LEVEL_SLUGS, type LevelSlug } from './config';

/**
 * Default fallback level for new users or unparseable SGF data.
 * Elementary (index 2) — a safe default for the Go tsumego context.
 */
export const DEFAULT_LEVEL: LevelSlug = LEVEL_SLUGS[2]!;

/**
 * Default fallback level for generic contexts (SGF parsing, adapters).
 * Beginner (index 1) — used when level is completely unknown.
 */
export const FALLBACK_LEVEL: LevelSlug = LEVEL_SLUGS[1]!;

/**
 * First level in difficulty order (novice).
 */
export const FIRST_LEVEL: LevelSlug = LEVEL_SLUGS[0]!;

/**
 * Last level in difficulty order (expert).
 */
export const LAST_LEVEL: LevelSlug = LEVEL_SLUGS[LEVEL_SLUGS.length - 1]!;
