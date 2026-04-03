/**
 * Level-to-rank mapping utility (UI-037)
 *
 * Maps puzzle level slugs to Go rank ranges from config/puzzle-levels.json.
 * Derives from build-time generated LEVELS metadata.
 *
 * @module lib/levelRanks
 */

import { LEVELS } from './levels/config';

/** Rank range for a puzzle level. */
export interface RankRange {
  min: string;
  max: string;
}

/**
 * Rank ranges derived from config/puzzle-levels.json.
 */
const RANK_RANGES: Readonly<Record<string, RankRange>> = Object.fromEntries(
  LEVELS.map(l => [l.slug, { min: l.rankRange.min, max: l.rankRange.max }])
);

/**
 * Get rank range for a level slug.
 * @param levelSlug - e.g. "upper-intermediate"
 * @returns Rank range or null if unknown level
 */
export function getRankRange(levelSlug: string): RankRange | null {
  return RANK_RANGES[levelSlug] ?? null;
}

/**
 * Format rank range as display string.
 * @param levelSlug - e.g. "upper-intermediate"
 * @returns e.g. "10k–6k" or null if unknown level
 */
export function formatRankRange(levelSlug: string): string | null {
  const range = getRankRange(levelSlug);
  if (!range) return null;
  return `${range.min}–${range.max}`;
}

/**
 * Humanize a collection slug for display.
 * Converts kebab-case to Title Case.
 * @param slug - e.g. "cho-chikun-life-death-elementary"
 * @returns e.g. "Cho Chikun Life Death Elementary"
 */
export function humanizeCollectionName(slug: string): string {
  return slug.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}
