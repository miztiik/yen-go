/**
 * useCanonicalUrl — Preact hook for canonical URL parameter sync.
 *
 * Replaces the legacy `useFilterParams` hook with P3 routing semantics.
 * Reads and writes compact filter keys (`l`, `t`, `c`, `q`) plus `offset`,
 * `id`, and `match` to/from the URL search string using `history.replaceState`.
 *
 * Filter changes never create browser history entries.
 *
 * @module hooks/useCanonicalUrl
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'preact/hooks';
import {
  parseCanonicalFilters,
  serializeCanonicalFilters,
  parseOffset,
  parseId,
  CANONICAL_PARAM_ORDER,
} from '@/lib/routing/canonicalUrl';
import type { CanonicalFilters } from '@/lib/routing/canonicalUrl';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Return value of the {@link useCanonicalUrl} hook. */
export interface UseCanonicalUrlResult {
  /** Current filter values from URL. */
  readonly filters: CanonicalFilters;
  /** Current offset from URL. */
  readonly offset: number | undefined;
  /** Current puzzle id from URL. */
  readonly id: string | undefined;
  /** Update one or more filter dimensions. Merges with existing. Empty array clears that dimension. */
  readonly setFilters: (update: Partial<CanonicalFilters>) => void;
  /** Set the offset value in URL. `undefined` removes it. */
  readonly setOffset: (offset: number | undefined) => void;
  /** Set the puzzle id in URL. `undefined` removes it. */
  readonly setId: (id: string | undefined) => void;
  /** Clear all filters (reset to empty). Does not clear offset/id. */
  readonly clearFilters: () => void;
  /** Whether any filter is active (any dimension has values). */
  readonly hasActiveFilters: boolean;
  /** Count of active filter dimensions (l, t, c, q). */
  readonly activeFilterCount: number;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** The four numeric filter dimension keys. */
const FILTER_DIMENSION_KEYS = ['l', 't', 'c', 'q'] as const;

/**
 * Merge a partial filter update into the current filters.
 *
 * - Dimensions present in `update` override the same dimension in `current`.
 * - An empty array (`[]`) removes that dimension from the result.
 * - Dimensions not mentioned in `update` are preserved from `current`.
 * - The `match` field is merged the same way: `undefined` in `update` preserves
 *   the current value; an explicit `undefined` cannot be passed via the
 *   Partial type, so consumers set `match` to the desired value or omit it.
 */
function mergeFilters(
  current: CanonicalFilters,
  update: Partial<CanonicalFilters>,
): CanonicalFilters {
  const merged: Record<string, readonly number[] | 'all' | 'any' | undefined> = {};

  // Start with current numeric dimensions.
  for (const key of FILTER_DIMENSION_KEYS) {
    const currentValue = current[key];
    if (currentValue && currentValue.length > 0) {
      merged[key] = currentValue;
    }
  }

  // Apply update: overwrite or remove numeric dimensions.
  for (const key of FILTER_DIMENSION_KEYS) {
    if (key in update) {
      const value = update[key];
      if (value && value.length > 0) {
        merged[key] = value;
      } else {
        // Empty array or undefined → remove the dimension.
        delete merged[key];
      }
    }
  }

  // Handle match mode.
  const matchValue = 'match' in update ? update.match : current.match;

  const result: CanonicalFilters = {};

  for (const key of FILTER_DIMENSION_KEYS) {
    const val = merged[key];
    if (Array.isArray(val) && val.length > 0) {
      (result as Record<string, readonly number[]>)[key] = val;
    }
  }

  if (matchValue) {
    (result as { match?: 'all' | 'any' }).match = matchValue;
  }

  return result;
}

/**
 * Build the full search string from filters, offset, and id,
 * using read-merge-write to preserve params owned by other hooks.
 *
 * Reads current URLSearchParams, sets/deletes only canonical keys,
 * re-orders canonical keys per {@link CANONICAL_PARAM_ORDER},
 * and preserves all unmanaged keys (e.g. `cat`, `s`, `q` from useBrowseParams).
 */
function buildSearchString(
  filters: CanonicalFilters,
  offset: number | undefined,
  id: string | undefined,
): string {
  // Start from the current URL to preserve unmanaged params (RC-3).
  const current = new URLSearchParams(window.location.search);
  const canonical = serializeCanonicalFilters(filters);

  // Set/delete each canonical key.
  for (const key of CANONICAL_PARAM_ORDER) {
    const value = canonical.get(key);
    if (value != null) {
      current.set(key, value);
    } else {
      current.delete(key);
    }
  }

  // Apply id and offset.
  if (id !== undefined) {
    current.set('id', id);
  } else {
    current.delete('id');
  }

  if (offset !== undefined) {
    current.set('offset', String(offset));
  } else {
    current.delete('offset');
  }

  // Re-sort: canonical keys first in deterministic order, then remaining.
  const ordered = new URLSearchParams();
  const knownKeys = new Set<string>(CANONICAL_PARAM_ORDER);

  for (const key of CANONICAL_PARAM_ORDER) {
    const value = current.get(key);
    if (value != null) {
      ordered.set(key, value);
    }
  }

  // Append non-canonical keys in their original order.
  for (const [key, value] of current.entries()) {
    if (!knownKeys.has(key)) {
      ordered.set(key, value);
    }
  }

  return ordered.toString();
}

/**
 * Count how many of the four numeric filter dimensions have at least one value.
 */
function countActiveDimensions(filters: CanonicalFilters): number {
  let count = 0;
  for (const key of FILTER_DIMENSION_KEYS) {
    const value = filters[key];
    if (value && value.length > 0) {
      count++;
    }
  }
  return count;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Sync canonical URL parameters with component state.
 *
 * On mount the hook reads the current URL search string and parses filters,
 * offset, and id. Setter calls update internal state and write the new
 * search string to the URL via `history.replaceState` — filter changes
 * never create browser history entries.
 *
 * All setters are stable references (wrapped in `useCallback`).
 *
 * @returns An object conforming to {@link UseCanonicalUrlResult}.
 *
 * @example
 * ```tsx
 * function MyPage() {
 *   const { filters, setFilters, hasActiveFilters, clearFilters } = useCanonicalUrl();
 *
 *   // Toggle a level filter
 *   const toggleLevel = (id: number) => {
 *     const current = filters.l ?? [];
 *     const next = current.includes(id)
 *       ? current.filter(v => v !== id)
 *       : [...current, id];
 *     setFilters({ l: next });
 *   };
 * }
 * ```
 */
export function useCanonicalUrl(): UseCanonicalUrlResult {
  // ---- initial parse from URL ----
  const [filters, setFiltersState] = useState<CanonicalFilters>(() =>
    parseCanonicalFilters(window.location.search),
  );
  const [offset, setOffsetState] = useState<number | undefined>(() =>
    parseOffset(window.location.search),
  );
  const [id, setIdState] = useState<string | undefined>(() =>
    parseId(window.location.search),
  );

  // F2 fix: refs for latest values — prevents stale closures in setters
  const filtersRef = useRef(filters);
  filtersRef.current = filters;
  const offsetRef = useRef(offset);
  offsetRef.current = offset;
  const idRef = useRef(id);
  idRef.current = id;

  // Track the last-written search string to avoid no-op replaceState calls.
  const lastWrittenSearch = useRef<string>(window.location.search.replace(/^\?/, ''));

  // ---- URL writer ----
  /**
   * Write the given state to the URL. Skips if the serialized result matches
   * the last-written value (avoids unnecessary replaceState calls).
   */
  const writeToUrl = useCallback(
    (
      nextFilters: CanonicalFilters,
      nextOffset: number | undefined,
      nextId: string | undefined,
    ): void => {
      const search = buildSearchString(nextFilters, nextOffset, nextId);

      if (search === lastWrittenSearch.current) return;

      lastWrittenSearch.current = search;

      const url = search
        ? `${window.location.pathname}?${search}${window.location.hash}`
        : `${window.location.pathname}${window.location.hash}`;

      window.history.replaceState(window.history.state, '', url);
    },
    [],
  );

  // ---- setters ----

  /**
   * Merge a partial filter update into the current filters and sync to URL.
   *
   * Dimensions present in `update` override. To clear a dimension pass an
   * empty array: `setFilters({ t: [] })`.
   */
  const setFilters = useCallback(
    (update: Partial<CanonicalFilters>): void => {
      setFiltersState((prev) => {
        const next = mergeFilters(prev, update);
        // Read latest offset/id from refs (F2 fix: eliminates stale closures)
        writeToUrl(next, offsetRef.current, idRef.current);
        return next;
      });
    },
    [writeToUrl],
  );

  /**
   * Set the offset value in the URL. Pass `undefined` to remove it.
   */
  const setOffset = useCallback(
    (nextOffset: number | undefined): void => {
      setOffsetState(nextOffset);
      writeToUrl(filtersRef.current, nextOffset, idRef.current);
    },
    [writeToUrl],
  );

  /**
   * Set the puzzle id in the URL. Pass `undefined` to remove it.
   */
  const setId = useCallback(
    (nextId: string | undefined): void => {
      setIdState(nextId);
      writeToUrl(filtersRef.current, offsetRef.current, nextId);
    },
    [writeToUrl],
  );

  /**
   * Clear all filter dimensions. Does not touch offset or id.
   */
  const clearFilters = useCallback((): void => {
    const empty: CanonicalFilters = {};
    setFiltersState(empty);
    writeToUrl(empty, offsetRef.current, idRef.current);
  }, [writeToUrl]);

  // ---- sync URL on state change (safety net) ----
  // The primary URL write happens eagerly inside each setter. This effect
  // acts as a safety net to catch any state drift (e.g. concurrent updates).
  useEffect(() => {
    writeToUrl(filters, offset, id);
  }, [filters, offset, id, writeToUrl]);

  // ---- derived values ----

  /** True when at least one numeric filter dimension has values. */
  const hasActiveFilters = useMemo(
    () => countActiveDimensions(filters) > 0,
    [filters],
  );

  /** Number of numeric filter dimensions that have values. */
  const activeFilterCount = useMemo(
    () => countActiveDimensions(filters),
    [filters],
  );

  return {
    filters,
    offset,
    id,
    setFilters,
    setOffset,
    setId,
    clearFilters,
    hasActiveFilters,
    activeFilterCount,
  };
}

export default useCanonicalUrl;
