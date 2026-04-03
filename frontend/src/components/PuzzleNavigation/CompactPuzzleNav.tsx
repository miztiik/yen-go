/**
 * CompactPuzzleNav Component
 * @module components/PuzzleNavigation/CompactPuzzleNav
 *
 * Unified navigation bar for puzzle collections.
 * Shows a sliding window of puzzle indicators centered on current puzzle.
 *
 * Design: Single navigation row with:
 * - Prev/Next arrows
 * - Sliding window of ~7-9 visible indicators
 * - Current puzzle counter (e.g., "7 / 88")
 *
 * Covers: FR-008, FR-010, FR-011
 */

import type { JSX } from 'preact';
import { useMemo, useCallback } from 'preact/hooks';

export type PuzzleStatus = 'unsolved' | 'correct' | 'incorrect' | 'current';

export interface CompactPuzzleNavProps {
  /** Total number of puzzles */
  totalPuzzles: number;
  /** Current puzzle index (0-based) */
  currentIndex: number;
  /** Status map: puzzleIndex -> status */
  statuses?: Map<number, 'correct' | 'incorrect'> | undefined;
  /** Handler when a puzzle indicator is clicked */
  onNavigate: (index: number) => void;
  /** Handler for previous button */
  onPrevious?: (() => void) | undefined;
  /** Handler for next button */
  onNext?: (() => void) | undefined;
  /** Handler to jump to first puzzle */
  onFirst?: (() => void) | undefined;
  /** Handler to jump to last puzzle */
  onLast?: (() => void) | undefined;
  /** Max visible indicators (default 9) */
  maxVisible?: number | undefined;
  /** Enable keyboard navigation */
  enableKeyboard?: boolean | undefined;
}

/**
 * Calculate which puzzle indices to show in the sliding window
 */
function calculateVisibleWindow(
  currentIndex: number,
  totalPuzzles: number,
  maxVisible: number
): number[] {
  if (totalPuzzles <= maxVisible) {
    // Show all puzzles if total fits
    return Array.from({ length: totalPuzzles }, (_, i) => i);
  }

  // Calculate window centered on current
  const halfWindow = Math.floor(maxVisible / 2);
  let start = currentIndex - halfWindow;
  let end = currentIndex + halfWindow;

  // Adjust if window extends past boundaries
  if (start < 0) {
    start = 0;
    end = maxVisible - 1;
  } else if (end >= totalPuzzles) {
    end = totalPuzzles - 1;
    start = totalPuzzles - maxVisible;
  }

  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

/**
 * Get indicator style based on status
 */
function getIndicatorStyle(
  status: PuzzleStatus,
  isCurrent: boolean
): JSX.CSSProperties {
  const base: JSX.CSSProperties = {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.7rem',
    fontWeight: isCurrent ? 600 : 400,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    border: 'none',
    flexShrink: 0,
  };

  if (isCurrent) {
    return {
      ...base,
      backgroundColor: 'var(--color-info-solid)',
      color: 'white',
      transform: 'scale(1.15)',
      boxShadow: '0 0 0 2px rgba(66, 153, 225, 0.4)',
    };
  }

  switch (status) {
    case 'correct':
      return {
        ...base,
        backgroundColor: 'var(--color-success-bg-solid)',
        color: 'var(--color-success-text)',
      };
    case 'incorrect':
      return {
        ...base,
        backgroundColor: 'var(--color-level-low-dan-bg)',
        color: 'var(--color-error)',
      };
    default:
      return {
        ...base,
        backgroundColor: 'var(--color-neutral-100)',
        color: 'var(--color-neutral-500)',
      };
  }
}

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '4px',
    padding: '8px 12px',
    backgroundColor: 'transparent',
  },
  // All nav buttons share same minimal style
  navButton: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    border: 'none',
    backgroundColor: 'transparent',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    fontSize: '1.1rem',
    color: 'var(--color-neutral-500)',
    transition: 'all 0.15s ease',
  },
  navButtonDisabled: {
    opacity: 0.25,
    cursor: 'not-allowed',
  },
  indicatorGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '2px',
  },
  ellipsis: {
    color: 'var(--color-neutral-400)',
    fontSize: '0.7rem',
    padding: '0 2px',
  },
};

/**
 * CompactPuzzleNav - Unified navigation for puzzle collections
 * 
 * Apple-inspired design:
 * [⏮] [←] ... 68 69 (70) 71 72 ... [→] [⏭]
 *  ^    ^       numbers centered        ^    ^
 *  |    prev                          next   |
 *  first                                    last
 */
export function CompactPuzzleNav({
  totalPuzzles,
  currentIndex,
  statuses = new Map(),
  onNavigate,
  onPrevious,
  onNext,
  onFirst,
  onLast,
  maxVisible = 9,
  enableKeyboard: _enableKeyboard = true,
}: CompactPuzzleNavProps): JSX.Element {
  // Calculate visible window
  const visibleIndices = useMemo(
    () => calculateVisibleWindow(currentIndex, totalPuzzles, maxVisible),
    [currentIndex, totalPuzzles, maxVisible]
  );

  // Show ellipsis indicators
  const showStartEllipsis = visibleIndices[0] !== undefined && visibleIndices[0] > 0;
  const lastVisibleIndex = visibleIndices[visibleIndices.length - 1];
  const showEndEllipsis =
    lastVisibleIndex !== undefined && lastVisibleIndex < totalPuzzles - 1;

  // Navigation handlers
  const handleFirst = useCallback(() => {
    if (currentIndex > 0) {
      if (onFirst) {
        onFirst();
      } else {
        onNavigate(0);
      }
    }
  }, [currentIndex, onFirst, onNavigate]);

  const handlePrev = useCallback(() => {
    if (currentIndex > 0) {
      if (onPrevious) {
        onPrevious();
      } else {
        onNavigate(currentIndex - 1);
      }
    }
  }, [currentIndex, onPrevious, onNavigate]);

  const handleNext = useCallback(() => {
    if (currentIndex < totalPuzzles - 1) {
      if (onNext) {
        onNext();
      } else {
        onNavigate(currentIndex + 1);
      }
    }
  }, [currentIndex, totalPuzzles, onNext, onNavigate]);

  const handleLast = useCallback(() => {
    if (currentIndex < totalPuzzles - 1) {
      if (onLast) {
        onLast();
      } else {
        onNavigate(totalPuzzles - 1);
      }
    }
  }, [currentIndex, totalPuzzles, onLast, onNavigate]);

  // Get status for an index
  const getStatus = (index: number): PuzzleStatus => {
    if (index === currentIndex) return 'current';
    const status = statuses.get(index);
    if (status) return status;
    return 'unsolved';
  };

  const isAtStart = currentIndex === 0;
  const isAtEnd = currentIndex === totalPuzzles - 1;

  return (
    <div style={styles.container}>
      {/* Skip to first */}
      <button
        style={{
          ...styles.navButton,
          ...(isAtStart ? styles.navButtonDisabled : {}),
        }}
        onClick={handleFirst}
        disabled={isAtStart}
        aria-label="First puzzle"
        title="First puzzle (Home)"
      >
        ⏮
      </button>

      {/* Previous button */}
      <button
        style={{
          ...styles.navButton,
          ...(isAtStart ? styles.navButtonDisabled : {}),
        }}
        onClick={handlePrev}
        disabled={isAtStart}
        aria-label="Previous puzzle"
        title="Previous (←)"
      >
        ‹
      </button>

      {/* Start ellipsis */}
      {showStartEllipsis && <span style={styles.ellipsis}>…</span>}

      {/* Visible indicators */}
      <div style={styles.indicatorGroup}>
        {visibleIndices.map((idx) => {
          const status = getStatus(idx);
          const isCurrent = idx === currentIndex;
          return (
            <button
              key={idx}
              style={getIndicatorStyle(status, isCurrent)}
              onClick={() => onNavigate(idx)}
              aria-label={`Puzzle ${idx + 1}${status !== 'unsolved' ? `, ${status}` : ''}`}
              aria-current={isCurrent ? 'true' : undefined}
            >
              {status === 'correct' ? '✓' : status === 'incorrect' ? '✗' : idx + 1}
            </button>
          );
        })}
      </div>

      {/* End ellipsis */}
      {showEndEllipsis && <span style={styles.ellipsis}>…</span>}

      {/* Next button */}
      <button
        style={{
          ...styles.navButton,
          ...(isAtEnd ? styles.navButtonDisabled : {}),
        }}
        onClick={handleNext}
        disabled={isAtEnd}
        aria-label="Next puzzle"
        title="Next (→)"
      >
        ›
      </button>

      {/* Skip to last */}
      <button
        style={{
          ...styles.navButton,
          ...(isAtEnd ? styles.navButtonDisabled : {}),
        }}
        onClick={handleLast}
        disabled={isAtEnd}
        aria-label="Last puzzle"
        title="Last puzzle (End)"
      >
        ⏭
      </button>
    </div>
  );
}

export default CompactPuzzleNav;
