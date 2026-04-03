/**
 * Tests for PuzzleSetPlayer utility functions.
 * @module tests/unit/puzzleSetUtils.test
 *
 * Covers: P1-1 (mapIdsToIndexes), P1-2 (findNextUnsolved)
 */

import { describe, it, expect } from 'vitest';
import { mapIdsToIndexes, findNextUnsolved } from '../../src/components/PuzzleSetPlayer/puzzleSetUtils';
import type { PuzzleSetLoader, LoaderStatus, PuzzleEntryMeta } from '../../src/services/puzzleLoaders';

// ============================================================================
// Helpers
// ============================================================================

/** Minimal mock loader that returns entries from a fixed array. */
function mockLoader(entries: PuzzleEntryMeta[]): PuzzleSetLoader {
  return {
    load: async () => {},
    getStatus: () => 'ready' as LoaderStatus,
    getTotal: () => entries.length,
    getEntry: (index: number) => entries[index] ?? null,
    getPuzzleSgf: async () => ({ success: false, error: 'not_found' as const, message: 'mock' }),
    getError: () => null,
  };
}

function entry(id: string): PuzzleEntryMeta {
  return { id, path: `sgf/0001/${id}.sgf`, level: 'beginner' };
}

// ============================================================================
// mapIdsToIndexes
// ============================================================================

describe('mapIdsToIndexes', () => {
  it('returns empty set when completedIds is empty', () => {
    const loader = mockLoader([entry('a'), entry('b'), entry('c')]);
    const result = mapIdsToIndexes(loader, []);
    expect(result.size).toBe(0);
  });

  it('returns empty set when loader has no entries', () => {
    const loader = mockLoader([]);
    const result = mapIdsToIndexes(loader, ['a', 'b']);
    expect(result.size).toBe(0);
  });

  it('maps single completed ID to its index', () => {
    const loader = mockLoader([entry('a'), entry('b'), entry('c')]);
    const result = mapIdsToIndexes(loader, ['b']);
    expect(result).toEqual(new Set([1]));
  });

  it('maps multiple completed IDs to their indexes', () => {
    const loader = mockLoader([entry('a'), entry('b'), entry('c'), entry('d')]);
    const result = mapIdsToIndexes(loader, ['a', 'c', 'd']);
    expect(result).toEqual(new Set([0, 2, 3]));
  });

  it('maps all IDs when all are completed', () => {
    const loader = mockLoader([entry('x'), entry('y'), entry('z')]);
    const result = mapIdsToIndexes(loader, ['x', 'y', 'z']);
    expect(result).toEqual(new Set([0, 1, 2]));
  });

  it('ignores IDs not present in loader entries', () => {
    const loader = mockLoader([entry('a'), entry('b')]);
    const result = mapIdsToIndexes(loader, ['a', 'missing', 'also-missing']);
    expect(result).toEqual(new Set([0]));
  });

  it('handles null entries from unloaded pages gracefully', () => {
    // Simulate a paginated loader where some pages aren't loaded
    const entries: PuzzleEntryMeta[] = [entry('a'), entry('b'), entry('c')];
    const loader: PuzzleSetLoader = {
      ...mockLoader(entries),
      getTotal: () => 5, // More total than loaded entries
      getEntry: (index: number) => entries[index] ?? null, // Index 3,4 return null
    };
    const result = mapIdsToIndexes(loader, ['a', 'c']);
    expect(result).toEqual(new Set([0, 2]));
  });

  it('handles duplicate IDs in completed list', () => {
    const loader = mockLoader([entry('a'), entry('b')]);
    const result = mapIdsToIndexes(loader, ['a', 'a', 'b', 'b']);
    expect(result).toEqual(new Set([0, 1]));
  });
});

// ============================================================================
// findNextUnsolved
// ============================================================================

describe('findNextUnsolved', () => {
  it('returns null for empty set', () => {
    expect(findNextUnsolved(0, 0, new Set())).toBeNull();
  });

  it('returns next index when current is solved', () => {
    // Puzzles: [solved, unsolved, unsolved]
    expect(findNextUnsolved(0, 3, new Set([0]))).toBe(1);
  });

  it('skips consecutive solved puzzles', () => {
    // Puzzles: 0=solved, 1=solved, 2=unsolved, 3=solved
    expect(findNextUnsolved(0, 4, new Set([0, 1, 3]))).toBe(2);
  });

  it('wraps around to find unsolved before current index', () => {
    // Puzzles: 0=unsolved, 1=solved, 2=solved, 3=solved
    // Starting at index 1, should wrap to 0
    expect(findNextUnsolved(1, 4, new Set([1, 2, 3]))).toBe(0);
  });

  it('returns null when all puzzles are solved', () => {
    expect(findNextUnsolved(2, 4, new Set([0, 1, 2, 3]))).toBeNull();
  });

  it('returns next adjacent unsolved', () => {
    // Puzzles: [unsolved, solved, unsolved, solved, unsolved]
    // From index 1: next unsolved is 2
    expect(findNextUnsolved(1, 5, new Set([1, 3]))).toBe(2);
  });

  it('finds unsolved at last position', () => {
    // From index 0 with 0,1 solved: should find index 2
    expect(findNextUnsolved(0, 3, new Set([0, 1]))).toBe(2);
  });

  it('wraps from last index to first unsolved', () => {
    // Puzzle: 0=unsolved, 1=solved, 2=solved
    // From index 2: wrap to 0
    expect(findNextUnsolved(2, 3, new Set([1, 2]))).toBe(0);
  });

  it('handles single puzzle (unsolved)', () => {
    // Only one puzzle, it's unsolved, but we start there — no OTHER unsolved
    expect(findNextUnsolved(0, 1, new Set())).toBeNull();
  });

  it('handles single puzzle (solved)', () => {
    expect(findNextUnsolved(0, 1, new Set([0]))).toBeNull();
  });

  it('handles two puzzles, skip forward', () => {
    // 0=solved, 1=unsolved. From 0 → 1
    expect(findNextUnsolved(0, 2, new Set([0]))).toBe(1);
  });

  it('handles two puzzles, wrap backward', () => {
    // 0=unsolved, 1=solved. From 1 → 0
    expect(findNextUnsolved(1, 2, new Set([1]))).toBe(0);
  });

  it('works correctly at boundary with large index', () => {
    // 100 puzzles. Only index 99 is unsolved. From index 0.
    const completed = new Set(Array.from({ length: 99 }, (_, i) => i));
    expect(findNextUnsolved(0, 100, completed)).toBe(99);
  });
});
