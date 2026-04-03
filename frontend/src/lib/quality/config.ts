/**
 * Quality configuration — single source of truth from config/puzzle-quality.json.
 *
 * Uses Vite JSON import (build-time inlined, tree-shakeable).
 * Uses Vite JSON import (build-time inlined). Replaces the old hand-maintained generated-types.ts.
 *
 * @module lib/quality/config
 */

import qualityJson from '../../../../config/puzzle-quality.json';

// ─── Types (derived from config JSON, same pattern as levels/tags) ─

/** Raw quality levels object from config. */
type QualityLevels = typeof qualityJson.levels;

/** A single quality entry from config. */
type QualityEntry = QualityLevels[keyof QualityLevels];

/** Valid quality slug union, derived from config. */
export type QualitySlug = QualityEntry['name'];

/** Quality display name union, derived from config. */
export type QualityName = QualityEntry['display_label'];

/** Quality level requirements from config. */
export interface QualityRequirements {
  readonly minRefutationCount: number;
  readonly requiresComments: boolean;
}

/** Quality metadata. */
export interface QualityMeta {
  readonly id: number;
  readonly slug: QualitySlug;
  readonly name: QualityName;
  readonly stars: number;
  readonly description: string;
  readonly selectionWeight: number;
  readonly requirements: QualityRequirements;
  readonly displayColor: string;
}

// ─── Data (derived from config JSON) ───────────────────────────────

/** Display colors from config. */
export const QUALITY_DISPLAY = {
  starColors: qualityJson.display.star_colors,
  levelColors: qualityJson.display.level_colors,
} as const;

/** All quality metadata in ascending order (worst → best). */
export const QUALITIES: readonly QualityMeta[] = Object.entries(qualityJson.levels)
  .sort(([a], [b]) => Number(a) - Number(b))
  .map(([idStr, entry]) => {
    const reqs = (entry as Record<string, unknown>).requirements as Record<string, unknown> | undefined;
    return {
      id: Number(idStr),
      slug: entry.name,
      name: entry.display_label,
      stars: entry.stars,
      description: entry.description,
      selectionWeight: (entry as Record<string, unknown>).selection_weight as number ?? 1,
      requirements: {
        minRefutationCount: Number(reqs?.refutation_count_min ?? 0),
        requiresComments: Boolean(reqs?.min_comment_level),
      },
      displayColor: (qualityJson.display.level_colors as Record<string, string>)[idStr] ?? '#9E9E9E',
    };
  });

/** All valid quality slugs in ascending order. */
export const QUALITY_SLUGS: readonly QualitySlug[] = QUALITIES.map(q => q.slug);

/** Total number of quality levels. */
export const QUALITY_COUNT = QUALITIES.length;

/** Quality ID → slug map. O(1) lookup. */
export const QUALITY_ID_MAP: ReadonlyMap<number, QualitySlug> = new Map(
  QUALITIES.map(q => [q.id, q.slug]),
);

/** Slug → quality ID map. O(1) lookup. */
export const QUALITY_SLUG_MAP: ReadonlyMap<QualitySlug, number> = new Map(
  QUALITIES.map(q => [q.slug, q.id]),
);

// ─── Functions ─────────────────────────────────────────────────────

/** Type guard for quality slugs. */
export function isValidQuality(value: string): value is QualitySlug {
  return QUALITY_SLUG_MAP.has(value);
}

/** Get quality ID from slug. */
export function getQualityId(slug: string): number | undefined {
  return QUALITY_SLUG_MAP.get(slug);
}

/** Get quality slug from numeric ID. */
export function getQualitySlug(id: number): QualitySlug | undefined {
  return QUALITY_ID_MAP.get(id);
}

// ─── Numeric quality types (migrated from models/quality.ts) ───────

/** Puzzle quality level values (1-5). Scale: 1=worst (unverified), 5=best (premium). */
export type PuzzleQualityLevel = 1 | 2 | 3 | 4 | 5;

/** Information about each puzzle quality level for display. */
export interface PuzzleQualityInfo {
  name: QualitySlug;
  displayLabel: string;
  stars: number;
  description: string;
  color: string;
}

/** Quality metrics from YQ SGF property. */
export interface QualityMetrics {
  level: PuzzleQualityLevel;
  refutationCount: number;
  commentLevel: 0 | 1 | 2;
}

/** Complexity metrics from YX SGF property. */
export interface ComplexityMetrics {
  solutionDepth: number;
  readingCount: number;
  stoneCount: number;
  uniqueness: 0 | 1;
}

// ─── Derived constants ─────────────────────────────────────────────

/** Puzzle quality level metadata derived from QUALITIES. */
export const PUZZLE_QUALITY_INFO: Record<PuzzleQualityLevel, PuzzleQualityInfo> =
  Object.fromEntries(
    QUALITIES.map(q => [q.id, { name: q.slug, displayLabel: q.name, stars: q.stars, description: q.description, color: q.displayColor }]),
  ) as Record<PuzzleQualityLevel, PuzzleQualityInfo>;

/** Default quality metrics (level 1 — Unverified, worst). */
export const DEFAULT_QUALITY_METRICS: QualityMetrics = {
  level: 1,
  refutationCount: 0,
  commentLevel: 0,
};

/** Default complexity metrics. */
export const DEFAULT_COMPLEXITY_METRICS: ComplexityMetrics = {
  solutionDepth: 0,
  readingCount: 0,
  stoneCount: 0,
  uniqueness: 1,
};

// ─── SGF property parsers ──────────────────────────────────────────

/** Parse YQ property string into QualityMetrics. */
export function parseQualityMetrics(value: string): QualityMetrics {
  const parts: Record<string, string> = {};
  for (const part of value.split(';')) {
    const [key, val] = part.split(':');
    if (key && val) {
      parts[key.trim()] = val.trim();
    }
  }
  return {
    level: (parseInt(parts.q || '1', 10) as PuzzleQualityLevel) || 1,
    refutationCount: parseInt(parts.rc || '0', 10),
    commentLevel: (Math.min(parseInt(parts.hc || '0', 10), 2) as 0 | 1 | 2),
  };
}

/** Parse YX property string into ComplexityMetrics. */
export function parseComplexityMetrics(value: string): ComplexityMetrics {
  const parts: Record<string, string> = {};
  for (const part of value.split(';')) {
    const [key, val] = part.split(':');
    if (key && val) {
      parts[key.trim()] = val.trim();
    }
  }
  return {
    solutionDepth: parseInt(parts.d || '0', 10),
    readingCount: parseInt(parts.r || '0', 10),
    stoneCount: parseInt(parts.s || '0', 10),
    uniqueness: (parseInt(parts.u || '1', 10) as 0 | 1) || 1,
  };
}

/** Get puzzle quality info for display. */
export function getPuzzleQualityInfo(level: PuzzleQualityLevel): PuzzleQualityInfo {
  return PUZZLE_QUALITY_INFO[level] || PUZZLE_QUALITY_INFO[1];
}

/** Check if a puzzle quality level value is valid (1-5). */
export function isValidPuzzleQualityLevel(level: number): level is PuzzleQualityLevel {
  return level >= 1 && level <= 5 && Number.isInteger(level);
}
