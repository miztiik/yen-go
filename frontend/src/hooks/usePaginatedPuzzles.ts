/**
 * React hook for loading paginated puzzles.
 * @module hooks/usePaginatedPuzzles
 *
 * Provides transparent loading of both single-file and paginated indexes
 * with automatic state management.
 *
 * Constitution Compliance:
 * - I. Zero Runtime Backend: Loads static JSON files
 * - III. Deterministic Builds: Same inputs produce same outputs
 */

import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import {
  PaginationState,
  initialPaginationState,
  ViewEntry,
  ViewType,
} from '../types/indexes';
import {
  createPaginationLoader,
} from '../lib/puzzle/pagination';

// ============================================================================
// Hook Configuration
// ============================================================================

/**
 * Return type for the usePaginatedPuzzles hook.
 */
export interface UsePaginatedPuzzlesResult<T = ViewEntry> {
  /** Current pagination state */
  state: PaginationState<T>;
  /** Load the first page (or all if single file) */
  loadInitial: () => Promise<void>;
  /** Load the next page */
  loadMore: () => Promise<void>;
  /** Reset to initial state */
  reset: () => void;
  /** Whether there are more pages to load */
  hasMore: boolean;
  /** Whether currently loading */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** All loaded puzzles */
  puzzles: T[];
  /** Total puzzle count */
  totalCount: number;
}

// ============================================================================
// Generic Hook (v3.0 API)
// ============================================================================

/**
 * Options for the generic usePaginatedView hook.
 */
export interface UsePaginatedViewOptions {
  /** View type: "level", "tag", or "collection" */
  type: ViewType;
  /** View name (e.g., "beginner", "life-and-death") */
  name: string;
  /** Base URL for the puzzle CDN (defaults to /puzzles) */
  baseUrl?: string;
  /** Auto-load on mount */
  autoLoad?: boolean;
}

/**
 * Generic hook for loading paginated view entries.
 * Uses the unified v3.0 `createPaginationLoader` API.
 *
 * @param options Hook options with type and name
 * @returns Pagination state and controls
 */
export function usePaginatedView<T extends ViewEntry = ViewEntry>(
  options: UsePaginatedViewOptions
): UsePaginatedPuzzlesResult<T> {
  const { type, name, baseUrl = '/puzzles', autoLoad = true } = options;

  const [state, setState] = useState<PaginationState<T>>(
    initialPaginationState<T>()
  );

  // Create loader with state callback
  const loader = useMemo(() => {
    if (!name) return null;
    return createPaginationLoader<T>(type, {
      baseUrl,
      name,
      onStateChange: (newState) => setState(newState as unknown as PaginationState<T>),
    });
  }, [baseUrl, name, type]);

  // Load initial data on mount or when name/type changes
  useEffect(() => {
    if (autoLoad && loader) {
      void loader.loadInitial();
    }
    return () => {
      loader?.reset();
    };
  }, [loader, autoLoad]);

  const loadInitial = useCallback(async () => {
    if (loader) {
      await loader.loadInitial();
    }
  }, [loader]);

  const loadMore = useCallback(async () => {
    if (loader) {
      await loader.loadMore();
    }
  }, [loader]);

  const reset = useCallback(() => {
    if (loader) {
      loader.reset();
    }
  }, [loader]);

  return {
    state,
    loadInitial,
    loadMore,
    reset,
    hasMore: state.hasMore,
    isLoading: state.isLoading,
    error: state.error,
    puzzles: state.loadedPuzzles,
    totalCount: state.totalCount,
  };
}

export default usePaginatedView;
