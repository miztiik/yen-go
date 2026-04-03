/**
 * CollectionsBrowsePage Component
 * @module pages/CollectionsBrowsePage
 *
 * Browse curated puzzle collections from config/collections.json.
 * Organized into category sections: Featured, Learning Paths, Techniques, Authors, Reference.
 * Search collapses sections into a flat filtered list.
 *
 * Uses only 2 HTTP fetches (config + view index) instead of ~170+.
 * Collections without published puzzles are shown grayed out ("Coming Soon").
 *
 * Reuses: PageLayout, PageHeader, PuzzleCollectionCard, EmptyState, ErrorState, useDebounce
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import type {
  CuratedCollection,
  CollectionCatalog,
  CollectionType,
  CollectionProgressSummary,
} from '@/models/collection';
import {
  loadCollectionCatalog,
  getFeaturedCollections,
  searchCollectionCatalog,
} from '@/services/collectionService';
import { searchCollectionsByTypes } from '@/services/puzzleQueryService';
import { LEVEL_SLUG_MAP } from '@/lib/levels/config';
import { getAllCollectionProgress } from '@/services/progressTracker';
import { EmptyState } from '@/components/shared/GoQuote';
import { ErrorState } from '@/components/shared/ErrorState';
import { PageLayout } from '@/components/Layout/PageLayout';
import { PuzzleCollectionCard } from '@/components/shared/PuzzleCollectionCard';
import { type MasteryLevel, getMasteryFromProgress } from '@/lib/mastery';
import { PageHeader } from '@/components/shared/PageHeader';
import { BookIcon, SearchIcon } from '@/components/shared/icons';
import { useDebounce } from '@/hooks/useDebounce';
import { useBrowseParams } from '@/hooks/useBrowseParams';

export interface CollectionsBrowsePageProps {
  /** Handler when user navigates to a collection */
  onNavigateToCollection: (collectionId: string) => void;
  /** Handler to go back home */
  onNavigateHome: () => void;
}

// ============================================================================
// Section Configuration
// ============================================================================

/** Section definition for category-based layout */
interface CollectionSection {
  id: string;
  title: string;
  subtitle: string;
  /** Single type or array of types to merge into one section */
  types: CollectionType[];
  /** Max items to show initially (0 = show all) */
  initialLimit: number;
}

/** Tier rank for sorting books (lower = higher priority) */
const TIER_RANK: Record<string, number> = {
  editorial: 0,
  premier: 1,
  curated: 2,
  community: 3,
};

/** Minimum puzzle count for a collection to be visible */
const MIN_PUZZLE_COUNT = 15;

/** Minimum visible collections for a section to render */
const MIN_SECTION_COLLECTIONS = 2;

const SECTIONS: CollectionSection[] = [
  {
    id: 'learning-paths',
    title: 'Learning Paths',
    subtitle: 'Structured progression from beginner to expert',
    types: ['graded'],
    initialLimit: 0,
  },
  {
    id: 'practice',
    title: 'Practice',
    subtitle: 'Master specific Go techniques and patterns',
    types: ['technique', 'reference'],
    initialLimit: 6,
  },
  {
    id: 'books',
    title: 'Books',
    subtitle: 'Collections from renowned Go masters and teachers',
    types: ['author'],
    initialLimit: 6,
  },
];

// ============================================================================
// Helpers
// ============================================================================

/**
 * Calculate mastery level from progress data using accuracy-based calculation.
 */
function getLocalMastery(
  progress: CollectionProgressSummary | undefined,
): MasteryLevel {
  if (!progress) return 'new';
  return getMasteryFromProgress({
    completed: progress.completedCount,
    total: progress.totalPuzzles,
  });
}

/**
 * Gather collections for a section from the catalog, merging multiple types.
 */
function getCollectionsForSection(
  catalog: CollectionCatalog,
  section: CollectionSection,
): CuratedCollection[] {
  const result: CuratedCollection[] = [];
  for (const t of section.types) {
    const items = catalog.byType[t];
    if (items) result.push(...items);
  }
  return result;
}

/**
 * Filter out collections with puzzleCount < MIN_PUZZLE_COUNT (when they have data).
 * Collections without data (coming soon) are also hidden — they can't meet the threshold.
 */
function applyMinPuzzleFilter(
  collections: readonly CuratedCollection[],
): CuratedCollection[] {
  return collections.filter(
    (c) => c.hasData && c.puzzleCount >= MIN_PUZZLE_COUNT,
  );
}

/**
 * Sort graded (Learning Paths) collections by difficulty level.
 * Uses level_hint → numeric ID from puzzle-levels.json.
 */
function sortByDifficulty(collections: CuratedCollection[]): CuratedCollection[] {
  return [...collections].sort((a, b) => {
    const aId = a.levelHint ? (LEVEL_SLUG_MAP.get(a.levelHint as never) ?? 999) : 999;
    const bId = b.levelHint ? (LEVEL_SLUG_MAP.get(b.levelHint as never) ?? 999) : 999;
    return aId - bId;
  });
}

/**
 * Sort books (author) by tier rank → puzzle_count desc → name alpha.
 */
function sortByTierAndCount(collections: CuratedCollection[]): CuratedCollection[] {
  return [...collections].sort((a, b) => {
    const tierDiff = (TIER_RANK[a.tier] ?? 3) - (TIER_RANK[b.tier] ?? 3);
    if (tierDiff !== 0) return tierDiff;
    const countDiff = b.puzzleCount - a.puzzleCount;
    if (countDiff !== 0) return countDiff;
    return a.name.localeCompare(b.name);
  });
}

/**
 * Apply section-specific sorting and filtering.
 */
function prepareSectionCollections(
  catalog: CollectionCatalog,
  section: CollectionSection,
): CuratedCollection[] {
  const raw = getCollectionsForSection(catalog, section);
  const filtered = applyMinPuzzleFilter(raw);

  if (section.id === 'learning-paths') return sortByDifficulty(filtered);
  if (section.id === 'books') return sortByTierAndCount(filtered);
  return filtered;
}

// ============================================================================
// Sub-components
// ============================================================================

/** Render a single collection card */
function CollectionCard({
  collection,
  progress,
  onClick,
}: {
  collection: CuratedCollection;
  progress: CollectionProgressSummary | undefined;
  onClick: () => void;
}): JSX.Element {
  // Build optional props conditionally to satisfy exactOptionalPropertyTypes
  const optionalProps: {
    tags?: readonly string[];
    progress?: { completed: number; total: number };
    mastery?: MasteryLevel;
  } = {};

  if (collection.hasData) {
    const puzzleLabel = `${collection.puzzleCount} puzzles`;
    if (collection.chapterCount > 0) {
      const chapterLabel = collection.hasNamedChapters
        ? `${collection.chapterCount} techniques`
        : `${collection.chapterCount} chapters`;
      optionalProps.tags = [puzzleLabel, chapterLabel];
    } else {
      optionalProps.tags = [puzzleLabel];
    }
    optionalProps.mastery = getLocalMastery(progress);
    optionalProps.progress = progress
      ? { completed: progress.completedCount, total: progress.totalPuzzles }
      : { completed: 0, total: collection.puzzleCount };
  }

  return (
    <div role="listitem">
      <PuzzleCollectionCard
        title={collection.name}
        subtitle={collection.curator !== 'Curated' && collection.curator !== 'Community' && collection.curator !== 'System'
          ? `by ${collection.curator}`
          : collection.description.length > 80
            ? collection.description.slice(0, 77) + '...'
            : collection.description}
        {...optionalProps}
        onClick={onClick}
        disabled={!collection.hasData}
        testId={`collection-${collection.slug}`}
      />
    </div>
  );
}

/** Render a section of collections by type */
function CollectionTypeSection({
  section,
  collections,
  progressMap,
  onCollectionClick,
}: {
  section: CollectionSection;
  collections: readonly CuratedCollection[];
  progressMap: Record<string, CollectionProgressSummary>;
  onCollectionClick: (slug: string) => void;
}): JSX.Element | null {
  const [expanded, setExpanded] = useState(false);
  const [sectionSearch, setSectionSearch] = useState('');
  const debouncedSectionSearch = useDebounce(sectionSearch, 250);

  // Section search: filter via DB FTS when search is active
  const filteredCollections = useMemo(() => {
    if (!debouncedSectionSearch.trim()) return collections;
    try {
      const dbResults = searchCollectionsByTypes(debouncedSectionSearch, section.types);
      const slugSet = new Set(dbResults.map((r) => r.slug));
      return collections.filter((c) => slugSet.has(c.slug));
    } catch {
      // Fallback to client-side filter if DB unavailable
      const lower = debouncedSectionSearch.toLowerCase();
      return collections.filter(
        (c) =>
          c.name.toLowerCase().includes(lower) ||
          c.description.toLowerCase().includes(lower) ||
          c.curator.toLowerCase().includes(lower),
      );
    }
  }, [collections, debouncedSectionSearch, section.types]);

  if (collections.length < MIN_SECTION_COLLECTIONS) return null;

  const limit = section.initialLimit;
  const isSearching = debouncedSectionSearch.trim().length > 0;
  const displayItems = isSearching
    ? filteredCollections
    : limit > 0 && !expanded
      ? filteredCollections.slice(0, limit)
      : filteredCollections;
  const hasMore = !isSearching && limit > 0 && filteredCollections.length > limit;

  return (
    <section className="mb-8" data-testid={`section-${section.id}`}>
      {/* Header row: title + count + search + show all */}
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h2 className="m-0 text-lg font-semibold text-[var(--color-text-primary)]">
            {section.title}
            <span className="ml-2 text-sm font-normal text-[var(--color-text-muted)]">
              ({filteredCollections.length})
            </span>
          </h2>
          <p className="m-0 mt-0.5 text-sm text-[var(--color-text-muted)]">
            {section.subtitle}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {/* In-section search */}
          <div className="relative">
            <SearchIcon
              size={14}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
            />
            <input
              type="search"
              value={sectionSearch}
              onInput={(e) => setSectionSearch((e.target as HTMLInputElement).value)}
              placeholder="Filter..."
              className="min-h-[36px] w-40 rounded-full border bg-[var(--color-bg-panel)] py-1.5 pl-8 pr-3 text-xs text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] outline-none transition-colors focus:ring-2 focus:ring-[var(--color-accent)]"
              style={{ borderColor: 'var(--color-border)' }}
              aria-label={`Filter ${section.title}`}
              data-testid={`section-search-${section.id}`}
            />
          </div>
          {/* Show all / Show less toggle */}
          {hasMore && (
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="cursor-pointer whitespace-nowrap rounded-full border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-secondary)]"
              data-testid={expanded ? `show-less-${section.id}` : `show-all-${section.id}`}
            >
              {expanded ? 'Show less' : `Show all ${filteredCollections.length}`}
            </button>
          )}
          {!hasMore && expanded && (
            <button
              type="button"
              onClick={() => setExpanded(false)}
              className="cursor-pointer whitespace-nowrap rounded-full border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-secondary)]"
              data-testid={`show-less-${section.id}`}
            >
              Show less
            </button>
          )}
        </div>
      </div>
      <div
        className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
        role="list"
        aria-label={section.title}
      >
        {displayItems.map((c) => (
            <CollectionCard
              key={c.slug}
              collection={c}
              progress={progressMap[c.slug]}
              onClick={() => onCollectionClick(c.slug)}
            />
        ))}
      </div>
      {isSearching && filteredCollections.length === 0 && (
        <p className="mt-3 text-sm text-[var(--color-text-muted)]">
          No collections match &ldquo;{debouncedSectionSearch}&rdquo;
        </p>
      )}
    </section>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Collections browsing page — curated catalog with category sections.
 */
export function CollectionsBrowsePage({
  onNavigateToCollection,
  onNavigateHome,
}: CollectionsBrowsePageProps): JSX.Element {
  const [catalog, setCatalog] = useState<CollectionCatalog | null>(null);
  const [featured, setFeatured] = useState<CuratedCollection[]>([]);
  const [progressMap, setProgressMap] = useState<Record<string, CollectionProgressSummary>>({});
  const { params: browseParams, setParam } = useBrowseParams({ q: '' });
  const searchTerm = browseParams.q;
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const debouncedSearch = useDebounce(searchTerm, 250);

  // Load catalog on mount
  useEffect(() => {
    const loadData = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await loadCollectionCatalog();
        if (!result.success || !result.data) {
          setError(result.message ?? 'Failed to load collections');
          setIsLoading(false);
          return;
        }

        setCatalog(result.data);
        setFeatured(getFeaturedCollections(result.data));

        // Load progress
        const progressResult = getAllCollectionProgress();
        if (progressResult.success && progressResult.data) {
          const map: Record<string, CollectionProgressSummary> = {};
          for (const p of progressResult.data) {
            map[p.collectionId] = p;
          }
          setProgressMap(map);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    };

    void loadData();
  }, []);

  // Search results
  const searchResults = useMemo(() => {
    if (!catalog || !debouncedSearch.trim()) return null;
    return searchCollectionCatalog(catalog, debouncedSearch);
  }, [catalog, debouncedSearch]);

  // Handle collection click
  const handleCollectionClick = useCallback(
    (slug: string) => {
      onNavigateToCollection(slug);
    },
    [onNavigateToCollection],
  );

  // Stats
  const totalCount = catalog?.collections.length ?? 0;
  const availableCount = catalog?.collections.filter((c) => c.hasData).length ?? 0;

  const ACCENT = {
    text: 'var(--color-accent, var(--color-mode-collections-text))',
    light: 'var(--color-accent-light, var(--color-mode-collections-light))',
    bg: 'var(--color-accent-bg, var(--color-mode-collections-bg))',
    border: 'var(--color-accent-border, var(--color-mode-collections-border))',
  } as const;

  const statsData = useMemo(() => {
    const items = [{ label: 'Collections', value: totalCount }];
    if (availableCount > 0) items.push({ label: 'Available', value: availableCount });
    return items;
  }, [totalCount, availableCount]);

  const isSearching = debouncedSearch.trim().length > 0;

  return (
    <PageLayout variant="single-column" mode="collections">
      <PageLayout.Content>
        {/* Header */}
        <PageHeader
          title="Collections"
          subtitle="Curated puzzle collections from Go masters and techniques"
          icon={<BookIcon size={36} />}
          stats={statsData}
          onBack={onNavigateHome}
          accent={ACCENT}
          testId="collections-header"
        />

        {/* Search bar */}
        <div
          className="px-4 py-3"
          style={{
            backgroundColor: 'var(--color-bg-elevated)',
            borderTop: `3px solid ${ACCENT.border}`,
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          <div className="mx-auto flex max-w-5xl items-center justify-center gap-3">
            <div className="relative w-full sm:w-96">
              <SearchIcon
                size={16}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]"
              />
              <input
                type="search"
                value={searchTerm}
                onInput={(e) => setParam('q', (e.target as HTMLInputElement).value)}
                placeholder="Search all collections by name, author, or topic..."
                className="min-h-[44px] w-full rounded-full border bg-[var(--color-bg-panel)] py-2 pl-9 pr-9 text-sm text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] outline-none transition-colors focus:ring-2 focus:ring-[var(--color-accent)]"
                style={{ borderColor: 'var(--color-border)' }}
                aria-label="Search collections by name, author, or topic"
                data-testid="collections-search"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setParam('q', '')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer border-none bg-transparent p-0 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                  aria-label="Clear search"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="mx-auto w-full max-w-5xl flex-1 p-4">
          {error ? (
            <ErrorState
              message="Couldn't load collections"
              onRetry={() => window.location.reload()}
              details={error}
            />
          ) : isLoading ? (
            <div className="flex items-center justify-center py-12 text-[var(--color-text-muted)]">
              Loading collections...
            </div>
          ) : isSearching ? (
            /* Search results — flat list */
            searchResults && searchResults.length > 0 ? (
              <div>
                <p className="mb-4 text-sm text-[var(--color-text-muted)]">
                  {searchResults.length} collection{searchResults.length !== 1 ? 's' : ''} matching &ldquo;{debouncedSearch}&rdquo;
                </p>
                <div
                  className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
                  role="list"
                  aria-label="Search results"
                >
                  {searchResults.map((c) => (
                    <CollectionCard
                      key={c.slug}
                      collection={c}
                      progress={progressMap[c.slug]}
                      onClick={() => handleCollectionClick(c.slug)}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState
                message={`No collections found for "${debouncedSearch}"`}
                quoteMode="daily"
              />
            )
          ) : (
            /* Category sections */
            <div>
              {/* Featured section */}
              {featured.length > 0 && (
                <section className="mb-8" data-testid="section-featured">
                  <div className="mb-3">
                    <h2 className="m-0 text-lg font-semibold text-[var(--color-text-primary)]">
                      Featured
                      <span className="ml-2 text-sm font-normal text-[var(--color-text-muted)]">
                        ({featured.length})
                      </span>
                    </h2>
                    <p className="m-0 mt-0.5 text-sm text-[var(--color-text-muted)]">
                      Hand-picked editorial collections
                    </p>
                  </div>
                  <div
                    className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
                    role="list"
                    aria-label="Featured collections"
                  >
                    {featured.map((c) => (
                      <CollectionCard
                        key={c.slug}
                        collection={c}
                        progress={progressMap[c.slug]}
                        onClick={() => handleCollectionClick(c.slug)}
                      />
                    ))}
                  </div>
                </section>
              )}

              {/* Type-based sections */}
              {catalog && SECTIONS.map((section) => (
                <CollectionTypeSection
                  key={section.id}
                  section={section}
                  collections={prepareSectionCollections(catalog, section)}
                  progressMap={progressMap}
                  onCollectionClick={handleCollectionClick}
                />
              ))}
            </div>
          )}
        </div>
      </PageLayout.Content>
    </PageLayout>
  );
}

export default CollectionsBrowsePage;