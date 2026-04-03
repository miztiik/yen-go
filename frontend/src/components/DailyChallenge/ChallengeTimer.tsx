/**
 * ChallengeTimer Component
 * @module components/DailyChallenge/ChallengeTimer
 *
 * Countdown timer for timed daily challenge mode.
 * Changes color as time runs low: green → amber → red.
 */

import type { JSX } from 'preact';
import { useState, useEffect, useRef } from 'preact/hooks';

export interface ChallengeTimerProps {
  /** Total duration in milliseconds */
  durationMs: number;
  /** Called when timer reaches zero */
  onTimeUp: () => void;
  /** Pause the timer (e.g. during transitions) */
  isPaused?: boolean;
}

/** Blitz default: 3 minutes */
export const BLITZ_DURATION_MS = 180_000;

export function ChallengeTimer({
  durationMs,
  onTimeUp,
  isPaused = false,
}: ChallengeTimerProps): JSX.Element {
  const [remainingMs, setRemainingMs] = useState(durationMs);
  const endTimeRef = useRef(Date.now() + durationMs);
  const timeUpCalled = useRef(false);
  // Stable ref so interval doesn't re-create on every render
  const onTimeUpRef = useRef(onTimeUp);
  onTimeUpRef.current = onTimeUp;

  useEffect(() => {
    if (isPaused) return;

    // Recalculate deadline from current remaining when resuming
    endTimeRef.current = Date.now() + remainingMs;

    const interval = setInterval(() => {
      const remaining = Math.max(0, endTimeRef.current - Date.now());
      setRemainingMs(remaining);

      if (remaining <= 0 && !timeUpCalled.current) {
        timeUpCalled.current = true;
        clearInterval(interval);
        onTimeUpRef.current();
      }
    }, 200);

    return () => clearInterval(interval);
    // Only restart interval when pause state changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPaused]);

  const totalSeconds = Math.ceil(remainingMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  // Color transitions based on fraction remaining
  const fraction = remainingMs / durationMs;
  let colorClass: string;
  if (fraction > 0.5) {
    colorClass = 'text-emerald-600';
  } else if (fraction > 0.2) {
    colorClass = 'text-amber-500';
  } else {
    colorClass = 'text-red-600';
  }

  return (
    <span
      className={`font-mono text-lg font-bold tabular-nums ${colorClass}`}
      role="timer"
      aria-label={`${minutes} minutes ${seconds} seconds remaining`}
    >
      {minutes}:{seconds.toString().padStart(2, '0')}
    </span>
  );
}
