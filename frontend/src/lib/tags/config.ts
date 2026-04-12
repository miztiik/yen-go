/**
 * Tag configuration — single source of truth from config/tags.json.
 *
 * Uses Vite JSON import (build-time inlined, tree-shakeable).
 * Replaces the old generate-types.ts script approach.
 *
 * @module lib/tags/config
 */

import tagsJson from '../../../../config/tags.json';

// ─── Types ─────────────────────────────────────────────────────────

/** Tag category. */
export type TagCategory = 'objective' | 'technique' | 'tesuji';

/** Valid tag slug union, derived from config keys. */
export type TagSlug = keyof typeof tagsJson.tags;

/** Tag metadata. */
export interface TagMeta {
  readonly slug: TagSlug;
  readonly id: number;
  readonly name: string;
  readonly category: TagCategory;
  readonly description: string;
}

// ─── Data ──────────────────────────────────────────────────────────

const rawTags = tagsJson.tags as Record<
  string,
  {
    slug: string;
    id: number;
    name: string;
    category: string;
    description: string;
    aliases: string[];
  }
>;

/** All valid tag slugs, sorted alphabetically. */
export const TAG_SLUGS: readonly TagSlug[] = (Object.keys(rawTags) as TagSlug[]).sort();

/** Total number of tags. */
export const TAG_COUNT = TAG_SLUGS.length;

/** All tag metadata keyed by slug. */
export const TAGS: Readonly<Record<TagSlug, TagMeta>> = Object.fromEntries(
  TAG_SLUGS.map((slug) => {
    const t = rawTags[slug]!;
    return [
      slug,
      {
        slug: t.slug as TagSlug,
        id: t.id,
        name: t.name,
        category: t.category as TagCategory,
        description: t.description,
      },
    ];
  })
) as Record<TagSlug, TagMeta>;

/** Sparse tag ID → slug map. O(1) lookup. */
export const TAG_ID_MAP: ReadonlyMap<number, TagSlug> = new Map(
  TAG_SLUGS.map((slug) => [TAGS[slug].id, slug])
);

/** Slug → sparse tag ID map. O(1) lookup. */
export const TAG_SLUG_MAP: ReadonlyMap<TagSlug, number> = new Map(
  TAG_SLUGS.map((slug) => [slug, TAGS[slug].id])
);

// ─── Functions ─────────────────────────────────────────────────────

/** Type guard for tag slugs. */
export function isValidTag(value: string): value is TagSlug {
  return TAG_SLUG_MAP.has(value as TagSlug);
}

/** Get tag slug from sparse numeric ID. */
export function getTagSlug(id: number): TagSlug | undefined {
  return TAG_ID_MAP.get(id);
}

/** Get sparse numeric ID from tag slug. */
export function getTagId(slug: string): number | undefined {
  return TAG_SLUG_MAP.get(slug as TagSlug);
}

/** Get tag metadata by slug. */
export function getTagMeta(slug: string): TagMeta | undefined {
  if (!TAG_SLUG_MAP.has(slug as TagSlug)) return undefined;
  return TAGS[slug as TagSlug];
}

/** Get all tags in a specific category. */
export function getTagsByCategory(category: TagCategory): TagMeta[] {
  return Object.values(TAGS).filter((t) => t.category === category);
}
