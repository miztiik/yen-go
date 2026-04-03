/**
 * Level System Types
 * @module lib/levels/types
 *
 * TypeScript type definitions for the 9-level difficulty system.
 * Constitution Compliance:
 * - VI. Type Safety: Strict TypeScript types for levels
 */

/**
 * Valid level IDs (1-9)
 */
export type LevelId = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;

/**
 * Level names corresponding to each ID
 */
export type LevelName =
  | 'Novice'
  | 'Beginner'
  | 'Elementary'
  | 'Intermediate'
  | 'Upper Intermediate'
  | 'Advanced'
  | 'Low Dan'
  | 'High Dan'
  | 'Expert';

/**
 * Short names for compact display
 */
export type LevelShortName =
  | 'Nov'
  | 'Beg'
  | 'Elem'
  | 'Int'
  | 'U.Int'
  | 'Adv'
  | 'L.Dan'
  | 'H.Dan'
  | 'Exp';

/**
 * Rank range definition for a level
 */
export interface RankRange {
  /** Weakest rank in range (e.g., "30k") */
  min: string;
  /** Strongest rank in range (e.g., "26k") */
  max: string;
}

/**
 * Complete level definition
 */
export interface LevelDefinition {
  /** Unique identifier (1-9) */
  id: LevelId;

  /** Full level name */
  name: LevelName;

  /** Short name for compact UI */
  shortName: LevelShortName;

  /** Rank range covered */
  rankRange: RankRange;

  /** Brief skill description */
  description: string;
}

/**
 * Level configuration loaded from config/puzzle-levels.json
 */
export interface LevelConfig {
  /** Config version */
  version: string;

  /** All level definitions */
  levels: LevelDefinition[];

  /** Rank to level ID mapping */
  rankMapping: Record<string, LevelId>;

  /** Migration defaults (old level -> new level) */
  migrationDefaults: Record<number, LevelId>;
}

/**
 * User progress by level
 */
export interface LevelProgress {
  /** Level ID */
  levelId: LevelId;

  /** Puzzles solved */
  solved: number;

  /** Total puzzles at this level */
  total: number;

  /** Completion percentage (0-100) */
  percentage: number;

  /** Is level mastered (100% complete) */
  isMastered: boolean;
}

/**
 * Schema version for localStorage
 */
export const LEVEL_SCHEMA_VERSION = 2;
