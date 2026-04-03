/**
 * Tree Navigation Hook Tests
 * @module tests/unit/tree-nav-hook.test.ts
 *
 * Unit tests for useTreeNavigation hook.
 * Covers: T029-T032 (sibling/branch navigation)
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, act, cleanup } from '@testing-library/preact';
import { useTreeNavigation } from '../../src/hooks/useTreeNavigation';
import type { SolutionNode } from '../../src/types/puzzle-internal';

// ============================================================================
// Test Fixtures
// ============================================================================

/**
 * Create a simple linear tree: root -> A -> B -> C
 * IDs: '0' -> '0-0' -> '0-0-0' -> '0-0-0-0'
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
  afterEach(() => {
    cleanup();
  });

  describe('Initial State', () => {
    it('should start at root node', () => {
      const tree = createLinearTree();
      const { result } = renderHook(() => useTreeNavigation({ tree }));

      expect(result.current.state.current.id).toBe('0');
      expect(result.current.state.current.node.move).toBe('root');
      expect(result.current.state.currentPath).toEqual(['0']);
      expect(result.current.moveNumber).toBe(1);
    });

    it('should accept initial node ID', () => {
      const tree = createLinearTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0' })
      );

      expect(result.current.state.current.id).toBe('0-0');
      expect(result.current.state.current.node.move).toBe('aa');
    });
  });

  describe('Basic Navigation', () => {
    it('should navigate forward to first child', () => {
      const tree = createLinearTree();
      const { result } = renderHook(() => useTreeNavigation({ tree }));

      act(() => {
        result.current.next();
      });

      expect(result.current.state.current.id).toBe('0-0');
      expect(result.current.state.current.node.move).toBe('aa');
    });

    it('should navigate backward to parent', () => {
      const tree = createLinearTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0' })
      );

      act(() => {
        result.current.prev();
      });

      expect(result.current.state.current.id).toBe('0');
      expect(result.current.state.current.node.move).toBe('root');
    });

    it('should navigate to specific node', () => {
      const tree = createLinearTree();
      const { result } = renderHook(() => useTreeNavigation({ tree }));

      act(() => {
        result.current.goTo('0-0-0');
      });

      expect(result.current.state.current.id).toBe('0-0-0');
      expect(result.current.state.currentPath).toEqual(['0', '0-0', '0-0-0']);
    });

    it('should reset to root', () => {
      const tree = createLinearTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0-0-0' })
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
      const tree = createBranchingTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0' })
      );

      expect(result.current.hasSiblings).toBe(true);

      act(() => {
        result.current.nextSibling();
      });

      expect(result.current.state.current.id).toBe('0-1');
      expect(result.current.state.current.node.move).toBe('ab');
    });

    it('should stay in place when no next sibling', () => {
      const tree = createBranchingTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-1' })
      );

      const initialId = result.current.state.current.id;

      act(() => {
        result.current.nextSibling();
      });

      expect(result.current.state.current.id).toBe(initialId);
    });

    it('should navigate to previous sibling', () => {
      const tree = createBranchingTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-1' })
      );

      act(() => {
        result.current.prevSibling();
      });

      expect(result.current.state.current.id).toBe('0-0');
      expect(result.current.state.current.node.move).toBe('aa');
    });

    it('should stay in place when no previous sibling', () => {
      const tree = createBranchingTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0' })
      );

      const initialId = result.current.state.current.id;

      act(() => {
        result.current.prevSibling();
      });

      expect(result.current.state.current.id).toBe(initialId);
    });

    it('should not change position when no siblings', () => {
      const tree = createLinearTree();
      const { result } = renderHook(() => useTreeNavigation({ tree }));

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
      const tree = createBranchingTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0-0' })
      );

      act(() => {
        result.current.toBranchPoint();
      });

      expect(result.current.state.current.id).toBe('0-0');
    });

    it('should navigate to root branch point from deep node', () => {
      const tree = createBranchingTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0' })
      );

      act(() => {
        result.current.toBranchPoint();
      });

      expect(result.current.state.current.id).toBe('0');
    });

    it('should stay in place when no branch points', () => {
      const tree = createLinearTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0-0-0' })
      );

      const initialId = result.current.state.current.id;

      act(() => {
        result.current.toBranchPoint();
      });

      expect(result.current.state.current.id).toBe(initialId);
    });
  });

  describe('Comment Handling', () => {
    it('should include comment in state when present', () => {
      const tree = createTreeWithComments();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0' })
      );

      expect(result.current.comment).toBe('Good move! This threatens the corner.');
    });

    it('should have null comment when not present', () => {
      const tree = createLinearTree();
      const { result } = renderHook(() => useTreeNavigation({ tree }));

      expect(result.current.comment).toBeNull();
    });
  });

  describe('Computed Properties', () => {
    it('should report hasSiblings correctly', () => {
      const linearTree = createLinearTree();
      const { result: linearResult } = renderHook(() =>
        useTreeNavigation({ tree: linearTree })
      );
      expect(linearResult.current.hasSiblings).toBe(false);

      const branchTree = createBranchingTree();
      const { result: branchResult } = renderHook(() =>
        useTreeNavigation({ tree: branchTree, initialNodeId: '0-0' })
      );
      expect(branchResult.current.hasSiblings).toBe(true);
    });

    it('should report isAtBranchPoint correctly', () => {
      const tree = createBranchingTree();
      const { result } = renderHook(() => useTreeNavigation({ tree }));

      expect(result.current.isAtBranchPoint).toBe(true);

      act(() => {
        result.current.goTo('0-1');
      });

      expect(result.current.isAtBranchPoint).toBe(false);
    });

    it('should provide siblings list', () => {
      const tree = createBranchingTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, initialNodeId: '0-0' })
      );

      expect(result.current.siblings).toHaveLength(2);
      expect(result.current.siblings.map((s) => s.id)).toEqual(['0-0', '0-1']);
    });
  });

  describe('Navigation Callback', () => {
    it('should call onChange when position changes', () => {
      const onChange = vi.fn();
      const tree = createLinearTree();
      const { result } = renderHook(() =>
        useTreeNavigation({ tree, onChange })
      );

      onChange.mockClear();

      act(() => {
        result.current.next();
      });

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          current: expect.objectContaining({ id: '0-0' }),
          currentPath: ['0', '0-0'],
        })
      );
    });
  });
});
