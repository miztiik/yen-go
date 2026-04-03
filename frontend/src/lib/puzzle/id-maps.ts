/**
 * Numeric ID ↔ Slug maps for compact view entries.
 * @module lib/puzzle/id-maps
 *
 * Source of truth: config/puzzle-levels.json, config/tags.json
 *
 * Compact view entries use sparse numeric IDs instead of string slugs
 * to reduce JSON payload size. These maps convert between representations.
 *
 * Level IDs: kyu range 110-160, dan range 210-230 (sparse, aligned to Go rank system)
 * Tag IDs: Obj 10-28, Tesuji 30-52, Tech 60-82 (even numbers, grouped by category)
 */

// ─── Level Maps ────────────────────────────────────────────────────

/** Numeric level ID → slug. Source: config/puzzle-levels.json */
export const LEVEL_ID_TO_SLUG: Readonly<Record<number, string>> = {
  110: 'novice',
  120: 'beginner',
  130: 'elementary',
  140: 'intermediate',
  150: 'upper-intermediate',
  160: 'advanced',
  210: 'low-dan',
  220: 'high-dan',
  230: 'expert',
} as const;

/** Slug → numeric level ID (reverse lookup). */
export const LEVEL_SLUG_TO_ID: Readonly<Record<string, number>> = Object.fromEntries(
  Object.entries(LEVEL_ID_TO_SLUG).map(([id, slug]) => [slug, Number(id)])
);

// ─── Tag Maps ──────────────────────────────────────────────────────

/** Numeric tag ID → slug. Source: config/tags.json */
export const TAG_ID_TO_SLUG: Readonly<Record<number, string>> = {
  // Objectives (10-28)
  10: 'life-and-death',
  12: 'ko',
  14: 'living',
  16: 'seki',
  // Tesuji (30-52)
  30: 'snapback',
  32: 'double-atari',
  34: 'ladder',
  36: 'net',
  38: 'throw-in',
  40: 'clamp',
  42: 'nakade',
  44: 'connect-and-die',
  46: 'under-the-stones',
  48: 'liberty-shortage',
  50: 'vital-point',
  52: 'tesuji',
  // Techniques (60-82)
  60: 'capture-race',
  62: 'eye-shape',
  64: 'dead-shapes',
  66: 'escape',
  68: 'connection',
  70: 'cutting',
  72: 'sacrifice',
  74: 'corner',
  76: 'shape',
  78: 'endgame',
  80: 'joseki',
  82: 'fuseki',
} as const;

/** Slug → numeric tag ID (reverse lookup). */
export const TAG_SLUG_TO_ID: Readonly<Record<string, number>> = Object.fromEntries(
  Object.entries(TAG_ID_TO_SLUG).map(([id, slug]) => [slug, Number(id)])
);

// ─── Lookup Helpers ────────────────────────────────────────────────

/**
 * Resolve a numeric level ID to its slug string.
 * Returns the number as a string if the ID is unknown (defensive).
 */
export function levelIdToSlug(id: number): string {
  return LEVEL_ID_TO_SLUG[id] ?? String(id);
}

/**
 * Resolve a numeric tag ID to its slug string.
 * Returns the number as a string if the ID is unknown (defensive).
 */
export function tagIdToSlug(id: number): string {
  return TAG_ID_TO_SLUG[id] ?? String(id);
}

/**
 * Resolve a level slug to its numeric ID.
 * Returns undefined if the slug is unknown.
 */
export function levelSlugToId(slug: string): number | undefined {
  return LEVEL_SLUG_TO_ID[slug];
}

/**
 * Resolve a tag slug to its numeric ID.
 * Returns undefined if the slug is unknown.
 */
export function tagSlugToId(slug: string): number | undefined {
  return TAG_SLUG_TO_ID[slug];
}

/**
 * Convert a numeric-keyed distribution map to slug-keyed.
 * Used for master index distributions (e.g., tag_distribution, level_distribution).
 *
 * @param dist - Distribution with numeric string keys (e.g., {"120": 5, "160": 3})
 * @param idToSlug - Lookup map (LEVEL_ID_TO_SLUG or TAG_ID_TO_SLUG)
 * @returns Distribution with slug keys (e.g., {"beginner": 5, "advanced": 3})
 */
export function resolveDistribution(
  dist: Record<string, number>,
  idToSlug: Readonly<Record<number, string>>
): Record<string, number> {
  const result: Record<string, number> = {};
  for (const [numericKey, count] of Object.entries(dist)) {
    const slug = idToSlug[Number(numericKey)] ?? numericKey;
    result[slug] = count;
  }
  return result;
}
