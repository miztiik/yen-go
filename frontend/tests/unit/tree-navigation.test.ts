/**
 * Tree Navigation Tests
 * @module tests/unit/tree-navigation.test.ts
 *
 * Unit tests for useTreeNavigation hook.
 * Covers: T029-T032 (sibling/branch navigation)
 *
 * NOTE: This test file was previously skipped due to a suspected import hang.
 * Investigation (Feb 2026) showed the imports work correctly. Tests were
 * updated to match the actual hook API (next/prev/reset vs forward/backward/goToRoot).
 *
 * IMPORTANT: Tests run sequentially (not parallel) to avoid hook cleanup issues.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, cleanup } from '@testing-library/preact';
import { useTreeNavigation } from '../../src/hooks/useTreeNavigation';
import type { SolutionNode } from '../../src/types/puzzle-internal';

// ============================================================================
// Test Fixtures
// ============================================================================

/**
 * Create a simple linear tree: root -> A -> B -> C
 * IDs will be: '0' -> '0-0' -> '0-0-0' -> '0-0-0-0'
 */
function createLinearTree(): SolutionNode {
  return {
    move: 'root',
    player: 'B',
    isCorrect: true,
    isUserMove: true,
    children: [
      {
        move: 'aa',
        player: 'W',
        isCorrect: true,
        isUserMove: false,
        children: [
          {
            move: 'bb',
            player: 'B',
            isCorrect: true,
            isUserMove: true,
            children: [
              {
                move: 'cc',
                player: 'W',
                isCorrect: true,
                isUserMove: false,
                children: [],
              },
            ],
          },
        ],
      },
    ],
  };
}

/**
 * Create a tree with branches:
 *       root (0)
 *      /    \
 *   A1(0-0)  A2(0-1)
 *    / \
 * B1(0-0-0) B2(0-0-1)
 */
function createBranchingTree(): SolutionNode {
  return {
    move: 'root',
    player: 'B',
    isCorrect: true,
    isUserMove: true,
    children: [
      {
        move: 'aa',
        player: 'W',
        isCorrect: true,
        isUserMove: false,
        children: [
          {
            move: 'bb',
            player: 'B',
            isCorrect: true,
            isUserMove: true,
            children: [],
          },
          {
            move: 'bc',
            player: 'B',
            isCorrect: false,
            isUserMove: true,
            children: [],
          },
        ],
      },
      {
        move: 'ab',
        player: 'W',
        isCorrect: false,
        isUserMove: false,
        children: [],
      },
    ],
  };
}

/**
 * Create a tree with comments.
 */
function createTreeWithComments(): SolutionNode {
  return {
    move: 'root',
    player: 'B',
    isCorrect: true,
    isUserMove: true,
    children: [
      {
        move: 'aa',
        player: 'W',
        isCorrect: true,
        isUserMove: false,
        comment: 'Good move! This threatens the corner.',
        children: [],
      },
    ],
  };
}

// ============================================================================
// Tests
// ============================================================================

describe('useTreeNavigation', () => {
  // Clean up after each test to avoid leaks
  afterEach(() => {
    cleanup();
  });
  describe('Initial State', () => {
    it('should start at root node', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({ tree: createLinearTree() })
      );

      expect(result.current.state.current.id).toBe('0');
      expect(result.current.state.current.node.move).toBe('root');
      expect(result.current.state.currentPath).toEqual(['0']);
      expect(result.current.moveNumber).toBe(1);
    });

    it('should accept initial node ID', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createLinearTree(),
          initialNodeId: '0-0',
        })
      );

      expect(result.current.state.current.id).toBe('0-0');
      expect(result.current.state.current.node.move).toBe('aa');
    });
  });

  describe('Basic Navigation', () => {
    it('should navigate forward to first child', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({ tree: createLinearTree() })
      );

      act(() => {
        result.current.next();
      });

      expect(result.current.state.current.id).toBe('0-0');
      expect(result.current.state.current.node.move).toBe('aa');
    });

    it('should navigate backward to parent', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createLinearTree(),
          initialNodeId: '0-0',
        })
      );

      act(() => {
        result.current.prev();
      });

      expect(result.current.state.current.id).toBe('0');
      expect(result.current.state.current.node.move).toBe('root');
    });

    it('should navigate to specific node', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({ tree: createLinearTree() })
      );

      act(() => {
        result.current.goTo('0-0-0');
      });

      expect(result.current.state.current.id).toBe('0-0-0');
      expect(result.current.state.currentPath).toEqual(['0', '0-0', '0-0-0']);
    });

    it('should navigate to root (reset)', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createLinearTree(),
          initialNodeId: '0-0-0-0',
        })
      );

      act(() => {
        result.current.reset();
      });

      expect(result.current.state.current.id).toBe('0');
      expect(result.current.state.current.node.move).toBe('root');
    });
  });

  describe('FR-010: Sibling Navigation', () => {
    it('should navigate to next sibling', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createBranchingTree(),
          initialNodeId: '0-0', // First child of root
        })
      );

      expect(result.current.hasSiblings).toBe(true);

      act(() => {
        result.current.nextSibling();
      });

      expect(result.current.state.current.id).toBe('0-1');
      expect(result.current.state.current.node.move).toBe('ab');
    });

    it('should not cycle to first sibling from last (returns undefined)', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createBranchingTree(),
          initialNodeId: '0-1', // Second child of root
        })
      );

      const initialId = result.current.state.current.id;

      act(() => {
        result.current.nextSibling();
      });

      // No next sibling, stays in place
      expect(result.current.state.current.id).toBe(initialId);
    });

    it('should navigate to previous sibling', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createBranchingTree(),
          initialNodeId: '0-1', // Second child of root
        })
      );

      act(() => {
        result.current.prevSibling();
      });

      expect(result.current.state.current.id).toBe('0-0');
      expect(result.current.state.current.node.move).toBe('aa');
    });

    it('should not cycle to last sibling from first (returns undefined)', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createBranchingTree(),
          initialNodeId: '0-0', // First child of root
        })
      );

      const initialId = result.current.state.current.id;

      act(() => {
        result.current.prevSibling();
      });

      // No previous sibling, stays in place
      expect(result.current.state.current.id).toBe(initialId);
    });

    it('should not change position when no siblings', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({ tree: createLinearTree() })
      );

      expect(result.current.hasSiblings).toBe(false);

      const initialId = result.current.state.current.id;

      act(() => {
        result.current.nextSibling();
      });

      expect(result.current.state.current.id).toBe(initialId);
    });
  });

  describe('FR-011: Branch Point Navigation', () => {
    it('should navigate to previous branch point', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createBranchingTree(),
          initialNodeId: '0-0-0', // Deep in first branch (B1)
        })
      );

      act(() => {
        result.current.toBranchPoint();
      });

      // Should jump to parent which has multiple children (0-0 has B1 and B2)
      expect(result.current.state.current.id).toBe('0-0');
    });

    it('should navigate to root branch point from deep node', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createBranchingTree(),
          initialNodeId: '0-0', // First child of root
        })
      );

      act(() => {
        result.current.toBranchPoint();
      });

      // Root has multiple children (A1 and A2), so should go to root
      expect(result.current.state.current.id).toBe('0');
    });

    it('should not change position when no branch points', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createLinearTree(),
          initialNodeId: '0-0-0-0', // Last node in linear tree
        })
      );

      const initialId = result.current.state.current.id;

      act(() => {
        result.current.toBranchPoint();
      });

      // No branch points in linear tree
      expect(result.current.state.current.id).toBe(initialId);
    });
  });

  describe('Comment Handling', () => {
    it('should include comment in state when present', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createTreeWithComments(),
          initialNodeId: '0-0',
        })
      );

      expect(result.current.comment).toBe('Good move! This threatens the corner.');
    });

    it('should have null comment when not present', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({ tree: createLinearTree() })
      );

      expect(result.current.comment).toBeNull();
    });
  });

  describe('Navigation Callback (FR-016/FR-017)', () => {
    it('should call onChange when position changes', () => {
      const onChange = vi.fn();

      const { result } = renderHook(() =>
        useTreeNavigation({
          tree: createLinearTree(),
          onChange,
        })
      );

      // Clear initial call
      onChange.mockClear();

      act(() => {
        result.current.next();
      });

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          current: expect.objectContaining({
            id: '0-0',
          }),
          currentPath: ['0', '0-0'],
        })
      );
    });
  });

  describe('Computed Properties', () => {
    it('should report hasSiblings correctly', () => {
      const { result: linearResult } = renderHook(() =>
        useTreeNavigation({ tree: createLinearTree() })
      );
      expect(linearResult.current.hasSiblings).toBe(false);

      const { result: branchResult } = renderHook(() =>
        useTreeNavigation({ tree: createBranchingTree(), initialNodeId: '0-0' })
      );
      expect(branchResult.current.hasSiblings).toBe(true);
    });

    it('should report isAtBranchPoint correctly', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({ tree: createBranchingTree() })
      );

      // Root has 2 children, so is a branch point
      expect(result.current.isAtBranchPoint).toBe(true);

      act(() => {
        result.current.goTo('0-1'); // Go to leaf node A2
      });

      // Leaf has no children, not a branch point
      expect(result.current.isAtBranchPoint).toBe(false);
    });

    it('should provide siblings list', () => {
      const { result } = renderHook(() =>
        useTreeNavigation({ tree: createBranchingTree(), initialNodeId: '0-0' })
      );

      expect(result.current.siblings).toHaveLength(2);
      expect(result.current.siblings.map((s) => s.id)).toEqual(['0-0', '0-1']);
    });
  });
});
