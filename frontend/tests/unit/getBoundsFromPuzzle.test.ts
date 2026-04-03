/**
 * Tests for getBoundsFromPuzzle utility (UI-032b)
 */
import { describe, it, expect } from 'vitest';
import { getBoundsFromPuzzle } from '../../src/lib/getBoundsFromPuzzle';
import type { PuzzleObject } from '../../src/lib/sgf-to-puzzle';

function makePuzzle(overrides: Partial<PuzzleObject> = {}): PuzzleObject {
  return {
    initial_state: { black: '', white: '' },
    move_tree: { x: -1, y: -1 },
    width: 19,
    height: 19,
    initial_player: 'black',
    ...overrides,
  };
}

describe('getBoundsFromPuzzle', () => {
  it('returns null for puzzle with no stones', () => {
    const puzzle = makePuzzle();
    expect(getBoundsFromPuzzle(puzzle)).toBeNull();
  });

  it('computes bounds for corner stones', () => {
    // Setup stones at aa (0,0) and cc (2,2)
    const puzzle = makePuzzle({
      initial_state: { black: 'aacc', white: '' },
    });
    const bounds = getBoundsFromPuzzle(puzzle, 2);
    expect(bounds).not.toBeNull();
    expect(bounds!.top).toBe(0); // Edge-snapped
    expect(bounds!.left).toBe(0); // Edge-snapped
  });

  it('includes move tree positions in bounds', () => {
    // Setup stone at aa (0,0), move tree has a move at jj (9,9)
    const puzzle = makePuzzle({
      initial_state: { black: 'aa', white: '' },
      move_tree: { x: 9, y: 9, correct_answer: true },
    });
    const bounds = getBoundsFromPuzzle(puzzle, 2);
    expect(bounds).not.toBeNull();
    // Should include both (0,0) and (9,9) plus padding
    expect(bounds!.bottom).toBeGreaterThanOrEqual(9);
  });

  it('returns null for full-board puzzles (>75% coverage)', () => {
    // Stones spread across entire board
    const puzzle = makePuzzle({
      initial_state: { black: 'aass', white: '' }, // (0,0) and (18,18)
    });
    const bounds = getBoundsFromPuzzle(puzzle, 2);
    expect(bounds).toBeNull(); // Too large to zoom
  });

  it('edge-snaps when close to board edge', () => {
    // Stone at (1,1) - within snap threshold of edge
    const puzzle = makePuzzle({
      initial_state: { black: 'bb', white: '' },
    });
    const bounds = getBoundsFromPuzzle(puzzle, 2);
    expect(bounds).not.toBeNull();
    expect(bounds!.top).toBe(0); // Snapped to edge
    expect(bounds!.left).toBe(0); // Snapped to edge
  });

  it('ensures minimum 5x5 zoom area', () => {
    // Single stone - should expand to at least 5x5
    const puzzle = makePuzzle({
      initial_state: { black: 'jj', white: '' }, // (9,9) center
    });
    const bounds = getBoundsFromPuzzle(puzzle, 1);
    expect(bounds).not.toBeNull();
    const w = bounds!.right - bounds!.left + 1;
    const h = bounds!.bottom - bounds!.top + 1;
    expect(w).toBeGreaterThanOrEqual(5);
    expect(h).toBeGreaterThanOrEqual(5);
  });
});
