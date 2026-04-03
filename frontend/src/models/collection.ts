/**
 * Collection types for puzzle collection browsing and progress tracking
 * @module models/collection
 *
 * Covers: FR-001 to FR-014 (Collection Browsing)
 */

import { LEVELS, type LevelSlug } from '@/lib/levels/config';

/** Skill levels for difficulty classification. Source of truth: config/puzzle-levels.json. */
export type SkillLevel = LevelSlug;

// ============================================================================
// Curated Collection Types (config/collections.json catalog)
// ============================================================================

/** Collection type from config/collections.json */
export type CollectionType = 'graded' | 'technique' | 'author' | 'reference' | 'system';

/** Collection tier from config/collections.json */
export type CollectionTier = 'editorial' | 'premier' | 'curated';

/**
 * A curated collection entry enriched with availability data.
 * Combines config/collections.json metadata with views/by-collection/index.json counts.
 */
export interface CuratedCollection {
  /** URL-safe unique ID (slug from config) */
  readonly slug: string;
  /** Human-readable name */
  readonly name: string;
  /** Multi-sentence description */
  readonly description: string;
  /** Author/curator name */
  readonly curator: string;
  /** Data source ("ogs", "kisvadim", "mixed", etc.) */
  readonly source: string;
  /** Collection type */
  readonly type: CollectionType;
  /** Quality tier */
  readonly tier: CollectionTier;
  /** Puzzle ordering strategy */
  readonly ordering: string;
  /** Alternate names for search matching */
  readonly aliases: readonly string[];
  /** Number of published puzzles (0 if unavailable) */
  readonly puzzleCount: number;
  /** Whether this collection has published puzzle data */
  readonly hasData: boolean;
  /** Optional level hint for graded collections (slug from config) */
  readonly levelHint?: string | undefined;
  /** Number of distinct chapters (0 = chapterless). */
  readonly chapterCount: number;
  /** Whether chapters are named strings (technique names) vs numeric. */
  readonly hasNamedChapters: boolean;
}

/**
 * Catalog of all curated collections, grouped by type.
 */
export interface CollectionCatalog {
  /** All collections */
  readonly collections: readonly CuratedCollection[];
  /** Collections grouped by type */
  readonly byType: Readonly<Record<CollectionType, readonly CuratedCollection[]>>;
}

/**
 * Summary of a collection for list/card display
 */
export interface CollectionSummary {
  /** Unique collection identifier (e.g., "beginner-life-death-set-1") */
  readonly id: string;
  /** Human-readable name */
  readonly name: string;
  /** Brief description */
  readonly description: string;
  /** Number of puzzles in collection */
  readonly puzzleCount: number;
  /** Estimated completion time in minutes */
  readonly estimatedMinutes: number;
  /** Difficulty range */
  readonly levelRange: {
    readonly min: SkillLevel;
    readonly max: SkillLevel;
  };
  /** Associated technique tags */
  readonly tags: readonly string[];
  /** Alternate names for search matching (Japanese terms, abbreviations) */
  readonly aliases?: readonly string[];
}

/**
 * Puzzle entry within a collection
 */
export interface CollectionPuzzleEntry {
  /** Unique puzzle ID */
  readonly id: string;
  /** Relative path to SGF file from CDN root */
  readonly path: string;
  /** Optional difficulty rank */
  readonly rank?: string;
  /** Optional technique tags */
  readonly tags?: readonly string[];
}

/**
 * Full collection with puzzle list
 */
export interface Collection {
  /** Unique collection identifier */
  readonly id: string;
  /** Human-readable name */
  readonly name: string;
  /** Brief description */
  readonly description: string;
  /** Schema version */
  readonly version: string;
  /** Generation timestamp (ISO) */
  readonly generatedAt: string;
  /** List of puzzles */
  readonly puzzles: readonly CollectionPuzzleEntry[];
}

/**
 * Index of all available collections
 */
export interface CollectionIndex {
  /** Schema version */
  readonly version: string;
  /** Generation timestamp (ISO) */
  readonly generatedAt: string;
  /** All available collections */
  readonly collections: readonly CollectionSummary[];
}

/**
 * Filter criteria for browsing collections
 */
export interface CollectionFilter {
  /** Filter by minimum level */
  minLevel?: SkillLevel | undefined;
  /** Filter by maximum level */
  maxLevel?: SkillLevel | undefined;
  /** Filter by tags (any match) */
  tags?: string[] | undefined;
  /** Search by name/description */
  searchTerm?: string | undefined;
}

/**
 * Collection status for UI display
 */
export type CollectionStatus = 'not-started' | 'in-progress' | 'completed';

/**
 * User's progress within a single collection
 */
export interface CollectionProgress {
  /** Collection identifier this progress belongs to */
  readonly collectionId: string;
  /** IDs of completed puzzles in this collection */
  readonly completed: readonly string[];
  /** Current puzzle index (0-based) */
  readonly currentIndex: number;
  /** When user started this collection (ISO date) */
  readonly startedAt: string;
  /** Last activity timestamp (ISO date) */
  readonly lastActivity: string;
  /** Total puzzles in collection */
  readonly totalPuzzles: number;
  /** Aggregated stats for this collection */
  readonly stats?: CollectionStats;
}

/**
 * Stats for a collection attempt
 */
export interface CollectionStats {
  /** Puzzles solved correctly on first try */
  readonly correctFirstTry: number;
  /** Total hints used */
  readonly hintsUsed: number;
  /** Total time spent (milliseconds) */
  readonly totalTimeMs: number;
  /** Average time per puzzle (milliseconds) */
  readonly avgTimeMs: number;
}

/**
 * Summary view of collection progress for list display
 */
export interface CollectionProgressSummary {
  readonly collectionId: string;
  readonly status: CollectionStatus;
  readonly completedCount: number;
  readonly totalPuzzles: number;
  readonly percentComplete: number;
  readonly lastActivity?: string;
}

/**
 * Skill level display metadata from config/puzzle-levels.json
 */
export interface SkillLevelInfo {
  readonly id: number;
  readonly slug: SkillLevel;
  readonly name: string;
  readonly shortName: string;
  readonly rankRange: {
    readonly min: string;
    readonly max: string;
  };
  readonly description: string;
}

/**
 * All skill levels with display metadata.
 * Derived from LEVELS (auto-generated from config/puzzle-levels.json).
 * Single source of truth - no hardcoded level data.
 */
export const SKILL_LEVELS: readonly SkillLevelInfo[] = LEVELS.map((level) => ({
  id: level.id,
  slug: level.slug,
  name: level.name,
  shortName: level.shortName,
  rankRange: level.rankRange,
  description: level.description,
}));

/**
 * Get skill level info by slug
 */
export function getSkillLevelInfo(slug: SkillLevel): SkillLevelInfo | undefined {
  return SKILL_LEVELS.find((level) => level.slug === slug);
}

/**
 * Get skill level display name
 */
export function getSkillLevelName(slug: SkillLevel): string {
  return getSkillLevelInfo(slug)?.name ?? slug;
}

/**
 * Compare skill levels (returns negative if a < b)
 */
export function compareSkillLevels(a: SkillLevel, b: SkillLevel): number {
  const aInfo = getSkillLevelInfo(a);
  const bInfo = getSkillLevelInfo(b);
  return (aInfo?.id ?? 0) - (bInfo?.id ?? 0);
}

/**
 * Stats for a single technique/tag
 */
export interface TechniqueStats {
  /** Tag/technique identifier */
  readonly techniqueId: string;
  /** Total puzzles attempted with this technique */
  readonly attempted: number;
  /** Puzzles solved correctly */
  readonly correct: number;
  /** Last practice timestamp (ISO) */
  readonly lastPracticed?: string;
}

/**
 * User's technique-specific progress across all collections
 */
export interface TechniqueProgress {
  /** Map of techniqueId to stats */
  readonly byTechnique: Readonly<Record<string, TechniqueStats>>;
  /** Last updated timestamp (ISO) */
  readonly updatedAt: string;
}
