/**
 * useFilterParams — URL query parameter persistence for filter state.
 * @module hooks/useFilterParams
 *
 * Reads filter state from URL on mount (`?level=130&tag=34`),
 * and writes back via `history.replaceState` on change (no history push).
 *
 * Spec: plan-compact-schema-filtering.md WP8 §8.15
 */

import { useEffect, useRef } from 'preact/hooks';
import { levelIdToSlug, tagIdToSlug } from '@/services/configService';

/** Tracked last-written state for skip-on-match (PURSIG Finding 3). */
interface WrittenState {
  levels: readonly number[];
  tags: readonly number[];
}

// ============================================================================
// Types
// ============================================================================

/** Filter dimensions a page supports. Unsupported dimensions are stripped from URL. */
export type FilterDimension = 'level' | 'tag';

export interface FilterParams {
  /** Level numeric IDs from URL, empty if not set. */
  readonly levels: readonly number[];
  /** Tag numeric IDs from URL, empty if not set. */
  readonly tags: readonly number[];
}

// ============================================================================
// Read / Write Utilities
// ============================================================================

/**
 * Parse a comma-separated string into an array of integers.
 * Returns empty array if input is null or contains no valid numbers.
 */
function toIntArray(s: string | null): number[] {
  if (s === null || s === '') return [];
  return s.split(',').map(v => parseInt(v.trim(), 10)).filter(n => !Number.isNaN(n));
}

/**
 * Read filter params from current URL search string.
 * Returns `{ levels, tags }` with parsed integer arrays.
 * Supports comma-separated multi-select: ?level=130,140&tag=34,36
 */
export function readFilterParams(): FilterParams {
  const params = new URLSearchParams(window.location.search);
  return {
    levels: toIntArray(params.get('level')),
    tags: toIntArray(params.get('tag')),
  };
}

/**
 * Write filter params to URL via `history.replaceState`.
 * Preserves existing non-filter query params.
 * Removes params whose value is empty.
 * Multi-select: arrays serialized as comma-separated: ?level=130,140
 */
export function writeFilterParams(levels: readonly number[], tags: readonly number[]): void {
  const params = new URLSearchParams(window.location.search);

  if (levels.length > 0) {
    params.set('level', levels.join(','));
  } else {
    params.delete('level');
  }

  if (tags.length > 0) {
    params.set('tag', tags.join(','));
  } else {
    params.delete('tag');
  }

  const search = params.toString();
  const url = search
    ? `${window.location.pathname}?${search}`
    : window.location.pathname;

  // Skip no-op writes (Finding 17)
  const current = window.location.pathname + window.location.search;
  if (url === current) return;

  window.history.replaceState(window.history.state, '', url);
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Sync filter state with URL query parameters.
 *
 * On mount: reads URL params for supported dimensions, applies to filter state.
 * On change: writes supported dimensions to URL via replaceState.
 * Unsupported dimensions are stripped from URL on mount (F14).
 * Supports multi-select via comma-separated values: ?level=130,140&tag=34,36
 *
 * @param levelIds - Current level filter IDs from useFilterState
 * @param tagIds - Current tag filter IDs from useFilterState
 * @param setLevelIds - Setter from useFilterState (array)
 * @param setTagIds - Setter from useFilterState (array)
 * @param dimensions - Which filter dimensions this page supports (F14)
 */
export function useFilterParams(
  levelIds: readonly number[],
  tagIds: readonly number[],
  setLevelIds: (ids: number[]) => void,
  setTagIds: (ids: number[]) => void,
  dimensions: readonly FilterDimension[] = ['level', 'tag'],
): void {
  const initialized = useRef(false);
  const lastWritten = useRef<WrittenState>({ levels: [], tags: [] });

  // F14: Pre-compute supported dimensions for fast lookup
  const supportsLevel = dimensions.includes('level');
  const supportsTag = dimensions.includes('tag');

  // On mount: read URL params and apply to filter state (only supported dimensions)
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const params = readFilterParams();

    // Validate IDs against known levels/tags (Finding 4 — discard invalid)
    const validLevels = supportsLevel
      ? params.levels.filter(id => levelIdToSlug(id) !== String(id))
      : [];
    const validTags = supportsTag
      ? params.tags.filter(id => tagIdToSlug(id) !== String(id))
      : [];

    // F14: Strip unsupported dimensions from URL
    const hadUnsupported =
      (!supportsLevel && params.levels.length > 0) ||
      (!supportsTag && params.tags.length > 0);
    const hadInvalid =
      (supportsLevel && params.levels.length > 0 && validLevels.length !== params.levels.length) ||
      (supportsTag && params.tags.length > 0 && validTags.length !== params.tags.length);

    if (validLevels.length > 0) setLevelIds(validLevels);
    if (validTags.length > 0) setTagIds(validTags);

    // Clean invalid or unsupported params from URL
    if (hadUnsupported || hadInvalid) {
      writeFilterParams(validLevels, validTags);
    }
  }, [setLevelIds, setTagIds, supportsLevel, supportsTag]);

  // On filter change: write supported dimensions to URL
  useEffect(() => {
    if (!initialized.current) return;
    // Only persist supported dimensions; unsupported stay empty in URL
    const writeLevels = supportsLevel ? levelIds : [];
    const writeTags = supportsTag ? tagIds : [];
    const prevLevels = lastWritten.current.levels;
    const prevTags = lastWritten.current.tags;
    if (arraysEqual(writeLevels, prevLevels) && arraysEqual(writeTags, prevTags)) return;
    lastWritten.current = { levels: writeLevels, tags: writeTags };
    writeFilterParams(writeLevels, writeTags);
  }, [levelIds, tagIds, supportsLevel, supportsTag]);
}

/** Shallow array equality check for number arrays. */
function arraysEqual(a: readonly number[], b: readonly number[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

export default useFilterParams;
