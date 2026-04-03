/**
 * Solution Tree Builder Unit Tests
 * @module tests/unit/solution-tree.test
 *
 * Tests for T007: Solution tree extraction from parsed SGF.
 * Tests the conversion from SGFNode to SolutionNode.
 *
 * TDD approach: Tests written before implementation.
 */

import { describe, it, expect } from 'vitest';
import type { SGFNode, ParsedSGF } from '../../src/types/sgf';
import type { SolutionNode } from '../../src/types/puzzle-internal';
import { buildSolutionTree, findMove, validatePath } from '../../src/lib/sgf-solution';

// ============================================================================
// Test Data: SGF Nodes (Simulated Parse Results)
// ============================================================================

/**
 * Simple linear solution: Black plays, White responds, Black finishes.
 */
const LINEAR_SGF_ROOT: SGFNode = {
  properties: {
    FF: '4',
    GM: '1',
    SZ: '9',
    AB: ['aa', 'ba', 'ca'],
    AW: ['ab', 'bb'],
    PL: 'B',
  },
  children: [
    {
      properties: { B: 'cb' },
      children: [
        {
          properties: { W: 'da' },
          children: [
            {
              properties: { B: 'db' },
              children: [],
            },
          ],
        },
      ],
    },
  ],
};

/**
 * Branching solution: Two correct first moves.
 */
const BRANCHING_SGF_ROOT: SGFNode = {
  properties: {
    FF: '4',
    GM: '1',
    SZ: '9',
    AB: ['aa', 'ba'],
    AW: ['ab'],
    PL: 'B',
  },
  children: [
    // First variation: B plays 'ca'
    {
      properties: { B: 'ca' },
      children: [
        {
          properties: { W: 'da' },
          children: [
            {
              properties: { B: 'ea' },
              children: [],
            },
          ],
        },
      ],
    },
    // Second variation: B plays 'cb'
    {
      properties: { B: 'cb' },
      children: [
        {
          properties: { W: 'db' },
          children: [
            {
              properties: { B: 'eb' },
              children: [],
            },
          ],
        },
      ],
    },
  ],
};

/**
 * White to move puzzle.
 */
const WHITE_TO_MOVE_ROOT: SGFNode = {
  properties: {
    FF: '4',
    GM: '1',
    SZ: '9',
    AB: ['aa', 'ba'],
    AW: ['ab', 'bb'],
    PL: 'W',
  },
  children: [
    {
      properties: { W: 'ca' },
      children: [
        {
          properties: { B: 'da' },
          children: [
            {
              properties: { W: 'ea' },
              children: [],
            },
          ],
        },
      ],
    },
  ],
};

/**
 * Multiple opponent responses to one move.
 */
const MULTIPLE_RESPONSES_ROOT: SGFNode = {
  properties: {
    FF: '4',
    GM: '1',
    SZ: '9',
    AB: ['aa'],
    AW: ['ab'],
    PL: 'B',
  },
  children: [
    {
      properties: { B: 'ba' },
      children: [
        // Opponent might respond with two different moves
        {
          properties: { W: 'ca' },
          children: [{ properties: { B: 'da' }, children: [] }],
        },
        {
          properties: { W: 'cb' },
          children: [{ properties: { B: 'db' }, children: [] }],
        },
      ],
    },
  ],
};

// ============================================================================
// Solution Tree Building Tests (T007)
// ============================================================================

describe('Solution Tree Builder', () => {
  describe('buildSolutionTree()', () => {
    it('builds tree from linear SGF', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      // Virtual root has one child (the first move)
      expect(tree.children.length).toBe(1);
      expect(tree.children[0]?.move).toBe('cb');
      expect(tree.children[0]?.player).toBe('B');
      expect(tree.children[0]?.isCorrect).toBe(true);
      expect(tree.children[0]?.isUserMove).toBe(true);
    });

    it('marks all SGF nodes as isCorrect=true', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      const firstMove = tree.children[0];
      expect(firstMove?.isCorrect).toBe(true);
      expect(firstMove?.children[0]?.isCorrect).toBe(true); // W response
      expect(firstMove?.children[0]?.children[0]?.isCorrect).toBe(true); // B finish
    });

    it('marks user moves vs opponent responses', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      const firstMove = tree.children[0];
      expect(firstMove?.isUserMove).toBe(true); // B plays (user)
      expect(firstMove?.children[0]?.isUserMove).toBe(false); // W responds (opponent)
      expect(firstMove?.children[0]?.children[0]?.isUserMove).toBe(true); // B plays (user)
    });

    it('handles branching solutions (multiple first moves)', () => {
      const tree = buildSolutionTree(BRANCHING_SGF_ROOT, 'B');
      // Virtual root with two children
      expect(tree.children.length).toBe(2);
      expect(tree.children[0]?.move).toBe('ca');
      expect(tree.children[1]?.move).toBe('cb');
    });

    it('handles White to move puzzles', () => {
      const tree = buildSolutionTree(WHITE_TO_MOVE_ROOT, 'W');
      expect(tree.children[0]?.move).toBe('ca');
      expect(tree.children[0]?.player).toBe('W');
      expect(tree.children[0]?.isUserMove).toBe(true);
      expect(tree.children[0]?.children[0]?.isUserMove).toBe(false); // B responds
    });

    it('handles multiple opponent responses', () => {
      const tree = buildSolutionTree(MULTIPLE_RESPONSES_ROOT, 'B');
      const firstMove = tree.children[0];
      expect(firstMove?.children.length).toBe(2); // Two opponent responses
      expect(firstMove?.children[0]?.move).toBe('ca');
      expect(firstMove?.children[1]?.move).toBe('cb');
    });

    it('returns empty tree for root with no moves', () => {
      const emptyRoot: SGFNode = {
        properties: { FF: '4', GM: '1', SZ: '9', PL: 'B' },
        children: [],
      };
      const tree = buildSolutionTree(emptyRoot, 'B');
      expect(tree.children).toEqual([]);
    });
  });

  describe('findMove()', () => {
    it('finds existing move in tree', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      const found = findMove(tree, 'cb');
      expect(found).not.toBeNull();
      expect(found?.move).toBe('cb');
    });

    it('returns null for move not in tree', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      const found = findMove(tree, 'zz');
      expect(found).toBeNull();
    });

    it('finds move in branching tree', () => {
      const tree = buildSolutionTree(BRANCHING_SGF_ROOT, 'B');
      const foundA = findMove(tree, 'ca');
      const foundB = findMove(tree, 'cb');
      expect(foundA).not.toBeNull();
      expect(foundB).not.toBeNull();
    });

    it('finds deeply nested move', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      // First, traverse to the position after first move
      const afterFirst = tree.children[0]?.children[0]; // W response node
      if (!afterFirst) throw new Error('Expected response node');
      const finalMove = findMove(afterFirst, 'db');
      expect(finalMove).not.toBeNull();
    });
  });

  describe('validatePath()', () => {
    it('returns true for correct move sequence', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      const isValid = validatePath(tree, ['cb', 'da', 'db']);
      expect(isValid).toBe(true);
    });

    it('returns false for incorrect first move', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      const isValid = validatePath(tree, ['zz']);
      expect(isValid).toBe(false);
    });

    it('returns false for wrong move in sequence', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      const isValid = validatePath(tree, ['cb', 'da', 'zz']);
      expect(isValid).toBe(false);
    });

    it('returns true for partial correct path', () => {
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      const isValid = validatePath(tree, ['cb']);
      expect(isValid).toBe(true);
    });

    it('returns true for either branch in branching tree', () => {
      const tree = buildSolutionTree(BRANCHING_SGF_ROOT, 'B');
      expect(validatePath(tree, ['ca'])).toBe(true);
      expect(validatePath(tree, ['cb'])).toBe(true);
    });
  });

  describe('Wrong Move Handling', () => {
    it('creates dead-end node for wrong move', () => {
      // When user plays a move not in the tree, we create a transient node
      // This is done by the component/verifier, not the builder
      // But we test that such nodes can be attached
      
      const tree = buildSolutionTree(LINEAR_SGF_ROOT, 'B');
      const wrongNode: SolutionNode = {
        move: 'zz',
        player: 'B',
        isCorrect: false,
        isUserMove: true,
        children: [],
      };
      tree.children.push(wrongNode);
      expect(tree.children.some((n: SolutionNode) => !n.isCorrect)).toBe(true);
    });
  });
});

// ============================================================================
// Solution Node Type Tests
// ============================================================================

describe('SolutionNode Type', () => {
  it('has correct shape', () => {
    const node: SolutionNode = {
      move: 'dd',
      player: 'B',
      isCorrect: true,
      isUserMove: true,
      children: [],
    };
    expect(node.move).toBe('dd');
    expect(node.player).toBe('B');
    expect(node.isCorrect).toBe(true);
    expect(node.isUserMove).toBe(true);
    expect(node.children).toEqual([]);
  });

  it('can have nested children', () => {
    const root: SolutionNode = {
      move: 'aa',
      player: 'B',
      isCorrect: true,
      isUserMove: true,
      children: [
        {
          move: 'bb',
          player: 'W',
          isCorrect: true,
          isUserMove: false,
          children: [
            {
              move: 'cc',
              player: 'B',
              isCorrect: true,
              isUserMove: true,
              children: [],
            },
          ],
        },
      ],
    };
    expect(root.children[0].children[0].move).toBe('cc');
  });

  it('can have optional comment', () => {
    const node: SolutionNode = {
      move: 'dd',
      player: 'B',
      isCorrect: true,
      isUserMove: true,
      children: [],
      comment: 'This is the key move!',
    };
    expect(node.comment).toBe('This is the key move!');
  });
});

// ============================================================================
// Spec 012: BM/TE Property Detection Tests
// ============================================================================

describe('Spec 012: Wrong Move Detection (BM[], comments)', () => {
  /**
   * SGF with BM[] (Bad Move) property marking a wrong move
   */
  const SGF_WITH_BM_PROPERTY: SGFNode = {
    properties: {
      FF: '4',
      GM: '1',
      SZ: '9',
      AB: ['aa', 'ba'],
      AW: ['ab'],
      PL: 'B',
    },
    children: [
      {
        properties: { B: 'ca' }, // Correct first move
        children: [],
      },
      {
        properties: { B: 'cb', BM: '1' }, // Wrong move marked with BM[]
        children: [],
      },
    ],
  };

  it('marks node with BM[] property as isCorrect: false', () => {
    const tree = buildSolutionTree(SGF_WITH_BM_PROPERTY, 'B');
    
    // First move should be correct
    expect(tree.children[0].isCorrect).toBe(true);
    expect(tree.children[0].move).toBe('ca');
    
    // Second move has BM[] so should be wrong
    expect(tree.children[1].isCorrect).toBe(false);
    expect(tree.children[1].move).toBe('cb');
  });

  /**
   * SGF with comment indicating wrong move
   */
  const SGF_WITH_WRONG_COMMENT: SGFNode = {
    properties: {
      FF: '4',
      GM: '1',
      SZ: '9',
      AB: ['aa'],
      PL: 'B',
    },
    children: [
      {
        properties: { B: 'ca', C: 'This is the correct move!' },
        children: [],
      },
      {
        properties: { B: 'cb', C: 'Wrong - White can escape' },
        children: [],
      },
    ],
  };

  it('marks node with "wrong" in comment as isCorrect: false', () => {
    const tree = buildSolutionTree(SGF_WITH_WRONG_COMMENT, 'B');
    
    expect(tree.children[0].isCorrect).toBe(true);
    expect(tree.children[1].isCorrect).toBe(false);
    expect(tree.children[1].comment).toContain('Wrong');
  });

  /**
   * SGF with Chinese/Japanese wrong indicators
   */
  const SGF_WITH_CJK_COMMENT: SGFNode = {
    properties: {
      FF: '4',
      GM: '1',
      SZ: '9',
      AB: ['aa'],
      PL: 'B',
    },
    children: [
      {
        properties: { B: 'ca', C: '失敗 - White lives' }, // Japanese: failure
        children: [],
      },
      {
        properties: { B: 'cb', C: '不正解' }, // Japanese: incorrect answer
        children: [],
      },
    ],
  };

  it('marks node with CJK wrong indicators in comment as isCorrect: false', () => {
    const tree = buildSolutionTree(SGF_WITH_CJK_COMMENT, 'B');
    
    expect(tree.children[0].isCorrect).toBe(false); // 失敗
    expect(tree.children[1].isCorrect).toBe(false); // 不正解
  });
});

describe('Spec 012: Tesuji Detection (TE[])', () => {
  /**
   * SGF with TE[] (Tesuji) property marking a key technique move
   */
  const SGF_WITH_TE_PROPERTY: SGFNode = {
    properties: {
      FF: '4',
      GM: '1',
      SZ: '9',
      AB: ['aa', 'ba'],
      AW: ['ab'],
      PL: 'B',
    },
    children: [
      {
        properties: { B: 'ca', TE: '1' }, // Tesuji move marked with TE[]
        children: [],
      },
      {
        properties: { B: 'cb' }, // Normal move (no TE)
        children: [],
      },
    ],
  };

  it('marks node with TE[] property as isTesuji: true', () => {
    const tree = buildSolutionTree(SGF_WITH_TE_PROPERTY, 'B');
    
    // First move has TE[] so should have isTesuji
    expect(tree.children[0].isTesuji).toBe(true);
    expect(tree.children[0].isCorrect).toBe(true);
    
    // Second move has no TE[] so should NOT have isTesuji
    expect(tree.children[1].isTesuji).toBeUndefined();
  });

  /**
   * SGF with both BM[] and TE[] (edge case - data error)
   */
  const SGF_WITH_BM_AND_TE: SGFNode = {
    properties: {
      FF: '4',
      GM: '1',
      SZ: '9',
      AB: ['aa'],
      PL: 'B',
    },
    children: [
      {
        properties: { B: 'ca', BM: '1', TE: '1' }, // Contradictory - both BM and TE
        children: [],
      },
    ],
  };

  it('handles node with both BM[] and TE[] (data error case)', () => {
    const tree = buildSolutionTree(SGF_WITH_BM_AND_TE, 'B');
    
    // BM takes precedence for isCorrect (marked wrong)
    expect(tree.children[0].isCorrect).toBe(false);
    // TE still sets isTesuji (both properties evaluated independently)
    expect(tree.children[0].isTesuji).toBe(true);
  });

  /**
   * Spec 021: Pipeline-marked sibling refutation (BM[1] + C[Wrong])
   * After mark_sibling_refutations() in the backend pipeline, unmarked
   * wrong siblings get BM[1] + C[Wrong]. The frontend must detect these.
   */
  const SGF_PIPELINE_MARKED_REFUTATION: SGFNode = {
    properties: {
      FF: '4',
      GM: '1',
      SZ: '9',
      AB: ['aa', 'ba'],
      AW: ['ab', 'bb'],
      PL: 'B',
    },
    children: [
      {
        properties: { B: 'ca', C: 'RIGHT' },
        children: [],
      },
      {
        properties: { B: 'da', BM: '1', C: 'Wrong' }, // pipeline-marked
        children: [],
      },
    ],
  };

  it('detects pipeline-marked sibling refutation (BM[1] + C[Wrong])', () => {
    const tree = buildSolutionTree(SGF_PIPELINE_MARKED_REFUTATION, 'B');

    // Correct sibling
    expect(tree.children[0].isCorrect).toBe(true);
    // Pipeline-marked wrong sibling
    expect(tree.children[1].isCorrect).toBe(false);
  });
});

// ============================================================================
// Export Test Data
// ============================================================================

export const SOLUTION_TREE_TEST_DATA = {
  LINEAR_SGF_ROOT,
  BRANCHING_SGF_ROOT,
  WHITE_TO_MOVE_ROOT,
  MULTIPLE_RESPONSES_ROOT,
};
