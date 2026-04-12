/**
 * CollectionCard Component
 * @module components/Collections/CollectionCard
 *
 * Displays a single collection in a card format for list/grid views.
 * Shows name, puzzle count, estimated time, and progress bar.
 *
 * Covers: FR-001, FR-002, FR-005, FR-007
 */

import type { JSX } from 'preact';
import type { CollectionSummary, CollectionProgressSummary } from '@/models/collection';
import { getSkillLevelName } from '@/models/collection';

export interface CollectionCardProps {
  /** Collection summary data */
  collection: CollectionSummary;
  /** User's progress (optional) */
  progress?: CollectionProgressSummary | undefined;
  /** Click handler */
  onClick?: (() => void) | undefined;
  /** Whether the card is selected */
  isSelected?: boolean | undefined;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg' | undefined;
}

const sizeStyles: Record<'sm' | 'md' | 'lg', JSX.CSSProperties> = {
  sm: { padding: '0.75rem', minHeight: '100px' },
  md: { padding: '1rem', minHeight: '140px' },
  lg: { padding: '1.25rem', minHeight: '180px' },
};

/**
 * Card displaying collection summary with progress
 */
export function CollectionCard({
  collection,
  progress,
  onClick,
  isSelected = false,
  size = 'md',
}: CollectionCardProps): JSX.Element {
  const percentComplete = progress?.percentComplete ?? 0;
  const status = progress?.status ?? 'not-started';

  const cardStyle: JSX.CSSProperties = {
    ...sizeStyles[size],
    background: isSelected
      ? 'linear-gradient(135deg, var(--color-info-bg-solid) 0%, var(--color-info-bg-solid) 100%)'
      : 'white',
    borderRadius: '12px',
    border: isSelected ? '2px solid var(--color-info-solid)' : '1px solid var(--color-neutral-200)',
    cursor: onClick ? 'pointer' : 'default',
    transition: 'all 0.2s ease',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  };

  const titleStyle: JSX.CSSProperties = {
    fontSize: size === 'sm' ? '0.875rem' : '1rem',
    fontWeight: 600,
    color: 'var(--color-neutral-800)',
    margin: 0,
    lineHeight: 1.3,
  };

  const descStyle: JSX.CSSProperties = {
    fontSize: size === 'sm' ? '0.75rem' : '0.875rem',
    color: 'var(--color-neutral-500)',
    margin: 0,
    lineHeight: 1.4,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  };

  const metaStyle: JSX.CSSProperties = {
    display: 'flex',
    gap: '0.75rem',
    fontSize: '0.75rem',
    color: 'var(--color-neutral-600)',
    flexWrap: 'wrap',
  };

  const metaItemStyle: JSX.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '0.25rem',
  };

  const levelBadgeStyle: JSX.CSSProperties = {
    display: 'inline-block',
    padding: '0.125rem 0.5rem',
    backgroundColor: 'var(--color-neutral-100)',
    borderRadius: '9999px',
    fontSize: '0.6875rem',
    fontWeight: 500,
    color: 'var(--color-neutral-600)',
  };

  const progressBarContainerStyle: JSX.CSSProperties = {
    marginTop: 'auto',
    paddingTop: '0.5rem',
  };

  const progressBarBgStyle: JSX.CSSProperties = {
    height: '6px',
    backgroundColor: 'var(--color-neutral-100)',
    borderRadius: '3px',
    overflow: 'hidden',
  };

  const progressBarFillStyle: JSX.CSSProperties = {
    height: '100%',
    width: `${percentComplete}%`,
    backgroundColor:
      status === 'completed' ? 'var(--color-success-solid)' : 'var(--color-info-solid)',
    borderRadius: '3px',
    transition: 'width 0.3s ease',
  };

  const progressTextStyle: JSX.CSSProperties = {
    fontSize: '0.6875rem',
    color: 'var(--color-neutral-500)',
    marginTop: '0.25rem',
    display: 'flex',
    justifyContent: 'space-between',
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
  };

  return (
    <div
      style={cardStyle}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
      aria-label={`${collection.name}, ${collection.puzzleCount} puzzles, ${percentComplete}% complete`}
    >
      <h3 style={titleStyle}>{collection.name}</h3>
      <p style={descStyle}>{collection.description}</p>

      <div style={metaStyle}>
        <span style={metaItemStyle}>📚 {collection.puzzleCount} puzzles</span>
        <span style={metaItemStyle}>⏱️ ~{collection.estimatedMinutes}min</span>
        <span style={levelBadgeStyle}>
          {getSkillLevelName(collection.levelRange.min)}
          {collection.levelRange.min !== collection.levelRange.max &&
            ` - ${getSkillLevelName(collection.levelRange.max)}`}
        </span>
      </div>

      {progress && (
        <div style={progressBarContainerStyle}>
          <div style={progressBarBgStyle}>
            <div style={progressBarFillStyle} />
          </div>
          <div style={progressTextStyle}>
            <span>
              {progress.completedCount} / {progress.totalPuzzles}
            </span>
            <span style={statusBadgeStyle}>
              {status === 'completed'
                ? '✓ Complete'
                : status === 'in-progress'
                  ? 'In Progress'
                  : 'Not Started'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default CollectionCard;
