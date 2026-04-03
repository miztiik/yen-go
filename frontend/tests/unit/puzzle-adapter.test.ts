/**
 * Tests for Puzzle Adapter Service
 * 
 * Note: Legacy adapter functions (adaptToLegacyPuzzle, adaptToLegacyPuzzles, createPlaceholderPuzzle)
 * have been removed as part of spec 115 (Frontend PuzzleView Consolidation).
 * The app now uses the new puzzle format exclusively via adaptToPagesPuzzle.
 */

import { describe, it, expect } from 'vitest';
import { adaptToPagesPuzzle } from '@/services/puzzleAdapter';
import type { InternalPuzzle, SolutionNode } from '@/types/puzzle-internal';

/**
 * Create a simple test puzzle.
 */
function createTestPuzzle(): InternalPuzzle {
  const solutionTree: SolutionNode = {
    move: '',
    player: 'B',
    isCorrect: true,
    isUserMove: false,
    children: [
      {
        move: 'ba', // (1, 0)
        player: 'B',
        isCorrect: true,
        isUserMove: true,
        children: [
          {
            move: 'cb', // opponent response
            player: 'W',
            isCorrect: true,
            isUserMove: false,
            children: [
              {
                move: 'dc', // user continues
                player: 'B',
                isCorrect: true,
                isUserMove: true,
                children: [],
              },
            ],
          },
        ],
      },
    ],
  };

  return {
    id: 'test-001',
    boardSize: 9,
    blackStones: [{ x: 0, y: 0 }, { x: 0, y: 1 }], // aa, ab
    whiteStones: [{ x: 2, y: 0 }], // ca
    sideToMove: 'B',
    solutionTree,
    level: 'beginner',
    tags: ['capture', 'ladder'],
    source: 'test',
    hints: {
      hints: ['Look at b1', 'Use capturing technique', 'Capture the white stone'],
      position: { x: 1, y: 0 },
      technique: 'capture',
      text: 'Capture the white stone',
    },
  };
}

describe('Puzzle Adapter', () => {
  describe('adaptToPagesPuzzle', () => {
    it('converts basic puzzle fields correctly', () => {
      const internal = createTestPuzzle();
      const puzzle = adaptToPagesPuzzle(internal);

      expect(puzzle.v).toBe(1);
      expect(puzzle.side).toBe('B');
      expect(puzzle.level).toBe('beginner');
    });

    it('converts stone positions to SGF coordinates', () => {
      const internal = createTestPuzzle();
      const puzzle = adaptToPagesPuzzle(internal);

      // Black stones at (0,0) and (0,1) -> 'aa' and 'ab'
      expect(puzzle.B).toContain('aa');
      expect(puzzle.B).toContain('ab');
      
      // White stone at (2,0) -> 'ca'
      expect(puzzle.W).toContain('ca');
    });

    it('extracts solution sequences from tree', () => {
      const internal = createTestPuzzle();
      const puzzle = adaptToPagesPuzzle(internal);

      // Should have at least one solution path
      expect(puzzle.sol.length).toBeGreaterThan(0);
      
      // First move should be 'ba' (1,0)
      expect(puzzle.sol[0]?.[0]).toBe('ba');
    });

    it('includes tags from internal puzzle', () => {
      const internal = createTestPuzzle();
      const puzzle = adaptToPagesPuzzle(internal);

      expect(puzzle.tags).toContain('capture');
      expect(puzzle.tags).toContain('ladder');
    });

    it('extracts hint from hints array', () => {
      const internal = createTestPuzzle();
      const puzzle = adaptToPagesPuzzle(internal);

      expect(puzzle.hint).toBe('Look at b1');
    });

    it('calculates board region', () => {
      const internal = createTestPuzzle();
      const puzzle = adaptToPagesPuzzle(internal);

      // Region should be calculated based on stone positions
      expect(puzzle.region).toBeDefined();
      expect(puzzle.region.w).toBeGreaterThan(0);
      expect(puzzle.region.h).toBeGreaterThan(0);
    });

    it('handles white to move', () => {
      const internal: InternalPuzzle = {
        ...createTestPuzzle(),
        sideToMove: 'W',
      };
      const puzzle = adaptToPagesPuzzle(internal);

      expect(puzzle.side).toBe('W');
    });

    it('handles puzzle with no black stones', () => {
      const internal: InternalPuzzle = {
        ...createTestPuzzle(),
        blackStones: [],
      };
      const puzzle = adaptToPagesPuzzle(internal);

      expect(puzzle.B).toBeUndefined();
    });

    it('handles puzzle with no white stones', () => {
      const internal: InternalPuzzle = {
        ...createTestPuzzle(),
        whiteStones: [],
      };
      const puzzle = adaptToPagesPuzzle(internal);

      expect(puzzle.W).toBeUndefined();
    });

    it('handles puzzle with empty hints', () => {
      const internal: InternalPuzzle = {
        ...createTestPuzzle(),
        hints: { hints: [] },
      };
      const puzzle = adaptToPagesPuzzle(internal);

      expect(puzzle.hint).toBeUndefined();
    });
  });
});
