/**
 * Status Indicator Component
 * @module components/ProblemNav/StatusIndicator
 *
 * Individual status indicator for puzzle state.
 *
 * Covers: T046
 */

import type { JSX } from 'preact';
import type { PuzzleStatus } from './ProblemNav';

/**
 * Status symbols mapping.
 */
export const STATUS_SYMBOLS: Record<PuzzleStatus, string> = {
  unsolved: '○',
  solved: '✓',
  failed: '✗',
};

/**
 * Props for StatusIndicator component.
 */
export interface StatusIndicatorProps {
  /** Puzzle status */
  status: PuzzleStatus;
  /** Problem number (1-indexed) */
  number: number;
  /** Whether this is the current problem */
  isCurrent?: boolean;
  /** Callback when clicked */
  onClick?: () => void;
  /** CSS class name */
  className?: string;
}

/**
 * StatusIndicator - Shows puzzle completion status.
 *
 * Symbols:
 * - ○ = unsolved
 * - ✓ = solved
 * - ✗ = failed
 */
export function StatusIndicator({
  status,
  number,
  isCurrent = false,
  onClick,
  className,
}: StatusIndicatorProps): JSX.Element {
  const classes = ['status-indicator', status, isCurrent ? 'current' : '', className]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      type="button"
      className={classes}
      onClick={onClick}
      role="tab"
      aria-selected={isCurrent}
      aria-label={`Problem ${number}, ${status}`}
      data-testid={`status-indicator-${number}`}
    >
      <span className="symbol" aria-hidden="true">
        {STATUS_SYMBOLS[status]}
      </span>
      <span className="number">{number}</span>
    </button>
  );
}

export default StatusIndicator;
