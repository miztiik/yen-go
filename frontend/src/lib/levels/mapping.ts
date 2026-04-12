/**
 * Rank Mapping Utilities
 * @module lib/levels/mapping
 *
 * Functions for normalizing and mapping Go ranks to level slugs.
 * The rank→slug table is derived at module load from config/puzzle-levels.json
 * via the rankRange fields — no hardcoded values.
 *
 * Constitution Compliance:
 * - VI. Type Safety: Strict TypeScript types
 * - V. No Browser AI: Pure validation only, no computation
 */

import { LEVELS, type LevelSlug } from './config';

/** Expand a rankRange pair into individual rank strings.
 * e.g. { min: "30k", max: "26k" } → ["30k","29k","28k","27k","26k"]
 *      { min: "1d",  max: "3d"  } → ["1d","2d","3d"]
 */
function expandRankRange(min: string, max: string): string[] {
  const isDan = min.endsWith('d');
  const minNum = parseInt(min, 10);
  const maxNum = parseInt(max, 10);
  const suffix = isDan ? 'd' : 'k';
  const ranks: string[] = [];
  if (isDan) {
    for (let i = minNum; i <= maxNum; i++) ranks.push(`${i}${suffix}`);
  } else {
    for (let i = minNum; i >= maxNum; i--) ranks.push(`${i}${suffix}`);
  }
  return ranks;
}

/** Rank string → level slug. Derived from config/puzzle-levels.json rankRange — single source of truth. */
const RANK_TO_SLUG: ReadonlyMap<string, LevelSlug> = new Map(
  LEVELS.flatMap((l) =>
    expandRankRange(l.rankRange.min, l.rankRange.max).map((rank) => [rank, l.slug] as const)
  )
);

/**
 * Normalize rank string to standard format.
 *
 * Handles various rank formats from different sources:
 * - "8K", "8k", "8 kyu", "8-kyu" -> "8k"
 * - "3D", "3d", "3 dan", "3-dan" -> "3d"
 *
 * @param rankStr - Raw rank string
 * @returns Normalized rank in format "Nk" or "Nd"
 *
 * @example
 * normalizeRank("8K") // "8k"
 * normalizeRank("3 dan") // "3d"
 */
export function normalizeRank(rankStr: string): string {
  if (!rankStr) return '';

  let rank = rankStr.toLowerCase().trim();

  // Remove common separators and suffixes
  rank = rank.replace(/-kyu/g, 'k');
  rank = rank.replace(/ kyu/g, 'k');
  rank = rank.replace(/kyu/g, 'k');
  rank = rank.replace(/-dan/g, 'd');
  rank = rank.replace(/ dan/g, 'd');
  rank = rank.replace(/dan/g, 'd');

  // Remove spaces
  rank = rank.replace(/\s/g, '');

  // Validate format
  if (/^\d+[kd]$/.test(rank)) {
    return rank;
  }

  // Try to extract just the number + k/d
  const match = rank.match(/(\d+)\s*([kd])/);
  if (match) {
    return `${match[1]}${match[2]}`;
  }

  return rank;
}

/**
 * Map normalized rank to level slug.
 *
 * @param normalizedRank - Rank in format "8k", "3d", etc.
 * @returns Level slug or null if not recognized
 *
 * @example
 * rankToLevel("8k") // 'upper-intermediate'
 * rankToLevel("3d") // 'low-dan'
 */
export function rankToLevel(normalizedRank: string): LevelSlug | null {
  if (!normalizedRank) return null;
  return RANK_TO_SLUG.get(normalizedRank.toLowerCase()) ?? null;
}

/**
 * Resolve ambiguous rank ranges to a single rank.
 *
 * For ranges like "10K-5K", returns the STRONGER rank.
 *
 * @param rankStr - Rank string, possibly a range
 * @returns Single normalized rank
 *
 * @example
 * resolveRankRange("10K-5K") // "5k"
 * resolveRankRange("1D-3D") // "3d"
 */
export function resolveRankRange(rankStr: string): string {
  if (!rankStr.includes('-')) {
    return normalizeRank(rankStr);
  }

  const parts = rankStr.split('-');
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    return normalizeRank(rankStr);
  }

  const rank1 = normalizeRank(parts[0]);
  const rank2 = normalizeRank(parts[1]);

  const level1 = rankToLevel(rank1);
  const level2 = rankToLevel(rank2);

  if (level1 !== null && level2 !== null) {
    // Return rank with higher level (stronger player)
    if (level2 > level1) return rank2;
    if (level1 > level2) return rank1;

    // Same level - compare numerically within the rank type
    // For dan: higher number is stronger (3d > 1d)
    // For kyu: lower number is stronger (5k > 10k)
    const num1 = parseInt(rank1, 10);
    const num2 = parseInt(rank2, 10);
    const isDan = rank1.endsWith('d');

    if (isDan) {
      // Dan ranks: higher number is stronger
      return num2 > num1 ? rank2 : rank1;
    } else {
      // Kyu ranks: lower number is stronger
      return num2 < num1 ? rank2 : rank1;
    }
  }

  // If one is valid, use it
  if (level1 !== null) return rank1;
  if (level2 !== null) return rank2;

  return normalizeRank(rankStr);
}

/**
 * Map raw rank string directly to level ID.
 * Combines normalization and mapping in one step.
 *
 * @param rankStr - Raw rank string (will be normalized)
 * @returns Level slug or null if not recognized
 *
 * @example
 * rankStringToLevel("8K") // 'upper-intermediate'
 * rankStringToLevel("3D") // 'low-dan'
 */
export function rankStringToLevel(rankStr: string): LevelSlug | null {
  const normalized = normalizeRank(rankStr);
  return rankToLevel(normalized);
}

/**
 * Get all ranks for a specific level slug.
 *
 * @param slug - Level slug (e.g. 'intermediate')
 * @returns Array of rank strings at that level
 */
export function getRanksForLevel(slug: LevelSlug): string[] {
  const result: string[] = [];
  for (const [rank, s] of RANK_TO_SLUG) {
    if (s === slug) result.push(rank);
  }
  return result;
}
