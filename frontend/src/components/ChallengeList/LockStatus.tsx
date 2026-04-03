/**
 * LockStatus - Visual indicator for locked/unlocked challenge status
 * @module components/ChallengeList/LockStatus
 *
 * Covers: US2 (Browse and Select Daily Challenges)
 *
 * Constitution Compliance:
 * - VI. Accessibility: Clear visual and text indicators
 */

import type { JSX } from 'preact';

/**
 * Props for LockStatus component
 */
export interface LockStatusProps {
  /** Whether the challenge is unlocked */
  readonly isUnlocked: boolean;
  /** Size variant */
  readonly size?: 'small' | 'medium' | 'large';
  /** Whether to show text label */
  readonly showLabel?: boolean;
  /** Optional CSS class */
  readonly className?: string;
}

/**
 * Size configurations
 */
const SIZES = {
  small: { icon: 16, fontSize: '0.7rem' },
  medium: { icon: 20, fontSize: '0.8rem' },
  large: { icon: 24, fontSize: '0.9rem' },
} as const;

/**
 * Styles for LockStatus component
 */
const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.25rem',
  },
  iconContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontWeight: '500',
  },
};

/**
 * Lock icon SVG (closed padlock)
 */
function LockIcon({ size, color }: { size: number; color: string }): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

/**
 * Unlock icon SVG (open padlock)
 */
function UnlockIcon({ size, color }: { size: number; color: string }): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 9.9-1" />
    </svg>
  );
}

/**
 * Checkmark icon SVG (for completed)
 */
function CheckIcon({ size, color }: { size: number; color: string }): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

/**
 * LockStatus - Displays lock/unlock status with icon and optional label
 */
export function LockStatus({
  isUnlocked,
  size = 'medium',
  showLabel = false,
  className,
}: LockStatusProps): JSX.Element {
  const sizeConfig = SIZES[size];
  const color = isUnlocked ? 'var(--color-success-solid)' : 'var(--color-accent-muted)';
  const label = isUnlocked ? 'Unlocked' : 'Locked';

  return (
    <div
      style={styles.container}
      className={className}
      role="status"
      aria-label={label}
    >
      <div style={styles.iconContainer}>
        {isUnlocked ? (
          <UnlockIcon size={sizeConfig.icon} color={color} />
        ) : (
          <LockIcon size={sizeConfig.icon} color={color} />
        )}
      </div>
      {showLabel && (
        <span style={{ ...styles.label, fontSize: sizeConfig.fontSize, color }}>
          {label}
        </span>
      )}
    </div>
  );
}

/**
 * CompletionStatus - Shows completion checkmark or partial progress
 */
export interface CompletionStatusProps {
  /** Completed count */
  readonly completed: number;
  /** Total count */
  readonly total: number;
  /** Size variant */
  readonly size?: 'small' | 'medium' | 'large';
}

export function CompletionStatus({
  completed,
  total,
  size = 'medium',
}: CompletionStatusProps): JSX.Element {
  const sizeConfig = SIZES[size];
  const isComplete = completed >= total;
  const color = isComplete ? 'var(--color-success-solid)' : 'var(--color-accent)';

  if (isComplete) {
    return (
      <div style={styles.iconContainer}>
        <CheckIcon size={sizeConfig.icon} color={color} />
      </div>
    );
  }

  return (
    <span
      style={{
        fontSize: sizeConfig.fontSize,
        color,
        fontWeight: '500',
      }}
    >
      {completed}/{total}
    </span>
  );
}

export default LockStatus;
