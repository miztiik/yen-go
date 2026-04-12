/**
 * Pure utility functions for PuzzleSetPlayer.
 *
 * Extracted for unit testability — these are the core algorithms
 * behind progress hydration (P1-1) and skip-to-unsolved (P1-2).
 *
 * @module components/PuzzleSetPlayer/puzzleSetUtils
 */

import type { PuzzleSetLoader } from '../../services/puzzleLoaders';

/**
 * P1-1: Map a list of completed puzzle IDs to their loader indexes.
 *
 * Iterates through all loaded entries in the loader and builds a Set<number>
 * of indexes whose IDs appear in the completed list. Entries on unloaded pages
 * (paginated results) will be null and are safely skipped.
 *
 * @param loader - The puzzle set loader with entries loaded
 * @param completedIds - Array of puzzle IDs previously completed
 * @returns Set of indexes corresponding to completed puzzles
 */
export function mapIdsToIndexes(
  loader: PuzzleSetLoader,
  completedIds: readonly string[]
): Set<number> {
  const result = new Set<number>();
  if (completedIds.length === 0) return result;

  const idSet = new Set(completedIds);
  const total = loader.getTotal();

  for (let i = 0; i < total; i++) {
    const entry = loader.getEntry(i);
    if (entry && idSet.has(entry.id)) {
      result.add(i);
    }
  }

  return result;
}

/**
 * P1-2: Find the next unsolved puzzle index, searching forward with wrap-around.
 *
 * Scans from (currentIndex + 1) through all indices (wrapping around) and
 * returns the first index not in the completed set. Returns null if all
 * puzzles are completed.
 *
 * @param currentIndex - Current puzzle position (0-based)
 * @param total - Total number of puzzles
 * @param completedIndexes - Set of already-completed indexes
 * @returns Next unsolved index, or null if all are completed
 */
export function findNextUnsolved(
  currentIndex: number,
  total: number,
  completedIndexes: ReadonlySet<number>
): number | null {
  if (total === 0) return null;

  for (let offset = 1; offset < total; offset++) {
    const idx = (currentIndex + offset) % total;
    if (!completedIndexes.has(idx)) {
      return idx;
    }
  }

  return null;
}
