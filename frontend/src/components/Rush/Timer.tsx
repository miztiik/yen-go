/**
 * Rush mode timer display component.
 * Shows countdown with visual feedback for urgency.
 * @module components/Rush/Timer
 */
import type { JSX } from 'preact';
import { formatTime } from '../../lib/rush';
import './Timer.css';

export interface TimerProps {
  /** Remaining time in milliseconds */
  remaining: number;
  /** Whether timer is running */
  isRunning: boolean;
  /** Whether timer is paused */
  isPaused: boolean;
  /** Total duration for progress calculation */
  totalDuration: number;
  /** Optional additional class name */
  className?: string;
}

/**
 * Get urgency level based on remaining time percentage.
 */
function getUrgencyLevel(remaining: number, total: number): 'normal' | 'warning' | 'critical' {
  const percent = (remaining / total) * 100;
  if (percent <= 10) return 'critical';
  if (percent <= 25) return 'warning';
  return 'normal';
}

/**
 * Rush mode timer display.
 */
export function Timer({
  remaining,
  isRunning,
  isPaused,
  totalDuration,
  className = '',
}: TimerProps): JSX.Element {
  const urgency = getUrgencyLevel(remaining, totalDuration);
  const progressPercent = (remaining / totalDuration) * 100;

  return (
    <div
      className={`rush-timer rush-timer--${urgency} ${isPaused ? 'rush-timer--paused' : ''} ${className}`}
      role="timer"
      aria-label={`${formatTime(remaining)} remaining`}
    >
      <div className="rush-timer__display">
        <span className="rush-timer__time">{formatTime(remaining)}</span>
        {isPaused && <span className="rush-timer__paused-badge">PAUSED</span>}
      </div>

      <div
        className="rush-timer__progress"
        role="progressbar"
        aria-valuenow={Math.round(progressPercent)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="rush-timer__progress-bar" style={{ width: `${progressPercent}%` }} />
      </div>

      {urgency === 'critical' && isRunning && !isPaused && (
        <span className="rush-timer__warning" aria-live="polite">
          Time running out!
        </span>
      )}
    </div>
  );
}

export default Timer;
