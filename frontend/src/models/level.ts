/**
 * Level types for puzzle difficulty classification
 * @module models/level
 */

import { LEVELS, type LevelSlug } from '@/lib/levels/config';
import { getLevelCategory, type CategoryFilter } from '@/lib/levels/categories';

/** Puzzles grouped by daily challenge difficulty group */
export interface LevelPuzzles {
  readonly beginner: readonly string[];
  readonly intermediate: readonly string[];
  readonly advanced: readonly string[];
}

/** A daily puzzle level */
export interface Level {
  readonly version: '1.0';
  readonly id: string; // Usually same as date
  readonly date: string; // YYYY-MM-DD
  readonly name: string;
  readonly description?: string;
  readonly puzzles: LevelPuzzles;
  readonly unlockRequirement: string | null;
}

import type { Puzzle } from './puzzle';

/** Level data loaded from JSON (includes puzzles array) */
export interface LevelData {
  readonly levelId: string;
  readonly puzzles: readonly Puzzle[];
}

/**
 * Daily challenge difficulty group identifiers.
 * Maps the 9 puzzle difficulty levels from config/puzzle-levels.json into 3 presentation groups.
 * Uses sparse level IDs (110-230) via shared getLevelCategory() from categories.ts.
 * - 'beginner': novice, beginner, elementary (IDs < 140)
 * - 'intermediate': intermediate, upper-intermediate, advanced (IDs 140-199)
 * - 'advanced': low-dan, high-dan, expert (IDs >= 200)
 *
 * Note: This excludes 'all' — it's only the 3 concrete groups.
 * @see config/puzzle-levels.json for the 9-level system definitions
 */
export type DailyChallengeGroup = Exclude<CategoryFilter, 'all'>;

/**
 * Mapping from 9 puzzle difficulty levels (config/puzzle-levels.json slugs)
 * to 3 daily challenge presentation groups.
 * Dynamically derived from LEVELS via shared getLevelCategory().
 * Single source of truth - no hardcoded level slugs or ordinal thresholds.
 */
export const PUZZLE_LEVEL_TO_DAILY_GROUP: Record<LevelSlug, DailyChallengeGroup> = 
  Object.fromEntries(
    LEVELS.map((level) => [level.slug, getLevelCategory(level.slug)])
  ) as Record<LevelSlug, DailyChallengeGroup>;

/**
 * All daily challenge groups in order from easiest to hardest.
 */
export const DAILY_CHALLENGE_GROUPS: readonly DailyChallengeGroup[] = [
  'beginner',
  'intermediate', 
  'advanced',
] as const;

/** Helper to get total puzzle count in a level */
export function getLevelPuzzleCount(puzzles: LevelPuzzles): number {
  return puzzles.beginner.length + puzzles.intermediate.length + puzzles.advanced.length;
}

/** Helper to get puzzles by daily challenge group */
export function getPuzzlesByGroup(puzzles: LevelPuzzles, group: DailyChallengeGroup): readonly string[] {
  return puzzles[group];
}

/** Helper to check if a level is unlocked */
export function isLevelUnlocked(
  level: Level,
  completedLevels: readonly string[]
): boolean {
  if (level.unlockRequirement === null) {
    return true; // First level is always unlocked
  }
  return completedLevels.includes(level.unlockRequirement);
}
