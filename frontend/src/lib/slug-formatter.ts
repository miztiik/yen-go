/**
 * formatSlug — Convert URL slugs to human-readable labels.
 * @module lib/slug-formatter
 *
 * Strips known prefixes (`tag-`, `level-`), checks config for
 * tag display names, title-cases words, and handles special phrases.
 *
 * Spec 132, T104
 */

import { getTagMeta, getLevelMeta } from '@/services/configService';

/** Known prefixes to strip from slugs. */
const KNOWN_PREFIXES = ['tag-', 'level-'] as const;

/**
 * Convert a URL slug to a human-readable label.
 *
 * @example
 * formatSlug('tag-life-and-death') // → "Life & Death"
 * formatSlug('level-beginner')     // → "Beginner"
 * formatSlug('cho-chikun-elementary') // → "Cho Chikun Elementary"
 * formatSlug('unknown-slug')       // → "Unknown Slug"
 */
export function formatSlug(slug: string): string {
  if (!slug || typeof slug !== 'string') return slug;

  // Strip known prefixes
  let cleaned = slug;
  for (const prefix of KNOWN_PREFIXES) {
    if (cleaned.startsWith(prefix)) {
      cleaned = cleaned.slice(prefix.length);
      break;
    }
  }

  // Check config for tag display name (covers special cases like Life & Death)
  const tagMeta = getTagMeta(cleaned);
  if (tagMeta) {
    return tagMeta.name;
  }

  // Check config for level display name
  const levelMeta = getLevelMeta(cleaned);
  if (levelMeta) {
    return levelMeta.name;
  }

  // Title-case: split on hyphens, capitalize each word
  return cleaned
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
