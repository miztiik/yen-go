/**
 * CollectionViewPage Component
 * @module pages/CollectionViewPage
 *
 * Thin wrapper around PuzzleSetPlayer for collection-based puzzle solving.
 * Provides collection-specific header and CompactPuzzleNav navigation.
 *
 * WP8: Adds level FilterBar + tag FilterDropdown for compound AND filtering.
 * Uses collection master index for distribution counts.
 *
 * Covers: FR-008 to FR-011 (Collection browsing/navigation)
 *
 * Refactored: Spec 122 T11.7 — Migrated from 533-line monolith to thin wrapper.
 * All shared logic now lives in PuzzleSetPlayer (T11.5).
 */

import type { JSX } from 'preact';
import { useState, useEffect, useMemo, useCallback } from 'preact/hooks';
import { PuzzleSetPlayer } from '../components/PuzzleSetPlayer';
import type { HeaderInfo } from '../components/PuzzleSetPlayer';
import { PuzzleSetHeader } from '../components/PuzzleSetPlayer/PuzzleSetHeader';
import { SkipIcon } from '../components/shared/icons';
import { CollectionPuzzleLoader } from '../services/puzzleLoaders';
import { recordCollectionPuzzleCompletion, getCollectionProgress } from '../services/progress';
import { recordPlay } from '../services/streakManager';
import { formatSlug } from '../lib/slug-formatter';
import { humanizeCollectionName } from '../lib/levelRanks';
import {
  loadCollectionMasterIndex,
  ensureCollectionIdsLoaded,
  resolveCollectionDirId,
  getChaptersForCollection,
} from '../services/collectionService';
import { getEditionCollections } from '../services/puzzleQueryService';
import type { CollectionRow } from '../services/puzzleQueryService';
import { EditionPicker } from '../components/Collections/EditionPicker';
import { useIsDesktop } from '../hooks/useMediaQuery';
import { FilterBar, type FilterOption } from '../components/shared/FilterBar';
import { FilterDropdown } from '../components/shared/FilterDropdown';
import { ActiveFilterChip } from '../components/shared/ActiveFilterChip';
import { ClearAllFiltersButton } from '../components/shared/ClearAllFiltersButton';
import { EmptyFilterState } from '../components/shared/EmptyFilterState';
import { usePuzzleFilters } from '../hooks/usePuzzleFilters';
import { useContentType } from '../hooks/useContentType';
import { ContentTypeFilter } from '../components/shared/ContentTypeFilter';
import type { CollectionMasterEntry, LevelMasterEntry, TagMasterEntry } from '../types/indexes';

// ============================================================================
// Types
// ============================================================================

export interface CollectionViewPageProps {
  /** Collection ID to load */
  collectionId: string;
  /** Starting puzzle index (0-based) */
  startIndex?: number | undefined;
  /** Callback when navigating back */
  onBack?: () => void;
  /** Label for the back button (default: "Back to collections") */
  backLabel?: string | undefined;
  /** CSS class name */
  className?: string | undefined;
}

/**
 * H6 audit fix: Mobile category options collapse 9 levels into 3 categories.
 * DDK = double-digit kyu (30k-11k), SDK = single-digit kyu (10k-1k), Dan = 1d+
 */
const MOBILE_LEVEL_CATEGORIES: readonly FilterOption[] = [
  { id: 'all', label: 'All' },
  { id: 'ddk', label: 'DDK' }, // 30k-11k: novice, beginner, elementary, intermediate
  { id: 'sdk', label: 'SDK' }, // 10k-1k: upper-intermediate, advanced
  { id: 'dan', label: 'Dan' }, // 1d-9d: low-dan, high-dan, expert
];

/** Map category ID to level numeric IDs. */
const CATEGORY_TO_LEVEL_IDS: Record<string, readonly number[]> = {
  all: [], // Empty = no filter
  ddk: [110, 120, 130, 140], // novice, beginner, elementary, intermediate
  sdk: [150, 160], // upper-intermediate, advanced
  dan: [210, 220, 230], // low-dan, high-dan, expert
};

// ============================================================================
// Renderers (T030: Tailwind migration — inline styles removed)
// ============================================================================

// T12.3: Removed standalone renderCollectionHeader — now uses PuzzleSetHeader.
// T12.3: Removed renderCollectionNav — ProblemNav in sidebar provides puzzle navigation.
// Having CompactPuzzleNav here caused duplicate navigation UI.

// ============================================================================
// Component
// ============================================================================

/**
 * CollectionViewPage — Puzzle solving view for collections.
 * WP8: Adds level + tag compound filtering via master index distributions.
 * Delegates all shared logic to PuzzleSetPlayer.
 */
export function CollectionViewPage({
  collectionId,
  startIndex = 0,
  onBack,
  backLabel: backLabelProp,
  className,
}: CollectionViewPageProps): JSX.Element {
  // H6: Responsive breakpoint for pill collapsing
  const isDesktop = useIsDesktop();

  // P3: Resolve collection query key for usePuzzleFilters
  const [queryKey, setQueryKey] = useState<string | null>(null);
  const [collectionMeta, setCollectionMeta] = useState<CollectionMasterEntry | null>(null);

  // Edition detection: check if collection is a parent with edition sub-collections
  const [editionState, setEditionState] = useState<{
    isParent: boolean;
    editions: CollectionRow[];
  } | null>(null);

  // Chapter filter state
  const [chapterData, setChapterData] = useState<{
    chapters: string[];
    chapterCounts: Record<string, number>;
  }>({ chapters: [], chapterCounts: {} });
  const [selectedChapter, setSelectedChapter] = useState<string | null>(null);

  // P1-1: Load previously-completed puzzle IDs from localStorage for dot hydration
  const [completedIds, setCompletedIds] = useState<readonly string[]>([]);

  useEffect(() => {
    const result = getCollectionProgress(collectionId);
    if (result.success && result.data) {
      setCompletedIds(result.data.completed);
    }
  }, [collectionId]);

  // Load chapter data for this collection
  useEffect(() => {
    let cancelled = false;
    void getChaptersForCollection(collectionId).then((data) => {
      if (!cancelled) setChapterData(data);
    });
    return () => {
      cancelled = true;
    };
  }, [collectionId]);

  // Resolve collection slug → numeric ID → query key
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      await ensureCollectionIdsLoaded();
      const numericId = resolveCollectionDirId(collectionId);
      if (!cancelled && numericId !== undefined) {
        setQueryKey(`c${numericId}`);
        // Check for editions
        try {
          const editions = getEditionCollections(numericId);
          setEditionState({
            isParent: editions.length > 0,
            editions,
          });
        } catch {
          setEditionState({ isParent: false, editions: [] });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [collectionId]);

  // P3: Load filter options from database distributions
  const {
    isLoaded: mastersLoaded,
    filterOptions,
    levelIds: filterLevelIds,
    tagIds: filterTagIds,
    toggleLevel: filterToggleLevel,
    setLevelIds: filterSetLevelIds,
    setTag: filterSetTag,
    setTagFromOption: filterSetTagFromOption,
    selectedLevelSlug,
    selectedLevelLabels,
    selectedTagSlug,
    selectedTagLabel,
    hasActiveFilters,
    activeFilterCount,
    clearFilters,
    setOffset: urlSetOffset,
    setId: urlSetId,
  } = usePuzzleFilters(queryKey);

  // Global content-type preference
  const { contentType, setContentType } = useContentType();
  const levelMasterEntries: readonly LevelMasterEntry[] = filterOptions.levelOptions
    .filter((o) => o.id !== 'all')
    .map((o) => ({
      id: Number(o.id),
      name: o.label,
      slug: '',
      count: o.count ?? 0,
      paginated: false,
      levels: {},
      tags: {},
    }));
  const tagMasterEntries: readonly TagMasterEntry[] = filterOptions.tagOptionGroups
    .flatMap((g) => g.options)
    .map((o) => ({
      id: Number(o.id),
      name: o.label,
      slug: '',
      count: o.count ?? 0,
      paginated: false,
      levels: {},
      tags: {},
    }));

  // Build a filterState adapter for the existing template code
  const filterState = {
    levelIds: [...filterLevelIds],
    tagIds: [...filterTagIds],
    setLevelIds: filterSetLevelIds,
    setTagIds: (_ids: number[]) => {
      void _ids; /* multi-tag not used in collection view */
    },
    setTag: filterSetTag,
    setTagFromOption: filterSetTagFromOption,
    toggleLevel: filterToggleLevel,
    levelOptions: filterOptions.levelOptions as FilterOption[],
    tagOptionGroups: filterOptions.tagOptionGroups.map((g) => ({
      label: g.label,
      options: [...g.options] as FilterOption[],
    })),
    tagId: filterTagIds.length === 1 ? filterTagIds[0]! : null,
    levelId: filterLevelIds.length === 1 ? filterLevelIds[0]! : null,
    selectedLevelSlug,
    selectedLevelLabels: [...selectedLevelLabels],
    selectedTagSlug,
    selectedTagLabel,
    hasActiveFilters,
    activeFilterCount,
    clearAll: clearFilters,
  };

  // WP8 §8.8: Load collection master index on mount
  useEffect(() => {
    let cancelled = false;
    void loadCollectionMasterIndex()
      .then((collectionMaster) => {
        if (cancelled || !collectionMaster) return;
        const slug = collectionId.replace(/^level-/, '');
        const meta = collectionMaster.collections.find((c) => c.slug === slug);
        if (meta) {
          const entry: CollectionMasterEntry = {
            id: meta.id,
            name: meta.name,
            slug: meta.slug,
            paginated: (meta.pages ?? 0) > 1,
            count: meta.count,
            ...(meta.pages !== undefined ? { pages: meta.pages } : {}),
            levels: meta.levels ?? {},
            tags: meta.tags ?? {},
          };
          setCollectionMeta(entry);
        }
      })
      .catch(() => {
        /* ignore */
      });
    return () => {
      cancelled = true;
    };
  }, [collectionId]);

  // WP8: Level FilterBar options using collection-specific distributions
  const levelBarOptions = useMemo((): FilterOption[] => {
    if (!collectionMeta)
      return filterState.levelOptions.map((o) => {
        const opt: FilterOption = { id: o.id, label: o.label };
        if (o.count !== undefined) opt.count = o.count;
        return opt;
      });

    // Use collection master's level distribution for counts
    const allCount = Object.values(collectionMeta.levels).reduce((s, c) => s + c, 0);
    const options: FilterOption[] = [{ id: 'all', label: 'All', count: allCount }];

    for (const o of filterState.levelOptions) {
      if (o.id === 'all') continue;
      const count = collectionMeta.levels[o.id] ?? 0;
      options.push({ id: o.id, label: o.label, count, tooltip: o.tooltip });
    }
    return options;
  }, [filterState.levelOptions, collectionMeta]);

  // WP8: Tag dropdown groups using collection-specific distributions
  const tagDropdownGroups = useMemo(() => {
    return filterState.tagOptionGroups.map((g) => ({
      label: g.label,
      options: g.options.map((o) => {
        const count = collectionMeta ? (collectionMeta.tags[o.id] ?? 0) : (o.count ?? 0);
        return { id: o.id, label: o.label, count };
      }),
    }));
  }, [filterState.tagOptionGroups, collectionMeta]);

  // WP8: Handle filter changes — multi-select toggles for collection pages
  const handleLevelToggle = useCallback(
    (id: string) => {
      if (id === 'all') {
        filterState.setLevelIds([]);
        return;
      }
      const n = Number(id);
      if (!Number.isNaN(n)) filterState.toggleLevel(n);
    },
    [filterState]
  );
  const handleTagChange = filterState.setTagFromOption;

  // H6: Mobile category-based level filter handler
  const handleMobileCategoryChange = useCallback(
    (categoryId: string) => {
      const levelIds = CATEGORY_TO_LEVEL_IDS[categoryId] ?? [];
      filterState.setLevelIds([...levelIds]);
    },
    [filterState]
  );

  // H6: Derive currently selected mobile category from levelIds
  const selectedMobileCategory = useMemo(() => {
    const ids = filterState.levelIds;
    if (ids.length === 0) return 'all';
    // Check if all selected IDs belong to a single category
    for (const [cat, catIds] of Object.entries(CATEGORY_TO_LEVEL_IDS)) {
      if (cat === 'all') continue;
      if (ids.length === catIds.length && ids.every((id) => catIds.includes(id))) {
        return cat;
      }
    }
    // Mixed selection — show as 'all' (mixed selection not representable in categories)
    return 'all';
  }, [filterState.levelIds]);

  // Create loader (memoized, re-created when filters change — C2 fix)
  // Pass full arrays for multi-select OR-within-dimension filtering.
  // P0-NAV: Use stable filterLevelIds/filterTagIds from usePuzzleFilters (not
  // filterState spread copies which create new array refs every render).
  const loader = useMemo(
    () =>
      new CollectionPuzzleLoader(
        collectionId,
        startIndex,
        filterLevelIds,
        filterTagIds,
        contentType,
        undefined,
        selectedChapter ?? undefined
      ),
    [collectionId, filterLevelIds, filterTagIds, contentType, selectedChapter]
  );

  // Progress tracking: record collection puzzle completion + streak
  const handlePuzzleComplete = useCallback(
    (puzzleId: string, isCorrect: boolean) => {
      recordCollectionPuzzleCompletion(collectionId, puzzleId, isCorrect, 0, 0);
      if (isCorrect) {
        recordPlay();
      }
    },
    [collectionId]
  );

  // Human-readable collection name for header display
  const collectionDisplayName = useMemo(() => {
    // Use master index name if available, otherwise format from slug
    if (collectionMeta?.name) return collectionMeta.name;
    const stripped = collectionId.replace(/^level-/, '');
    return formatSlug(stripped);
  }, [collectionId, collectionMeta]);

  // Build filter strip content for PuzzleSetHeader
  const filterStripContent =
    mastersLoaded && (levelMasterEntries.length > 0 || tagMasterEntries.length > 0) ? (
      <div className="flex flex-wrap items-center gap-2" data-testid="collection-filter-strip">
        {/* Content type global filter */}
        <ContentTypeFilter
          counts={filterOptions.contentTypeOptions.reduce<Record<number, number>>((acc, o) => {
            if (o.count !== undefined) acc[Number(o.id)] = o.count;
            return acc;
          }, {})}
        />

        {/* Visual separator between content-type and level/tag filters */}
        <div className="hidden sm:block w-px h-6 self-center bg-[var(--color-border)] mx-1" />

        {/* Level FilterBar — H6: responsive categories on mobile, multi-select on desktop */}
        {levelMasterEntries.length > 0 &&
          (isDesktop ? (
            <div className="overflow-x-auto max-w-full">
              <FilterBar
                label="Filter by level"
                options={levelBarOptions}
                selected={
                  filterState.levelIds.length > 0 ? filterState.levelIds.map(String) : 'all'
                }
                onChange={handleLevelToggle}
                multiSelect
                testId="collection-level-filter"
              />
            </div>
          ) : (
            /* Mobile: Show 3 category pills (DDK/SDK/Dan) — H6 audit fix */
            <FilterBar
              label="Filter by level category"
              options={MOBILE_LEVEL_CATEGORIES}
              selected={selectedMobileCategory}
              onChange={handleMobileCategoryChange}
              testId="collection-level-filter-mobile"
            />
          ))}

        {/* Tag FilterDropdown */}
        {tagMasterEntries.length > 0 && (
          <FilterDropdown
            label="Tag"
            placeholder="All Tags"
            groups={tagDropdownGroups}
            selected={filterState.tagId !== null ? String(filterState.tagId) : null}
            onChange={handleTagChange}
            testId="collection-tag-filter"
          />
        )}

        {/* Chapter FilterDropdown — only for chaptered collections */}
        {chapterData.chapters.length > 0 && (
          <FilterDropdown
            label="Chapter"
            placeholder="All Chapters"
            groups={[
              {
                label: 'Chapters',
                options: chapterData.chapters.map((ch) => {
                  const isNumeric = /^\d+$/.test(ch);
                  const label = isNumeric ? `Chapter ${ch}` : humanizeCollectionName(ch);
                  return { id: ch, label, count: chapterData.chapterCounts[ch] ?? 0 };
                }),
              },
            ]}
            selected={selectedChapter}
            onChange={(val) => setSelectedChapter(val)}
            testId="collection-chapter-filter"
          />
        )}

        {/* Active filter chips */}
        <div className="ml-auto flex items-center gap-1.5">
          {filterState.selectedLevelLabels.map((label, i) => (
            <ActiveFilterChip
              key={`level-${filterState.levelIds[i]}`}
              label={label}
              onDismiss={() => filterState.toggleLevel(filterState.levelIds[i]!)}
              testId={`collection-level-chip-${filterState.levelIds[i]}`}
            />
          ))}
          {filterState.selectedTagSlug && (
            <ActiveFilterChip
              label={filterState.selectedTagLabel ?? filterState.selectedTagSlug}
              onDismiss={() => filterState.setTag(null)}
              testId="collection-tag-chip"
            />
          )}
          {selectedChapter && (
            <ActiveFilterChip
              label={
                /^\d+$/.test(selectedChapter)
                  ? `Chapter ${selectedChapter}`
                  : humanizeCollectionName(selectedChapter)
              }
              onDismiss={() => setSelectedChapter(null)}
              testId="collection-chapter-chip"
            />
          )}
          {filterState.activeFilterCount >= 2 && (
            <ClearAllFiltersButton onClear={filterState.clearAll} testId="collection-clear-all" />
          )}
        </div>
      </div>
    ) : undefined;

  // Chapter subtitle: show when a chapter is selected
  const chapterSubtitle = useMemo(() => {
    if (!selectedChapter) return undefined;
    const isNumeric = /^\d+$/.test(selectedChapter);
    const label = isNumeric
      ? `Chapter ${selectedChapter}`
      : humanizeCollectionName(selectedChapter);
    const count = chapterData.chapterCounts[selectedChapter];
    return count ? `${label} (${count} puzzles)` : label;
  }, [selectedChapter, chapterData.chapterCounts]);

  // Unified header using PuzzleSetHeader (Option A compact toolbar)
  const renderHeaderWithFilters = (info: HeaderInfo): JSX.Element => {
    // P1-2: Skip-to-unsolved button in header right slot
    const skipButton = info.onSkipToUnsolved ? (
      <button
        type="button"
        onClick={info.onSkipToUnsolved}
        className="flex items-center gap-1 rounded-full bg-[var(--color-bg-secondary)] px-3 py-1 text-xs font-medium text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-accent)] hover:text-white"
        aria-label="Skip to next unsolved puzzle"
        title="Skip to next unsolved puzzle"
        data-testid="skip-to-unsolved"
      >
        <SkipIcon size={14} /> Next unsolved
      </button>
    ) : undefined;

    return (
      <PuzzleSetHeader
        title={collectionDisplayName}
        {...(chapterSubtitle ? { subtitle: chapterSubtitle } : {})}
        currentIndex={info.currentIndex}
        totalPuzzles={info.totalPuzzles}
        {...(info.onBack ? { onBack: info.onBack } : {})}
        backLabel={backLabelProp ?? 'Back to collections'}
        {...(filterStripContent ? { filterStrip: filterStripContent } : {})}
        {...(skipButton ? { rightContent: skipButton } : {})}
        progress={
          info.totalPuzzles > 0 ? Math.round((info.completedCount / info.totalPuzzles) * 100) : 0
        }
        testId="collection-header"
      />
    );
  };

  // H5: Render EmptyFilterState when filters produce zero results
  const hasAnyFilter = filterState.hasActiveFilters || contentType > 0 || !!selectedChapter;

  const contentTypeInfo =
    contentType > 0
      ? (() => {
          const typeNames: Record<number, string> = {
            1: 'Curated',
            2: 'Practice',
            3: 'Training Lab',
          };
          const availableTypes = filterOptions.contentTypeOptions
            .filter(
              (opt) => opt.id !== '0' && opt.id !== String(contentType) && (opt.count ?? 0) > 0
            )
            .map((opt) => ({ name: opt.label, count: opt.count ?? 0 }));
          return {
            activeTypeName: typeNames[contentType] ?? 'selected',
            availableTypes,
            onShowAllTypes: () => setContentType(0),
          };
        })()
      : undefined;

  const handleClearAllFilters = () => {
    filterState.clearAll();
    setContentType(0);
    setSelectedChapter(null);
  };

  const renderEmptyWithFilters = hasAnyFilter
    ? () => (
        <>
          {renderHeaderWithFilters({
            name: collectionDisplayName,
            currentIndex: 0,
            totalPuzzles: 0,
            completedCount: 0,
            ...(onBack ? { onBack } : {}),
          })}
          <EmptyFilterState
            onClearFilters={handleClearAllFilters}
            testId="collection-empty-filter"
            {...(contentTypeInfo ? { contentTypeInfo } : {})}
          />
        </>
      )
    : undefined;

  // Track current puzzle index + hash in URL for deep-linking and sharing
  // P3/F3 fix: Use useCanonicalUrl setOffset/setId via usePuzzleFilters
  const handlePuzzleChange = useCallback(
    (puzzleId: string | null, index?: number) => {
      if (index === undefined) return;
      urlSetOffset(index);
      urlSetId(puzzleId ?? undefined);
    },
    [urlSetOffset, urlSetId]
  );

  // Edition detection: if this is a parent collection with editions, show EditionPicker
  if (editionState?.isParent && editionState.editions.length > 0) {
    return (
      <div {...(className ? { className } : {})}>
        <PuzzleSetHeader
          title={collectionDisplayName}
          currentIndex={0}
          totalPuzzles={0}
          {...(onBack ? { onBack } : {})}
          backLabel={backLabelProp ?? 'Back to collections'}
          testId="collection-header"
        />
        <EditionPicker
          editions={editionState.editions}
          parentName={collectionDisplayName}
          onSelect={(editionSlug: string) => {
            if (onBack) {
              // Navigate to the edition's collection page
              window.location.hash = `#/collections/${editionSlug}`;
            }
          }}
        />
      </div>
    );
  }

  return (
    <PuzzleSetPlayer
      loader={loader}
      startIndex={startIndex}
      {...(onBack ? { onBack } : {})}
      onPuzzleComplete={handlePuzzleComplete}
      onPuzzleChange={handlePuzzleChange}
      renderHeader={renderHeaderWithFilters}
      {...(renderEmptyWithFilters ? { renderEmpty: renderEmptyWithFilters } : {})}
      {...(className ? { className } : {})}
      mode="collections"
      initialCompletedIds={completedIds}
    />
  );
}

export default CollectionViewPage;
