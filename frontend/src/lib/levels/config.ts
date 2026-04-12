/**
 * Level configuration — single source of truth from config/puzzle-levels.json.
 *
 * Uses Vite JSON import (build-time inlined, tree-shakeable).
 * Replaces the old generate-types.ts script approach.
 *
 * @module lib/levels/config
 */

import levelsJson from '../../../../config/puzzle-levels.json';

// ─── Types (derived from config shape) ─────────────────────────────

/** A single level entry from config/puzzle-levels.json. */
type LevelEntry = (typeof levelsJson.levels)[number];

/** Valid level slug union, derived from config. */
export type LevelSlug = LevelEntry['slug'];

/** Level display name union. */
export type LevelName = LevelEntry['name'];

/** Level short name union. */
export type LevelShortName = LevelEntry['shortName'];

/** Level metadata. */
export interface LevelMeta {
  readonly id: number;
  readonly slug: LevelSlug;
  readonly name: LevelName;
  readonly shortName: LevelShortName;
  readonly rankRange: { readonly min: string; readonly max: string };
  readonly description: string;
}

// ─── Data (frozen arrays and maps) ─────────────────────────────────

/** All levels in difficulty order (easiest → hardest). */
export const LEVELS: readonly LevelMeta[] = levelsJson.levels as readonly LevelMeta[];

/** All valid level slugs in difficulty order. */
export const LEVEL_SLUGS: readonly LevelSlug[] = LEVELS.map((l) => l.slug);

/** Total number of levels. */
export const LEVEL_COUNT = LEVELS.length;

/** Sparse level ID → slug map. O(1) lookup. */
export const LEVEL_ID_MAP: ReadonlyMap<number, LevelSlug> = new Map(
  LEVELS.map((l) => [l.id, l.slug])
);

/** Slug → sparse level ID map. O(1) lookup. */
export const LEVEL_SLUG_MAP: ReadonlyMap<LevelSlug, number> = new Map(
  LEVELS.map((l) => [l.slug, l.id])
);

// ─── Functions ─────────────────────────────────────────────────────

/** Type guard for level slugs. */
export function isValidLevel(value: string): value is LevelSlug {
  return LEVEL_SLUG_MAP.has(value);
}

/** Get sparse level ID from slug. Returns undefined if invalid. */
export function getLevelId(slug: string): number | undefined {
  return LEVEL_SLUG_MAP.get(slug);
}

/** Get level slug from sparse numeric ID. Returns undefined if invalid. */
export function getLevelSlug(id: number): LevelSlug | undefined {
  return LEVEL_ID_MAP.get(id);
}

/** Get level metadata by slug. */
export function getLevelMeta(slug: string): LevelMeta | undefined {
  return LEVELS.find((l) => l.slug === slug);
}

/** Get level metadata by numeric ID. */
export function getLevelById(id: number): LevelMeta | undefined {
  const slug = LEVEL_ID_MAP.get(id);
  return slug ? LEVELS.find((l) => l.slug === slug) : undefined;
}

/** Get display name with rank range (e.g. "Intermediate (15k-11k)"). */
export function getLevelDisplayName(id: number): string {
  const level = getLevelById(id);
  if (!level) return `Level ${id}`;
  return `${level.name} (${level.rankRange.min}-${level.rankRange.max})`;
}

/** Get level name by slug. */
export function getLevelName(slug: string): string {
  return getLevelMeta(slug)?.name ?? slug;
}
