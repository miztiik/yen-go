/**
 * FeedbackOverlay Component - Shows move feedback to the user
 * @module components/Puzzle/FeedbackOverlay
 *
 * Covers: FR-002 to FR-005, US1
 */

import type { JSX } from 'preact';
import { useEffect, useCallback } from 'preact/hooks';

/** Types of feedback */
export type FeedbackType = 'correct' | 'incorrect' | 'invalid' | 'suboptimal' | 'hint';

/** Props for FeedbackOverlay */
export interface FeedbackOverlayProps {
  /** Type of feedback to display */
  type: FeedbackType;
  /** Feedback message */
  message: string;
  /** Callback when overlay is dismissed */
  onDismiss?: () => void;
  /** Auto-dismiss after this many milliseconds (0 = no auto-dismiss) */
  autoDismissMs?: number;
}

/** Feedback configuration by type */
const FEEDBACK_CONFIG: Record<FeedbackType, {
  icon: string;
  color: string;
  background: string;
}> = {
  correct: {
    icon: '✓',
    color: '#155724',
    background: 'rgba(212, 237, 218, 0.95)',
  },
  incorrect: {
    icon: '✗',
    color: '#721c24',
    background: 'rgba(248, 215, 218, 0.95)',
  },
  invalid: {
    icon: '⚠',
    color: '#856404',
    background: 'rgba(255, 243, 205, 0.95)',
  },
  suboptimal: {
    icon: '◐',
    color: '#0c5460',
    background: 'rgba(209, 236, 241, 0.95)',
  },
  hint: {
    icon: '💡',
    color: '#383d41',
    background: 'rgba(233, 236, 239, 0.95)',
  },
};

/**
 * FeedbackOverlay - Displays feedback about moves to the user
 */
export function FeedbackOverlay({
  type,
  message,
  onDismiss,
  autoDismissMs = 0,
}: FeedbackOverlayProps): JSX.Element {
  const config = FEEDBACK_CONFIG[type];

  // Handle click to dismiss
  const handleClick = useCallback((): void => {
    if (onDismiss) {
      onDismiss();
    }
  }, [onDismiss]);

  // Handle keyboard dismiss
  const handleKeyDown = useCallback(
    (event: KeyboardEvent): void => {
      if (event.key === 'Escape' || event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        if (onDismiss) {
          onDismiss();
        }
      }
    },
    [onDismiss]
  );

  // Auto-dismiss after timeout
  useEffect(() => {
    if (autoDismissMs > 0 && onDismiss) {
      const timer = setTimeout(onDismiss, autoDismissMs);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [autoDismissMs, onDismiss]);

  // Add keyboard listener
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  return (
    <div
      style={{
        ...styles.overlay,
        background: config.background,
        color: config.color,
        borderColor: config.color,
      }}
      onClick={handleClick}
      role="alert"
      aria-live="polite"
      tabIndex={0}
    >
      <span style={styles.icon}>{config.icon}</span>
      <span style={styles.message}>{message}</span>
      {onDismiss && (
        <button
          onClick={handleClick}
          style={styles.dismissButton}
          aria-label="Dismiss feedback"
        >
          ×
        </button>
      )}
    </div>
  );
}

/** Component styles */
const styles: Record<string, JSX.CSSProperties> = {
  overlay: {
    position: 'absolute',
    bottom: '10%',
    left: '50%',
    transform: 'translateX(-50%)',
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.75rem 1.5rem',
    borderRadius: '8px',
    borderWidth: '1px',
    borderStyle: 'solid',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    cursor: 'pointer',
    zIndex: 100,
    maxWidth: '90%',
    animation: 'fadeIn 0.2s ease-out',
  },
  icon: {
    fontSize: '1.5rem',
    lineHeight: 1,
  },
  message: {
    fontSize: '1rem',
    lineHeight: 1.4,
    flex: 1,
  },
  dismissButton: {
    background: 'transparent',
    border: 'none',
    fontSize: '1.5rem',
    lineHeight: 1,
    cursor: 'pointer',
    opacity: 0.6,
    padding: '0 0.25rem',
    marginLeft: '0.5rem',
  },
};

export default FeedbackOverlay;
