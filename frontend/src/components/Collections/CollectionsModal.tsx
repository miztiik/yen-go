/**
 * CollectionsModal Component
 * @module components/Collections/CollectionsModal
 *
 * Modal for browsing and selecting collections.
 * Shows collection list with progress, opens from home tile.
 *
 * Covers: FR-001, FR-002, FR-003
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { Modal } from '@/components/shared/Modal';
import { CollectionList } from './CollectionList';
import { CollectionFilter } from './CollectionFilter';
import type {
  CollectionSummary,
  CollectionFilter as FilterType,
  CollectionProgressSummary,
} from '@/models/collection';
import { loadCollectionIndex, getFilteredCollections } from '@/services/collectionService';
import { getAllCollectionProgress } from '@/services/progressTracker';
import { EmptyState } from '@/components/shared/GoQuote';

export interface CollectionsModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Handler to close the modal */
  onClose: () => void;
  /** Handler when a collection is selected */
  onSelectCollection: (collection: CollectionSummary) => void;
}

/**
 * Modal for browsing collections
 */
export function CollectionsModal({
  isOpen,
  onClose,
  onSelectCollection,
}: CollectionsModalProps): JSX.Element {
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [progressMap, setProgressMap] = useState<Record<string, CollectionProgressSummary>>({});
  const [filter, setFilter] = useState<FilterType>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load collections on mount
  useEffect(() => {
    if (!isOpen) return;

    const loadData = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        // Load collections
        const indexResult = await loadCollectionIndex();
        if (!indexResult.success || !indexResult.data) {
          setError(indexResult.message ?? 'Failed to load collections');
          setIsLoading(false);
          return;
        }

        setCollections(indexResult.data.collections as CollectionSummary[]);

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
  }, [isOpen]);

  // Filter collections
  const handleFilterChange = useCallback(async (newFilter: FilterType) => {
    setFilter(newFilter);
    setIsLoading(true);

    try {
      const result = await getFilteredCollections(newFilter);
      if (result.success && result.data) {
        setCollections(result.data);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle collection click
  const handleCollectionClick = useCallback((collection: CollectionSummary) => {
    onSelectCollection(collection);
  }, [onSelectCollection]);

  const contentStyle: JSX.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    minHeight: '400px',
    maxHeight: '70vh',
    overflow: 'hidden',
  };

  const listContainerStyle: JSX.CSSProperties = {
    flex: 1,
    overflowY: 'auto',
    paddingBottom: '1rem',
  };

  const footerStyle: JSX.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.5rem 0',
    fontSize: '0.75rem',
    color: 'var(--color-neutral-500)',
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Browse Collections"
      size="lg"
    >
      <div style={contentStyle}>
        <CollectionFilter
          filter={filter}
          onFilterChange={(f) => { void handleFilterChange(f); }}
        />

        <div style={listContainerStyle}>
          {error ? (
            <EmptyState
              message={error}
              action={{ label: 'Try Again', onClick: () => window.location.reload() }}
            />
          ) : (
            <CollectionList
              collections={collections}
              progressMap={progressMap}
              onCollectionClick={handleCollectionClick}
              isLoading={isLoading}
              emptyMessage="No collections match your filters"
            />
          )}
        </div>

        <div style={footerStyle}>
          <span>{collections.length} collections</span>
          {Object.keys(progressMap).length > 0 && (
            <span>
              {Object.values(progressMap).filter(p => p.status === 'completed').length} completed
            </span>
          )}
        </div>
      </div>
    </Modal>
  );
}

export default CollectionsModal;
