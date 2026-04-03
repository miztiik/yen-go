/**
 * LoadMore component for paginated puzzle lists.
 * @module components/PuzzleList/LoadMore
 *
 * Provides a button to load more puzzles from a paginated index.
 *
 * Constitution Compliance:
 * - I. Zero Runtime Backend: Triggers static file fetches
 */

import { FunctionComponent } from 'preact';
import './LoadMore.css';

/**
 * Props for the LoadMore component.
 */
export interface LoadMoreProps {
  /** Whether more pages are available */
  hasMore: boolean;
  /** Whether currently loading */
  isLoading: boolean;
  /** Callback when load more is clicked */
  onLoadMore: () => void;
  /** Total number of puzzles */
  totalCount?: number;
  /** Number of puzzles loaded so far */
  loadedCount?: number;
  /** Custom loading text */
  loadingText?: string;
  /** Custom button text */
  buttonText?: string;
  /** Custom class name */
  className?: string;
}

/**
 * LoadMore button component.
 */
export const LoadMore: FunctionComponent<LoadMoreProps> = ({
  hasMore,
  isLoading,
  onLoadMore,
  totalCount,
  loadedCount,
  loadingText = 'Loading...',
  buttonText = 'Load More',
  className = '',
}) => {
  // Don't render if no more pages
  if (!hasMore && !isLoading) {
    return null;
  }

  // Calculate progress if counts are provided
  const showProgress = typeof totalCount === 'number' && typeof loadedCount === 'number';
  const progressText = showProgress
    ? `${loadedCount} of ${totalCount} puzzles`
    : undefined;

  return (
    <div className={`load-more ${className}`}>
      {showProgress && (
        <div className="load-more__progress">
          <div
            className="load-more__progress-bar"
            style={{ width: `${(loadedCount / totalCount) * 100}%` }}
          />
          <span className="load-more__progress-text">{progressText}</span>
        </div>
      )}
      <button
        className="load-more__button"
        onClick={onLoadMore}
        disabled={isLoading}
        aria-busy={isLoading}
      >
        {isLoading ? (
          <>
            <span className="load-more__spinner" aria-hidden="true" />
            {loadingText}
          </>
        ) : (
          buttonText
        )}
      </button>
    </div>
  );
};

export default LoadMore;
