/**
 * CollectionsPage Component
 * @module pages/CollectionsPage
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

export interface CollectionsPageProps {
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
  type: CollectionType;
  /** Max items to show initially (0 = show all) */
  initialLimit: number;
}

const SECTIONS: CollectionSection[] = [
  {
    id: 'learning-paths',
    title: 'Learning Paths',
    subtitle: 'Structured progression from beginner to expert',
    type: 'graded',
    initialLimit: 0, // Show all ~9 graded collections
  },
  {
    id: 'techniques',
    title: 'By Technique',
    subtitle: 'Master specific Go techniques and patterns',
    type: 'technique',
    initialLimit: 6,
  },
  {
    id: 'authors',
    title: 'By Author',
    subtitle: 'Collections from renowned Go masters and teachers',
    type: 'author',
    initialLimit: 6,
  },
  {
    id: 'reference',
    title: 'Reference Collections',
    subtitle: 'Comprehensive problem sets and study material',
    type: 'reference',
    initialLimit: 6,
  },
];

// ============================================================================
// Helpers
// ============================================================================

/**
 * Calculate mastery level from progress data using accuracy-based calculation.
 */
function getLocalMastery(progress: CollectionProgressSummary | undefined): MasteryLevel {
  if (!progress) return 'new';
  // CollectionProgressSummary doesn't have accuracy field yet,
  // so we pass completed/total and let getMasteryFromProgress use default 100%
  return getMasteryFromProgress({
    completed: progress.completedCount,
    total: progress.totalPuzzles,
  });
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
    optionalProps.tags = [`${collection.puzzleCount} puzzles`];
    optionalProps.mastery = getLocalMastery(progress);
    optionalProps.progress = progress
      ? { completed: progress.completedCount, total: progress.totalPuzzles }
      : { completed: 0, total: collection.puzzleCount };
  }

  return (
    <div role="listitem">
      <PuzzleCollectionCard
        title={collection.name}
        subtitle={
          collection.curator !== 'Curated' &&
          collection.curator !== 'Community' &&
          collection.curator !== 'System'
            ? `by ${collection.curator}`
            : collection.description.length > 80
              ? collection.description.slice(0, 77) + '...'
              : collection.description
        }
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

  if (collections.length === 0) return null;

  const limit = section.initialLimit;
  const displayItems = limit > 0 && !expanded ? collections.slice(0, limit) : collections;
  const hasMore = limit > 0 && collections.length > limit;

  return (
    <section className="mb-8" data-testid={`section-${section.id}`}>
      <div className="mb-3">
        <h2 className="m-0 text-lg font-semibold text-[var(--color-text-primary)]">
          {section.title}
          <span className="ml-2 text-sm font-normal text-[var(--color-text-muted)]">
            ({collections.length})
          </span>
        </h2>
        <p className="m-0 mt-0.5 text-sm text-[var(--color-text-muted)]">{section.subtitle}</p>
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
      {hasMore && !expanded && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="mt-3 cursor-pointer rounded-full border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-4 py-2 text-sm text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-secondary)]"
          data-testid={`show-all-${section.id}`}
        >
          Show all {collections.length} collections
        </button>
      )}
      {hasMore && expanded && (
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="mt-3 cursor-pointer rounded-full border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-4 py-2 text-sm text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-secondary)]"
        >
          Show less
        </button>
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
export function CollectionsPage({
  onNavigateToCollection,
  onNavigateHome,
}: CollectionsPageProps): JSX.Element {
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
    [onNavigateToCollection]
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
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    aria-hidden="true"
                  >
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
                  {searchResults.length} collection{searchResults.length !== 1 ? 's' : ''} matching
                  &ldquo;{debouncedSearch}&rdquo;
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
              {SECTIONS.map((section) => (
                <CollectionTypeSection
                  key={section.id}
                  section={section}
                  collections={catalog?.byType[section.type] ?? []}
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

export default CollectionsPage;
