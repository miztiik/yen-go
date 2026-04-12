/**
 * MyCollectionsPage
 * @module pages/MyCollectionsPage
 *
 * Dashboard showing user's collection progress in categories:
 * Completed, In Progress, Not Started.
 *
 * Covers: T033, T034, T035 - User Story 4 (Progress Overview)
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import { CollectionProgressSummary } from '@/components/Progress/CollectionProgressSummary';
import type {
  CollectionSummary,
  CollectionProgressSummary as ProgressSummaryType,
  CollectionStatus,
} from '@/models/collection';
import { loadCollectionIndex } from '@/services/collectionService';
import { getAllCollectionProgress } from '@/services/progressTracker';
import { EmptyState } from '@/components/shared/GoQuote';
import { ChevronLeftIcon } from '@/components/shared/icons';

// ============================================================================
// Types
// ============================================================================

export interface MyCollectionsPageProps {
  /** Handler when a collection is selected */
  onSelectCollection: (collectionId: string) => void;
  /** Handler to navigate back */
  onBack?: () => void;
  /** Custom className */
  className?: string | undefined;
}

interface CollectionWithProgress {
  collection: CollectionSummary;
  progress: ProgressSummaryType;
}

// ============================================================================
// Styles
// ============================================================================

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: 'var(--color-neutral-50)',
    padding: '1.5rem',
  } as JSX.CSSProperties,

  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    marginBottom: '2rem',
  } as JSX.CSSProperties,

  backButton: {
    padding: '0.5rem',
    backgroundColor: 'white',
    border: '1px solid var(--color-neutral-200)',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '1.25rem',
    lineHeight: 1,
  } as JSX.CSSProperties,

  title: {
    fontSize: '1.75rem',
    fontWeight: 700,
    color: 'var(--color-neutral-800)',
    margin: 0,
  } as JSX.CSSProperties,

  statsRow: {
    display: 'flex',
    gap: '1rem',
    marginBottom: '2rem',
    flexWrap: 'wrap',
  } as JSX.CSSProperties,

  statCard: {
    flex: '1 1 140px',
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '1rem',
    textAlign: 'center',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  } as JSX.CSSProperties,

  statNumber: {
    fontSize: '2rem',
    fontWeight: 700,
    color: 'var(--color-neutral-800)',
  } as JSX.CSSProperties,

  statLabel: {
    fontSize: '0.8125rem',
    color: 'var(--color-neutral-500)',
    marginTop: '0.25rem',
  } as JSX.CSSProperties,

  section: {
    marginBottom: '2rem',
  } as JSX.CSSProperties,

  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '1rem',
  } as JSX.CSSProperties,

  sectionTitle: {
    fontSize: '1.125rem',
    fontWeight: 600,
    color: 'var(--color-text-secondary)',
    margin: 0,
  } as JSX.CSSProperties,

  sectionCount: {
    fontSize: '0.8125rem',
    color: 'var(--color-neutral-400)',
    backgroundColor: 'var(--color-neutral-100)',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
  } as JSX.CSSProperties,

  collectionList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  } as JSX.CSSProperties,

  loading: {
    textAlign: 'center',
    padding: '3rem',
    color: 'var(--color-neutral-500)',
  } as JSX.CSSProperties,
};

// ============================================================================
// Helper Functions
// ============================================================================

function getStatus(completed: number, total: number): CollectionStatus {
  if (completed === 0) return 'not-started';
  if (completed >= total) return 'completed';
  return 'in-progress';
}

// ============================================================================
// Component
// ============================================================================

/**
 * MyCollectionsPage - User's collection progress dashboard
 */
export function MyCollectionsPage({
  onSelectCollection,
  onBack,
  className = '',
}: MyCollectionsPageProps): JSX.Element {
  const [collections, setCollections] = useState<CollectionWithProgress[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load collections and progress
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        // Load collection index
        const indexResult = await loadCollectionIndex();
        if (!indexResult.success || !indexResult.data) {
          setCollections([]);
          return;
        }

        // Load all progress
        const progressResult = getAllCollectionProgress();
        const progressMap = new Map<string, ProgressSummaryType>();

        if (progressResult.success && progressResult.data) {
          for (const p of progressResult.data) {
            progressMap.set(p.collectionId, p);
          }
        }

        // Combine collections with progress
        const combined: CollectionWithProgress[] = indexResult.data.collections.map(
          (collection) => {
            const existingProgress = progressMap.get(collection.id);
            const completedCount = existingProgress?.completedCount ?? 0;
            const totalPuzzles = collection.puzzleCount;
            const status = getStatus(completedCount, totalPuzzles);
            const percentComplete =
              totalPuzzles > 0 ? Math.round((completedCount / totalPuzzles) * 100) : 0;

            const progress: ProgressSummaryType =
              existingProgress?.lastActivity !== undefined
                ? {
                    collectionId: collection.id,
                    status,
                    completedCount,
                    totalPuzzles,
                    percentComplete,
                    lastActivity: existingProgress.lastActivity,
                  }
                : {
                    collectionId: collection.id,
                    status,
                    completedCount,
                    totalPuzzles,
                    percentComplete,
                  };

            return { collection, progress };
          }
        );

        setCollections(combined);
      } catch (error) {
        console.error('Failed to load collections:', error);
        setCollections([]);
      } finally {
        setIsLoading(false);
      }
    };

    void loadData();
  }, []);

  // Group by status
  const { completed, inProgress, notStarted, stats } = useMemo(() => {
    const completed: CollectionWithProgress[] = [];
    const inProgress: CollectionWithProgress[] = [];
    const notStarted: CollectionWithProgress[] = [];

    let totalPuzzles = 0;
    let completedPuzzles = 0;

    for (const item of collections) {
      totalPuzzles += item.collection.puzzleCount;
      completedPuzzles += item.progress.completedCount;

      switch (item.progress.status) {
        case 'completed':
          completed.push(item);
          break;
        case 'in-progress':
          inProgress.push(item);
          break;
        case 'not-started':
          notStarted.push(item);
          break;
      }
    }

    // Sort in-progress by last activity (most recent first)
    inProgress.sort((a, b) => {
      const aDate = a.progress.lastActivity ?? '';
      const bDate = b.progress.lastActivity ?? '';
      return bDate.localeCompare(aDate);
    });

    return {
      completed,
      inProgress,
      notStarted,
      stats: {
        totalCollections: collections.length,
        completedCollections: completed.length,
        totalPuzzles,
        completedPuzzles,
      },
    };
  }, [collections]);

  const handleCollectionClick = useCallback(
    (collectionId: string) => {
      onSelectCollection(collectionId);
    },
    [onSelectCollection]
  );

  if (isLoading) {
    return (
      <div style={styles.container} class={className}>
        <div style={styles.loading}>Loading collections...</div>
      </div>
    );
  }

  if (collections.length === 0) {
    return (
      <div style={styles.container} class={className}>
        <div style={styles.header}>
          {onBack && (
            <button type="button" style={styles.backButton} onClick={onBack} aria-label="Go back">
              <ChevronLeftIcon size={18} />
            </button>
          )}
          <h1 style={styles.title}>My Collections</h1>
        </div>
        <EmptyState message="No collections available yet" />
      </div>
    );
  }

  const overallPercent =
    stats.totalPuzzles > 0 ? Math.round((stats.completedPuzzles / stats.totalPuzzles) * 100) : 0;

  return (
    <div style={styles.container} class={`my-collections-page ${className}`}>
      {/* Header */}
      <div style={styles.header}>
        {onBack && (
          <button type="button" style={styles.backButton} onClick={onBack} aria-label="Go back">
            <ChevronLeftIcon size={18} />
          </button>
        )}
        <h1 style={styles.title}>My Collections</h1>
      </div>

      {/* Stats Overview */}
      <div style={styles.statsRow}>
        <div style={styles.statCard}>
          <div style={styles.statNumber}>{stats.completedCollections}</div>
          <div style={styles.statLabel}>Completed</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statNumber}>{inProgress.length}</div>
          <div style={styles.statLabel}>In Progress</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statNumber}>{stats.completedPuzzles}</div>
          <div style={styles.statLabel}>Puzzles Solved</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statNumber}>{overallPercent}%</div>
          <div style={styles.statLabel}>Overall Progress</div>
        </div>
      </div>

      {/* In Progress Section */}
      {inProgress.length > 0 && (
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>In Progress</h2>
            <span style={styles.sectionCount}>{inProgress.length}</span>
          </div>
          <div style={styles.collectionList}>
            {inProgress.map((item) => (
              <CollectionProgressSummary
                key={item.collection.id}
                name={item.collection.name}
                progress={item.progress}
                onClick={() => handleCollectionClick(item.collection.id)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Completed Section */}
      {completed.length > 0 && (
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>Completed</h2>
            <span style={styles.sectionCount}>{completed.length}</span>
          </div>
          <div style={styles.collectionList}>
            {completed.map((item) => (
              <CollectionProgressSummary
                key={item.collection.id}
                name={item.collection.name}
                progress={item.progress}
                onClick={() => handleCollectionClick(item.collection.id)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Not Started Section */}
      {notStarted.length > 0 && (
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>Not Started</h2>
            <span style={styles.sectionCount}>{notStarted.length}</span>
          </div>
          <div style={styles.collectionList}>
            {notStarted.map((item) => (
              <CollectionProgressSummary
                key={item.collection.id}
                name={item.collection.name}
                progress={item.progress}
                onClick={() => handleCollectionClick(item.collection.id)}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default MyCollectionsPage;
