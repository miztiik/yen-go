/**
 * usePuzzleFilters — Preact hook that builds filter UI options from database
 * distributions and manages filter state via canonical URL parameters.
 *
 * Replaces the deleted `useFilterState` + `useMasterIndexes` hooks with a
 * single composable that derives filter options directly from SQLite queries.
 *
 * @module hooks/usePuzzleFilters
 */

import { useState, useEffect, useMemo, useCallback } from 'preact/hooks';
import { init as initDb } from '@/services/sqliteService';
import { getFilterCounts, type QueryFilters } from '@/services/puzzleQueryService';
import depthPresetsConfig from '../../../config/depth-presets.json';
import {
  levelIdToSlug,
  tagIdToSlug,
  qualityIdToSlug,
  contentTypeIdToSlug,
  getLevelMeta,
  getTagMeta,
  getQualityMeta,
  getTagsByCategory,
  getOrderedTagCategories,
} from '@/services/configService';
import { useCanonicalUrl } from '@/hooks/useCanonicalUrl';
import type { CanonicalFilters } from '@/lib/routing/canonicalUrl';
import type { FilterOption } from '@/components/shared/FilterBar';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Filter options derived from database distributions. */
export interface PuzzleFilterOptions {
  /** Level filter options with counts from database distribution. */
  readonly levelOptions: readonly FilterOption[];
  /** Tag option groups by category with counts. */
  readonly tagOptionGroups: readonly { label: string; options: readonly FilterOption[] }[];
  /** Quality filter options with counts. */
  readonly qualityOptions: readonly FilterOption[];
  /** Content-type filter options with counts. */
  readonly contentTypeOptions: readonly FilterOption[];
  /** Depth preset filter options (quick/medium/deep) with counts. */
  readonly depthPresetOptions: readonly FilterOption[];
}

/** Return value of the {@link usePuzzleFilters} hook. */
export interface UsePuzzleFiltersResult {
  /** Whether filter data has been loaded. */
  readonly isLoaded: boolean;
  /** Loading error message, if any. */
  readonly error: string | null;
  /** Filter options derived from database distributions. */
  readonly filterOptions: PuzzleFilterOptions;
  /** Current filter state from URL. */
  readonly filters: CanonicalFilters;
  /** Set filters (delegates to useCanonicalUrl). */
  readonly setFilters: (update: Partial<CanonicalFilters>) => void;
  /** Clear all filters. */
  readonly clearFilters: () => void;
  /** Whether any filter is active. */
  readonly hasActiveFilters: boolean;
  /** Count of active filter dimensions. */
  readonly activeFilterCount: number;

  // ── Offset / ID passthrough from useCanonicalUrl ──

  /** Current offset from URL. */
  readonly offset: number | undefined;
  /** Current puzzle id from URL. */
  readonly id: string | undefined;
  /** Set the offset value in URL. `undefined` removes it. */
  readonly setOffset: (offset: number | undefined) => void;
  /** Set the puzzle id in URL. `undefined` removes it. */
  readonly setId: (id: string | undefined) => void;

  // ── Convenience filter accessors ──

  /** Currently selected level IDs. */
  readonly levelIds: readonly number[];
  /** Currently selected tag IDs. */
  readonly tagIds: readonly number[];
  /** Slug of the single selected level, or null if zero/multiple selected. */
  readonly selectedLevelSlug: string | null;
  /** Slug of the single selected tag, or null if zero/multiple selected. */
  readonly selectedTagSlug: string | null;
  /** Display label of the single selected tag, or null. */
  readonly selectedTagLabel: string | null;
  /** Display labels for all selected levels (in selection order). */
  readonly selectedLevelLabels: readonly string[];

  // ── Convenience filter setters ──

  /** Toggle a level ID in the current selection. */
  readonly toggleLevel: (id: number) => void;
  /** Replace all level IDs. */
  readonly setLevelIds: (ids: number[]) => void;
  /** Replace all tag IDs. */
  readonly setTagIds: (ids: number[]) => void;
  /** Set a single tag (or null to clear). */
  readonly setTag: (id: number | null) => void;
  /** Set a single tag from a FilterOption id string (or null/'' to clear). */
  readonly setTagFromOption: (id: string | null) => void;
  /** Set a single level from a FilterOption id string ('all' or null/'' clears). */
  readonly setLevelFromOption: (id: string | null) => void;

  // ── Depth preset accessors ──

  /** Currently selected depth preset slug (e.g. 'quick'), or null if none. */
  readonly depthPreset: string | null;
  /** Set depth preset by id (or null/'' to clear). */
  readonly setDepthPreset: (id: string | null) => void;
}

// ---------------------------------------------------------------------------
// Empty defaults
// ---------------------------------------------------------------------------

const EMPTY_LEVEL_OPTIONS: readonly FilterOption[] = [];
const EMPTY_TAG_GROUPS: readonly { label: string; options: readonly FilterOption[] }[] = [];
const EMPTY_QUALITY_OPTIONS: readonly FilterOption[] = [];
const EMPTY_CONTENT_TYPE_OPTIONS: readonly FilterOption[] = [];
const EMPTY_DEPTH_PRESET_OPTIONS: readonly FilterOption[] = [];

const EMPTY_FILTER_OPTIONS: PuzzleFilterOptions = {
  levelOptions: EMPTY_LEVEL_OPTIONS,
  tagOptionGroups: EMPTY_TAG_GROUPS,
  qualityOptions: EMPTY_QUALITY_OPTIONS,
  contentTypeOptions: EMPTY_CONTENT_TYPE_OPTIONS,
  depthPresetOptions: EMPTY_DEPTH_PRESET_OPTIONS,
};

// ---------------------------------------------------------------------------
// Query key → QueryFilters translation
// ---------------------------------------------------------------------------

const SEGMENT_RE = /^([a-z]+)(\d+)$/;

/** Convert a query key string (e.g. "c6", "l120-t36") to QueryFilters. */
function queryKeyToFilters(key: string): QueryFilters {
  const result: QueryFilters = {};
  for (const seg of key.split('-')) {
    const m = SEGMENT_RE.exec(seg);
    if (!m) continue;
    const dim = m[1]!;
    const id = Number(m[2]);
    switch (dim) {
      case 'l': result.levelId = id; break;
      case 't': result.tagIds = [...(result.tagIds ?? []), id]; break;
      case 'c': result.collectionId = id; break;
      case 'q': result.quality = id; break;
      case 'ct': result.contentType = id; break;
    }
  }
  return result;
}

/**
 * Translate a depth preset slug (e.g. 'quick') to minDepth/maxDepth for QueryFilters.
 * Returns empty object if the preset is not found or null.
 * Exported for use by Archetype B pages that wire filters directly.
 */
export function depthPresetToRange(
  presetId: string | null | undefined,
): Pick<QueryFilters, 'minDepth' | 'maxDepth'> {
  if (!presetId) return {};
  const preset = depthPresetsConfig.presets.find((p) => p.id === presetId);
  if (!preset) return {};
  return {
    minDepth: preset.minDepth,
    ...(preset.maxDepth != null ? { maxDepth: preset.maxDepth } : {}),
  };
}

/** Internal distribution maps derived from SQL filter counts. */
interface FilterDistributions {
  readonly level?: Readonly<Record<string, number>>;
  readonly tag?: Readonly<Record<string, number>>;
  readonly quality?: Readonly<Record<string, number>>;
  readonly content_type?: Readonly<Record<string, number>>;
  readonly depth_preset?: Readonly<Record<string, number>>;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Build level filter options from a distribution map.
 * Includes an "All" synthetic option at index 0 whose count is the sum of
 * all individual level counts. Levels are sorted by ID ascending (difficulty).
 */
function buildLevelOptions(
  dist: Readonly<Record<string, number>>,
): readonly FilterOption[] {
  const entries = Object.entries(dist)
    .map(([key, count]) => ({ id: Number(key), count }))
    .filter(e => !Number.isNaN(e.id) && (e.id !== 0 || e.count > 0));

  // Sort by numeric ID ascending (maps to difficulty order).
  entries.sort((a, b) => a.id - b.id);

  const totalCount = entries.reduce((sum, e) => sum + e.count, 0);

  const allOption: FilterOption = {
    id: 'all',
    label: 'All',
    count: totalCount,
  };

  const levelOptions: FilterOption[] = entries.map(({ id, count }) => {
    const slug = levelIdToSlug(id);
    const meta = getLevelMeta(slug);
    const label = meta?.name ?? slug;
    const tooltip = meta
      ? `${meta.name} (${meta.rankRange.min}–${meta.rankRange.max})`
      : undefined;
    return { id: String(id), label, count, tooltip };
  });

  return [allOption, ...levelOptions];
}

/**
 * Build tag option groups from a distribution map.
 * Groups are ordered by {@link getOrderedTagCategories} display order.
 * Within each group, tags are sorted alphabetically by label.
 * Tags not present in the distribution are omitted.
 */
function buildTagOptionGroups(
  dist: Readonly<Record<string, number>>,
): readonly { label: string; options: readonly FilterOption[] }[] {
  // Build a lookup: tag slug → { id, count }
  const tagCountMap = new Map<string, { numericId: number; count: number }>();
  for (const [key, count] of Object.entries(dist)) {
    const numericId = Number(key);
    if (Number.isNaN(numericId)) continue;
    if (numericId === 0 && count <= 0) continue; // skip zero-count null bucket
    const slug = tagIdToSlug(numericId);
    tagCountMap.set(slug, { numericId, count });
  }

  const categories = getOrderedTagCategories();
  const groups: { label: string; options: FilterOption[] }[] = [];

  for (const cat of categories) {
    const categoryTags = getTagsByCategory(cat.key);
    const options: FilterOption[] = [];

    for (const tag of categoryTags) {
      const entry = tagCountMap.get(tag.slug);
      if (!entry) continue;
      options.push({
        id: String(entry.numericId),
        label: tag.name,
        count: entry.count,
      });
    }

    // Sort alphabetically by label within each category.
    options.sort((a, b) => a.label.localeCompare(b.label));

    if (options.length > 0) {
      groups.push({ label: cat.label, options });
    }
  }

  return groups;
}

/**
 * Build quality filter options from a distribution map.
 * Sorted by quality ID ascending.
 */
function buildQualityOptions(
  dist: Readonly<Record<string, number>>,
): readonly FilterOption[] {
  const entries = Object.entries(dist)
    .map(([key, count]) => ({ id: Number(key), count }))
    .filter(e => !Number.isNaN(e.id) && (e.id !== 0 || e.count > 0));

  entries.sort((a, b) => a.id - b.id);

  return entries.map(({ id, count }) => {
    const slug = qualityIdToSlug(id);
    const meta = getQualityMeta(slug);
    const label = meta?.name ?? slug;
    return { id: String(id), label, count };
  });
}

/**
 * Build content-type filter options from a distribution map.
 * Sorted by content-type ID ascending.
 */
function buildContentTypeOptions(
  dist: Readonly<Record<string, number>>,
): readonly FilterOption[] {
  const entries = Object.entries(dist)
    .map(([key, count]) => ({ id: Number(key), count }))
    .filter(e => !Number.isNaN(e.id) && (e.id !== 0 || e.count > 0));

  entries.sort((a, b) => a.id - b.id);

  return entries.map(({ id, count }) => {
    const slug = contentTypeIdToSlug(id);
    // Capitalize first letter for display
    const label = slug.charAt(0).toUpperCase() + slug.slice(1);
    return { id: String(id), label, count };
  });
}

/**
 * Build depth preset filter options from a distribution map.
 * Uses the depth-presets.json config for labels; preserves config order.
 * Exported for use by Archetype B pages that wire filters directly.
 */
export function buildDepthPresetOptions(
  dist: Readonly<Record<string, number>>,
): readonly FilterOption[] {
  return depthPresetsConfig.presets.map((preset) => ({
    id: preset.id,
    label: preset.label,
    count: dist[preset.id] ?? 0,
  }));
}

/**
 * Build all filter options from distribution maps.
 * Only includes dimensions that are present in the distributions.
 */
function buildFilterOptions(distributions: FilterDistributions): PuzzleFilterOptions {
  const levelOptions = distributions.level
    ? buildLevelOptions(distributions.level)
    : EMPTY_LEVEL_OPTIONS;

  const tagOptionGroups = distributions.tag
    ? buildTagOptionGroups(distributions.tag)
    : EMPTY_TAG_GROUPS;

  const qualityOptions = distributions.quality
    ? buildQualityOptions(distributions.quality)
    : EMPTY_QUALITY_OPTIONS;

  const contentTypeOptions = distributions.content_type
    ? buildContentTypeOptions(distributions.content_type)
    : EMPTY_CONTENT_TYPE_OPTIONS;

  const depthPresetOptions = distributions.depth_preset
    ? buildDepthPresetOptions(distributions.depth_preset)
    : EMPTY_DEPTH_PRESET_OPTIONS;

  return { levelOptions, tagOptionGroups, qualityOptions, contentTypeOptions, depthPresetOptions };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * usePuzzleFilters — Builds filter UI options from database distributions.
 *
 * Queries the SQLite database for the given key, derives level / tag / quality
 * filter options from the distributions, and exposes the canonical URL
 * filter state alongside convenience accessors and setters.
 *
 * @param queryKey - The primary query key to load data for (e.g., "c6", "l120").
 *   Pass `null` to skip loading (returns empty options with `isLoaded=false`).
 * @param options - Reserved for future dimension filtering (currently unused).
 * @returns Filter options, state, and mutators.
 *
 * @example
 * ```tsx
 * const { isLoaded, filterOptions, toggleLevel } = usePuzzleFilters('c6');
 * if (!isLoaded) return <Spinner />;
 * return <FilterBar options={filterOptions.levelOptions} onChange={id => toggleLevel(Number(id))} />;
 * ```
 */
export function usePuzzleFilters(
  queryKey: string | null,
  _options?: { dimensions?: readonly ('level' | 'tag' | 'quality')[] },
): UsePuzzleFiltersResult {
  // ── Filter counts fetch state ───────────────────────────────────
  const [distributions, setDistributions] = useState<FilterDistributions | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Reset on key change.
    setDistributions(null);
    setIsLoaded(false);
    setError(null);

    if (queryKey === null) return;

    let cancelled = false;

    void (async () => {
      try {
        await initDb();
        const filters = queryKeyToFilters(queryKey);
        const counts = getFilterCounts(filters);
        if (cancelled) return;
        setDistributions({
          level: counts.levels as unknown as Record<string, number>,
          tag: counts.tags as unknown as Record<string, number>,
          quality: counts.quality as unknown as Record<string, number>,
          content_type: counts.contentTypes as unknown as Record<string, number>,
          depth_preset: counts.depthPresets as unknown as Record<string, number>,
        });
        setIsLoaded(true);
      } catch (err: unknown) {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : 'Failed to load filter counts';
        setError(message);
        setIsLoaded(true); // loaded (with error)
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [queryKey]);

  // ── Filter options (derived from distributions) ─────────────────
  const filterOptions = useMemo<PuzzleFilterOptions>(
    () => (distributions ? buildFilterOptions(distributions) : EMPTY_FILTER_OPTIONS),
    [distributions],
  );

  // ── Canonical URL filter state ──────────────────────────────────
  const {
    filters,
    setFilters,
    clearFilters,
    hasActiveFilters,
    activeFilterCount,
    offset,
    id,
    setOffset,
    setId,
  } = useCanonicalUrl();

  // ── Convenience accessors ───────────────────────────────────────
  const levelIds: readonly number[] = useMemo(
    () => filters.l ?? [],
    [filters.l],
  );

  const tagIds: readonly number[] = useMemo(
    () => filters.t ?? [],
    [filters.t],
  );

  const selectedLevelSlug: string | null = useMemo(
    () => (levelIds.length === 1 ? levelIdToSlug(levelIds[0]!) : null),
    [levelIds],
  );

  const selectedTagSlug: string | null = useMemo(
    () => (tagIds.length === 1 ? tagIdToSlug(tagIds[0]!) : null),
    [tagIds],
  );

  const selectedTagLabel: string | null = useMemo(
    () => (selectedTagSlug ? getTagMeta(selectedTagSlug)?.name ?? null : null),
    [selectedTagSlug],
  );

  const selectedLevelLabels: readonly string[] = useMemo(
    () =>
      levelIds.map((id) => {
        const slug = levelIdToSlug(id);
        return getLevelMeta(slug)?.name ?? '';
      }),
    [levelIds],
  );

  // ── Convenience setters ─────────────────────────────────────────

  /** Toggle a level ID: add if absent, remove if present. */
  const toggleLevel = useCallback(
    (id: number): void => {
      const current = filters.l ?? [];
      const next = current.includes(id)
        ? current.filter((v) => v !== id)
        : [...current, id];
      setFilters({ l: next });
    },
    [filters.l, setFilters],
  );

  /** Replace all selected level IDs. */
  const setLevelIds = useCallback(
    (ids: number[]): void => {
      setFilters({ l: ids });
    },
    [setFilters],
  );

  /** Replace all selected tag IDs. */
  const setTagIds = useCallback(
    (ids: number[]): void => {
      setFilters({ t: ids });
    },
    [setFilters],
  );

  /** Set a single tag selection (or null to clear). */
  const setTag = useCallback(
    (id: number | null): void => {
      setFilters({ t: id === null ? [] : [id] });
    },
    [setFilters],
  );

  /**
   * Set a single tag from a FilterOption id string.
   * Pass `null` or `''` to clear the tag filter.
   */
  const setTagFromOption = useCallback(
    (id: string | null): void => {
      if (id === null || id === '') {
        setFilters({ t: [] });
        return;
      }
      const numericId = Number(id);
      if (Number.isNaN(numericId)) return;
      setFilters({ t: [numericId] });
    },
    [setFilters],
  );

  /**
   * Set a single level from a FilterOption id string.
   * Pass `null`, `''`, or `'all'` to clear the level filter.
   */
  const setLevelFromOption = useCallback(
    (id: string | null): void => {
      if (id === null || id === '' || id === 'all') {
        setFilters({ l: [] });
        return;
      }
      const numericId = Number(id);
      if (Number.isNaN(numericId)) return;
      setFilters({ l: [numericId] });
    },
    [setFilters],
  );

  // ── Depth preset accessors ──────────────────────────────────────

  const depthPreset: string | null = filters.dp ?? null;

  const setDepthPreset = useCallback(
    (id: string | null): void => {
      if (id && id !== '') {
        setFilters({ dp: id });
      } else {
        setFilters({});
      }
    },
    [setFilters],
  );

  // ── Return ──────────────────────────────────────────────────────
  return {
    isLoaded,
    error,
    filterOptions,
    filters,
    setFilters,
    clearFilters,
    hasActiveFilters,
    activeFilterCount,

    offset,
    id,
    setOffset,
    setId,

    levelIds,
    tagIds,
    selectedLevelSlug,
    selectedTagSlug,
    selectedTagLabel,
    selectedLevelLabels,

    toggleLevel,
    setLevelIds,
    setTagIds,
    setTag,
    setTagFromOption,
    setLevelFromOption,

    depthPreset,
    setDepthPreset,
  };
}
