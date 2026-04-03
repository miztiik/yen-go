/**
 * Explore Hints Unit Tests
 * @module tests/unit/explore-hints.test
 *
 * Tests for T020: Explore mode hints extraction from solution tree.
 * Covers FR-007, FR-008, FR-009, FR-010.
 */

import { describe, it, expect } from 'vitest';
import {
  getExploreHints,
  getExploreHintsFromTree,
  getOptimalMove,
  isMoveValid,
  type SolutionTreeNode,
} from '../../src/lib/presentation/exploreHints';
import type { Coordinate } from '../../src/models/SolutionPresentation';

// ============================================================================
// Test Data: Solution Trees (using correct `coord` property)
// ============================================================================

/** Simple linear solution (one correct path) */
const LINEAR_SOLUTION: SolutionTreeNode = {
  coord: { x: 2, y: 2 },
  color: 'B',
  isCorrect: true,
  children: [
    {
      coord: { x: 3, y: 3 },
      color: 'W',
      isCorrect: true,
      children: [],
    },
  ],
};

/** Root node with branches (coord is null for root) */
const BRANCHING_ROOT: SolutionTreeNode = {
  coord: null,
  isCorrect: true,
  children: [
    {
      coord: { x: 2, y: 2 },
      color: 'B',
      isCorrect: true,
      children: [],
    },
    {
      coord: { x: 3, y: 3 },
      color: 'B',
      isCorrect: false,
      children: [],
    },
    {
      coord: { x: 4, y: 4 },
      color: 'B',
      isCorrect: false,
      children: [],
    },
  ],
};

/** Node with main line marker */
const MAINLINE_NODE: SolutionTreeNode = {
  coord: null,
  children: [
    {
      coord: { x: 1, y: 1 },
      isCorrect: true,
      isMainLine: false,
      children: [],
    },
    {
      coord: { x: 2, y: 2 },
      isCorrect: true,
      isMainLine: true,
      children: [],
    },
    {
      coord: { x: 3, y: 3 },
      isCorrect: false,
      children: [],
    },
  ],
};

/** Legal moves for testing */
const ALL_LEGAL_MOVES: Coordinate[] = [
  { x: 2, y: 2 },
  { x: 3, y: 3 },
  { x: 4, y: 4 },
  { x: 5, y: 5 }, // Not in solution tree
];

// ============================================================================
// getExploreHints Tests
// ============================================================================

describe('getExploreHints', () => {
  it('should return empty result for null node', () => {
    const result = getExploreHints(null, []);
    
    expect(result.hints).toHaveLength(0);
    expect(result.validMoves).toHaveLength(0);
    expect(result.invalidMoves).toHaveLength(0);
    expect(result.hasHints).toBe(false);
  });

  it('should classify moves from solution tree children', () => {
    const result = getExploreHints(BRANCHING_ROOT, ALL_LEGAL_MOVES);
    
    expect(result.hasHints).toBe(true);
    expect(result.hints.length).toBe(ALL_LEGAL_MOVES.length);
  });

  it('should mark valid moves correctly', () => {
    const result = getExploreHints(BRANCHING_ROOT, ALL_LEGAL_MOVES);
    
    // Only (2,2) is marked as correct in BRANCHING_ROOT
    expect(result.validMoves).toHaveLength(1);
    expect(result.validMoves[0]).toEqual({ x: 2, y: 2 });
  });

  it('should mark invalid moves correctly', () => {
    const result = getExploreHints(BRANCHING_ROOT, ALL_LEGAL_MOVES);
    
    // (3,3), (4,4) are marked incorrect, (5,5) not in tree
    expect(result.invalidMoves).toHaveLength(3);
  });

  it('should include move not in tree as invalid', () => {
    const result = getExploreHints(BRANCHING_ROOT, ALL_LEGAL_MOVES);
    
    const unknownMove = result.hints.find(
      (h) => h.coord.x === 5 && h.coord.y === 5
    );
    expect(unknownMove).toBeDefined();
    expect(unknownMove?.isValid).toBe(false);
    expect(unknownMove?.outcome).toContain('Not in solution tree');
  });

  it('should include coordinate in hints', () => {
    const result = getExploreHints(BRANCHING_ROOT, ALL_LEGAL_MOVES);
    
    result.hints.forEach((hint) => {
      expect(hint.coord).toBeDefined();
      expect(typeof hint.coord.x).toBe('number');
      expect(typeof hint.coord.y).toBe('number');
    });
  });

  it('should use isCorrect=true as default', () => {
    const nodeWithNoIsCorrect: SolutionTreeNode = {
      coord: null,
      children: [
        { coord: { x: 1, y: 1 }, children: [] }, // No isCorrect
      ],
    };

    const result = getExploreHints(nodeWithNoIsCorrect, [{ x: 1, y: 1 }]);
    expect(result.validMoves).toHaveLength(1);
  });
});

// ============================================================================
// getExploreHintsFromTree Tests
// ============================================================================

describe('getExploreHintsFromTree', () => {
  it('should return empty result for null node', () => {
    const result = getExploreHintsFromTree(null);
    
    expect(result.hints).toHaveLength(0);
    expect(result.hasHints).toBe(false);
  });

  it('should return empty for node with no children', () => {
    const leafNode: SolutionTreeNode = {
      coord: { x: 1, y: 1 },
      children: [],
    };

    const result = getExploreHintsFromTree(leafNode);
    expect(result.hasHints).toBe(false);
  });

  it('should extract hints from children only', () => {
    const result = getExploreHintsFromTree(BRANCHING_ROOT);
    
    expect(result.hints).toHaveLength(3); // Only the 3 children
    expect(result.validMoves).toHaveLength(1);
    expect(result.invalidMoves).toHaveLength(2);
  });

  it('should skip children with null coord', () => {
    const nodeWithNullChild: SolutionTreeNode = {
      coord: null,
      children: [
        { coord: null, children: [] }, // Should be skipped
        { coord: { x: 1, y: 1 }, isCorrect: true, children: [] },
      ],
    };

    const result = getExploreHintsFromTree(nodeWithNullChild);
    expect(result.hints).toHaveLength(1);
  });
});

// ============================================================================
// getOptimalMove Tests (takes SolutionTreeNode, not hints array)
// ============================================================================

describe('getOptimalMove', () => {
  it('should return null for null node', () => {
    const optimal = getOptimalMove(null);
    expect(optimal).toBeNull();
  });

  it('should return null for node with no children', () => {
    const leafNode: SolutionTreeNode = {
      coord: { x: 1, y: 1 },
      children: [],
    };

    const optimal = getOptimalMove(leafNode);
    expect(optimal).toBeNull();
  });

  it('should prefer main line move', () => {
    const optimal = getOptimalMove(MAINLINE_NODE);
    
    // Main line is at (2, 2)
    expect(optimal).toEqual({ x: 2, y: 2 });
  });

  it('should return first correct move if no main line', () => {
    const optimal = getOptimalMove(BRANCHING_ROOT);
    
    // First correct child is at (2, 2)
    expect(optimal).toEqual({ x: 2, y: 2 });
  });

  it('should return null if no correct moves', () => {
    const allWrongNode: SolutionTreeNode = {
      coord: null,
      children: [
        { coord: { x: 1, y: 1 }, isCorrect: false, children: [] },
        { coord: { x: 2, y: 2 }, isCorrect: false, children: [] },
      ],
    };

    const optimal = getOptimalMove(allWrongNode);
    expect(optimal).toBeNull();
  });
});

// ============================================================================
// isMoveValid Tests (takes coord and SolutionTreeNode)
// ============================================================================

describe('isMoveValid', () => {
  it('should return false for null node', () => {
    const result = isMoveValid({ x: 2, y: 2 }, null);
    expect(result).toBe(false);
  });

  it('should return true for valid move in tree', () => {
    const result = isMoveValid({ x: 2, y: 2 }, BRANCHING_ROOT);
    expect(result).toBe(true);
  });

  it('should return false for invalid move in tree', () => {
    const result = isMoveValid({ x: 3, y: 3 }, BRANCHING_ROOT);
    expect(result).toBe(false);
  });

  it('should return false for move not in tree', () => {
    const result = isMoveValid({ x: 99, y: 99 }, BRANCHING_ROOT);
    expect(result).toBe(false);
  });
});

// ============================================================================
// Edge Cases
// ============================================================================

describe('edge cases', () => {
  it('should handle deeply nested trees', () => {
    const deepTree: SolutionTreeNode = {
      coord: { x: 0, y: 0 },
      isCorrect: true,
      children: [
        {
          coord: { x: 1, y: 1 },
          isCorrect: true,
          children: [
            {
              coord: { x: 2, y: 2 },
              isCorrect: true,
              children: [],
            },
          ],
        },
      ],
    };

    // Get hints at root level
    const rootHints = getExploreHintsFromTree(deepTree);
    expect(rootHints.hints).toHaveLength(1);

    // Get optimal at root
    const optimal = getOptimalMove(deepTree);
    expect(optimal).toEqual({ x: 1, y: 1 });
  });

  it('should handle multiple valid moves at same position', () => {
    const multiValid: SolutionTreeNode = {
      coord: null,
      children: [
        { coord: { x: 1, y: 1 }, isCorrect: true, children: [] },
        { coord: { x: 2, y: 2 }, isCorrect: true, children: [] },
      ],
    };

    const result = getExploreHintsFromTree(multiValid);
    expect(result.validMoves).toHaveLength(2);
  });

  it('should preserve outcome/comment in hints', () => {
    const nodeWithComments: SolutionTreeNode = {
      coord: null,
      children: [
        {
          coord: { x: 1, y: 1 },
          isCorrect: true,
          comment: 'Good move!',
          children: [],
        },
      ],
    };

    const result = getExploreHintsFromTree(nodeWithComments);
    expect(result.hints[0].outcome).toBe('Good move!');
  });
});
