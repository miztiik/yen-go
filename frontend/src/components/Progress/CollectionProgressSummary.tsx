/**
 * CollectionProgressSummary Component
 * @module components/Progress/CollectionProgressSummary
 *
 * Displays progress summary for a single collection.
 * Shows status badge, progress bar, and last activity.
 *
 * Covers: T032 - User Story 4 (Progress Overview)
 */

import type { JSX } from 'preact';
import type { CollectionProgressSummary as ProgressSummary } from '@/models/collection';

// ============================================================================
// Types
// ============================================================================

export interface CollectionProgressSummaryProps {
  /** Collection progress data */
  progress: ProgressSummary;
  /** Collection name */
  name: string;
  /** Handler when collection is clicked */
  onClick?: () => void;
  /** Custom className */
  className?: string | undefined;
}

type ProgressStatus = 'completed' | 'in-progress' | 'not-started';

// ============================================================================
// Styles
// ============================================================================

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    padding: '1rem',
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    border: '1px solid var(--color-neutral-200)',
  } as JSX.CSSProperties,

  statusBadge: (status: ProgressStatus): JSX.CSSProperties => {
    const colors = {
      completed: {
        bg: 'var(--color-success-bg-solid)',
        text: 'var(--color-success)',
        border: 'var(--color-success-border)',
      },
      'in-progress': {
        bg: 'var(--color-mode-collections-bg)',
        text: 'var(--color-warning)',
        border: 'var(--color-warning-border)',
      },
      'not-started': {
        bg: 'var(--color-neutral-100)',
        text: 'var(--color-neutral-500)',
        border: 'var(--color-neutral-400)',
      },
    };
    const c = colors[status];
    return {
      padding: '0.25rem 0.5rem',
      fontSize: '0.6875rem',
      fontWeight: 600,
      borderRadius: '4px',
      backgroundColor: c.bg,
      color: c.text,
      border: `1px solid ${c.border}`,
      textTransform: 'uppercase',
      letterSpacing: '0.025em',
      whiteSpace: 'nowrap',
    };
  },

  content: {
    flex: 1,
    minWidth: 0,
  } as JSX.CSSProperties,

  name: {
    fontSize: '1rem',
    fontWeight: 600,
    color: 'var(--color-neutral-800)',
    marginBottom: '0.25rem',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  } as JSX.CSSProperties,

  progressRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  } as JSX.CSSProperties,

  progressBar: {
    flex: 1,
    height: '6px',
    backgroundColor: 'var(--color-neutral-200)',
    borderRadius: '3px',
    overflow: 'hidden',
  } as JSX.CSSProperties,

  progressFill: (percent: number, status: ProgressStatus): JSX.CSSProperties => ({
    height: '100%',
    width: `${percent}%`,
    backgroundColor:
      status === 'completed' ? 'var(--color-success-border)' : 'var(--color-info-border)',
    borderRadius: '3px',
    transition: 'width 0.3s ease',
  }),

  progressText: {
    fontSize: '0.75rem',
    color: 'var(--color-neutral-500)',
    minWidth: '3.5rem',
    textAlign: 'right',
  } as JSX.CSSProperties,

  meta: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginTop: '0.375rem',
    fontSize: '0.6875rem',
    color: 'var(--color-neutral-400)',
  } as JSX.CSSProperties,

  statsColumn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '0.25rem',
    minWidth: '4rem',
  } as JSX.CSSProperties,

  statValue: {
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--color-neutral-800)',
  } as JSX.CSSProperties,

  statLabel: {
    fontSize: '0.6875rem',
    color: 'var(--color-neutral-400)',
  } as JSX.CSSProperties,
};

// ============================================================================
// Helper Functions
// ============================================================================

function getStatusLabel(status: ProgressStatus): string {
  switch (status) {
    case 'completed':
      return 'Complete';
    case 'in-progress':
      return 'In Progress';
    case 'not-started':
      return 'Not Started';
  }
}

function formatLastActivity(dateString: string | undefined): string {
  if (!dateString) return '';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return date.toLocaleDateString();
}

// ============================================================================
// Component
// ============================================================================

/**
 * CollectionProgressSummary - Progress display for a collection
 */
export function CollectionProgressSummary({
  progress,
  name,
  onClick,
  className = '',
}: CollectionProgressSummaryProps): JSX.Element {
  const { completedCount, totalPuzzles, lastActivity, percentComplete, status } = progress;
  const percent = percentComplete;

  return (
    <div
      class={`collection-progress-summary ${className}`}
      style={styles.container}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      {/* Status Badge */}
      <span style={styles.statusBadge(status)}>{getStatusLabel(status)}</span>

      {/* Content */}
      <div style={styles.content}>
        <div style={styles.name} title={name}>
          {name}
        </div>

        {/* Progress Bar */}
        <div style={styles.progressRow}>
          <div style={styles.progressBar}>
            <div style={styles.progressFill(percent, status)} />
          </div>
          <span style={styles.progressText}>
            {completedCount}/{totalPuzzles}
          </span>
        </div>

        {/* Meta info */}
        <div style={styles.meta}>
          {lastActivity && <span>Last: {formatLastActivity(lastActivity)}</span>}
        </div>
      </div>

      {/* Completion percentage */}
      <div style={styles.statsColumn}>
        <span style={styles.statValue}>{percent}%</span>
        <span style={styles.statLabel}>progress</span>
      </div>
    </div>
  );
}

export default CollectionProgressSummary;
