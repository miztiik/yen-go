/**
 * Tree Layout Tests
 * @module tests/unit/tree/layout.test.ts
 *
 * Tests for the tree layout algorithm.
 *
 * Feature: 056-solution-tree-visualization
 */

import { describe, it, expect } from 'vitest';
import {
  computeTreeLayout,
  findNodeById,
  computePathToNode,
  collectAllNodes,
  getNodeDepth,
} from '../../../src/lib/tree/layout';
import type { SolutionNode } from '../../../src/types/puzzle-internal';

// Helper to create a simple SolutionNode
function createNode(
  move: string,
  player: 'B' | 'W',
  children: SolutionNode[] = [],
  isCorrect = false
): SolutionNode {
  return {
    move,
    player,
    isCorrect,
    isUserMove: false,
    children,
  };
}

describe('computeTreeLayout', () => {
  it('should compute layout for a single node', () => {
    const tree = createNode('aa', 'B');
    const layout = computeTreeLayout(tree);

    expect(layout.root).toBeDefined();
    expect(layout.root.id).toBe('0');
    expect(layout.root.moveNumber).toBe(1);
    expect(layout.root.layout.x).toBe(0);
    expect(layout.root.layout.y).toBe(0);
    expect(layout.width).toBe(1);
    expect(layout.height).toBe(1);
  });

  it('should compute layout for linear sequence', () => {
    const tree = createNode('aa', 'B', [
      createNode('bb', 'W', [createNode('cc', 'B')]),
    ]);
    const layout = computeTreeLayout(tree);

    expect(layout.width).toBe(3);
    expect(layout.height).toBe(1);

    const nodes = collectAllNodes(layout.root);
    expect(nodes.length).toBe(3);

    // Check depths
    expect(nodes[0].layout.x).toBe(0);
    expect(nodes[1].layout.x).toBe(1);
    expect(nodes[2].layout.x).toBe(2);

    // All on same row
    expect(nodes[0].layout.y).toBe(0);
    expect(nodes[1].layout.y).toBe(0);
    expect(nodes[2].layout.y).toBe(0);
  });

  it('should compute layout for branching tree', () => {
    const tree = createNode('aa', 'B', [
      createNode('bb', 'W'), // First variation
      createNode('cc', 'W'), // Second variation
    ]);
    const layout = computeTreeLayout(tree);

    expect(layout.width).toBe(2);
    expect(layout.height).toBe(2); // Two rows for two variations

    const nodes = collectAllNodes(layout.root);
    expect(nodes.length).toBe(3);

    // Root at (0, 0)
    expect(nodes[0].layout.x).toBe(0);
    expect(nodes[0].layout.y).toBe(0);

    // First child at (1, 0) - continues main line
    expect(nodes[1].layout.x).toBe(1);
    expect(nodes[1].layout.y).toBe(0);

    // Second child at (1, 1) - new row
    expect(nodes[2].layout.x).toBe(1);
    expect(nodes[2].layout.y).toBe(1);
  });

  it('should generate unique IDs for all nodes', () => {
    const tree = createNode('aa', 'B', [
      createNode('bb', 'W', [createNode('dd', 'B')]),
      createNode('cc', 'W', [createNode('ee', 'B')]),
    ]);
    const layout = computeTreeLayout(tree);

    const nodes = collectAllNodes(layout.root);
    const ids = nodes.map((n) => n.id);
    const uniqueIds = new Set(ids);

    expect(uniqueIds.size).toBe(ids.length);
  });

  it('should populate nodeMap for O(1) lookup', () => {
    const tree = createNode('aa', 'B', [createNode('bb', 'W')]);
    const layout = computeTreeLayout(tree);

    expect(layout.nodeMap.size).toBe(2);
    expect(layout.nodeMap.has('0')).toBe(true);
    expect(layout.nodeMap.has('0-0')).toBe(true);
  });

  it('should calculate SVG coordinates', () => {
    const tree = createNode('aa', 'B');
    const layout = computeTreeLayout(tree);

    // Default GRID_SIZE is 120, offset is 60
    expect(layout.root.layout.svgX).toBe(60); // 0 * 120 + 60
    expect(layout.root.layout.svgY).toBe(60); // 0 * 120 + 60
  });

  it('should convert SGF coordinates to display format', () => {
    const tree = createNode('ba', 'B'); // SGF 'ba' = column B, row 1 from top
    const layout = computeTreeLayout(tree);

    // 'ba' -> column 1 (B), row 0 from top -> row 19 in standard notation
    expect(layout.root.displayCoord).toBe('B19');
  });
});

describe('findNodeById', () => {
  it('should find root node by ID', () => {
    const tree = createNode('aa', 'B');
    const layout = computeTreeLayout(tree);

    const found = findNodeById(layout, '0');
    expect(found).toBeDefined();
    expect(found?.node.move).toBe('aa');
  });

  it('should find nested node by ID', () => {
    const tree = createNode('aa', 'B', [
      createNode('bb', 'W', [createNode('cc', 'B')]),
    ]);
    const layout = computeTreeLayout(tree);

    const found = findNodeById(layout, '0-0-0');
    expect(found).toBeDefined();
    expect(found?.node.move).toBe('cc');
  });

  it('should return undefined for non-existent ID', () => {
    const tree = createNode('aa', 'B');
    const layout = computeTreeLayout(tree);

    const found = findNodeById(layout, 'nonexistent');
    expect(found).toBeUndefined();
  });
});

describe('computePathToNode', () => {
  it('should return path from root to node', () => {
    const tree = createNode('aa', 'B', [
      createNode('bb', 'W', [createNode('cc', 'B')]),
    ]);
    const layout = computeTreeLayout(tree);

    const path = computePathToNode(layout, '0-0-0');
    expect(path).toEqual(['0', '0-0', '0-0-0']);
  });

  it('should return single element for root', () => {
    const tree = createNode('aa', 'B');
    const layout = computeTreeLayout(tree);

    const path = computePathToNode(layout, '0');
    expect(path).toEqual(['0']);
  });

  it('should return empty array for non-existent node', () => {
    const tree = createNode('aa', 'B');
    const layout = computeTreeLayout(tree);

    const path = computePathToNode(layout, 'nonexistent');
    expect(path).toEqual([]);
  });
});

describe('collectAllNodes', () => {
  it('should collect all nodes in tree', () => {
    const tree = createNode('aa', 'B', [
      createNode('bb', 'W'),
      createNode('cc', 'W'),
    ]);
    const layout = computeTreeLayout(tree);

    const nodes = collectAllNodes(layout.root);
    expect(nodes.length).toBe(3);
  });

  it('should include root as first element', () => {
    const tree = createNode('aa', 'B', [createNode('bb', 'W')]);
    const layout = computeTreeLayout(tree);

    const nodes = collectAllNodes(layout.root);
    expect(nodes[0].id).toBe('0');
  });
});

describe('getNodeDepth', () => {
  it('should return 0 for root', () => {
    const tree = createNode('aa', 'B');
    const layout = computeTreeLayout(tree);

    expect(getNodeDepth(layout.root)).toBe(0);
  });

  it('should return correct depth for nested nodes', () => {
    const tree = createNode('aa', 'B', [
      createNode('bb', 'W', [createNode('cc', 'B')]),
    ]);
    const layout = computeTreeLayout(tree);

    const leaf = findNodeById(layout, '0-0-0');
    expect(getNodeDepth(leaf!)).toBe(2);
  });
});
