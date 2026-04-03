/**
 * useFilterState — unified multi-dimensional filter state hook.
 * @module hooks/useFilterState
 *
 * Manages cascading level + tag filter state with cross-dimension
 * count recalculation from master index distributions.
 *
 * When a level is selected, tag counts reflect only puzzles at that level.
 * When a tag is selected, level counts reflect only puzzles with that tag.
 *
 * Spec: plan-compact-schema-filtering.md §5.3 useFilterState Hook
 */

import { useState, useMemo, useCallback } from 'preact/hooks';
import type { LevelMasterEntry, TagMasterEntry } from '@/types/indexes';
import {
  getAllLevels,
  getTagsByCategory,
  getOrderedTagCategories,
  levelIdToSlug,
  tagIdToSlug,
} from '@/services/configService';

// ============================================================================
// Types
// ============================================================================

/** Level filter option for FilterBar consumption. */
export interface LevelFilterOption {
  readonly id: string;
  readonly label: string;
  readonly count: number;
  /** Full name + rank range (e.g., "Beginner (25k–21k)"). WP8 §8.18. */
  readonly tooltip?: string | undefined;
}

/** Tag filter option for FilterDropdown consumption. */
export interface TagFilterOption {
  readonly id: string;
  readonly label: string;
  readonly count: number;
}

/** A grouped set of tag filter options. */
export interface TagFilterOptionGroup {
  readonly label: string;
  readonly options: readonly TagFilterOption[];
}

export interface UseFilterStateConfig {
  /** Level master index entries (from master index fetch). */
  readonly levelMaster: readonly LevelMasterEntry[];
  /** Tag master index entries (from master index fetch). */
  readonly tagMaster: readonly TagMasterEntry[];
}

export interface UseFilterStateReturn {
  /** Currently selected level numeric ID, or null for "All". (First of levelIds for backward compat.) */
  readonly levelId: number | null;
  /** Currently selected tag numeric ID, or null for "All". (First of tagIds for backward compat.) */
  readonly tagId: number | null;
  /** All selected level numeric IDs (empty = no filter). */
  readonly levelIds: readonly number[];
  /** All selected tag numeric IDs (empty = no filter). */
  readonly tagIds: readonly number[];
  /** Set single level filter by numeric ID (null to clear). */
  readonly setLevel: (id: number | null) => void;
  /** Set single tag filter by numeric ID (null to clear). */
  readonly setTag: (id: number | null) => void;
  /** Set multiple level IDs at once. */
  readonly setLevelIds: (ids: number[]) => void;
  /** Set multiple tag IDs at once. */
  readonly setTagIds: (ids: number[]) => void;
  /** Toggle a level ID on/off (for multi-select FilterBar). */
  readonly toggleLevel: (id: number) => void;
  /** Toggle a tag ID on/off (for multi-select FilterDropdown). */
  readonly toggleTag: (id: number) => void;
  /** Set level from FilterBar option ID ('all' → null, '130' → 130). PURSIG Finding 13. */
  readonly setLevelFromOption: (optionId: string) => void;
  /** Set tag from FilterDropdown option ID (null → null, '36' → 36). PURSIG Finding 13. */
  readonly setTagFromOption: (optionId: string | null) => void;
  /** Clear all active filters. */
  readonly clearAll: () => void;
  /** Whether any filter is currently active. */
  readonly hasActiveFilters: boolean;
  /** Number of active filter dimensions (0, 1, or 2). */
  readonly activeFilterCount: number;
  /** Level options for FilterBar (with cascading counts). */
  readonly levelOptions: readonly LevelFilterOption[];
  /** Tag options grouped by category for FilterDropdown (with cascading counts). */
  readonly tagOptionGroups: readonly TagFilterOptionGroup[];
  /** Flat tag options for simple lookup. */
  readonly tagOptions: readonly TagFilterOption[];
  /** Selected level slug (first, for display), or null. */
  readonly selectedLevelSlug: string | null;
  /** Selected tag slug (first, for display), or null. */
  readonly selectedTagSlug: string | null;
  /** All selected level slugs. */
  readonly selectedLevelSlugs: readonly string[];
  /** All selected tag slugs. */
  readonly selectedTagSlugs: readonly string[];
  /** Resolved label for selected level (from options), or null. F18. */
  readonly selectedLevelLabel: string | null;
  /** Resolved label for selected tag (from options), or null. F18. */
  readonly selectedTagLabel: string | null;
  /** All resolved labels for selected levels. */
  readonly selectedLevelLabels: readonly string[];
  /** All resolved labels for selected tags. */
  readonly selectedTagLabels: readonly string[];
}

// ============================================================================
// Hook
// ============================================================================

export function useFilterState({
  levelMaster,
  tagMaster,
}: UseFilterStateConfig): UseFilterStateReturn {
  const [levelIds, setLevelIdsRaw] = useState<number[]>([]);
  const [tagIds, setTagIdsRaw] = useState<number[]>([]);

  // ── Backward compat derived values ───────────────────────────────

  const levelId = levelIds.length > 0 ? levelIds[0]! : null;
  const tagId = tagIds.length > 0 ? tagIds[0]! : null;

  // ── Setters ──────────────────────────────────────────────────────

  const setLevel = useCallback((id: number | null) => {
    setLevelIdsRaw(id !== null ? [id] : []);
  }, []);

  const setTag = useCallback((id: number | null) => {
    setTagIdsRaw(id !== null ? [id] : []);
  }, []);

  const setLevelIds = useCallback((ids: number[]) => {
    setLevelIdsRaw(ids);
  }, []);

  const setTagIds = useCallback((ids: number[]) => {
    setTagIdsRaw(ids);
  }, []);

  const toggleLevel = useCallback((id: number) => {
    setLevelIdsRaw(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  }, []);

  const toggleTag = useCallback((id: number) => {
    setTagIdsRaw(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  }, []);

  const clearAll = useCallback(() => {
    setLevelIdsRaw([]);
    setTagIdsRaw([]);
  }, []);

  // PURSIG Finding 13: Internalize 'all'→null conversion so pages don't duplicate it
  // F12: NaN guard for non-numeric option IDs
  const setLevelFromOption = useCallback((optionId: string) => {
    if (optionId === 'all') { setLevelIdsRaw([]); return; }
    const n = Number(optionId);
    setLevelIdsRaw(Number.isNaN(n) ? [] : [n]);
  }, []);

  const setTagFromOption = useCallback((optionId: string | null) => {
    if (optionId === null) { setTagIdsRaw([]); return; }
    const n = Number(optionId);
    setTagIdsRaw(Number.isNaN(n) ? [] : [n]);
  }, []);

  const hasActiveFilters = levelIds.length > 0 || tagIds.length > 0;
  const activeFilterCount = (levelIds.length > 0 ? 1 : 0) + (tagIds.length > 0 ? 1 : 0);

  // ── Slug lookups (for display) ───────────────────────────────────

  const selectedLevelSlug = levelId !== null ? levelIdToSlug(levelId) : null;
  const selectedTagSlug = tagId !== null ? tagIdToSlug(tagId) : null;  const selectedLevelSlugs = useMemo(() => levelIds.map(id => levelIdToSlug(id)), [levelIds]);
  const selectedTagSlugs = useMemo(() => tagIds.map(id => tagIdToSlug(id)), [tagIds]);

  // ── Cascading level options ──────────────────────────────────────

  const levelOptions = useMemo((): readonly LevelFilterOption[] => {
    const levels = getAllLevels();

    // Build ID → total count map from master
    const masterCounts = new Map<number, number>();
    for (const entry of levelMaster) {
      masterCounts.set(entry.id, entry.count);
    }

    // If tags are selected, recalculate level counts from those tags' distributions
    const tagDistCounts = new Map<number, number>();
    if (tagIds.length > 0) {
      for (const tid of tagIds) {
        const tagEntry = tagMaster.find((t) => t.id === tid);
        if (tagEntry) {
          for (const [numericLevelId, count] of Object.entries(tagEntry.levels)) {
            const lid = Number(numericLevelId);
            tagDistCounts.set(lid, (tagDistCounts.get(lid) ?? 0) + count);
          }
        }
      }
    }

    // "All" shows total sum
    const allCount = tagIds.length > 0
      ? sumMapValues(tagDistCounts)
      : sumMapValues(masterCounts);

    const options: LevelFilterOption[] = [
      { id: 'all', label: 'All', count: allCount },
    ];

    for (const level of levels) {
      const count = tagIds.length > 0
        ? tagDistCounts.get(level.id) ?? 0
        : masterCounts.get(level.id) ?? 0;
      options.push({
        id: String(level.id),
        label: level.name,
        count,
        // WP8 §8.18: Full name + rank range tooltip
        tooltip: `${level.name} (${level.rankRange.min}–${level.rankRange.max})`,
      });
    }

    return options;
  }, [levelMaster, tagMaster, tagIds]);

  // ── Cascading tag options (grouped by category) ──────────────────

  const tagOptionGroups = useMemo((): readonly TagFilterOptionGroup[] => {
    // Build ID → total count map from master
    const masterCounts = new Map<number, number>();
    for (const entry of tagMaster) {
      masterCounts.set(entry.id, entry.count);
    }

    // If levels are selected, recalculate tag counts from those levels' distributions
    const levelDistCounts = new Map<number, number>();
    if (levelIds.length > 0) {
      for (const lid of levelIds) {
        const levelEntry = levelMaster.find((l) => l.id === lid);
        if (levelEntry) {
          for (const [numericTagId, count] of Object.entries(levelEntry.tags)) {
            const tid = Number(numericTagId);
            levelDistCounts.set(tid, (levelDistCounts.get(tid) ?? 0) + count);
          }
        }
      }
    }

    // PURSIG Finding 10: Categories derived from config, not hardcoded
    const categories = getOrderedTagCategories();

    const groups: TagFilterOptionGroup[] = [];

    for (const cat of categories) {
      const tagsInCategory = getTagsByCategory(cat.key);
      if (tagsInCategory.length === 0) continue;

      const options: TagFilterOption[] = tagsInCategory.map((tag) => {
        const count = levelIds.length > 0
          ? levelDistCounts.get(tag.id) ?? 0
          : masterCounts.get(tag.id) ?? 0;
        return { id: String(tag.id), label: tag.name, count };
      });

      groups.push({ label: cat.label, options });
    }

    return groups;
  }, [levelMaster, tagMaster, levelIds]);

  // ── Flat tag options (for lookup/chip display) ───────────────────

  const tagOptions = useMemo((): readonly TagFilterOption[] => {
    return tagOptionGroups.flatMap((g) => g.options);
  }, [tagOptionGroups]);

  // F18: Resolved display labels from options arrays (avoid duplicated lookup in pages)
  const selectedLevelLabel = useMemo(() => {
    if (levelId === null) return null;
    const opt = levelOptions.find(o => o.id === String(levelId));
    return opt?.label ?? selectedLevelSlug;
  }, [levelId, levelOptions, selectedLevelSlug]);

  const selectedTagLabel = useMemo(() => {
    if (tagId === null) return null;
    const opt = tagOptions.find(o => o.id === String(tagId));
    return opt?.label ?? selectedTagSlug;
  }, [tagId, tagOptions, selectedTagSlug]);

  const selectedLevelLabels = useMemo(() => {
    return levelIds.map(id => {
      const opt = levelOptions.find(o => o.id === String(id));
      return opt?.label ?? levelIdToSlug(id);
    });
  }, [levelIds, levelOptions]);

  const selectedTagLabels = useMemo(() => {
    return tagIds.map(id => {
      const opt = tagOptions.find(o => o.id === String(id));
      return opt?.label ?? tagIdToSlug(id);
    });
  }, [tagIds, tagOptions]);

  return {
    levelId,
    tagId,
    levelIds,
    tagIds,
    setLevel,
    setTag,
    setLevelIds,
    setTagIds,
    toggleLevel,
    toggleTag,
    setLevelFromOption,
    setTagFromOption,
    clearAll,
    hasActiveFilters,
    activeFilterCount,
    levelOptions,
    tagOptionGroups,
    tagOptions,
    selectedLevelSlug,
    selectedTagSlug,
    selectedLevelSlugs,
    selectedTagSlugs,
    selectedLevelLabel,
    selectedTagLabel,
    selectedLevelLabels,
    selectedTagLabels,
  };
}

// ============================================================================
// Helpers
// ============================================================================

function sumMapValues(map: Map<number, number>): number {
  let total = 0;
  for (const v of map.values()) {
    total += v;
  }
  return total;
}
