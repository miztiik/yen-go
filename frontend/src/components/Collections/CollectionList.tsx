/**
 * CollectionList Component
 * @module components/Collections/CollectionList
 *
 * Displays a grid of collection cards.
 * Supports responsive layout and empty state.
 *
 * Covers: FR-001, FR-002
 */

import type { JSX } from 'preact';
import type { CollectionSummary, CollectionProgressSummary } from '@/models/collection';
import { CollectionCard } from './CollectionCard';
import { EmptyState } from '@/components/shared/GoQuote';

export interface CollectionListProps {
  /** Collections to display */
  collections: CollectionSummary[];
  /** Progress data for each collection (by collectionId) */
  progressMap?: Record<string, CollectionProgressSummary>;
  /** Handler when a collection is clicked */
  onCollectionClick?: (collection: CollectionSummary) => void;
  /** Currently selected collection ID */
  selectedId?: string;
  /** Loading state */
  isLoading?: boolean;
  /** Card size */
  cardSize?: 'sm' | 'md' | 'lg';
  /** Empty state message */
  emptyMessage?: string;
}

/**
 * Grid display of collection cards
 */
export function CollectionList({
  collections,
  progressMap = {},
  onCollectionClick,
  selectedId,
  isLoading = false,
  cardSize = 'md',
  emptyMessage = 'No collections found',
}: CollectionListProps): JSX.Element {
  const gridStyle: JSX.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '1rem',
    padding: '0.5rem',
  };

  const loadingStyle: JSX.CSSProperties = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '3rem',
    color: 'var(--color-neutral-500)',
  };

  if (isLoading) {
    return (
      <div style={loadingStyle}>
        <span>Loading collections...</span>
      </div>
    );
  }

  if (collections.length === 0) {
    return <EmptyState message={emptyMessage} quoteMode="daily" />;
  }

  return (
    <div style={gridStyle} role="list" aria-label="Collections">
      {collections.map((collection) => {
        const collectionProgress = progressMap[collection.id];
        return (
          <div key={collection.id} role="listitem">
            <CollectionCard
              collection={collection}
              progress={collectionProgress}
              onClick={onCollectionClick ? () => onCollectionClick(collection) : undefined}
              isSelected={selectedId === collection.id}
              size={cardSize}
            />
          </div>
        );
      })}
    </div>
  );
}

export default CollectionList;
