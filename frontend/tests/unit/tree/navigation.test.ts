/**
 * Tree Navigation Tests
 * @module tests/unit/tree/navigation.test.ts
 *
 * Tests for the tree navigation utilities.
 *
 * Feature: 056-solution-tree-visualization
 */

import { describe, it, expect } from 'vitest';
import { computeTreeLayout, findNodeById } from '../../../src/lib/tree/layout';
import {
  findNextSibling,
  findPrevSibling,
  findBranchPoint,
  findNextNode,
  findPrevNode,
  findLastMainLineNode,
  findRoot,
  isBranchPoint,
  isLeaf,
  isOnMainLine,
  countVariations,
} from '../../../src/lib/tree/navigation';
import type { SolutionNode } from '../../../src/types/puzzle-internal';

// Helper to create a simple SolutionNode
function createNode(
  move: string,
  player: 'B' | 'W',
  children: SolutionNode[] = []
): SolutionNode {
  return {
    move,
    player,
    isCorrect: false,
    isUserMove: false,
    children,
  };
}

describe('Sibling Navigation', () => {
  describe('findNextSibling', () => {
    it('should find next sibling', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W'),
        createNode('cc', 'W'),
        createNode('dd', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      const first = findNodeById(layout, '0-0');
      const next = findNextSibling(first!);

      expect(next).toBeDefined();
      expect(next?.node.move).toBe('cc');
    });

    it('should return undefined for last sibling', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W'),
        createNode('cc', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      const last = findNodeById(layout, '0-1');
      const next = findNextSibling(last!);

      expect(next).toBeUndefined();
    });

    it('should return undefined for root (no siblings)', () => {
      const tree = createNode('aa', 'B');
      const layout = computeTreeLayout(tree);

      const next = findNextSibling(layout.root);
      expect(next).toBeUndefined();
    });
  });

  describe('findPrevSibling', () => {
    it('should find previous sibling', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W'),
        createNode('cc', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      const second = findNodeById(layout, '0-1');
      const prev = findPrevSibling(second!);

      expect(prev).toBeDefined();
      expect(prev?.node.move).toBe('bb');
    });

    it('should return undefined for first sibling', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W'),
        createNode('cc', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      const first = findNodeById(layout, '0-0');
      const prev = findPrevSibling(first!);

      expect(prev).toBeUndefined();
    });
  });
});

describe('Branch Navigation', () => {
  describe('findBranchPoint', () => {
    it('should find nearest branch point', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W', [createNode('dd', 'B')]),
        createNode('cc', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      const leaf = findNodeById(layout, '0-0-0');
      const branch = findBranchPoint(leaf!);

      expect(branch).toBeDefined();
      expect(branch?.node.move).toBe('aa');
    });

    it('should return undefined when no branch point exists', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W', [createNode('cc', 'B')]),
      ]);
      const layout = computeTreeLayout(tree);

      const leaf = findNodeById(layout, '0-0-0');
      const branch = findBranchPoint(leaf!);

      expect(branch).toBeUndefined();
    });
  });
});

describe('Linear Navigation', () => {
  describe('findNextNode', () => {
    it('should find first child', () => {
      const tree = createNode('aa', 'B', [createNode('bb', 'W')]);
      const layout = computeTreeLayout(tree);

      const next = findNextNode(layout.root);
      expect(next).toBeDefined();
      expect(next?.node.move).toBe('bb');
    });

    it('should return undefined for leaf', () => {
      const tree = createNode('aa', 'B');
      const layout = computeTreeLayout(tree);

      const next = findNextNode(layout.root);
      expect(next).toBeUndefined();
    });
  });

  describe('findPrevNode', () => {
    it('should find parent', () => {
      const tree = createNode('aa', 'B', [createNode('bb', 'W')]);
      const layout = computeTreeLayout(tree);

      const child = findNodeById(layout, '0-0');
      const prev = findPrevNode(child!);

      expect(prev).toBeDefined();
      expect(prev?.node.move).toBe('aa');
    });

    it('should return undefined for root', () => {
      const tree = createNode('aa', 'B');
      const layout = computeTreeLayout(tree);

      const prev = findPrevNode(layout.root);
      expect(prev).toBeUndefined();
    });
  });

  describe('findLastMainLineNode', () => {
    it('should find leaf of main line', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W', [createNode('cc', 'B')]),
        createNode('dd', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      const last = findLastMainLineNode(layout.root);
      expect(last.node.move).toBe('cc');
    });

    it('should return self if already leaf', () => {
      const tree = createNode('aa', 'B');
      const layout = computeTreeLayout(tree);

      const last = findLastMainLineNode(layout.root);
      expect(last.node.move).toBe('aa');
    });
  });

  describe('findRoot', () => {
    it('should find root from any node', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W', [createNode('cc', 'B')]),
      ]);
      const layout = computeTreeLayout(tree);

      const leaf = findNodeById(layout, '0-0-0');
      const root = findRoot(leaf!);

      expect(root.node.move).toBe('aa');
    });
  });
});

describe('Node Type Checks', () => {
  describe('isBranchPoint', () => {
    it('should return true for node with multiple children', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W'),
        createNode('cc', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      expect(isBranchPoint(layout.root)).toBe(true);
    });

    it('should return false for node with single child', () => {
      const tree = createNode('aa', 'B', [createNode('bb', 'W')]);
      const layout = computeTreeLayout(tree);

      expect(isBranchPoint(layout.root)).toBe(false);
    });
  });

  describe('isLeaf', () => {
    it('should return true for leaf node', () => {
      const tree = createNode('aa', 'B');
      const layout = computeTreeLayout(tree);

      expect(isLeaf(layout.root)).toBe(true);
    });

    it('should return false for internal node', () => {
      const tree = createNode('aa', 'B', [createNode('bb', 'W')]);
      const layout = computeTreeLayout(tree);

      expect(isLeaf(layout.root)).toBe(false);
    });
  });

  describe('isOnMainLine', () => {
    it('should return true for main line nodes', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W', [createNode('cc', 'B')]),
        createNode('dd', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      const mainLineLeaf = findNodeById(layout, '0-0-0');
      expect(isOnMainLine(mainLineLeaf!)).toBe(true);
    });

    it('should return false for variation nodes', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W'),
        createNode('dd', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      const variation = findNodeById(layout, '0-1');
      expect(isOnMainLine(variation!)).toBe(false);
    });
  });

  describe('countVariations', () => {
    it('should count children', () => {
      const tree = createNode('aa', 'B', [
        createNode('bb', 'W'),
        createNode('cc', 'W'),
        createNode('dd', 'W'),
      ]);
      const layout = computeTreeLayout(tree);

      expect(countVariations(layout.root)).toBe(3);
    });

    it('should return 0 for leaf', () => {
      const tree = createNode('aa', 'B');
      const layout = computeTreeLayout(tree);

      expect(countVariations(layout.root)).toBe(0);
    });
  });
});
