/**
 * Unified config service for levels, tags, and collections.
 * @module services/configService
 *
 * Delegates to config modules (Vite JSON imports from config/*.json)
 * as the single source of truth.
 *
 * Levels and tags: synchronous (build-time inlined JSON).
 * Collections: async init from CDN (master index) — deferred to WP5.
 *
 * This module is the ONLY place in the frontend that performs
 * numeric ID ↔ slug resolution.
 *
 * See also: docs/architecture/frontend/view-index-types.md
 */

import {
  LEVEL_ID_MAP,
  LEVEL_SLUG_MAP,
  LEVELS,
  getLevelSlug,
  getLevelId,
  type LevelSlug,
  type LevelMeta,
} from '@/lib/levels/config';
import {
  TAG_ID_MAP,
  TAG_SLUG_MAP,
  TAGS,
  getTagSlug,
  getTagId,
  type TagSlug,
  type TagMeta,
  type TagCategory,
} from '@/lib/tags/config';
import {
  QUALITY_ID_MAP,
  QUALITY_SLUG_MAP,
  QUALITIES,
  getQualitySlug,
  getQualityId,
  type QualitySlug,
  type QualityMeta,
} from '@/lib/quality/config';

// ─── Re-exports (convenience) ──────────────────────────────────────

export type { LevelSlug, LevelMeta, TagSlug, TagMeta, TagCategory, QualitySlug, QualityMeta };

// ─── Level Lookups (synchronous) ───────────────────────────────────

/**
 * Resolve a numeric level ID to its slug string.
 * Returns the number as a string if the ID is unknown (defensive).
 */
export function levelIdToSlug(id: number): string {
  return getLevelSlug(id) ?? String(id);
}

/**
 * Resolve a level slug to its numeric ID.
 * Returns undefined if the slug is unknown.
 */
export function levelSlugToId(slug: string): number | undefined {
  return getLevelId(slug);
}

/**
 * Get all level metadata in difficulty order.
 */
export function getAllLevels(): readonly LevelMeta[] {
  return LEVELS;
}

/**
 * Get level metadata by slug.
 */
export function getLevelMeta(slug: string): LevelMeta | undefined {
  return LEVELS.find(l => l.slug === slug);
}

// ─── Tag Lookups (synchronous) ─────────────────────────────────────

/**
 * Resolve a numeric tag ID to its slug string.
 * Returns the number as a string if the ID is unknown (defensive).
 */
export function tagIdToSlug(id: number): string {
  return getTagSlug(id) ?? String(id);
}

/**
 * Resolve a tag slug to its numeric ID.
 * Returns undefined if the slug is unknown.
 */
export function tagSlugToId(slug: string): number | undefined {
  return getTagId(slug);
}

/**
 * Get all tag metadata keyed by slug.
 */
export function getAllTags(): Readonly<Record<TagSlug, TagMeta>> {
  return TAGS;
}

/**
 * Get tag metadata by slug.
 * Returns undefined for unknown slugs (guard against arbitrary string input).
 */
export function getTagMeta(slug: string): TagMeta | undefined {
  if (!TAG_SLUG_MAP.has(slug as TagSlug)) return undefined;
  return TAGS[slug as TagSlug];
}

/**
 * Get all tags in a specific category.
 * @planned WP7 (FilterDropdown groups tags by category)
 */
export function getTagsByCategory(category: TagCategory): TagMeta[] {
  return Object.values(TAGS).filter(t => t.category === category);
}

// ─── Tag Category Metadata ─────────────────────────────────────────

/** Ordered tag category metadata for UI display (PURSIG Finding 10). */
export interface TagCategoryMeta {
  readonly key: TagCategory;
  readonly label: string;
}

/**
 * All tag categories in display order.
 * Derived from config — single source of truth for category→label mapping.
 * PURSIG Finding 10: Replaces hardcoded arrays in useFilterState/TechniqueBrowsePage.
 */
const TAG_CATEGORIES: readonly TagCategoryMeta[] = [
  { key: 'objective', label: 'Objectives' },
  { key: 'tesuji', label: 'Tesuji Patterns' },
  { key: 'technique', label: 'Techniques' },
];

/** Get all tag categories in display order. */
export function getOrderedTagCategories(): readonly TagCategoryMeta[] {
  return TAG_CATEGORIES;
}

// ─── Distribution Resolution ───────────────────────────────────────

/**
 * Convert a numeric-keyed distribution map to slug-keyed.
 * Used for master index distributions (e.g., tag_distribution, level_distribution).
 * @planned WP5, WP8 (master index consumption for filter counts)
 *
 * @param dist - Distribution with numeric string keys (e.g., {"120": 5, "160": 3})
 * @param idToSlugFn - Lookup function (levelIdToSlug or tagIdToSlug)
 * @returns Distribution with slug keys (e.g., {"beginner": 5, "advanced": 3})
 */
export function resolveDistribution(
  dist: Readonly<Record<string, number>>,
  idToSlugFn: (id: number) => string
): Record<string, number> {
  const result: Record<string, number> = {};
  for (const [numericKey, count] of Object.entries(dist)) {
    const slug = idToSlugFn(Number(numericKey));
    result[slug] = count;
  }
  return result;
}

/**
 * Resolve a level distribution (numeric ID keys → slug keys).
 */
export function resolveLevelDistribution(
  dist: Readonly<Record<string, number>>
): Record<string, number> {
  return resolveDistribution(dist, levelIdToSlug);
}

/**
 * Resolve a tag distribution (numeric ID keys → slug keys).
 */
export function resolveTagDistribution(
  dist: Readonly<Record<string, number>>
): Record<string, number> {
  return resolveDistribution(dist, tagIdToSlug);
}

/**
 * Resolve a quality distribution (numeric ID keys → slug keys).
 */
export function resolveQualityDistribution(
  dist: Readonly<Record<string, number>>
): Record<string, number> {
  return resolveDistribution(dist, qualityIdToSlug);
}

/**
 * Resolve a content type distribution (numeric ID keys → slug keys).
 */
export function resolveContentTypeDistribution(
  dist: Readonly<Record<string, number>>
): Record<string, number> {
  return resolveDistribution(dist, contentTypeIdToSlug);
}

// ─── Quality Lookups (synchronous) ─────────────────────────────────

/**
 * Resolve a numeric quality ID to its slug string.
 * Returns the number as a string if the ID is unknown (defensive).
 * Returns 'unassigned' for quality 0 (null bucket).
 */
export function qualityIdToSlug(id: number): string {
  if (id === 0) return 'unassigned';
  return getQualitySlug(id) ?? String(id);
}

/**
 * Resolve a quality slug to its numeric ID.
 * Returns undefined if the slug is unknown.
 */
export function qualitySlugToId(slug: string): number | undefined {
  if (slug === 'unassigned') return 0;
  return getQualityId(slug);
}

/**
 * Get all quality metadata in ascending order.
 */
export function getAllQualities(): readonly QualityMeta[] {
  return QUALITIES;
}

/**
 * Get quality metadata by slug.
 */
export function getQualityMeta(slug: string): QualityMeta | undefined {
  return QUALITIES.find(q => q.slug === slug);
}

// ─── Raw Map Access (for interop) ──────────────────────────────────

/** Level ID → slug map (ReadonlyMap). Prefer levelIdToSlug() for lookups. */
export { LEVEL_ID_MAP, LEVEL_SLUG_MAP, TAG_ID_MAP, TAG_SLUG_MAP, QUALITY_ID_MAP, QUALITY_SLUG_MAP };

// ─── Content Type Lookups (synchronous, hardcoded) ─────────────────

/**
 * Content type numeric ID → slug mapping.
 * Only 3 static values — no generated types needed.
 */
/** Content type slug union — matches YenGoMetadata.contentType */
export type ContentTypeSlug = 'curated' | 'practice' | 'training';

const CONTENT_TYPE_ID_TO_SLUG: ReadonlyMap<number, ContentTypeSlug> = new Map([
  [1, 'curated'],
  [2, 'practice'],
  [3, 'training'],
]);

const CONTENT_TYPE_SLUG_TO_ID: ReadonlyMap<string, number> = new Map([
  ['curated', 1],
  ['practice', 2],
  ['training', 3],
]);

/**
 * Resolve a numeric content type ID to its slug.
 * Returns 'practice' as default (content type 2).
 */
export function contentTypeIdToSlug(id: number): ContentTypeSlug {
  return CONTENT_TYPE_ID_TO_SLUG.get(id) ?? 'practice';
}

/**
 * Resolve a content type slug to its numeric ID.
 * Returns undefined if slug is unknown.
 */
export function contentTypeSlugToId(slug: string): number | undefined {
  return CONTENT_TYPE_SLUG_TO_ID.get(slug);
}
