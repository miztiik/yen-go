// @ts-nocheck
/**
 * LevelList Component - Displays list of available puzzle levels
 * @module components/Level/LevelList
 *
 * Covers: FR-012, FR-013, US2
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: UI only, delegates to puzzleLoader
 * - IV. Offline First: Works with cached manifest data
 * - IX. Accessibility: WCAG 2.1 AA compliant list
 */

import { useState, useEffect } from 'preact/hooks';
import type { JSX } from 'preact';
import { getLevels, type LoaderResult, type LevelManifestEntry } from '@services/puzzleLoader';
import { LevelCard } from './LevelCard';

/** Props for LevelList component */
export interface LevelListProps {
  /** IDs of completed levels (for showing unlock status) */
  completedLevelIds?: readonly string[];
  /** Callback when a level is selected */
  onLevelSelect?: (levelId: string) => void;
  /** CSS class name */
  className?: string;
}

/** Component state */
interface LevelListState {
  levels: readonly LevelManifestEntry[];
  loading: boolean;
  error: string | null;
}

/**
 * LevelList - Displays available puzzle levels from manifest
 */
export function LevelList({
  completedLevelIds = [],
  onLevelSelect,
  className = '',
}: LevelListProps): JSX.Element {
  const [state, setState] = useState<LevelListState>({
    levels: [],
    loading: true,
    error: null,
  });

  // Load levels on mount
  useEffect(() => {
    let cancelled = false;

    async function loadLevelsData(): Promise<void> {
      const result: LoaderResult<readonly LevelManifestEntry[]> = await getLevels();

      if (cancelled) return;

      if (result.success && result.data) {
        setState({
          levels: result.data,
          loading: false,
          error: null,
        });
      } else {
        setState({
          levels: [],
          loading: false,
          error: result.message ?? 'Failed to load levels',
        });
      }
    }

    void loadLevelsData();

    return (): void => {
      cancelled = true;
    };
  }, []);

  /**
   * Check if a level is unlocked
   * First level is always unlocked, others require previous level completion
   */
  const isLevelUnlocked = (_level: LevelManifestEntry, index: number): boolean => {
    if (index === 0) return true;
    // Check if the previous level is completed
    const previousLevel = state.levels[index - 1];
    if (previousLevel) {
      return completedLevelIds.includes(previousLevel.id);
    }
    return false;
  };

  /**
   * Check if a level is completed
   */
  const isLevelCompleted = (levelId: string): boolean => {
    return completedLevelIds.includes(levelId);
  };

  /**
   * Handle level card click
   */
  const handleLevelClick = (levelId: string, isUnlocked: boolean): void => {
    if (!isUnlocked) return;
    onLevelSelect?.(levelId);
  };

  // Loading state
  if (state.loading) {
    return (
      <div className={`level-list level-list--loading ${className}`} aria-busy="true">
        <p className="level-list__message">Loading levels...</p>
      </div>
    );
  }

  // Error state
  if (state.error) {
    return (
      <div className={`level-list level-list--error ${className}`} role="alert">
        <p className="level-list__message level-list__message--error">
          {state.error}
        </p>
        <button
          type="button"
          className="level-list__retry"
          onClick={(): void => {
            setState({ ...state, loading: true, error: null });
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  // Empty state
  if (state.levels.length === 0) {
    return (
      <div className={`level-list level-list--empty ${className}`}>
        <p className="level-list__message">No levels available yet.</p>
      </div>
    );
  }

  // Calculate stats
  const totalLevels = state.levels.length;
  const completedCount = completedLevelIds.length;

  return (
    <section className={`level-list ${className}`} aria-label="Puzzle Levels">
      <header className="level-list__header">
        <h2 className="level-list__title">Daily Challenges</h2>
        <p className="level-list__stats">
          {completedCount} / {totalLevels} levels completed
        </p>
      </header>

      <ul className="level-list__grid" role="list">
        {state.levels.map((level, index) => {
          const isUnlocked = isLevelUnlocked(level, index);
          const isCompleted = isLevelCompleted(level.id);

          return (
            <li key={level.id} className="level-list__item">
              <LevelCard
                level={level}
                isUnlocked={isUnlocked}
                isCompleted={isCompleted}
                onClick={(): void => handleLevelClick(level.id, isUnlocked)}
              />
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default LevelList;
