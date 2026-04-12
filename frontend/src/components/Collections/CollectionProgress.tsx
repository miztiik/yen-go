/**
 * CollectionProgress Component
 * @module components/Collections/CollectionProgress
 *
 * Progress bar with percentage display for collection completion.
 *
 * Covers: FR-007, FR-009
 */

import type { JSX } from 'preact';
import type { CollectionStatus } from '@/models/collection';

export interface CollectionProgressProps {
  /** Number of completed puzzles */
  completedCount: number;
  /** Total number of puzzles */
  totalPuzzles: number;
  /** Current status */
  status?: CollectionStatus | undefined;
  /** Show percentage text */
  showPercentage?: boolean | undefined;
  /** Show count text */
  showCount?: boolean | undefined;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg' | undefined;
  /** Custom className */
  className?: string | undefined;
}

const sizeConfig: Record<'sm' | 'md' | 'lg', { barHeight: string; fontSize: string }> = {
  sm: { barHeight: '4px', fontSize: '0.6875rem' },
  md: { barHeight: '8px', fontSize: '0.75rem' },
  lg: { barHeight: '12px', fontSize: '0.875rem' },
};

/**
 * Progress bar showing collection completion
 */
export function CollectionProgress({
  completedCount,
  totalPuzzles,
  status,
  showPercentage = true,
  showCount = true,
  size = 'md',
  className = '',
}: CollectionProgressProps): JSX.Element {
  const percentComplete = totalPuzzles > 0 ? Math.round((completedCount / totalPuzzles) * 100) : 0;

  const config = sizeConfig[size];

  // Determine color based on status or percentage
  const getBarColor = (): string => {
    if (status === 'completed') return 'var(--color-success-solid)'; // green
    if (percentComplete >= 70) return 'var(--color-mode-collections-border)'; // purple
    if (percentComplete >= 30) return 'var(--color-info-solid)'; // blue
    return 'var(--color-info-solid)'; // blue
  };

  const containerStyle: JSX.CSSProperties = {
    width: '100%',
  };

  const progressBarBgStyle: JSX.CSSProperties = {
    height: config.barHeight,
    backgroundColor: 'var(--color-neutral-100)',
    borderRadius: config.barHeight,
    overflow: 'hidden',
    position: 'relative',
  };

  const progressBarFillStyle: JSX.CSSProperties = {
    height: '100%',
    width: `${percentComplete}%`,
    backgroundColor: getBarColor(),
    borderRadius: config.barHeight,
    transition: 'width 0.3s ease',
  };

  const textContainerStyle: JSX.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '0.25rem',
    fontSize: config.fontSize,
    color: 'var(--color-neutral-500)',
  };

  const percentStyle: JSX.CSSProperties = {
    fontWeight: 600,
    color: status === 'completed' ? 'var(--color-success-text)' : 'var(--color-neutral-600)',
  };

  const statusBadgeStyle: JSX.CSSProperties = {
    fontSize: '0.625rem',
    padding: '0.125rem 0.375rem',
    borderRadius: '4px',
    fontWeight: 500,
    backgroundColor:
      status === 'completed'
        ? 'var(--color-success-bg-solid)'
        : status === 'in-progress'
          ? 'var(--color-info-bg-solid)'
          : 'var(--color-neutral-100)',
    color:
      status === 'completed'
        ? 'var(--color-success-text)'
        : status === 'in-progress'
          ? 'var(--color-info-text)'
          : 'var(--color-neutral-500)',
    marginLeft: '0.5rem',
  };

  return (
    <div class={`collection-progress ${className}`} style={containerStyle}>
      <div
        style={progressBarBgStyle}
        role="progressbar"
        aria-valuenow={percentComplete}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${percentComplete}% complete (${completedCount} of ${totalPuzzles} puzzles)`}
      >
        <div style={progressBarFillStyle} />
      </div>

      {(showPercentage || showCount) && (
        <div style={textContainerStyle}>
          {showCount && (
            <span>
              {completedCount} / {totalPuzzles}
            </span>
          )}
          <span>
            {showPercentage && <span style={percentStyle}>{percentComplete}%</span>}
            {status && (
              <span style={statusBadgeStyle}>
                {status === 'completed'
                  ? '✓ Complete'
                  : status === 'in-progress'
                    ? 'In Progress'
                    : 'Not Started'}
              </span>
            )}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Compact progress display (just bar, no text)
 */
export function CompactProgress({
  completedCount,
  totalPuzzles,
  status,
}: Pick<CollectionProgressProps, 'completedCount' | 'totalPuzzles' | 'status'>): JSX.Element {
  return (
    <CollectionProgress
      completedCount={completedCount}
      totalPuzzles={totalPuzzles}
      status={status}
      showPercentage={false}
      showCount={false}
      size="sm"
    />
  );
}

export default CollectionProgress;
