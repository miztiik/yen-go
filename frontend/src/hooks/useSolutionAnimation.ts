/**
 * Solution Animation Hook
 * @module hooks/useSolutionAnimation
 *
 * Custom hook for managing solution animation playback state.
 * Extracted from ReviewPage.tsx for reusability (FR-004, FR-005, FR-006).
 *
 * Constitution Compliance:
 * - V. No Browser AI: Timer-based progression only
 * - VI. Type Safety: Strict TypeScript types
 */

import { useState, useRef, useEffect, useCallback } from 'preact/hooks';
import type {
  SolutionAnimationState,
  SolutionAnimationActions,
} from '@models/SolutionPresentation';

/** Default delay between animation frames in milliseconds */
const DEFAULT_DELAY_MS = 1500;

/** Minimum delay (for fast playback) */
const MIN_DELAY_MS = 500;

/** Maximum delay (for slow playback) */
const MAX_DELAY_MS = 3000;

/**
 * Hook result combining state and actions.
 */
export interface UseSolutionAnimationResult {
  /** Current animation state */
  state: SolutionAnimationState;
  /** Animation control actions */
  actions: SolutionAnimationActions;
  /** Whether animation can proceed forward */
  canGoForward: boolean;
  /** Whether animation can go back */
  canGoBack: boolean;
}

/**
 * Hook for managing solution animation playback.
 *
 * @param totalFrames - Total number of frames (moves) in the solution
 * @param initialDelayMs - Initial delay between frames (default: 1500ms)
 * @returns Animation state and control actions
 *
 * @example
 * ```tsx
 * const { state, actions, canGoForward } = useSolutionAnimation(solutionMoves.length);
 *
 * // In render:
 * <button onClick={state.isPlaying ? actions.pause : actions.play}>
 *   {state.isPlaying ? 'Pause' : 'Play'}
 * </button>
 * ```
 */
export function useSolutionAnimation(
  totalFrames: number,
  initialDelayMs: number = DEFAULT_DELAY_MS
): UseSolutionAnimationResult {
  // Animation state
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [delayMs, setDelayMs] = useState(
    Math.max(MIN_DELAY_MS, Math.min(MAX_DELAY_MS, initialDelayMs))
  );

  // Timer reference for cleanup
  const timerRef = useRef<number | null>(null);

  // Computed values
  const canGoForward = currentFrame < totalFrames;
  const canGoBack = currentFrame > 0;

  // Clear timer utility
  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // Auto-advance effect (FR-004)
  useEffect(() => {
    if (isPlaying && canGoForward) {
      timerRef.current = window.setTimeout(() => {
        setCurrentFrame((f) => f + 1);
      }, delayMs);
    } else if (isPlaying && !canGoForward) {
      // Stop at end (FR-006)
      setIsPlaying(false);
    }

    return clearTimer;
  }, [isPlaying, currentFrame, delayMs, canGoForward, clearTimer]);

  // Cleanup on unmount (FR-006)
  useEffect(() => {
    return () => {
      clearTimer();
    };
  }, [clearTimer]);

  // Reset when totalFrames changes (new puzzle loaded)
  useEffect(() => {
    setCurrentFrame(0);
    setIsPlaying(false);
    clearTimer();
  }, [totalFrames, clearTimer]);

  // Actions (FR-005)
  const play = useCallback(() => {
    if (canGoForward) {
      setIsPlaying(true);
    }
  }, [canGoForward]);

  const pause = useCallback(() => {
    setIsPlaying(false);
    clearTimer();
  }, [clearTimer]);

  const reset = useCallback(() => {
    setIsPlaying(false);
    setCurrentFrame(0);
    clearTimer();
  }, [clearTimer]);

  const goToFrame = useCallback(
    (frame: number) => {
      const clampedFrame = Math.max(0, Math.min(totalFrames, frame));
      setCurrentFrame(clampedFrame);
    },
    [totalFrames]
  );

  const stepForward = useCallback(() => {
    if (canGoForward) {
      setCurrentFrame((f) => f + 1);
    }
  }, [canGoForward]);

  const stepBackward = useCallback(() => {
    if (canGoBack) {
      setCurrentFrame((f) => f - 1);
    }
  }, [canGoBack]);

  const setDelay = useCallback((newDelayMs: number) => {
    const clampedDelay = Math.max(MIN_DELAY_MS, Math.min(MAX_DELAY_MS, newDelayMs));
    setDelayMs(clampedDelay);
  }, []);

  // Build state object
  const state: SolutionAnimationState = {
    currentFrame,
    totalFrames,
    isPlaying,
    delayMs,
  };

  // Build actions object
  const actions: SolutionAnimationActions = {
    play,
    pause,
    reset,
    goToFrame,
    stepForward,
    stepBackward,
    setDelay,
  };

  return {
    state,
    actions,
    canGoForward,
    canGoBack,
  };
}

export default useSolutionAnimation;
