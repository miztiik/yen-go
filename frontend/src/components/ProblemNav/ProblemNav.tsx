/**
 * Problem Navigation Component
 * @module components/ProblemNav/ProblemNav
 *
 * Navigation carousel for puzzle sets with status indicators.
 *
 * Constitution Compliance:
 * - FR-026 to FR-030: Problem navigation
 * - FR-043 to FR-047: Status indicators
 *
 * Covers: T045
 */

import type { JSX } from 'preact';
import { useCallback, useEffect } from 'preact/hooks';
import { StreakIcon } from '../shared/icons';
import './ProblemNav.css';

/**
 * Puzzle status type.
 */
export type PuzzleStatus = 'unsolved' | 'solved' | 'failed';

/**
 * Status indicator symbols.
 */
export const STATUS_SYMBOLS: Record<PuzzleStatus, string> = {
  unsolved: '○',
  solved: '✓',
  failed: '✗',
};

/**
 * Props for ProblemNav component.
 */
export interface ProblemNavProps {
  /** Total number of problems */
  totalProblems: number;
  /** Current problem index (0-based) */
  currentIndex: number;
  /** Status array for each problem */
  statuses: PuzzleStatus[];
  /** Callback when a specific problem is selected */
  onNavigate: (index: number) => void;
  /** Callback to go to previous problem */
  onPrev: () => void;
  /** Callback to go to next problem */
  onNext: () => void;
  /** Whether to enable keyboard navigation */
  enableKeyboard?: boolean;
  /** CSS class name */
  className?: string;
  /** Current streak of consecutive correct answers */
  currentStreak?: number | undefined;
}

/**
 * ProblemNav - Navigation carousel for puzzle sets.
 *
 * Features:
 * - Status indicators (○/✓/✗)
 * - Current problem highlight
 * - Prev/Next navigation buttons
 * - Keyboard support (← →)
 * - Progress display
 */
export function ProblemNav({
  totalProblems,
  currentIndex,
  statuses,
  onNavigate,
  onPrev,
  onNext,
  enableKeyboard = true,
  className,
  currentStreak,
}: ProblemNavProps): JSX.Element {
  // Keyboard navigation
  useEffect(() => {
    if (!enableKeyboard) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          if (currentIndex > 0) {
            onPrev();
          }
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (currentIndex < totalProblems - 1) {
            onNext();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enableKeyboard, currentIndex, totalProblems, onPrev, onNext]);

  const handleIndicatorClick = useCallback(
    (index: number) => {
      if (index !== currentIndex) {
        onNavigate(index);
      }
    },
    [currentIndex, onNavigate]
  );

  const solvedCount = statuses.filter((s) => s === 'solved').length;
  const completionPct = totalProblems > 0 ? Math.round((solvedCount / totalProblems) * 100) : 0;
  // Always use numeric counter for consistency across filtered/unfiltered views.
  // Dots only for very small daily challenge sets (≤ 10).
  const useDots = totalProblems <= 10;

  return (
    <nav
      className={`problem-nav ${className ?? ''}`}
      data-testid="problem-nav"
      role="navigation"
      aria-label="Problem navigation"
    >
      {/* Top row: ← dots/counter → */}
      <div className="nav-row">
        <button
          type="button"
          className="nav-button prev"
          onClick={onPrev}
          disabled={currentIndex === 0}
          aria-label="Previous problem"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M15 6l-6 6 6 6" />
          </svg>
        </button>

        {useDots ? (
          <div className="problem-dots" role="tablist" aria-label="Problems">
            {Array.from({ length: totalProblems }, (_, i) => {
              const status = statuses[i] || 'unsolved';
              const isCurrent = i === currentIndex;

              return (
                <button
                  key={i}
                  type="button"
                  className={`dot ${status} ${isCurrent ? 'current' : ''}`}
                  onClick={() => handleIndicatorClick(i)}
                  role="tab"
                  aria-selected={isCurrent}
                  aria-label={`Problem ${i + 1}, ${status}`}
                  data-testid={`indicator-${i}`}
                />
              );
            })}
          </div>
        ) : (
          <span className="progress-counter" aria-live="polite">
            {currentIndex + 1} / {totalProblems}
          </span>
        )}

        <button
          type="button"
          className="nav-button next"
          onClick={onNext}
          disabled={currentIndex === totalProblems - 1}
          aria-label="Next problem"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M9 6l6 6-6 6" />
          </svg>
        </button>
      </div>

      {/* Progress bar */}
      <div className="progress-bar-track" aria-hidden="true">
        <div className="progress-bar-fill" style={{ width: `${completionPct}%` }} />
      </div>

      {/* Bottom row: completion % + streak */}
      <div className="nav-footer">
        <span className="completion-text">
          Solved: {solvedCount}/{totalProblems} ({completionPct}%)
        </span>
        {currentStreak !== undefined && currentStreak >= 2 && (
          <span
            className="streak-badge"
            data-testid="streak-badge"
            data-tier={currentStreak >= 10 ? 'peak' : currentStreak >= 5 ? 'elevated' : 'base'}
          >
            <StreakIcon size={14} /> {currentStreak} in a row
          </span>
        )}
      </div>
    </nav>
  );
}

export default ProblemNav;
