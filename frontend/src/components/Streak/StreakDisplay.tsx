/**
 * StreakDisplay - Shows current streak prominently.
 * @module components/Streak/StreakDisplay
 *
 * Covers: US4 (Daily Streaks), FR-026 (Display current streak prominently)
 *
 * Per spec.md US4-Scenario 4:
 * "Given I have a streak, When I view my profile/dashboard,
 *  Then I see my current streak prominently displayed"
 *
 * Constitution Compliance:
 * - X. Design Philosophy: Minimal chrome, content-first, subtle feedback
 */

import type { JSX } from 'preact';
import { useMemo } from 'preact/hooks';
import type { StreakData } from '../../models/progress';
import { isStreakAtRisk, getHoursUntilStreakEnds } from '../../lib/streak';
import { StreakIcon } from '../shared/icons/StreakIcon';

/**
 * Props for StreakDisplay component.
 */
export interface StreakDisplayProps {
  /** Current streak data */
  readonly streakData: StreakData;
  /** Display size variant */
  readonly size?: 'small' | 'medium' | 'large';
  /** Whether to show the "at risk" warning */
  readonly showWarning?: boolean;
  /** Optional CSS class */
  readonly className?: string;
  /** Optional click handler */
  readonly onClick?: () => void;
}

/**
 * Styles for StreakDisplay.
 */
const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.5rem 1rem',
    borderRadius: '24px',
    background: 'var(--color-accent-container)',
    border: '1px solid transparent',
    cursor: 'default',
    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
  },
  containerClickable: {
    cursor: 'pointer',
  },
  containerAtRisk: {
    background: 'var(--color-accent-container)',
    border: '1px solid var(--color-accent)',
  },
  containerLarge: {
    padding: '0.75rem 1.5rem',
    gap: '0.75rem',
  },
  containerSmall: {
    padding: '0.25rem 0.75rem',
    gap: '0.25rem',
  },
  fireIcon: {
    display: 'flex',
    alignItems: 'center',
    color: 'var(--color-accent)',
    lineHeight: 1,
  },
  fireIconLarge: {
    /* icon rendered at larger size */
  },
  fireIconSmall: {
    /* icon rendered at smaller size */
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '0.125rem',
  },
  streakCount: {
    fontSize: '1.25rem',
    fontWeight: '600',
    color: 'var(--color-accent)',
    lineHeight: 1,
    fontFamily: '"SF Pro Display", -apple-system, BlinkMacSystemFont, sans-serif',
  },
  streakCountLarge: {
    fontSize: '2rem',
  },
  streakCountSmall: {
    fontSize: '1rem',
  },
  label: {
    fontSize: '0.7rem',
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    fontWeight: '500',
  },
  labelLarge: {
    fontSize: '0.85rem',
  },
  labelSmall: {
    fontSize: '0.6rem',
  },
  warning: {
    fontSize: '0.65rem',
    color: 'var(--color-warning)',
    marginTop: '0.125rem',
    fontWeight: '500',
  },
  noStreak: {
    fontSize: '0.75rem',
    color: 'var(--color-neutral-400)',
    fontStyle: 'italic',
  },
};

/**
 * Get icon size based on display size.
 */
function getIconSize(size: 'small' | 'medium' | 'large'): number {
  if (size === 'large') return 24;
  if (size === 'small') return 14;
  return 18;
}

/**
 * Get label text based on streak length.
 */
function getStreakLabel(streak: number, longestStreak: number): string {
  if (streak === 0) return 'Start a streak';
  if (streak === longestStreak && streak >= 7) return 'Personal best!';
  if (streak >= 100) return 'Incredible streak';
  if (streak >= 30) return 'Amazing streak';
  if (streak >= 7) return 'Day streak';
  return 'Day streak';
}

/**
 * StreakDisplay component.
 * Shows the current streak count with visual feedback.
 */
export function StreakDisplay({
  streakData,
  size = 'medium',
  showWarning = true,
  className,
  onClick,
}: StreakDisplayProps): JSX.Element {
  const { currentStreak, longestStreak } = streakData;

  const atRisk = useMemo(
    () => showWarning && isStreakAtRisk(streakData),
    [streakData, showWarning]
  );

  const hoursRemaining = useMemo(
    () => (atRisk ? getHoursUntilStreakEnds(streakData) : null),
    [streakData, atRisk]
  );

  const containerStyle: JSX.CSSProperties = {
    ...styles.container,
    ...(size === 'large' ? styles.containerLarge : {}),
    ...(size === 'small' ? styles.containerSmall : {}),
    ...(atRisk ? styles.containerAtRisk : {}),
    ...(onClick ? styles.containerClickable : {}),
  };

  const fireStyle: JSX.CSSProperties = {
    ...styles.fireIcon,
    ...(size === 'large' ? styles.fireIconLarge : {}),
    ...(size === 'small' ? styles.fireIconSmall : {}),
  };

  const countStyle: JSX.CSSProperties = {
    ...styles.streakCount,
    ...(size === 'large' ? styles.streakCountLarge : {}),
    ...(size === 'small' ? styles.streakCountSmall : {}),
  };

  const labelStyle: JSX.CSSProperties = {
    ...styles.label,
    ...(size === 'large' ? styles.labelLarge : {}),
    ...(size === 'small' ? styles.labelSmall : {}),
  };

  const handleClick = onClick
    ? (e: MouseEvent) => {
        e.stopPropagation();
        onClick();
      }
    : undefined;

  const handleKeyDown = onClick
    ? (e: KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }
    : undefined;

  return (
    <div
      class={className}
      style={containerStyle}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={`Current streak: ${currentStreak} days${atRisk ? ', at risk of ending today' : ''}`}
    >
      <span style={fireStyle} aria-hidden="true">
        <StreakIcon size={getIconSize(size)} />
      </span>
      <div style={styles.content}>
        <span style={countStyle}>{currentStreak}</span>
        <span style={labelStyle}>{getStreakLabel(currentStreak, longestStreak)}</span>
        {atRisk && hoursRemaining !== null && (
          <span style={styles.warning}>
            {hoursRemaining <= 1 ? 'Ending soon!' : `${hoursRemaining}h left`}
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Compact streak badge for tight spaces.
 */
export interface StreakBadgeProps {
  /** Current streak count */
  readonly streak: number;
  /** Optional CSS class */
  readonly className?: string;
}

const badgeStyles: Record<string, JSX.CSSProperties> = {
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.25rem',
    padding: '0.125rem 0.5rem 0.125rem 0.375rem',
    borderRadius: '9999px',
    background: 'var(--color-accent-container)',
    fontSize: '0.75rem',
    fontWeight: '600',
    color: 'var(--color-accent)',
  },
  icon: {
    display: 'flex',
    alignItems: 'center',
  },
};

export function StreakBadge({ streak, className }: StreakBadgeProps): JSX.Element {
  if (streak === 0) {
    return <span class={className} style={{ display: 'none' }} />;
  }

  return (
    <span class={className} style={badgeStyles.badge} aria-label={`${streak} day streak`}>
      <span style={badgeStyles.icon} aria-hidden="true">
        <StreakIcon size={12} />
      </span>
      {streak}
    </span>
  );
}

export default StreakDisplay;
