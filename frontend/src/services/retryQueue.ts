/**
 * Retry Queue Service
 * @module services/retryQueue
 *
 * Simple localStorage-backed retry queue for puzzles the user failed.
 * Provides add/get/remove/clear operations with optional context filtering.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RetryEntry {
  readonly puzzleId: string;
  readonly context: string; // technique slug or collection slug
  readonly failedAt: string; // ISO 8601
  readonly retryCount: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'yen-go-retry-queue';

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function readQueue(): RetryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as RetryEntry[];
  } catch {
    return [];
  }
}

function writeQueue(entries: readonly RetryEntry[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Add a puzzle to the retry queue.
 * If the puzzle already exists, increments its retryCount and updates failedAt.
 */
export function addToRetryQueue(puzzleId: string, context: string): void {
  const queue = readQueue();
  const idx = queue.findIndex((e) => e.puzzleId === puzzleId);

  if (idx >= 0) {
    const existing = queue[idx]!;
    queue[idx] = {
      puzzleId: existing.puzzleId,
      context,
      failedAt: new Date().toISOString(),
      retryCount: existing.retryCount + 1,
    };
  } else {
    queue.push({
      puzzleId,
      context,
      failedAt: new Date().toISOString(),
      retryCount: 1,
    });
  }

  writeQueue(queue);
}

/**
 * Get retry queue entries, optionally filtered by context.
 */
export function getRetryQueue(context?: string): readonly RetryEntry[] {
  const queue = readQueue();
  if (context === undefined) return queue;
  return queue.filter((e) => e.context === context);
}

/**
 * Remove a specific puzzle from the retry queue.
 */
export function removeFromRetryQueue(puzzleId: string): void {
  const queue = readQueue();
  writeQueue(queue.filter((e) => e.puzzleId !== puzzleId));
}

/**
 * Clear the retry queue. If context is provided, only clears entries matching that context.
 */
export function clearRetryQueue(context?: string): void {
  if (context === undefined) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  const queue = readQueue();
  writeQueue(queue.filter((e) => e.context !== context));
}
