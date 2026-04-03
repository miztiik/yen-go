/**
 * Rush mode puzzle queue management.
 * Handles puzzle selection, ordering, and tracking.
 * @module lib/rush/queue
 */

import type { PuzzleWithId } from '../../types';

/**
 * Queue item representing a puzzle in the rush queue.
 */
export interface QueueItem {
  /** Puzzle ID */
  readonly puzzleId: string;
  /** Whether the puzzle has been completed */
  readonly completed: boolean;
  /** Whether the puzzle was skipped */
  readonly skipped: boolean;
  /** Whether the puzzle was solved correctly */
  readonly correct: boolean | null;
  /** Time taken to solve in milliseconds */
  readonly timeMs: number | null;
  /** Number of attempts */
  readonly attempts: number;
}

/**
 * Rush queue state.
 */
export interface QueueState {
  /** All puzzles in the queue */
  readonly items: readonly QueueItem[];
  /** Current puzzle index */
  readonly currentIndex: number;
  /** Total puzzles completed (correct or skipped) */
  readonly completedCount: number;
  /** Total puzzles solved correctly */
  readonly correctCount: number;
  /** Total puzzles skipped */
  readonly skippedCount: number;
}

/**
 * Queue configuration.
 */
export interface QueueConfig {
  /** Shuffle puzzles randomly */
  readonly shuffle?: boolean;
  /** Maximum puzzles to include (0 = all) */
  readonly maxPuzzles?: number;
  /** Difficulty filter (if supported) */
  readonly difficulty?: 'easy' | 'medium' | 'hard' | 'all';
}

/**
 * Create initial queue state.
 */
export function createQueueState(puzzleIds: readonly string[]): QueueState {
  return {
    items: puzzleIds.map(puzzleId => ({
      puzzleId,
      completed: false,
      skipped: false,
      correct: null,
      timeMs: null,
      attempts: 0,
    })),
    currentIndex: 0,
    completedCount: 0,
    correctCount: 0,
    skippedCount: 0,
  };
}

/**
 * Shuffle array using Fisher-Yates algorithm.
 */
function shuffleArray<T>(array: readonly T[]): T[] {
  const result = [...array];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    // Fisher-Yates guarantees i and j are valid indices
    const temp = result[i]!;
    result[i] = result[j]!;
    result[j] = temp;
  }
  return result;
}

/**
 * Rush mode puzzle queue manager.
 */
export class RushQueue {
  private state: QueueState;

  constructor(puzzleIds: readonly string[], config: QueueConfig = {}) {
    let ids = [...puzzleIds];

    // Apply shuffle if requested
    if (config.shuffle) {
      ids = shuffleArray(ids);
    }

    // Apply max puzzles limit
    if (config.maxPuzzles && config.maxPuzzles > 0) {
      ids = ids.slice(0, config.maxPuzzles);
    }

    this.state = createQueueState(ids);
  }

  /**
   * Get current queue state.
   */
  getState(): QueueState {
    return this.state;
  }

  /**
   * Get the current puzzle ID.
   */
  getCurrentPuzzleId(): string | null {
    const item = this.state.items[this.state.currentIndex];
    return item ? item.puzzleId : null;
  }

  /**
   * Get the current queue item.
   */
  getCurrentItem(): QueueItem | null {
    return this.state.items[this.state.currentIndex] || null;
  }

  /**
   * Check if queue has more puzzles.
   */
  hasNext(): boolean {
    return this.state.currentIndex < this.state.items.length - 1;
  }

  /**
   * Check if all puzzles are completed.
   */
  isComplete(): boolean {
    return this.state.completedCount >= this.state.items.length;
  }

  /**
   * Get total number of puzzles in queue.
   */
  getTotalCount(): number {
    return this.state.items.length;
  }

  /**
   * Record an attempt on current puzzle.
   */
  recordAttempt(): void {
    const currentItem = this.state.items[this.state.currentIndex];
    if (!currentItem) return;

    const updatedItems = this.state.items.map((item, index) =>
      index === this.state.currentIndex
        ? { ...item, attempts: item.attempts + 1 }
        : item
    );

    this.state = {
      ...this.state,
      items: updatedItems,
    };
  }

  /**
   * Mark current puzzle as completed (correct).
   */
  markCorrect(timeMs: number): void {
    const currentItem = this.state.items[this.state.currentIndex];
    if (!currentItem || currentItem.completed) return;

    const updatedItems = this.state.items.map((item, index) =>
      index === this.state.currentIndex
        ? { ...item, completed: true, correct: true, timeMs }
        : item
    );

    this.state = {
      ...this.state,
      items: updatedItems,
      completedCount: this.state.completedCount + 1,
      correctCount: this.state.correctCount + 1,
    };
  }

  /**
   * Mark current puzzle as skipped.
   */
  markSkipped(): void {
    const currentItem = this.state.items[this.state.currentIndex];
    if (!currentItem || currentItem.completed) return;

    const updatedItems = this.state.items.map((item, index) =>
      index === this.state.currentIndex
        ? { ...item, completed: true, skipped: true, correct: false, timeMs: null }
        : item
    );

    this.state = {
      ...this.state,
      items: updatedItems,
      completedCount: this.state.completedCount + 1,
      skippedCount: this.state.skippedCount + 1,
    };
  }

  /**
   * Move to next puzzle.
   * @returns True if moved successfully, false if at end
   */
  moveNext(): boolean {
    if (!this.hasNext()) {
      return false;
    }

    this.state = {
      ...this.state,
      currentIndex: this.state.currentIndex + 1,
    };

    return true;
  }

  /**
   * Get summary statistics.
   */
  getSummary(): {
    total: number;
    completed: number;
    correct: number;
    skipped: number;
    accuracy: number;
    averageTimeMs: number | null;
  } {
    const { items, completedCount, correctCount, skippedCount } = this.state;

    const times = items
      .filter(item => item.correct && item.timeMs !== null)
      .map(item => item.timeMs!);

    const averageTimeMs = times.length > 0
      ? times.reduce((sum, t) => sum + t, 0) / times.length
      : null;

    const accuracy = completedCount > 0
      ? (correctCount / completedCount) * 100
      : 0;

    return {
      total: items.length,
      completed: completedCount,
      correct: correctCount,
      skipped: skippedCount,
      accuracy,
      averageTimeMs,
    };
  }

  /**
   * Get all completed items for review.
   */
  getCompletedItems(): readonly QueueItem[] {
    return this.state.items.filter(item => item.completed);
  }

  /**
   * Reset the queue to start over.
   */
  reset(): void {
    this.state = {
      ...this.state,
      items: this.state.items.map(item => ({
        ...item,
        completed: false,
        skipped: false,
        correct: null,
        timeMs: null,
        attempts: 0,
      })),
      currentIndex: 0,
      completedCount: 0,
      correctCount: 0,
      skippedCount: 0,
    };
  }
}

/**
 * Create a rush queue from puzzle IDs.
 */
export function createRushQueue(
  puzzleIds: readonly string[],
  config?: QueueConfig
): RushQueue {
  return new RushQueue(puzzleIds, config);
}

/**
 * Create a rush queue from puzzle data array.
 */
export function createRushQueueFromPuzzles(
  puzzles: readonly PuzzleWithId[],
  config?: QueueConfig
): RushQueue {
  const ids = puzzles.map(p => p.id);
  return createRushQueue(ids, config);
}
