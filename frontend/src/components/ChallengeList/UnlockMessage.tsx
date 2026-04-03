/**
 * UnlockMessage - Displays unlock requirements for locked challenges
 * @module components/ChallengeList/UnlockMessage
 *
 * Covers: US2 Scenario 4 - Shows message explaining unlock requirements
 *
 * Constitution Compliance:
 * - VI. Accessibility: Clear, informative messages
 */

import type { JSX } from 'preact';

/**
 * Props for UnlockMessage component
 */
export interface UnlockMessageProps {
  /** Required challenge to complete for unlock */
  readonly requiredChallengeId: string;
  /** Formatted display date of required challenge */
  readonly requiredChallengeDate: string;
  /** Number of puzzles needed in required challenge */
  readonly puzzlesNeeded?: number;
  /** Number of puzzles already completed in required challenge */
  readonly puzzlesCompleted?: number;
  /** Size variant */
  readonly variant?: 'inline' | 'banner' | 'modal';
  /** Optional CSS class */
  readonly className?: string;
}

/**
 * Styles for UnlockMessage variants
 */
const styles: Record<string, JSX.CSSProperties> = {
  inline: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.5rem 0.75rem',
    background: 'rgba(154, 138, 122, 0.1)',
    borderRadius: '6px',
    fontSize: '0.8rem',
    color: 'var(--color-text-secondary)',
  },
  banner: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
    padding: '1rem',
    background: 'linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-secondary) 100%)',
    borderRadius: '8px',
    border: '1px solid var(--color-border)',
    textAlign: 'center',
  },
  modal: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
    padding: '1.5rem',
    background: 'var(--color-bg-elevated)',
    borderRadius: '12px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
    textAlign: 'center',
    maxWidth: '320px',
    margin: '0 auto',
  },
  lockIcon: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: '0.5rem',
  },
  title: {
    margin: 0,
    fontSize: '1.1rem',
    fontWeight: '600',
    color: 'var(--color-text-primary)',
  },
  message: {
    margin: 0,
    fontSize: '0.9rem',
    color: 'var(--color-text-secondary)',
    lineHeight: 1.5,
  },
  highlight: {
    fontWeight: '600',
    color: 'var(--color-accent)',
  },
  progress: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.5rem',
    marginTop: '0.5rem',
    fontSize: '0.85rem',
    color: 'var(--color-text-muted)',
  },
  progressBar: {
    flex: 1,
    maxWidth: '120px',
    height: '4px',
    background: 'var(--color-bg-secondary)',
    borderRadius: '2px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: 'var(--color-accent)',
    borderRadius: '2px',
    transition: 'width 0.3s ease',
  },
};

/**
 * Lock icon for modal/banner variants
 */
function LargeLockIcon(): JSX.Element {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--color-accent-muted)"
      strokeWidth="1.5"
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
 * Small lock icon for inline variant
 */
function SmallLockIcon(): JSX.Element {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--color-accent-muted)"
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
 * UnlockMessage - Displays requirements to unlock a challenge
 */
export function UnlockMessage({
  requiredChallengeId: _requiredChallengeId, // Reserved for future deep-linking
  requiredChallengeDate,
  puzzlesNeeded,
  puzzlesCompleted = 0,
  variant = 'inline',
  className,
}: UnlockMessageProps): JSX.Element {
  const progressPercent =
    puzzlesNeeded && puzzlesNeeded > 0
      ? Math.round((puzzlesCompleted / puzzlesNeeded) * 100)
      : 0;

  if (variant === 'inline') {
    return (
      <div style={styles.inline} className={className} role="alert">
        <SmallLockIcon />
        <span>
          Complete <span style={styles.highlight}>{requiredChallengeDate}</span> to unlock
        </span>
      </div>
    );
  }

  if (variant === 'banner') {
    return (
      <div style={styles.banner} className={className} role="alert">
        <p style={styles.message}>
          Complete the <span style={styles.highlight}>{requiredChallengeDate}</span> challenge
          to unlock this one.
        </p>
        {puzzlesNeeded && puzzlesNeeded > 0 && (
          <div style={styles.progress}>
            <span>
              {puzzlesCompleted}/{puzzlesNeeded}
            </span>
            <div style={styles.progressBar}>
              <div
                style={{
                  ...styles.progressFill,
                  width: `${progressPercent}%`,
                }}
              />
            </div>
          </div>
        )}
      </div>
    );
  }

  // Modal variant
  return (
    <div style={styles.modal} className={className} role="alertdialog" aria-labelledby="unlock-title">
      <div style={styles.lockIcon}>
        <LargeLockIcon />
      </div>
      <h3 id="unlock-title" style={styles.title}>
        Challenge Locked
      </h3>
      <p style={styles.message}>
        Complete all puzzles in the{' '}
        <span style={styles.highlight}>{requiredChallengeDate}</span> challenge to unlock this
        one.
      </p>
      {puzzlesNeeded && puzzlesNeeded > 0 && (
        <div style={styles.progress}>
          <span>Progress:</span>
          <div style={styles.progressBar}>
            <div
              style={{
                ...styles.progressFill,
                width: `${progressPercent}%`,
              }}
            />
          </div>
          <span>
            {puzzlesCompleted}/{puzzlesNeeded}
          </span>
        </div>
      )}
    </div>
  );
}

export default UnlockMessage;
