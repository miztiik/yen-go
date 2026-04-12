/**
 * Progress Bar Component
 * @module components/ProblemNav/ProgressBar
 *
 * Spec 118 - T3.2: ProgressBar Component
 * Progress indicator below carousel
 */

import type { JSX } from 'preact';

export interface ProgressBarProps {
  /** Number of completed puzzles */
  completed: number;
  /** Total number of puzzles */
  total: number;
  /** Compact mode (smaller, for tight spaces) */
  compact?: boolean;
}

/**
 * ProgressBar - Visual completion indicator
 *
 * Features:
 * - Percentage display
 * - Animated fill
 * - Accessible (ARIA)
 */
export function ProgressBar({ completed, total, compact = false }: ProgressBarProps): JSX.Element {
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div
      className={`progress-bar ${compact ? 'compact' : ''}`}
      role="progressbar"
      aria-valuenow={percentage}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Progress: ${completed} of ${total} puzzles completed`}
    >
      <div className="progress-bar-track">
        <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
      </div>
      {!compact && (
        <div className="progress-bar-label">
          {completed}/{total} ({percentage}%)
        </div>
      )}
    </div>
  );
}

export default ProgressBar;
