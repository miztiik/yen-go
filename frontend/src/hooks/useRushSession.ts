/**
 * useRushSession Hook — Manages Puzzle Rush game session.
 * @module hooks/useRushSession
 *
 * Handles:
 * - Timer countdown (180s, 300s, 600s modes)
 * - Lives system (3 lives default, -1 on wrong)
 * - Score tracking
 * - Auto-advance on correct solution
 * - Session end conditions
 *
 * Spec 125, Task T088
 */

import { useState, useCallback, useEffect, useMemo } from 'preact/hooks';
import type { RushSessionState } from '../types/goban';

// ============================================================================
// Types
// ============================================================================

export interface RushSessionConfig {
  /** Session duration in seconds (60–1800). */
  duration: number;
  /** Number of starting lives (default: 3) */
  startingLives?: number;
  /** Points per correct puzzle (default: 100) */
  pointsPerPuzzle?: number;
  /** Streak bonus multiplier (default: 1.5 at 5 streak) */
  streakBonusThreshold?: number;
}

export interface RushSessionActions {
  /** Start the rush session */
  start: () => void;
  /** Record a correct answer */
  recordCorrect: () => void;
  /** Record a wrong answer */
  recordWrong: () => void;
  /** Pause the session */
  pause: () => void;
  /** Resume the session */
  resume: () => void;
  /** Reset the session to initial state */
  reset: () => void;
  /** Skip current puzzle (costs 1 life) */
  skip: () => void;
}

export interface UseRushSessionResult {
  /** Current session state */
  state: RushSessionState;
  /** Session actions */
  actions: RushSessionActions;
  /** Whether session is over (no lives or time up) */
  isGameOver: boolean;
  /** Whether session is paused */
  isPaused: boolean;
  /** Formatted time remaining (MM:SS) */
  timeDisplay: string;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_STARTING_LIVES = 3;
const DEFAULT_POINTS_PER_PUZZLE = 100;
const DEFAULT_STREAK_BONUS_THRESHOLD = 5;
const STREAK_MULTIPLIER = 1.5;
const TIMER_INTERVAL_MS = 1000;

// ============================================================================
// Hook
// ============================================================================

/**
 * useRushSession — Manages Puzzle Rush gameplay session.
 *
 * @param config - Session configuration
 * @returns Session state and actions
 *
 * @example
 * ```tsx
 * const { state, actions, isGameOver, timeDisplay } = useRushSession({
 *   duration: 300,
 * });
 *
 * return (
 *   <div>
 *     <span>Time: {timeDisplay}</span>
 *     <span>Score: {state.score}</span>
 *     <span>Lives: {'❤️'.repeat(state.lives)}</span>
 *     <button onClick={actions.start}>Start</button>
 *   </div>
 * );
 * ```
 */
export function useRushSession(config: RushSessionConfig): UseRushSessionResult {
  const {
    duration,
    startingLives = DEFAULT_STARTING_LIVES,
    pointsPerPuzzle = DEFAULT_POINTS_PER_PUZZLE,
    streakBonusThreshold = DEFAULT_STREAK_BONUS_THRESHOLD,
  } = config;

  // Session state
  const [state, setState] = useState<RushSessionState>(() => ({
    isActive: false,
    duration,
    timeRemaining: duration,
    lives: startingLives,
    maxLives: startingLives,
    score: 0,
    puzzlesSolved: 0,
    puzzlesFailed: 0,
    currentStreak: 0,
  }));

  const [isPaused, setIsPaused] = useState(false);

  // Computed values
  const isGameOver = state.isActive && (state.lives === 0 || state.timeRemaining === 0);

  const timeDisplay = useMemo(() => {
    const minutes = Math.floor(state.timeRemaining / 60);
    const seconds = state.timeRemaining % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, [state.timeRemaining]);

  // Timer effect — stable interval keyed only on active/paused state.
  // timeRemaining and lives are checked inside the callback via setState(prev => ...)
  // to avoid re-creating the interval every tick (which causes multi-counting).
  useEffect(() => {
    if (!state.isActive || isPaused) return;
    const id = window.setInterval(() => {
      setState((prev) => {
        if (prev.timeRemaining <= 0 || prev.lives <= 0) return prev;
        return { ...prev, timeRemaining: prev.timeRemaining - 1 };
      });
    }, TIMER_INTERVAL_MS);
    return () => clearInterval(id);
  }, [state.isActive, isPaused]);

  // Start session
  const start = useCallback((): void => {
    setState({
      isActive: true,
      duration,
      timeRemaining: duration,
      lives: startingLives,
      maxLives: startingLives,
      score: 0,
      puzzlesSolved: 0,
      puzzlesFailed: 0,
      currentStreak: 0,
    });
    setIsPaused(false);
  }, [duration, startingLives]);

  // Record correct answer
  const recordCorrect = useCallback((): void => {
    setState((prev) => {
      const newStreak = prev.currentStreak + 1;
      let points = pointsPerPuzzle;

      // Apply streak bonus
      if (newStreak >= streakBonusThreshold) {
        points = Math.round(points * STREAK_MULTIPLIER);
      }

      return {
        ...prev,
        score: prev.score + points,
        puzzlesSolved: prev.puzzlesSolved + 1,
        currentStreak: newStreak,
      };
    });
  }, [pointsPerPuzzle, streakBonusThreshold]);

  // Record wrong answer
  const recordWrong = useCallback((): void => {
    setState((prev) => ({
      ...prev,
      lives: Math.max(0, prev.lives - 1),
      puzzlesFailed: prev.puzzlesFailed + 1,
      currentStreak: 0, // Break streak
    }));
  }, []);

  // Pause session
  const pause = useCallback((): void => {
    setIsPaused(true);
  }, []);

  // Resume session
  const resume = useCallback((): void => {
    setIsPaused(false);
  }, []);

  // Reset session
  const reset = useCallback((): void => {
    setState({
      isActive: false,
      duration,
      timeRemaining: duration,
      lives: startingLives,
      maxLives: startingLives,
      score: 0,
      puzzlesSolved: 0,
      puzzlesFailed: 0,
      currentStreak: 0,
    });
    setIsPaused(false);
  }, [duration, startingLives]);

  // Skip puzzle (costs 1 life)
  const skip = useCallback((): void => {
    setState((prev) => ({
      ...prev,
      lives: Math.max(0, prev.lives - 1),
      currentStreak: 0, // Break streak
    }));
  }, []);

  const actions: RushSessionActions = useMemo(() => ({
    start,
    recordCorrect,
    recordWrong,
    pause,
    resume,
    reset,
    skip,
  }), [start, recordCorrect, recordWrong, pause, resume, reset, skip]);

  return {
    state,
    actions,
    isGameOver,
    isPaused,
    timeDisplay,
  };
}

export default useRushSession;
