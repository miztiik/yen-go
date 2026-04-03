/**
 * Tests for Solution Verifier Service
 * @module tests/unit/solutionVerifier.test
 *
 * Covers: FR-002 to FR-007, US1
 */

import { describe, it, expect } from 'vitest';
import {
  createSolutionState,
  verifyMove,
  advanceSolutionState,
  getValidMoves,
  getHint,
  getSolutionPath,
  validateMove,
  hasCorrectMoves,
} from '../../src/services/solutionVerifier';
import type { Puzzle, SolutionNode } from '../../src/models/puzzle';
import { BLACK, WHITE } from '../../src/models/puzzle';

/**
 * Helper to create an empty 9x9 board
 */
function createEmptyBoard(): ('empty' | 'black' | 'white')[][] {
  return Array.from({ length: 9 }, () =>
    Array.from({ length: 9 }, () => 'empty' as const)
  );
}

/**
 * Helper to create a test puzzle matching the actual Puzzle interface
 */
function createTestPuzzle(): Puzzle {
  // Solution tree structure:
  // Root: play at (4,4) - optimal
  //   -> response (5,4) from white
  //     -> branches to (4,5) - winning
  // Also: play at (3,3) - suboptimal
  const solutionTree: SolutionNode = {
    move: { x: 4, y: 4 }, // First correct move (optimal)
    response: { x: 5, y: 4 }, // White responds
    branches: [
      {
        move: { x: 4, y: 5 }, // Follow-up move
        isWinning: true,
      },
      {
        move: { x: 3, y: 3 }, // Suboptimal move
      },
    ],
  };

  return {
    version: '1.0',
    id: 'test-puzzle',
    boardSize: 9,
    initialState: createEmptyBoard(),
    sideToMove: 'black',
    solutionTree,
    hints: ['Look at the center'],
    explanations: [
      { move: { x: 4, y: 4 }, text: 'Correct! This captures the white group.' },
      { move: { x: 4, y: 5 }, text: 'Well done! Puzzle complete.' },
    ],
    metadata: {
      difficulty: 'beginner',
      difficultyScore: 2,
      tags: ['capture'],
      level: '2026-01-20',
      source: 'test',
      createdAt: '2026-01-20T00:00:00Z',
    },
  };
}

/**
 * Helper to create a puzzle with multiple initial branches
 * The first branch (index 0) is optimal, subsequent branches are suboptimal
 */
function createMultiBranchPuzzle(): Puzzle {
  const solutionTree: SolutionNode = {
    move: { x: 4, y: 4 }, // Primary move (optimal)
    branches: [
      {
        move: { x: 5, y: 5 }, // First branch - also optimal
      },
      {
        move: { x: 3, y: 3 }, // Second branch - suboptimal
      },
    ],
  };

  return {
    version: '1.0',
    id: 'multi-branch-puzzle',
    boardSize: 9,
    initialState: createEmptyBoard(),
    sideToMove: 'black',
    solutionTree,
    hints: [],
    explanations: [],
    metadata: {
      difficulty: 'intermediate',
      difficultyScore: 5,
      tags: ['life-and-death'],
      level: '2026-01-20',
      createdAt: '2026-01-20T00:00:00Z',
    },
  };
}

describe('solutionVerifier', () => {
  describe('createSolutionState', () => {
    it('should create initial state from puzzle', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      expect(state.currentNode).toBe(puzzle.solutionTree);
      expect(state.moveHistory).toEqual([]);
      expect(state.isComplete).toBe(false);
    });
  });

  describe('verifyMove', () => {
    it('should identify correct optimal move', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      // The optimal move is the root node's move: (4,4)
      const result = verifyMove(state, { x: 4, y: 4 }, 'black');

      expect(result.isCorrect).toBe(true);
      expect(result.feedback).toBe('optimal');
      expect(result.matchedNode).toBeDefined();
    });

    it('should identify correct suboptimal move from branches', () => {
      const puzzle = createMultiBranchPuzzle();
      const state = createSolutionState(puzzle);

      // The suboptimal move is in branches at index 1: (3,3)
      const result = verifyMove(state, { x: 3, y: 3 }, 'black');

      expect(result.isCorrect).toBe(true);
      expect(result.feedback).toBe('suboptimal');
    });

    it('should identify incorrect move', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      // Any move not in the solution tree
      const result = verifyMove(state, { x: 0, y: 0 }, 'black');

      expect(result.isCorrect).toBe(false);
      expect(result.feedback).toBe('incorrect');
    });

    it('should indicate opponent response', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const result = verifyMove(state, { x: 4, y: 4 }, 'black');

      expect(result.responseMove).toEqual({ x: 5, y: 4 });
    });

    it('should not include response when none exists', () => {
      const puzzle: Puzzle = {
        ...createTestPuzzle(),
        solutionTree: {
          move: { x: 4, y: 4 },
          isWinning: true,
          // No response
        },
      };
      const state = createSolutionState(puzzle);

      const result = verifyMove(state, { x: 4, y: 4 }, 'black');

      expect(result.responseMove).toBeUndefined();
      expect(result.isComplete).toBe(true);
    });
  });

  describe('advanceSolutionState', () => {
    it('should advance state after correct move', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const result = verifyMove(state, { x: 4, y: 4 }, 'black');
      const newState = advanceSolutionState(
        state,
        result.matchedNode!,
        { x: 4, y: 4 }
      );

      expect(newState.moveHistory).toHaveLength(1);
      expect(newState.moveHistory[0]!.x).toBe(4);
      expect(newState.moveHistory[0]!.y).toBe(4);
    });

    it('should mark complete when reaching winning node', () => {
      const puzzle: Puzzle = {
        ...createTestPuzzle(),
        solutionTree: {
          move: { x: 4, y: 4 },
          isWinning: true,
        },
      };
      const state = createSolutionState(puzzle);
      const result = verifyMove(state, { x: 4, y: 4 }, 'black');
      const newState = advanceSolutionState(
        state,
        result.matchedNode!,
        { x: 4, y: 4 }
      );

      expect(newState.isComplete).toBe(true);
    });
  });

  describe('getValidMoves', () => {
    it('should return root move plus branch moves', () => {
      const puzzle = createMultiBranchPuzzle();
      const state = createSolutionState(puzzle);

      const validMoves = getValidMoves(state);

      // Root (4,4) + branches (5,5) and (3,3) = 3 moves
      expect(validMoves).toHaveLength(3);
      expect(validMoves).toContainEqual({ x: 4, y: 4 });
      expect(validMoves).toContainEqual({ x: 5, y: 5 });
      expect(validMoves).toContainEqual({ x: 3, y: 3 });
    });

    it('should return only root move when no branches', () => {
      const puzzle: Puzzle = {
        ...createTestPuzzle(),
        solutionTree: {
          move: { x: 4, y: 4 },
        },
      };
      const state = createSolutionState(puzzle);

      const validMoves = getValidMoves(state);

      expect(validMoves).toHaveLength(1);
      expect(validMoves[0]).toEqual({ x: 4, y: 4 });
    });
  });

  describe('getHint', () => {
    it('should return optimal move as hint', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const hint = getHint(state, 1);

      expect(hint).toEqual({ x: 4, y: 4 });
    });
  });

  describe('getSolutionPath', () => {
    it('should return moves along main line', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const path = getSolutionPath(state);

      expect(path.length).toBeGreaterThan(0);
      expect(path[0]!.x).toBe(4);
      expect(path[0]!.y).toBe(4);
    });

    it('should alternate colors in path', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const path = getSolutionPath(state);

      if (path.length >= 2) {
        expect(path[0]!.color).toBe(BLACK);
        expect(path[1]!.color).toBe(WHITE);
      }
    });
  });

  describe('hasCorrectMoves', () => {
    it('should return true when solution tree has moves', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      expect(hasCorrectMoves(state)).toBe(true);
    });
  });

  describe('validateMove', () => {
    it('should return not correct for rules-invalid move', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const result = validateMove(puzzle, state, { x: 0, y: 0 }, false);

      expect(result.isCorrect).toBe(false);
      expect(result.explanation).toContain('Invalid move');
    });

    it('should return not correct for wrong move', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const result = validateMove(puzzle, state, { x: 0, y: 0 }, true);

      expect(result.isCorrect).toBe(false);
      expect(result.explanation).toContain('Incorrect');
    });

    it('should return correct for right move', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const result = validateMove(puzzle, state, { x: 4, y: 4 }, true);

      expect(result.isCorrect).toBe(true);
      expect(result.explanation).toContain('Correct');
    });

    it('should include nextNode for correct move', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const result = validateMove(puzzle, state, { x: 4, y: 4 }, true);

      expect(result.nextNode).toBeDefined();
    });

    it('should include response coordinate for correct move with response', () => {
      const puzzle = createTestPuzzle();
      const state = createSolutionState(puzzle);

      const result = validateMove(puzzle, state, { x: 4, y: 4 }, true);

      expect(result.response).toEqual({ x: 5, y: 4 });
    });
  });
});
