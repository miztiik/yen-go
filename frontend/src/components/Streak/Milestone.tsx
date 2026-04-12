/**
 * Milestone - Shows streak milestone achievements.
 * @module components/Streak/Milestone
 *
 * Covers: US4 (Daily Streaks), FR-027 (Recognize milestones)
 *
 * Per spec.md US4-Scenario 3:
 * "Given I have maintained a streak for 7/30/100 days,
 *  When I complete my puzzle for that day,
 *  Then I see a special recognition for reaching that milestone"
 *
 * Milestones per spec: 7, 30, 100, 365 days
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { getMilestoneName } from '../../lib/streak';

/**
 * Milestone thresholds per spec.
 */
export const MILESTONE_DAYS = [7, 30, 100, 365] as const;
export type MilestoneDays = (typeof MILESTONE_DAYS)[number];

/**
 * Props for Milestone component.
 */
export interface MilestoneProps {
  /** The milestone day count */
  readonly days: MilestoneDays;
  /** Whether this milestone is unlocked */
  readonly unlocked: boolean;
  /** Display size */
  readonly size?: 'small' | 'medium' | 'large';
  /** Optional CSS class */
  readonly className?: string;
}

/**
 * Get milestone icon based on days.
 */
function getMilestoneIcon(days: MilestoneDays): string {
  switch (days) {
    case 7:
      return '⭐';
    case 30:
      return '🌟';
    case 100:
      return '💫';
    case 365:
      return '🏆';
    default:
      return '⭐';
  }
}

/**
 * Get milestone color based on days.
 */
function getMilestoneColor(days: MilestoneDays): string {
  switch (days) {
    case 7:
      return 'var(--color-streak-fire)'; // Amber
    case 30:
      return 'var(--color-level-advanced)'; // Purple
    case 100:
      return 'var(--color-info-border)'; // Blue
    case 365:
      return 'var(--color-error)'; // Red/Gold
    default:
      return 'var(--color-neutral-500)';
  }
}

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '1rem',
    borderRadius: '12px',
    background: 'var(--color-neutral-50)',
    border: '2px solid var(--color-neutral-200)',
    transition: 'all 0.3s ease',
  },
  containerUnlocked: {
    background:
      'linear-gradient(135deg, var(--color-mode-daily-light) 0%, var(--color-mode-daily-bg) 100%)',
    border: '2px solid var(--color-streak-fire)',
    boxShadow: '0 4px 12px rgba(251, 191, 36, 0.2)',
  },
  containerLocked: {
    opacity: 0.5,
    filter: 'grayscale(50%)',
  },
  containerLarge: {
    padding: '1.5rem 2rem',
  },
  containerSmall: {
    padding: '0.5rem 0.75rem',
  },
  icon: {
    fontSize: '2rem',
    marginBottom: '0.5rem',
  },
  iconLarge: {
    fontSize: '3rem',
    marginBottom: '0.75rem',
  },
  iconSmall: {
    fontSize: '1.25rem',
    marginBottom: '0.25rem',
  },
  days: {
    fontSize: '1.5rem',
    fontWeight: '700',
    marginBottom: '0.25rem',
  },
  daysLarge: {
    fontSize: '2rem',
  },
  daysSmall: {
    fontSize: '1rem',
  },
  label: {
    fontSize: '0.75rem',
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    fontWeight: '500',
  },
  labelLarge: {
    fontSize: '0.9rem',
  },
  labelSmall: {
    fontSize: '0.65rem',
  },
};

/**
 * Milestone badge component.
 * Shows a streak milestone achievement.
 */
export function Milestone({
  days,
  unlocked,
  size = 'medium',
  className,
}: MilestoneProps): JSX.Element {
  const milestoneName = getMilestoneName(days);
  const milestoneColor = getMilestoneColor(days);

  const containerStyle: JSX.CSSProperties = {
    ...styles.container,
    ...(unlocked ? styles.containerUnlocked : styles.containerLocked),
    ...(size === 'large' ? styles.containerLarge : {}),
    ...(size === 'small' ? styles.containerSmall : {}),
  };

  const iconStyle: JSX.CSSProperties = {
    ...styles.icon,
    ...(size === 'large' ? styles.iconLarge : {}),
    ...(size === 'small' ? styles.iconSmall : {}),
  };

  const daysStyle: JSX.CSSProperties = {
    ...styles.days,
    color: unlocked ? milestoneColor : 'var(--color-text-muted)',
    ...(size === 'large' ? styles.daysLarge : {}),
    ...(size === 'small' ? styles.daysSmall : {}),
  };

  const labelStyle: JSX.CSSProperties = {
    ...styles.label,
    ...(size === 'large' ? styles.labelLarge : {}),
    ...(size === 'small' ? styles.labelSmall : {}),
  };

  return (
    <div
      class={className}
      style={containerStyle}
      role="img"
      aria-label={`${days} day milestone${unlocked ? ' (achieved)' : ' (locked)'}`}
    >
      <span style={iconStyle} aria-hidden="true">
        {getMilestoneIcon(days)}
      </span>
      <span style={daysStyle}>{days}</span>
      <span style={labelStyle}>{unlocked ? milestoneName : 'Days'}</span>
    </div>
  );
}

/**
 * Props for MilestoneList component.
 */
export interface MilestoneListProps {
  /** Current streak count */
  readonly currentStreak: number;
  /** Longest streak ever achieved */
  readonly longestStreak: number;
  /** Display size */
  readonly size?: 'small' | 'medium' | 'large';
  /** Optional CSS class */
  readonly className?: string;
}

const listStyles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '1rem',
    justifyContent: 'center',
  },
  containerSmall: {
    gap: '0.5rem',
  },
};

/**
 * MilestoneList component.
 * Shows all milestones with their unlock status.
 */
export function MilestoneList({
  currentStreak,
  longestStreak,
  size = 'medium',
  className,
}: MilestoneListProps): JSX.Element {
  // Use longest streak to determine unlocked milestones
  const maxStreak = Math.max(currentStreak, longestStreak);

  return (
    <div
      class={className}
      style={{
        ...listStyles.container,
        ...(size === 'small' ? listStyles.containerSmall : {}),
      }}
    >
      {MILESTONE_DAYS.map((days) => (
        <Milestone key={days} days={days} unlocked={maxStreak >= days} size={size} />
      ))}
    </div>
  );
}

/**
 * Props for MilestoneCelebration component.
 */
export interface MilestoneCelebrationProps {
  /** The milestone just reached */
  readonly milestone: number;
  /** Callback when celebration is dismissed */
  readonly onDismiss: () => void;
  /** Auto-dismiss delay in ms (default: 5000) */
  readonly autoDismissDelay?: number;
}

const celebrationStyles: Record<string, JSX.CSSProperties> = {
  overlay: {
    position: 'fixed',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    zIndex: 1000,
    animation: 'fadeIn 0.3s ease',
  },
  modal: {
    background:
      'linear-gradient(180deg, var(--color-mode-daily-light) 0%, var(--color-mode-daily-bg) 100%)',
    borderRadius: '24px',
    padding: '2rem 3rem',
    textAlign: 'center',
    maxWidth: '90vw',
    animation: 'scaleIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
  },
  icon: {
    fontSize: '4rem',
    marginBottom: '1rem',
    animation: 'bounce 0.6s ease infinite',
  },
  title: {
    fontSize: '1.75rem',
    fontWeight: '700',
    color: 'var(--color-warning-text)',
    marginBottom: '0.5rem',
  },
  subtitle: {
    fontSize: '1.125rem',
    color: 'var(--color-warning)',
    marginBottom: '1.5rem',
  },
  button: {
    background: 'var(--color-streak-fire)',
    color: 'white',
    border: 'none',
    borderRadius: '12px',
    padding: '0.75rem 2rem',
    fontSize: '1rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'transform 0.2s ease, background 0.2s ease',
  },
};

/**
 * MilestoneCelebration component.
 * Shows a celebratory modal when reaching a milestone.
 */
export function MilestoneCelebration({
  milestone,
  onDismiss,
  autoDismissDelay = 5000,
}: MilestoneCelebrationProps): JSX.Element {
  const [visible, setVisible] = useState(true);

  const handleDismiss = useCallback(() => {
    setVisible(false);
    setTimeout(onDismiss, 300); // Allow fade out animation
  }, [onDismiss]);

  // Auto-dismiss after delay
  useEffect(() => {
    const timer = setTimeout(handleDismiss, autoDismissDelay);
    return () => clearTimeout(timer);
  }, [autoDismissDelay, handleDismiss]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleDismiss();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleDismiss]);

  // Find the appropriate milestone tier for this streak length
  const milestoneValue = MILESTONE_DAYS.reduce<number | null>(
    (found, m) => (milestone >= m ? m : found),
    null
  );
  const icon = getMilestoneIcon((milestoneValue ?? 7) as MilestoneDays);
  const name = getMilestoneName(milestoneValue ?? 7);

  if (!visible) {
    return <div />;
  }

  return (
    <div
      style={celebrationStyles.overlay}
      onClick={handleDismiss}
      role="dialog"
      aria-modal="true"
      aria-label={`Milestone celebration: ${milestone} day streak`}
    >
      <div style={celebrationStyles.modal} onClick={(e) => e.stopPropagation()} role="document">
        <div style={celebrationStyles.icon} aria-hidden="true">
          {icon}
        </div>
        <h2 style={celebrationStyles.title}>{milestone} Day Streak!</h2>
        <p style={celebrationStyles.subtitle}>You&apos;ve reached {name}!</p>
        <button style={celebrationStyles.button} onClick={handleDismiss} type="button">
          Awesome!
        </button>
      </div>
    </div>
  );
}

export default Milestone;
