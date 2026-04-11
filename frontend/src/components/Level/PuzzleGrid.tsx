// @ts-nocheck
/**
 * PuzzleGrid Component - Displays puzzles in a level by difficulty
 * @module components/Level/PuzzleGrid
 *
 * Covers: FR-012, FR-014, US2, US6
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: UI only, receives data via props
 * - IX. Accessibility: Grid with proper ARIA roles
 * - I. Zero Runtime Backend: Loads static JSON files
 */

import { useState, useEffect, useCallback } from 'preact/hooks';
import type { JSX } from 'preact';
import type { LevelEntry, ViewEnvelope } from '@/types/indexes';
import { loadLevelIndex, type LoaderResult } from '@services/puzzleLoader';
import { usePaginatedView } from '@/hooks/usePaginatedPuzzles';
import { LoadMore } from '@/components/PuzzleList/LoadMore';
import { APP_CONSTANTS } from '@/config/constants';
const CDN_BASE_PATH = APP_CONSTANTS.paths.cdnBase;

/** Skill level display info */
type SkillLevel = 'beginner' | 'basic' | 'intermediate' | 'advanced' | 'expert';

/** Props for PuzzleGrid component */
export interface PuzzleGridProps {
  /** Level ID to display (e.g., "beginner", "intermediate") */
  levelId: string;
  /** IDs of completed puzzles */
  completedPuzzleIds?: readonly string[];
  /** Callback when a puzzle is selected */
  onPuzzleSelect?: (puzzleId: string, entry: { id?: string; path: string; tags?: readonly string[] }) => void;
  /** CSS class name */
  className?: string;
  /** Enable pagination mode for large puzzle sets (T059) */
  enablePagination?: boolean;
  /** Base URL for CDN (when using pagination) */
  baseUrl?: string;
}

/** Component state */
interface PuzzleGridState {
  levelData: ViewEnvelope<LevelEntry> | null;
  loading: boolean;
  error: string | null;
}

/** Skill level colors and labels */
const LEVEL_INFO: Record<SkillLevel, { label: string; icon: string; color: string }> = {
  beginner: { label: 'Beginner', icon: '🟢', color: 'var(--color-level-beginner)' },
  basic: { label: 'Basic', icon: '🟡', color: 'var(--color-level-elementary)' },
  intermediate: { label: 'Intermediate', icon: '🟠', color: 'var(--color-level-intermediate)' },
  advanced: { label: 'Advanced', icon: '🔴', color: 'var(--color-level-advanced)' },
  expert: { label: 'Expert', icon: '⚫', color: 'var(--color-level-expert)' },
};

/**
 * PuzzleGrid - Displays puzzles in a skill level
 * 
 * Supports two modes:
 * 1. Standard mode (default): Loads all puzzles at once
 * 2. Pagination mode: Loads puzzles page by page for large collections (T059)
 */
export function PuzzleGrid({
  levelId,
  completedPuzzleIds = [],
  onPuzzleSelect,
  className = '',
  enablePagination = false,
  baseUrl = CDN_BASE_PATH,
}: PuzzleGridProps): JSX.Element {
  // Standard mode state
  const [state, setState] = useState<PuzzleGridState>({
    levelData: null,
    loading: true,
    error: null,
  });

  // Pagination mode hook (v3.0 generic API)
  const paginationResult = usePaginatedView<LevelEntry>({
    type: 'level',
    name: enablePagination && levelId ? levelId : '',
    baseUrl,
    autoLoad: enablePagination,
  });

  // Load level data on mount or levelId change (standard mode only)
  useEffect(() => {
    if (enablePagination) return; // Skip if using pagination mode
    
    let cancelled = false;

    async function loadLevelData(): Promise<void> {
      setState({ levelData: null, loading: true, error: null });

      const result: LoaderResult<ViewEnvelope<LevelEntry>> = await loadLevelIndex(levelId);

      if (cancelled) return;

      if (result.success && result.data) {
        setState({
          levelData: result.data,
          loading: false,
          error: null,
        });
      } else {
        setState({
          levelData: null,
          loading: false,
          error: result.message ?? `Failed to load level ${levelId}`,
        });
      }
    }

    void loadLevelData();

    return (): void => {
      cancelled = true;
    };
  }, [levelId, enablePagination]);

  /**
   * Check if a puzzle is completed
   */
  const isPuzzleCompleted = (puzzleId: string | undefined): boolean => {
    return puzzleId ? completedPuzzleIds.includes(puzzleId) : false;
  };

  /**
   * Handle puzzle click
   */
  const handlePuzzleClick = (entry: { id?: string; path: string; tags?: readonly string[] }): void => {
    if (entry.id) {
      onPuzzleSelect?.(entry.id, entry);
    }
  };

  /**
   * Handle load more click (pagination mode)
   */
  const handleLoadMore = useCallback(() => {
    void paginationResult.loadMore();
  }, [paginationResult]);

  // Determine loading state
  const isLoading = enablePagination ? paginationResult.isLoading : state.loading;
  const errorMessage = enablePagination ? paginationResult.error : state.error;

  // Loading state (only show on initial load)
  if (isLoading && (enablePagination ? paginationResult.puzzles.length === 0 : !state.levelData)) {
    return (
      <div className={`puzzle-grid puzzle-grid--loading ${className}`} aria-busy="true">
        <p className="puzzle-grid__message">Loading puzzles...</p>
      </div>
    );
  }

  // Error state
  if (errorMessage) {
    return (
      <div className={`puzzle-grid puzzle-grid--error ${className}`} role="alert">
        <p className="puzzle-grid__message puzzle-grid__message--error">
          {errorMessage}
        </p>
      </div>
    );
  }

  // Determine puzzles to display
  let puzzles: Array<{ id?: string; path: string; tags?: readonly string[] }>;
  let totalCount: number;
  
  if (enablePagination) {
    // Pagination mode: convert LevelEntry to entry with id extracted from path
    puzzles = paginationResult.puzzles.map(p => ({
      id: p.path.replace(/\.sgf$/, '').split('/').pop() ?? '',
      path: p.path,
      tags: p.tags,
    }));
    totalCount = paginationResult.totalCount;
  } else {
    // Standard mode: extract id from path for each entry
    const entries = state.levelData?.entries ?? [];
    puzzles = entries.map(e => ({
      id: e.path.replace(/\.sgf$/, '').split('/').pop() ?? '',
      path: e.path,
      tags: e.tags,
    }));
    totalCount = puzzles.length;
  }

  // Empty state
  if (puzzles.length === 0) {
    return (
      <div className={`puzzle-grid puzzle-grid--empty ${className}`}>
        <p className="puzzle-grid__message">No puzzles in this level.</p>
      </div>
    );
  }

  const completedCount = puzzles.filter((p) => isPuzzleCompleted(p.id)).length;
  const levelInfo = LEVEL_INFO[levelId as SkillLevel] ?? LEVEL_INFO.beginner;

  return (
    <section className={`puzzle-grid ${className}`} aria-label="Puzzle Grid">
      {/* Level header */}
      <header className="puzzle-grid__header">
        <h2 className="puzzle-grid__title">
          {levelInfo.icon} {levelInfo.label} Level
        </h2>
        <span className="puzzle-grid__count">
          {totalCount} {totalCount === 1 ? 'puzzle' : 'puzzles'}
          {enablePagination && paginationResult.hasMore && ` (${puzzles.length} loaded)`}
        </span>
      </header>

      {/* Progress indicator */}
      <div className="puzzle-grid__progress">
        <span className="puzzle-grid__progress-text">
          {completedCount} / {totalCount} completed
        </span>
        <progress
          className="puzzle-grid__progress-bar"
          value={completedCount}
          max={totalCount}
          aria-label={`${completedCount} of ${totalCount} puzzles completed`}
        />
      </div>

      {/* Puzzle grid */}
      <ul className="puzzle-grid__list" role="list">
        {puzzles.map((entry, index) => {
          const puzzleId = entry.id ?? `puzzle-${index}`;
          const isCompleted = isPuzzleCompleted(entry.id);
          const tags = entry.tags ?? [];
          const primaryTag = tags.length > 0 ? tags[0] : null;

          return (
            <li key={puzzleId} className="puzzle-grid__item">
              <button
                type="button"
                className={`puzzle-card puzzle-card--${levelId} ${isCompleted ? 'puzzle-card--completed' : ''}`}
                onClick={(): void => handlePuzzleClick(entry)}
                aria-label={`Puzzle ${index + 1}. ${levelInfo.label} difficulty. ${isCompleted ? 'Completed.' : 'Not completed.'}`}
              >
                <span className="puzzle-card__icon" aria-hidden="true">
                  {isCompleted ? '✅' : levelInfo.icon}
                </span>
                <span className="puzzle-card__number">#{index + 1}</span>
                {primaryTag && (
                  <span className="puzzle-card__category">{primaryTag}</span>
                )}
              </button>
            </li>
          );
        })}
      </ul>

      {/* Load more button (pagination mode only) */}
      {enablePagination && (
        <LoadMore
          hasMore={paginationResult.hasMore}
          isLoading={paginationResult.isLoading}
          onLoadMore={handleLoadMore}
          totalCount={totalCount}
          loadedCount={puzzles.length}
          buttonText="Load More Puzzles"
          loadingText="Loading puzzles..."
        />
      )}
    </section>
  );
}

export default PuzzleGrid;
