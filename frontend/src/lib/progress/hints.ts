/**
 * Hint usage tracking for progress persistence.
 * Tracks how many hints were used per puzzle.
 * @module lib/progress/hints
 */

import type { HintLevel } from '../hints/progressive';
import type { PuzzleCompletion, UserProgress } from '../../types/progress';
import { getProgressStorage } from './storage';

/**
 * Load progress from storage (sync version for internal use).
 */
function loadProgressSync(): UserProgress | null {
  const result = getProgressStorage().get();
  return result.success && result.data !== undefined ? result.data : null;
}

/**
 * Save progress to storage (sync version for internal use).
 */
function saveProgressSync(progress: UserProgress): void {
  getProgressStorage().set(progress);
}

/**
 * Hint usage record for a puzzle session.
 */
export interface HintUsageRecord {
  /** Puzzle ID */
  readonly puzzleId: string;
  /** Maximum hint level reached during the session */
  readonly maxHintLevel: HintLevel;
  /** Timestamps when each hint level was requested */
  readonly hintTimestamps: readonly string[];
}

/**
 * Hint session tracker for tracking hints during puzzle solving.
 */
export class HintSessionTracker {
  private puzzleId: string;
  private maxLevel: HintLevel = 0;
  private timestamps: string[] = [];

  constructor(puzzleId: string) {
    this.puzzleId = puzzleId;
  }

  /**
   * Record a hint request.
   */
  recordHint(level: HintLevel): void {
    if (level > this.maxLevel) {
      this.maxLevel = level;
    }
    this.timestamps.push(new Date().toISOString());
  }

  /**
   * Get the number of hints used.
   */
  getHintsUsed(): number {
    return this.maxLevel;
  }

  /**
   * Get the maximum hint level reached.
   */
  getMaxLevel(): HintLevel {
    return this.maxLevel;
  }

  /**
   * Get the full usage record.
   */
  getRecord(): HintUsageRecord {
    return {
      puzzleId: this.puzzleId,
      maxHintLevel: this.maxLevel,
      hintTimestamps: [...this.timestamps],
    };
  }

  /**
   * Reset the tracker.
   */
  reset(): void {
    this.maxLevel = 0;
    this.timestamps = [];
  }
}

/**
 * Get total hints used across all completed puzzles.
 */
export function getTotalHintsUsed(): number {
  const progress = loadProgressSync();
  if (!progress) return 0;

  return Object.values(progress.completedPuzzles).reduce<number>(
    (total, completion) => total + ((completion).hintsUsed || 0),
    0
  );
}

/**
 * Get count of puzzles completed without hints.
 */
export function getPuzzlesWithoutHints(): number {
  const progress = loadProgressSync();
  if (!progress) return 0;

  return Object.values(progress.completedPuzzles).filter(
    (completion) => (completion).hintsUsed === 0
  ).length;
}

/**
 * Get hint statistics for a specific puzzle.
 */
export function getPuzzleHintStats(
  puzzleId: string
): { hintsUsed: number } | null {
  const progress = loadProgressSync();
  if (!progress) return null;

  const completion = progress.completedPuzzles[puzzleId];
  if (!completion) return null;

  return {
    hintsUsed: completion.hintsUsed || 0,
  };
}

/**
 * Update hint count for a completed puzzle.
 * Called when puzzle is completed with hints used.
 */
export function updatePuzzleHints(
  puzzleId: string,
  hintsUsed: number
): void {
  const progress = loadProgressSync();
  if (!progress) return;

  const existing = progress.completedPuzzles[puzzleId];
  if (!existing) return;

  const updated: PuzzleCompletion = {
    ...existing,
    hintsUsed,
  };

  // Update the puzzle in progress and save
  const updatedProgress: UserProgress = {
    ...progress,
    completedPuzzles: {
      ...progress.completedPuzzles,
      [puzzleId]: updated,
    },
  };

  saveProgressSync(updatedProgress);
}

/**
 * Create a new hint session tracker for a puzzle.
 */
export function createHintTracker(puzzleId: string): HintSessionTracker {
  return new HintSessionTracker(puzzleId);
}

/**
 * Check if hints were used for a specific puzzle.
 */
export function wereHintsUsed(puzzleId: string): boolean {
  const stats = getPuzzleHintStats(puzzleId);
  return stats !== null && stats.hintsUsed > 0;
}
