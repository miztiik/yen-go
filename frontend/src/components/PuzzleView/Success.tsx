/**
 * Success Component - Puzzle completion message/animation
 * @module components/PuzzleView/Success
 *
 * Covers: FR-016 (Puzzle completion), US1 (Puzzle solving)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Success display separate from puzzle logic
 * - IX. Accessibility: Screen reader announcements, visible feedback
 */

import type { JSX } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import type { CompletionResult } from '../../lib/solver/completion';

/**
 * Props for Success component
 */
export interface SuccessProps {
  /** Completion result */
  result: CompletionResult;
  /** Puzzle title or ID */
  puzzleTitle?: string;
  /** Callback for "Next Puzzle" button */
  onNextPuzzle?: () => void;
  /** Callback for "Review Solution" button */
  onReviewSolution?: () => void;
  /** Callback for "Retry" button */
  onRetry?: () => void;
  /** Whether to auto-dismiss after delay */
  autoDismiss?: boolean;
  /** Auto-dismiss delay in ms */
  autoDismissDelay?: number;
  /** Additional CSS class */
  className?: string;
}

/**
 * Format time in seconds to MM:SS or SS.ms
 */
function formatTime(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds >= 60) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }
  return `${seconds}s`;
}

/**
 * Get star rating based on performance
 */
function getStarRating(result: CompletionResult): number {
  if (!result.isComplete) return 0;

  let stars = 3;

  // Lose a star for wrong attempts
  if (result.wrongAttempts >= 2) stars--;
  if (result.wrongAttempts >= 4) stars--;

  // Lose a star for using hints
  if (result.hintsUsed && result.hintsUsed >= 2) stars--;

  return Math.max(1, stars);
}

/**
 * Success message component - shown when puzzle is completed
 */
export function Success({
  result,
  puzzleTitle,
  onNextPuzzle,
  onReviewSolution,
  onRetry,
  autoDismiss = false,
  autoDismissDelay = 3000,
  className = '',
}: SuccessProps): JSX.Element {
  const [visible, setVisible] = useState(true);
  const [animating, setAnimating] = useState(true);
  const stars = getStarRating(result);

  // Auto-dismiss if configured
  useEffect(() => {
    if (autoDismiss) {
      const timer = setTimeout(() => {
        setVisible(false);
      }, autoDismissDelay);
      return () => clearTimeout(timer);
    }
  }, [autoDismiss, autoDismissDelay]);

  // Animation completion
  useEffect(() => {
    const timer = setTimeout(() => setAnimating(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (!visible) return <></>;

  const containerStyle: JSX.CSSProperties = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    zIndex: 1000,
    animation: animating ? 'fadeIn 0.3s ease-out' : undefined,
  };

  const cardStyle: JSX.CSSProperties = {
    backgroundColor: '#fff',
    borderRadius: '16px',
    padding: '32px',
    maxWidth: '400px',
    width: '90%',
    textAlign: 'center',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
    animation: animating ? 'slideUp 0.4s ease-out' : undefined,
  };

  const titleStyle: JSX.CSSProperties = {
    fontSize: '28px',
    fontWeight: 700,
    color: '#4caf50',
    marginBottom: '8px',
  };

  const subtitleStyle: JSX.CSSProperties = {
    fontSize: '14px',
    color: '#666',
    marginBottom: '24px',
  };

  const starsContainerStyle: JSX.CSSProperties = {
    fontSize: '32px',
    marginBottom: '24px',
  };

  const statsStyle: JSX.CSSProperties = {
    display: 'flex',
    justifyContent: 'center',
    gap: '24px',
    marginBottom: '24px',
  };

  const statStyle: JSX.CSSProperties = {
    textAlign: 'center',
  };

  const statValueStyle: JSX.CSSProperties = {
    fontSize: '20px',
    fontWeight: 600,
    color: '#333',
  };

  const statLabelStyle: JSX.CSSProperties = {
    fontSize: '12px',
    color: '#666',
    textTransform: 'uppercase',
  };

  const buttonsStyle: JSX.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  };

  const primaryButtonStyle: JSX.CSSProperties = {
    backgroundColor: '#4caf50',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    padding: '14px 24px',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  };

  const secondaryButtonStyle: JSX.CSSProperties = {
    backgroundColor: 'transparent',
    color: '#666',
    border: '1px solid #ddd',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s, border-color 0.2s',
  };

  return (
    <div
      className={`success-overlay ${className}`}
      style={containerStyle}
      role="dialog"
      aria-modal="true"
      aria-labelledby="success-title"
    >
      <div className="success-card" style={cardStyle}>
        <h2 id="success-title" style={titleStyle}>
          🎉 Correct!
        </h2>

        {puzzleTitle && <p style={subtitleStyle}>{puzzleTitle}</p>}

        <div style={starsContainerStyle} aria-label={`${stars} out of 3 stars`}>
          {[1, 2, 3].map((n) => (
            <span
              key={n}
              style={{
                color: n <= stars ? '#ffc107' : '#e0e0e0',
                animation:
                  n <= stars && animating
                    ? `starPop 0.3s ease-out ${n * 0.1}s backwards`
                    : undefined,
              }}
            >
              ★
            </span>
          ))}
        </div>

        <div style={statsStyle}>
          {result.timeTaken !== undefined && (
            <div style={statStyle}>
              <div style={statValueStyle}>{formatTime(result.timeTaken)}</div>
              <div style={statLabelStyle}>Time</div>
            </div>
          )}

          <div style={statStyle}>
            <div style={statValueStyle}>{result.movesPlayed}</div>
            <div style={statLabelStyle}>Moves</div>
          </div>

          {result.wrongAttempts > 0 && (
            <div style={statStyle}>
              <div style={statValueStyle}>{result.wrongAttempts}</div>
              <div style={statLabelStyle}>Wrong</div>
            </div>
          )}
        </div>

        <div style={buttonsStyle}>
          {onNextPuzzle && (
            <button
              onClick={onNextPuzzle}
              style={primaryButtonStyle}
              aria-label="Continue to next puzzle"
            >
              Next Puzzle →
            </button>
          )}

          {onReviewSolution && (
            <button
              onClick={onReviewSolution}
              style={secondaryButtonStyle}
              aria-label="Review the solution"
            >
              Review Solution
            </button>
          )}

          {onRetry && (
            <button
              onClick={onRetry}
              style={secondaryButtonStyle}
              aria-label="Try the puzzle again"
            >
              Try Again
            </button>
          )}
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes starPop {
          from {
            opacity: 0;
            transform: scale(0);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .success-card button:hover {
          filter: brightness(1.1);
        }

        .success-card button:focus {
          outline: 2px solid #4caf50;
          outline-offset: 2px;
        }
      `}</style>
    </div>
  );
}

/**
 * Compact success indicator (inline use)
 */
export function SuccessIndicator({ className = '' }: { className?: string }): JSX.Element {
  return (
    <span
      className={`success-indicator ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        color: '#4caf50',
        fontWeight: 600,
      }}
      role="status"
      aria-label="Correct answer"
    >
      <span style={{ fontSize: '1.2em' }}>✓</span>
      Correct!
    </span>
  );
}

/**
 * Get encouraging feedback based on context (T3.6)
 */
function getEncouragingMessage(wrongAttempts: number, _hintsUsed?: number): string {
  const messages = [
    'That allows the opponent to escape—try again!',
    'Good attempt! The key is finding the vital point.',
    "Keep going! Focus on the opponent's weaknesses.",
    'Almost there! Think about what happens after your move.',
    "Try reading ahead a few moves—you've got this!",
    'The solution requires a clever sequence. Keep exploring!',
  ];

  // Pick a message based on wrong attempts to give varied feedback
  const index = wrongAttempts % messages.length;
  // Safe: modulo ensures index is always in bounds
  return messages[index] as string;
}

/**
 * Failure message component - shown when puzzle is failed
 */
export function Failure({
  result,
  puzzleTitle,
  onRetry,
  onShowSolution,
  onSkip,
  className = '',
}: {
  result: CompletionResult;
  puzzleTitle?: string;
  onRetry?: () => void;
  onShowSolution?: () => void;
  onSkip?: () => void;
  className?: string;
}): JSX.Element {
  const containerStyle: JSX.CSSProperties = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    zIndex: 1000,
  };

  const cardStyle: JSX.CSSProperties = {
    backgroundColor: '#fff',
    borderRadius: '16px',
    padding: '32px',
    maxWidth: '400px',
    width: '90%',
    textAlign: 'center',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
  };

  const titleStyle: JSX.CSSProperties = {
    fontSize: '24px',
    fontWeight: 700,
    color: '#f44336',
    marginBottom: '16px',
  };

  const messageStyle: JSX.CSSProperties = {
    fontSize: '14px',
    color: '#666',
    marginBottom: '24px',
  };

  const encouragingStyle: JSX.CSSProperties = {
    fontSize: '15px',
    color: '#2196f3',
    fontStyle: 'italic',
    marginBottom: '16px',
    padding: '12px',
    backgroundColor: '#e3f2fd',
    borderRadius: '8px',
  };

  const buttonsStyle: JSX.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  };

  const primaryButtonStyle: JSX.CSSProperties = {
    backgroundColor: '#2196f3',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    padding: '14px 24px',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
  };

  const secondaryButtonStyle: JSX.CSSProperties = {
    backgroundColor: 'transparent',
    color: '#666',
    border: '1px solid #ddd',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '14px',
    cursor: 'pointer',
  };

  return (
    <div
      className={`failure-overlay ${className}`}
      style={containerStyle}
      role="dialog"
      aria-modal="true"
      aria-labelledby="failure-title"
    >
      <div className="failure-card" style={cardStyle}>
        <h2 id="failure-title" style={titleStyle}>
          Not quite...
        </h2>

        {puzzleTitle && <p style={{ ...messageStyle, marginBottom: '8px' }}>{puzzleTitle}</p>}

        {/* Encouraging feedback (T3.6) */}
        <p style={encouragingStyle}>
          💡 {getEncouragingMessage(result.wrongAttempts, result.hintsUsed)}
        </p>

        <p style={messageStyle}>
          You made {result.wrongAttempts} wrong attempts.
          {result.hintsUsed
            ? ` Used ${result.hintsUsed} hint${result.hintsUsed > 1 ? 's' : ''}.`
            : ''}
        </p>

        <div style={buttonsStyle}>
          {onRetry && (
            <button onClick={onRetry} style={primaryButtonStyle}>
              Try Again
            </button>
          )}

          {onShowSolution && (
            <button onClick={onShowSolution} style={secondaryButtonStyle}>
              Show Solution
            </button>
          )}

          {onSkip && (
            <button onClick={onSkip} style={secondaryButtonStyle}>
              Skip Puzzle
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default Success;
