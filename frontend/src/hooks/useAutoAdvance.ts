/**
 * useAutoAdvance — reusable hook for auto-advancing to the next puzzle.
 *
 * Starts a countdown after puzzle completion. Fires `onAdvance` when the
 * timer expires. Can be cancelled by the user (click, Escape, etc.).
 *
 * The hook is a no-op when `enabled` is false — `startCountdown` does
 * nothing and no timers are created.
 *
 * @module hooks/useAutoAdvance
 */

import { useState, useRef, useCallback, useEffect } from 'preact/hooks';

// ============================================================================
// Types
// ============================================================================

export interface UseAutoAdvanceOptions {
  /** Whether auto-advance is enabled (from settings). */
  enabled: boolean;
  /** Delay in milliseconds before advancing. */
  delayMs: number;
  /** Callback fired when countdown completes — advance to next puzzle. */
  onAdvance: () => void;
  /** Optional callback fired when countdown is cancelled. */
  onCancel?: () => void;
}

export interface UseAutoAdvanceReturn {
  /** Start the countdown. No-op if disabled or already counting. */
  startCountdown: () => void;
  /** Cancel an active countdown. Reverts to idle. */
  cancelCountdown: () => void;
  /** Whether a countdown is currently active. */
  isCountingDown: boolean;
  /** Remaining time in milliseconds (0 when idle). */
  remainingMs: number;
  /** Total delay in ms (for progress ring calculation). */
  totalMs: number;
}

// ============================================================================
// Constants
// ============================================================================

/** Tick interval for smooth visual updates (100ms). */
const TICK_INTERVAL = 100;

// ============================================================================
// Hook
// ============================================================================

export function useAutoAdvance({
  enabled,
  delayMs,
  onAdvance,
  onCancel,
}: UseAutoAdvanceOptions): UseAutoAdvanceReturn {
  const [isCountingDown, setIsCountingDown] = useState(false);
  const [remainingMs, setRemainingMs] = useState(0);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const onAdvanceRef = useRef(onAdvance);
  const onCancelRef = useRef(onCancel);
  const delayMsRef = useRef(delayMs);

  // Keep refs up-to-date without re-creating timers
  onAdvanceRef.current = onAdvance;
  onCancelRef.current = onCancel;
  delayMsRef.current = delayMs;

  /** Clear the interval timer. */
  const clearTimer = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  /** Cancel an active countdown. No-op if not currently counting. */
  const cancelCountdown = useCallback(() => {
    if (intervalRef.current === null) return;
    clearTimer();
    setIsCountingDown(false);
    setRemainingMs(0);
    onCancelRef.current?.();
  }, [clearTimer]);

  /** Start the countdown. No-op if disabled or already counting. */
  const startCountdown = useCallback(() => {
    if (!enabled) return;
    if (intervalRef.current !== null) return; // already counting

    const totalDelay = delayMsRef.current;
    startTimeRef.current = Date.now();
    setRemainingMs(totalDelay);
    setIsCountingDown(true);

    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startTimeRef.current;
      const remaining = Math.max(0, totalDelay - elapsed);
      setRemainingMs(remaining);

      if (remaining <= 0) {
        clearTimer();
        setIsCountingDown(false);
        setRemainingMs(0);
        onAdvanceRef.current();
      }
    }, TICK_INTERVAL);
  }, [enabled, clearTimer]);

  // Cancel countdown if `enabled` is toggled off mid-countdown
  useEffect(() => {
    if (!enabled && isCountingDown) {
      cancelCountdown();
    }
  }, [enabled, isCountingDown, cancelCountdown]);

  // Cleanup on unmount
  useEffect(() => {
    return () => clearTimer();
  }, [clearTimer]);

  return {
    startCountdown,
    cancelCountdown,
    isCountingDown,
    remainingMs,
    totalMs: delayMs,
  };
}

export default useAutoAdvance;
