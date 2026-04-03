/**
 * useProgressTracker — Hook for integrating puzzle events with progress tracking.
 * @module hooks/useProgressTracker
 *
 * Listens to puzzle completion events from usePuzzleState and writes
 * ProgressRecord to localStorage via the progressTracker service.
 *
 * This hook bridges the goban-based puzzle solving with the application's
 * progress tracking system (streaks, achievements, statistics).
 *
 * Spec 125, Task T033
 */

import { useEffect, useRef, useCallback } from 'preact/hooks';
import type { PuzzleSolveState, PuzzleStatus } from './usePuzzleState';
import {
  recordPuzzleCompletion,
  getStreakData,
  updateStreakData,
  type PuzzleCompletionInput,
} from '../services/progressTracker';
import { PUZZLE_LEVEL_TO_DAILY_GROUP, type DailyChallengeGroup } from '../models/level';
import type { LevelSlug } from '../lib/levels/config';
import type { StreakData } from '../models/progress';

// ============================================================================
// Types
// ============================================================================

/**
 * Options for useProgressTracker hook.
 */
export interface UseProgressTrackerOptions {
  /** Puzzle ID (required for tracking) */
  puzzleId: string;
  /** Current puzzle solve state from usePuzzleState */
  puzzleState: PuzzleSolveState;
  /** Skill level of the puzzle (for difficulty grouping) */
  skillLevel: LevelSlug;
  /** Whether to track this puzzle (default: true) */
  enabled?: boolean;
}

/**
 * Result of useProgressTracker hook.
 */
export interface UseProgressTrackerResult {
  /** Whether the puzzle has been tracked (completion recorded) */
  isTracked: boolean;
  /** Force track completion (for manual tracking) */
  trackCompletion: (success: boolean) => void;
  /** Current streak count */
  currentStreak: number;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Determine if the puzzle status represents a terminal state (solved or failed).
 */
function isTerminalStatus(status: PuzzleStatus): boolean {
  return status === 'complete' || (status === 'wrong');
}

/**
 * Get the difficulty group for a skill level.
 */
function getDifficultyGroup(level: LevelSlug): DailyChallengeGroup {
  return PUZZLE_LEVEL_TO_DAILY_GROUP[level] ?? 'intermediate';
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Track puzzle progress and update statistics on completion.
 *
 * @example
 * ```tsx
 * const { isTracked, currentStreak } = useProgressTracker({
 *   puzzleId: 'abc123',
 *   puzzleState: puzzleState,
 *   skillLevel: 'intermediate',
 * });
 * ```
 */
export function useProgressTracker(
  options: UseProgressTrackerOptions
): UseProgressTrackerResult {
  const { puzzleId, puzzleState, skillLevel, enabled = true } = options;

  // Track if we've already recorded this puzzle
  const hasTrackedRef = useRef(false);
  const previousStatusRef = useRef<PuzzleStatus>(puzzleState.status);

  // Current streak state
  const streakRef = useRef<number>(0);

  // Initialize streak on mount
  useEffect(() => {
    if (!enabled) return;

    try {
      const streakData = getStreakData();
      streakRef.current = streakData.currentStreak;
    } catch {
      // Ignore errors, streak defaults to 0
    }
  }, [enabled]);

  // -------------------------------------------------------------------------
  // Track completion
  // -------------------------------------------------------------------------
  const trackCompletion = useCallback((success: boolean): void => {
    if (!enabled || hasTrackedRef.current) return;

    const difficultyGroup = getDifficultyGroup(skillLevel);
    
    // Calculate time spent
    const timeSpentMs = puzzleState.startedAt
      ? Date.now() - puzzleState.startedAt
      : 0;

    // Prepare completion input
    const completionInput: PuzzleCompletionInput = {
      timeSpentMs,
      attempts: puzzleState.wrongAttempts + (success ? 0 : 1),
      hintsUsed: puzzleState.currentHintTier,
      perfectSolve: success && puzzleState.wrongAttempts === 0 && !puzzleState.hintsUsed,
      difficulty: difficultyGroup,
    };

    // Record completion
    try {
      const result = recordPuzzleCompletion(puzzleId, completionInput);
      if (result.success) {
        hasTrackedRef.current = true;

        // Update streak if successful
        if (success) {
          const today = new Date().toISOString().split('T')[0] ?? '';
          const currentStreakData = getStreakData();
          const newStreak = currentStreakData.currentStreak + 1;
          
          const updatedStreakData: StreakData = {
            currentStreak: newStreak,
            longestStreak: Math.max(currentStreakData.longestStreak, newStreak),
            lastPlayedDate: today,
            streakStartDate: currentStreakData.streakStartDate ?? today,
          };
          
          const streakResult = updateStreakData(updatedStreakData);
          if (streakResult.success) {
            streakRef.current = newStreak;
          }
        }
      }
    } catch (error) {
      console.error('[useProgressTracker] Failed to record completion:', error);
    }
  }, [enabled, puzzleId, skillLevel, puzzleState]);

  // -------------------------------------------------------------------------
  // Auto-track on status change to terminal state
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (!enabled) return;

    const currentStatus = puzzleState.status;
    const previousStatus = previousStatusRef.current;
    previousStatusRef.current = currentStatus;

    // Check for transition to terminal state
    if (!isTerminalStatus(previousStatus) && isTerminalStatus(currentStatus)) {
      // Only track if we haven't already
      if (!hasTrackedRef.current) {
        const success = currentStatus === 'complete';
        trackCompletion(success);
      }
    }
  }, [enabled, puzzleState.status, trackCompletion]);

  // -------------------------------------------------------------------------
  // Reset tracking when puzzle ID changes
  // -------------------------------------------------------------------------
  useEffect(() => {
    hasTrackedRef.current = false;
    previousStatusRef.current = 'loading';
  }, [puzzleId]);

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------
  return {
    isTracked: hasTrackedRef.current,
    trackCompletion,
    currentStreak: streakRef.current,
  };
}

export default useProgressTracker;
