/**
 * Index Type Definitions
 * @module types/indexes
 *
 * Types for JSON index files served from the static puzzle CDN.
 * Entry types for decoded view data and daily challenge structures.
 */

// ─── Entry Types ───────────────────────────────────────────────────

/** Entry in a by-level view. Cross-references puzzle tags. */
export interface LevelEntry {
  /** Relative path to SGF file. Pattern: ^sgf/.+\.sgf$ */
  readonly path: string;
  /** Technique tags for this puzzle. */
  readonly tags: readonly string[];
}

/** Entry in a by-tag view. Cross-references puzzle difficulty level. */
export interface TagEntry {
  /** Relative path to SGF file. Pattern: ^sgf/.+\.sgf$ */
  readonly path: string;
  /** Difficulty level slug. */
  readonly level: string;
}

/** Entry in a by-collection view. Preserves author-curated ordering. */
export interface CollectionEntry {
  /** Relative path to SGF file. Pattern: ^sgf/.+\.sgf$ */
  readonly path: string;
  /** Difficulty level slug. */
  readonly level: string;
  /** Author-curated ordering within collection (1-indexed). */
  readonly sequence_number: number;
}

/** Union of all entry types for generic usage. */
export type ViewEntry = LevelEntry | TagEntry | CollectionEntry;

// ─── Master Index Entry Types (v2.0) ──────────────────────────────

/** Level master index entry (v2.0 — includes tag distribution). */
export interface LevelMasterEntry {
  /** Numeric ID for this entity. */
  readonly id: number;
  /** Display name. */
  readonly name: string;
  /** URL-safe slug. */
  readonly slug: string;
  /** Whether this entity uses paginated format. */
  readonly paginated: boolean;
  /** Total puzzle count. */
  readonly count: number;
  /** Number of pages (v2.0+, always-paginated). */
  readonly pages?: number;
  /** Tag distribution: numeric tag ID → count. */
  readonly tags: Readonly<Record<string, number>>;
}

/** Tag master index entry (v2.0 — includes level distribution). */
export interface TagMasterEntry {
  /** Numeric ID for this entity. */
  readonly id: number;
  /** Display name. */
  readonly name: string;
  /** URL-safe slug. */
  readonly slug: string;
  /** Whether this entity uses paginated format. */
  readonly paginated: boolean;
  /** Total puzzle count. */
  readonly count: number;
  /** Number of pages (v2.0+, always-paginated). */
  readonly pages?: number;
  /** Level distribution: numeric level ID → count. */
  readonly levels: Readonly<Record<string, number>>;
}

/** Collection master index entry (v2.0 — includes level and tag distributions). */
export interface CollectionMasterEntry {
  /** Numeric ID for this entity. */
  readonly id: number;
  /** Display name. */
  readonly name: string;
  /** URL-safe slug. */
  readonly slug: string;
  /** Whether this entity uses paginated format. */
  readonly paginated: boolean;
  /** Total puzzle count. */
  readonly count: number;
  /** Number of pages (v2.0+, always-paginated). */
  readonly pages?: number;
  /** Level distribution: numeric level ID → count. */
  readonly levels: Readonly<Record<string, number>>;
  /** Tag distribution: numeric tag ID → count. */
  readonly tags: Readonly<Record<string, number>>;
}

// ============================================================================
// Daily Index (daily_schedule + daily_puzzles tables in yengo-search.db)
// ============================================================================

/**
 * Puzzle entry in daily challenge (with full path info).
 * Spec 119: Simplified schema - id extractable from path.
 * The id field is not stored in JSON but populated at runtime from path.
 */
export interface DailyPuzzleEntry {
  /** Skill level */
  level: string;
  /** Path to SGF file */
  path: string;
  /** Puzzle ID (extracted from path at runtime, not stored in JSON) */
  id?: string;
}

/**
 * Standard daily challenge configuration.
 */
export interface DailyStandard {
  /** Puzzle entries for standard daily challenge */
  puzzles: DailyPuzzleEntry[] | string[];
  /** Total puzzle count */
  total?: number;
  /** Featured technique for this day */
  technique_of_day?: string;
}

/**
 * Scoring configuration for timed challenges.
 */
export interface TimedScoring {
  beginner: number;
  basic: number;
  intermediate: number;
  advanced: number;
  expert: number;
}

/**
 * Timed challenge configuration (v1 - legacy).
 */
export interface DailyTimed {
  /** Puzzle entries for timed mode queue (v1 flat list) */
  queue: DailyPuzzleEntry[] | string[];
  /** Queue size */
  queue_size?: number;
  /** Suggested duration options in seconds */
  suggested_durations?: number[];
  /** Scoring multipliers by level */
  scoring?: TimedScoring;
}

/**
 * Timed set for v2.0 format.
 * Each set contains a fixed number of puzzles.
 */
export interface DailyTimedSet {
  /** Set number (1-based) */
  set_number: number;
  /** Puzzles in this set */
  puzzles: DailyPuzzleEntry[];
}

/**
 * Timed challenge configuration (v2.0 format).
 * Contains structured sets instead of flat queue.
 */
export interface DailyTimedV2 {
  /** Array of timed sets */
  sets: DailyTimedSet[];
  /** Number of sets */
  set_count: number;
  /** Puzzles per set */
  puzzles_per_set: number;
  /** Suggested duration options in seconds */
  suggested_durations: number[];
  /** Scoring points by level */
  scoring: Record<string, number>;
}

/**
 * By-tag challenge entry (v2.0).
 */
export interface DailyByTagEntry {
  /** Puzzles for this tag */
  puzzles: DailyPuzzleEntry[];
  /** Total count */
  total: number;
}

/**
 * By-tag challenges object (v2.0).
 * Maps tag names to their puzzle sets.
 */
export type DailyByTag = Record<string, DailyByTagEntry>;

/**
 * Standard daily challenge (v2.0 format).
 */
export interface DailyStandardV2 {
  /** Puzzle entries */
  puzzles: DailyPuzzleEntry[];
  /** Total count */
  total: number;
  /** Featured technique */
  technique_of_day?: string;
  /** Distribution by level */
  distribution?: Record<string, number>;
}

/**
 * Tag challenge configuration.
 */
export interface DailyTag {
  /** Tag/technique name */
  tag: string;
  /** Technique name (may be same as tag) */
  technique_of_day?: string;
  /** Puzzle entries with this tag */
  puzzles: DailyPuzzleEntry[] | string[];
  /** Total puzzle count */
  total?: number;
}

/**
 * Gauntlet challenge configuration.
 */
export interface DailyGauntlet {
  /** Puzzle entries for gauntlet mode */
  puzzles: DailyPuzzleEntry[] | string[];
  /** Total puzzle count */
  total?: number;
}

/**
 * Source spotlight challenge configuration.
 */
export interface DailySourceSpotlight {
  /** Featured source name */
  source: string;
  /** Puzzle entries from this source */
  puzzles: DailyPuzzleEntry[] | string[];
  /** Total puzzle count */
  total?: number;
}

/**
 * Daily challenge index for a specific date.
 * Stored in daily_schedule + daily_puzzles tables in yengo-search.db.
 * 
 * Supports v1 (legacy), v2.0 (spec 035), and v2.1 (spec 112) formats:
 * - v1: Uses timed.queue (flat list)
 * - v2.0: Uses timed.sets (array of sets), by_tag (object)
 * - v2.1: Adds technique_of_day at root level
 */
export interface DailyIndex {
  /** Index format version (e.g., "1.0", "2.0", "2.1") */
  indexVersion?: string;
  /** Schema version for v2.x ("2.0", "2.1") */
  version?: string;
  /** Date in YYYY-MM-DD format */
  date: string;
  /** When this index was generated (ISO timestamp) - supports both cases */
  generatedAt?: string;
  generated_at?: string;
  
  // ---- v1 and v2 common ----
  /** Standard daily challenge */
  standard?: DailyStandard | DailyStandardV2;
  
  // ---- v1 format ----
  /** Timed challenge queue (v1 - flat list) */
  timed?: DailyTimed | DailyTimedV2;
  /** Tag challenge (v1) */
  tag?: DailyTag;
  
  // ---- v2.0+ format ----
  /** By-tag challenges (v2.0+ - object keyed by tag name) */
  by_tag?: DailyByTag;
  /** Week reference (e.g., "2026-W04") */
  weekly_ref?: string;
  /** Config used for generation (v2.0+) */
  config_used?: Record<string, unknown>;
  
  // ---- v2.1 fields (spec 112) ----
  /** Featured technique of the day at root level (v2.1) */
  technique_of_day?: string;
  
  // ---- Legacy fields ----
  /** Gauntlet challenge - optional */
  gauntlet?: DailyGauntlet;
  /** Source spotlight challenge - optional */
  source_spotlight?: DailySourceSpotlight;
  /** Featured technique tag for this day (legacy camelCase) */
  techniqueOfDay?: string;
}

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Check if an object is a valid DailyIndex.
 */
export function isDailyIndex(value: unknown): value is DailyIndex {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.indexVersion === 'string' &&
    typeof obj.date === 'string' &&
    typeof obj.generatedAt === 'string' &&
    typeof obj.standard === 'object' &&
    typeof obj.timed === 'object'
  );
}


