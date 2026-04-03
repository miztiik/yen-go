/**
 * Level category grouping utilities.
 * @module lib/levels/categories
 *
 * Provides the 3-tier category system (beginner/intermediate/advanced)
 * used by Training and Random pages. These are UI grouping concepts,
 * NOT level slugs — they map to ranges of Go ranks.
 *
 * The string values 'beginner', 'intermediate', 'advanced' are
 * category labels, not puzzle level slugs.
 */

import { LEVELS, type LevelSlug } from './config';
import type { FilterOption } from '@/components/shared/FilterBar';

/**
 * UI category filter — coarser than the 9-level system.
 * 'beginner' here means "beginner tier" (kyu levels < 140), not the
 * level slug 'beginner'.
 */
export type CategoryFilter = 'all' | 'beginner' | 'intermediate' | 'advanced';

/**
 * Category filter options for FilterBar.
 */
export const CATEGORY_OPTIONS: readonly FilterOption[] = [
  { id: 'all', label: 'All Levels' },
  { id: 'beginner', label: 'Beginner' },
  { id: 'intermediate', label: 'Intermediate' },
  { id: 'advanced', label: 'Advanced' },
];

/**
 * Map category to level slugs — derived from config IDs.
 * - beginner: kyu levels with ID < 140 (novice through elementary)
 * - intermediate: kyu levels 140-160 (intermediate through advanced)
 * - advanced: dan levels with ID >= 200 (low-dan through expert)
 *
 * Results are memoized since LEVELS is a static const array.
 */
const categoryLevelsCache = new Map<CategoryFilter, readonly LevelSlug[]>();

export function getCategoryLevels(category: CategoryFilter): readonly LevelSlug[] {
  const cached = categoryLevelsCache.get(category);
  if (cached) return cached;

  let result: readonly LevelSlug[];
  if (category === 'all') result = LEVELS.map(l => l.slug);
  else if (category === 'beginner') result = LEVELS.filter(l => l.id < 140).map(l => l.slug);
  else if (category === 'intermediate') result = LEVELS.filter(l => l.id >= 140 && l.id < 200).map(l => l.slug);
  else result = LEVELS.filter(l => l.id >= 200).map(l => l.slug);

  categoryLevelsCache.set(category, result);
  return result;
}

/**
 * Get the category for a given level slug.
 * Returns 'beginner' for unknown slugs (safe default).
 */
export function getLevelCategory(slug: string): CategoryFilter {
  const level = LEVELS.find(l => l.slug === slug);
  if (!level) return 'beginner';
  if (level.id < 140) return 'beginner';
  if (level.id < 200) return 'intermediate';
  return 'advanced';
}
