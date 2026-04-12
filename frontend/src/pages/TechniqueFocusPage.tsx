import type { FunctionalComponent } from 'preact';
import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import { TechniqueList, type TechniqueSortOption } from '../components/TechniqueFocus';
import type { TechniqueInfo } from '../components/TechniqueFocus/TechniqueCard';
import type { TechniqueStats, TechniqueProgress } from '../models/collection';
import { PageLayout } from '../components/Layout/PageLayout';
import { FilterBar, type FilterOption } from '../components/shared/FilterBar';
import { EmptyFilterState } from '../components/shared/EmptyFilterState';
import { getTagsConfig } from '../services/tagsService';
import { ErrorState } from '../components/shared/ErrorState';
import { ChevronLeftIcon } from '../components/shared/icons';
import { TechniqueIcon } from '../components/Home/TileIcons';
import { useIsDesktop } from '../hooks/useMediaQuery';
import { getAccentPalette } from '../lib/accent-palette';
import { getOrderedTagCategories, getAllLevels } from '../services/configService';
import { useCanonicalUrl } from '../hooks/useCanonicalUrl';
import { useBrowseParams } from '../hooks/useBrowseParams';
import { useMasterIndexes } from '../hooks/useMasterIndexes';

const TECHNIQUE_PROGRESS_KEY = 'yen-go-technique-progress';

/** Accent palette — PURSIG Finding 12: shared utility */
const ACCENT = getAccentPalette('technique');

export interface TechniqueFocusPageProps {
  onNavigateBack: () => void;
  onSelectTechnique: (techniqueId: string) => void;
}

/** Category filter options for FilterBar (PURSIG Finding 10: config-driven). */
const CATEGORY_OPTIONS: readonly FilterOption[] = [
  { id: 'all', label: 'All' },
  ...getOrderedTagCategories().map((c) => ({ id: c.key, label: c.label })),
];

/** Sort options for FilterBar. */
const SORT_OPTIONS: readonly FilterOption[] = [
  { id: 'name', label: 'Name' },
  { id: 'puzzleCount', label: 'Puzzles' },
];

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

/**
 * Full-page view for browsing and selecting techniques for focused practice.
 *
 * Visual DNA inherited from HomeTile: emerald-tinted header, icon circle,
 * bold typography, stat badges, accent border divider.
 */
export const TechniqueFocusPage: FunctionalComponent<TechniqueFocusPageProps> = ({
  onNavigateBack,
  onSelectTechnique,
}) => {
  const [techniques, setTechniques] = useState<TechniqueInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { params: browseParams, setParam } = useBrowseParams({ cat: 'all', s: 'name' });
  const categoryFilter = browseParams.cat;
  const sortBy = browseParams.s;
  const [stats, setStats] = useState<Readonly<Record<string, TechniqueStats>>>({});

  // H6: Responsive breakpoint for pill collapsing
  const isDesktop = useIsDesktop();

  // P3: URL-synced filter state
  const {
    filters,
    setFilters,
    hasActiveFilters: urlHasActiveFilters,
    clearFilters,
  } = useCanonicalUrl();

  // Load level/tag master indexes from database
  const { levelMasterEntries, tagMasterEntries } = useMasterIndexes();

  // Build level filter options from config
  const allLevels = getAllLevels();

  // Bridge filter state for the existing template code
  const filterLevelIds = filters.l ?? [];
  const filterState = {
    levelIds: [...filterLevelIds],
    tagIds: [] as number[],
    setLevelIds: (ids: number[]) => setFilters({ l: ids }),
    setTagIds: (_ids: number[]) => {},
    setLevelFromOption: (id: string | null) => {
      if (id === null || id === '' || id === 'all') {
        setFilters({ l: [] });
        return;
      }
      const n = Number(id);
      if (!Number.isNaN(n)) setFilters({ l: [n] });
    },
    levelOptions: [
      { id: 'all', label: 'All' } as FilterOption,
      ...allLevels.map(
        (l) =>
          ({
            id: String(l.id),
            label: l.name,
            tooltip: `${l.name} (${l.rankRange.min}\u2013${l.rankRange.max})`,
          }) as FilterOption
      ),
    ],
    levelId: filterLevelIds.length === 1 ? filterLevelIds[0]! : null,
    hasActiveFilters: urlHasActiveFilters,
    clearAll: clearFilters,
  };

  // Load technique stats from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(TECHNIQUE_PROGRESS_KEY);
      if (stored) {
        const progress = JSON.parse(stored) as TechniqueProgress;
        setStats(progress.byTechnique);
      }
    } catch (err) {
      console.error('Error loading technique stats:', err);
    }
  }, []);

  // Load techniques from tagsService (master indexes loaded by useMasterIndexes)
  useEffect(() => {
    let cancelled = false;
    const loadTechniques = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const config = await getTagsConfig();
        if (cancelled) return;

        const techniqueList: TechniqueInfo[] = Object.values(config.tags)
          .filter((tag): tag is typeof tag & { category: 'tesuji' | 'technique' | 'objective' } =>
            ['tesuji', 'technique', 'objective'].includes(tag.category)
          )
          .map((tag) => ({
            id: tag.slug,
            name: tag.name,
            category: tag.category,
            description: tag.description,
            // Puzzle count will be derived from master indexes in filteredTechniques
            puzzleCount: 0,
          }));

        setTechniques(techniqueList);
      } catch (err) {
        if (cancelled) return;
        console.error('Error loading techniques:', err);
        setError('Failed to load techniques. Please try again.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    void loadTechniques();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelectTechnique = useCallback(
    (techniqueId: string) => {
      onSelectTechnique(techniqueId);
    },
    [onSelectTechnique]
  );

  // Build slug→tagEntry lookup for O(1) access
  const tagSlugMap = useMemo(() => {
    const map = new Map<string, (typeof tagMasterEntries)[number]>();
    for (const entry of tagMasterEntries) {
      map.set(entry.slug, entry);
    }
    return map;
  }, [tagMasterEntries]);

  // Derive puzzle counts from master indexes (unfiltered baseline)
  const puzzleCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const entry of tagMasterEntries) {
      counts[entry.slug] = entry.count;
    }
    return counts;
  }, [tagMasterEntries]);

  // WP8 §8.6: Filter technique list by selected level (reactive counts)
  const filteredTechniques = useMemo(() => {
    // Enrich techniques with puzzle counts from master indexes
    const enriched = techniques.map((tech) => ({
      ...tech,
      puzzleCount: puzzleCounts[tech.id] ?? 0,
    }));

    if (filterState.levelId === null) return enriched;

    // When a level is selected, update technique puzzle counts to show
    // only puzzles at that level (from level master index tag distributions)
    const levelEntry = levelMasterEntries.find((l) => l.id === filterState.levelId);
    if (!levelEntry) return enriched;

    return enriched
      .map((tech) => {
        // Find the tag's numeric ID from tag master entries using slug lookup
        const tagEntry = tagSlugMap.get(tech.id);
        if (!tagEntry) return { ...tech, puzzleCount: 0 };
        // Level's tag distribution tells us count for this tag at this level
        const countAtLevel = levelEntry.tags[String(tagEntry.id)] ?? 0;
        return { ...tech, puzzleCount: countAtLevel };
      })
      .filter((tech) => tech.puzzleCount > 0);
  }, [techniques, filterState.levelId, levelMasterEntries, puzzleCounts, tagSlugMap]);

  // WP8: Level filter bar options — pass through as FilterOption[]
  const levelBarOptions: FilterOption[] = [...filterState.levelOptions];

  // WP8: Handle level filter change from FilterBar (PURSIG Finding 13: internalized)
  const handleLevelFilterChange = filterState.setLevelFromOption;

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
    // Mixed selection — show as 'all' (or first matching, but 'all' is safer)
    return 'all';
  }, [filterState.levelIds]);

  // Calculate summary stats
  const summaryStats = useMemo(() => {
    const practiced = Object.values(stats);
    const totalAttempted = practiced.reduce((sum, s) => sum + s.attempted, 0);
    const totalCorrect = practiced.reduce((sum, s) => sum + s.correct, 0);
    const accuracy = totalAttempted > 0 ? Math.round((totalCorrect / totalAttempted) * 100) : 0;

    return {
      total: techniques.length,
      practiced: practiced.length,
      solved: totalAttempted,
      accuracy,
    };
  }, [techniques.length, stats]);

  return (
    <PageLayout variant="single-column" mode="technique">
      <PageLayout.Content>
        {/* Header (Layer 1) — HomeTile DNA: icon circle, bold type, stat badges */}
        <div className="px-4 pb-4 pt-4" style={{ backgroundColor: ACCENT.light }}>
          <div className="mx-auto max-w-5xl">
            {/* Back button */}
            <button
              type="button"
              onClick={onNavigateBack}
              className="mb-3 inline-flex cursor-pointer items-center gap-1 rounded-lg border-none bg-transparent px-2 py-1.5 text-sm font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-elevated)] hover:text-[var(--color-text-primary)]"
              aria-label="Go back"
            >
              <ChevronLeftIcon size={14} /> Back
            </button>

            {/* Title row: icon circle + title */}
            <div className="flex items-center gap-4">
              <div
                className="flex shrink-0 items-center justify-center rounded-full"
                style={{
                  width: '72px',
                  height: '72px',
                  backgroundColor: ACCENT.bg,
                  fontSize: '2rem',
                }}
              >
                <TechniqueIcon size="lg" />
              </div>
              <div>
                <h1
                  className="m-0 text-[var(--color-text-primary)]"
                  style={{ fontSize: '1.75rem', fontWeight: 800, lineHeight: 1.2 }}
                >
                  Technique Focus
                </h1>
                <p
                  className="m-0 mt-1 text-sm text-[var(--color-text-muted)]"
                  style={{ fontWeight: 500 }}
                >
                  Master specific Go techniques through targeted practice
                </p>
              </div>
            </div>

            {/* Stat badges — HomeTile statBadge visual treatment */}
            <div className="mt-4 flex flex-wrap gap-3" data-testid="technique-stats">
              <span
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider"
                style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
              >
                {summaryStats.total} Techniques
              </span>
              <span
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider"
                style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
              >
                {summaryStats.practiced} Practiced
              </span>
              <span
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider"
                style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
              >
                {summaryStats.solved} Solved
              </span>
              <span
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider"
                style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
              >
                {summaryStats.accuracy}% Accuracy
              </span>
            </div>
          </div>
        </div>

        {/* Filter bar — accent divider top, elevated background */}
        <div
          className="px-4 py-3"
          style={{
            backgroundColor: 'var(--color-bg-elevated)',
            borderTop: `3px solid ${ACCENT.border}`,
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          <div className="mx-auto flex max-w-5xl flex-col gap-2">
            {/* Row 1: Content type + Category + Sort */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <FilterBar
                label="Filter by category"
                options={CATEGORY_OPTIONS}
                selected={categoryFilter}
                onChange={(v) => setParam('cat', v)}
                testId="category-filter"
              />
              <FilterBar
                label="Sort by"
                options={SORT_OPTIONS}
                selected={sortBy}
                onChange={(v) => setParam('s', v)}
                testId="sort-filter"
              />
            </div>

            {/* Row 2: WP8 §8.4 + H6 — Level FilterBar (9 pills desktop, 3 category pills mobile) */}
            {levelMasterEntries.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                {isDesktop ? (
                  /* Desktop: Show all 9 level pills with horizontal scroll fallback */
                  <div className="overflow-x-auto max-w-full" data-testid="level-filter-scroll">
                    <FilterBar
                      label="Filter by level"
                      options={levelBarOptions}
                      selected={filterState.levelId !== null ? String(filterState.levelId) : 'all'}
                      onChange={handleLevelFilterChange}
                      testId="level-filter"
                    />
                  </div>
                ) : (
                  /* Mobile: Show 3 category pills (DDK/SDK/Dan) — H6 audit fix */
                  <FilterBar
                    label="Filter by level category"
                    options={MOBILE_LEVEL_CATEGORIES}
                    selected={selectedMobileCategory}
                    onChange={handleMobileCategoryChange}
                    testId="level-filter-mobile"
                  />
                )}

                {/* WP8 §8.11: Level pills are self-evident; no chip needed (F19) */}
              </div>
            )}
          </div>
        </div>

        {/* Content (Layer 2) */}
        <div className="mx-auto w-full max-w-5xl flex-1 p-4">
          {isLoading && (
            <div className="flex h-[300px] items-center justify-center text-[var(--color-text-muted)]">
              Loading techniques...
            </div>
          )}

          {error && (
            <ErrorState
              message="Couldn't load techniques"
              onRetry={() => window.location.reload()}
              onGoBack={onNavigateBack}
              details={error}
            />
          )}

          {!isLoading &&
            !error &&
            filteredTechniques.length === 0 &&
            filterState.hasActiveFilters && (
              <EmptyFilterState
                message="No techniques match your level filter"
                onClearFilters={filterState.clearAll}
                testId="technique-empty-filter"
              />
            )}

          {!isLoading &&
            !error &&
            (filteredTechniques.length > 0 || !filterState.hasActiveFilters) && (
              <TechniqueList
                techniques={filteredTechniques}
                stats={stats}
                categoryFilter={categoryFilter as 'all' | 'tesuji' | 'technique' | 'objective'}
                sortBy={sortBy as TechniqueSortOption}
                onSelectTechnique={handleSelectTechnique}
              />
            )}
        </div>
      </PageLayout.Content>
    </PageLayout>
  );
};

/**
 * Save technique stats to localStorage
 */
export function saveTechniqueStats(techniqueId: string, correct: boolean): void {
  try {
    const stored = localStorage.getItem(TECHNIQUE_PROGRESS_KEY);
    const progress: TechniqueProgress = stored
      ? (JSON.parse(stored) as TechniqueProgress)
      : { byTechnique: {}, updatedAt: new Date().toISOString() };

    const existing = progress.byTechnique[techniqueId];
    const now = new Date().toISOString();

    const updated: TechniqueStats = {
      techniqueId,
      attempted: (existing?.attempted ?? 0) + 1,
      correct: (existing?.correct ?? 0) + (correct ? 1 : 0),
      lastPracticed: now,
    };

    const newProgress: TechniqueProgress = {
      byTechnique: {
        ...progress.byTechnique,
        [techniqueId]: updated,
      },
      updatedAt: now,
    };

    localStorage.setItem(TECHNIQUE_PROGRESS_KEY, JSON.stringify(newProgress));
  } catch (err) {
    console.error('Error saving technique stats:', err);
  }
}

/**
 * Get all technique stats
 */
export function getTechniqueStats(): Readonly<Record<string, TechniqueStats>> {
  try {
    const stored = localStorage.getItem(TECHNIQUE_PROGRESS_KEY);
    if (stored) {
      const progress = JSON.parse(stored) as TechniqueProgress;
      return progress.byTechnique;
    }
  } catch (err) {
    console.error('Error loading technique stats:', err);
  }
  return {};
}

export default TechniqueFocusPage;
