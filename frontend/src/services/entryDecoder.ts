/**
 * Entry decoder — converts SQLite PuzzleRow to domain types.
 * @module services/entryDecoder
 *
 * Provides DecodedEntry type and decodePuzzleRow() for SQLite rows.
 * The decode boundary lives in the loaders — everything downstream uses
 * string slugs and full SGF paths.
 *
 * See also: docs/concepts/sqlite-index-architecture.md
 */

import { levelIdToSlug, qualityIdToSlug, contentTypeIdToSlug } from './configService';
import type { PuzzleRow } from './puzzleQueryService';

// ─── Decoded Type (full fields including complexity) ───────────────

/**
 * Complexity metrics decoded from the compact `x` array.
 * Named CompactComplexity (matching CompactEntry naming convention) to distinguish
 * from YX SGF property string decoding which has different field semantics.
 */
export interface CompactComplexity {
  /** Solution tree depth */
  readonly depth: number;
  /** Number of refutation (wrong) moves */
  readonly refutations: number;
  /** Total moves in solution path */
  readonly solutionLength: number;
  /** Unique correct responses */
  readonly uniqueResponses: number;
}

/**
 * Fully decoded entry with ALL fields including complexity.
 * Use when downstream code needs more than what LevelEntry/TagEntry/CollectionEntry provide.
 */
export interface DecodedEntry {
  /** Full SGF path (e.g., "sgf/0001/hash.sgf") */
  readonly path: string;
  /** Level slug (e.g., "beginner") */
  readonly level: string;
  /** Tag slugs (e.g., ["net", "capture-race"]) */
  readonly tags: readonly string[];
  /** Collection IDs (numeric, not decoded — collections are async) */
  readonly collections: readonly number[];
  /** Complexity metrics */
  readonly complexity: CompactComplexity;
  /** Quality slug (e.g., "standard", "unassigned") */
  readonly quality: string;
  /** Content type slug (e.g., "curated", "practice", "training") */
  readonly contentType: string;
  /** Analysis completeness level (0=untouched, 1=enriched, 2=ai_solved, 3=verified) */
  readonly ac: number;
  /** Sequence number within collection (if present) */
  readonly sequenceNumber?: number | undefined;
}

// ─── Path Reconstruction ───────────────────────────────────────────

/**
 * Reconstruct full SGF path from compact batch/hash reference.
 *
 * @param compactPath - "batch/hash" (e.g., "0001/1e9b57de9becd05f")
 * @returns Full relative path (e.g., "sgf/0001/1e9b57de9becd05f.sgf")
 * @throws Error if compactPath is empty or whitespace-only
 */
export function expandPath(compactPath: string): string {
  if (!compactPath || !compactPath.trim()) {
    throw new Error('expandPath: compactPath must not be empty');
  }
  return `sgf/${compactPath}.sgf`;
}

// ─── PuzzleRow Decoder (SQLite) ────────────────────────────────────

/**
 * Decode a PuzzleRow (from SQLite query) into a DecodedEntry.
 * Tags and collections are not included in PuzzleRow and must be loaded separately.
 */
export function decodePuzzleRow(row: PuzzleRow): DecodedEntry {
  return {
    path: expandPath(`${row.batch}/${row.content_hash}`),
    level: levelIdToSlug(row.level_id),
    tags: [],
    collections: [],
    complexity: {
      depth: row.cx_depth,
      refutations: row.cx_refutations,
      solutionLength: row.cx_solution_len,
      uniqueResponses: row.cx_unique_resp,
    },
    quality: qualityIdToSlug(row.quality),
    contentType: contentTypeIdToSlug(row.content_type),
    ac: row.ac,
  };
}


