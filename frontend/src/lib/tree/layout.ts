/**
 * Tree Layout Algorithm
 * @module lib/tree/layout
 *
 * Computes layout positions for solution tree visualization.
 * Ported from Besogo's recursiveTreeBuild() approach.
 *
 * Algorithm:
 * - X axis = depth (move number, column)
 * - Y axis = variation index (row, increments for each branch)
 * - Uses DFS traversal, tracking consumed rows
 *
 * Feature: 056-solution-tree-visualization
 * Tasks: T005, T006, T007, T008
 *
 * Constitution Compliance:
 * - VI. Type Safety: Full TypeScript types
 * - V. No Browser AI: Layout only, no move generation
 */

import type { SolutionNode } from '../../types/puzzle-internal';
import type {
  VisualTreeNode,
  TreeLayoutResult,
  TreeNodeLayout,
} from '../../types/tree';
import { GRID_SIZE, GRID_OFFSET, TREE_PADDING } from './constants';
import { sgfToDisplayCoord, calculateViewBox } from './svg-utils';

// ============================================================================
// Main Layout Function
// ============================================================================

/**
 * Computes layout for entire solution tree.
 * This is the main entry point for tree visualization.
 *
 * @param tree - Root of solution tree from SGF parser
 * @param boardSize - Board size for coordinate display (default 19)
 * @returns TreeLayoutResult with positioned nodes and metadata
 */
export function computeTreeLayout(
  tree: SolutionNode,
  boardSize = 19
): TreeLayoutResult {
  const nodeMap = new Map<string, VisualTreeNode>();
  let maxY = 0;

  /**
   * Recursive layout builder.
   * Based on Besogo's recursiveTreeBuild().
   *
   * @param node - Current solution node
   * @param depth - Depth from root (x coordinate)
   * @param y - Current row (y coordinate)
   * @param parent - Parent visual node
   * @param moveNumber - Current move number (1-based)
   * @param idPrefix - ID prefix for unique identification
   * @returns Visual node and next available y coordinate
   */
  function buildLayout(
    node: SolutionNode,
    depth: number,
    y: number,
    parent: VisualTreeNode | null,
    moveNumber: number,
    idPrefix: string
  ): { visualNode: VisualTreeNode; nextY: number } {
    // Create layout position
    const layout = createNodeLayout(depth, y);

    // Generate unique ID
    const id = idPrefix || '0';

    // Create visual node
    const visualNode: VisualTreeNode = {
      id,
      node,
      layout,
      parent,
      children: [],
      moveNumber,
      displayCoord: sgfToDisplayCoord(node.move, boardSize),
    };

    // Register in node map
    nodeMap.set(id, visualNode);

    // Track max Y for height calculation
    maxY = Math.max(maxY, y);

    // Process children
    let nextY = y;
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i];
      if (!child) continue; // Skip undefined children
      const childId = `${id}-${i}`;

      // For first child, continue at same Y (main line)
      // For subsequent children, use next available Y (variations)
      const childY = i === 0 ? nextY : nextY + 1;

      const result = buildLayout(
        child,
        depth + 1,
        childY,
        visualNode,
        moveNumber + 1,
        childId
      );

      visualNode.children.push(result.visualNode);
      nextY = Math.max(nextY, result.nextY);
    }

    return {
      visualNode,
      nextY: visualNode.children.length > 0 ? nextY : y,
    };
  }

  // Build layout starting from root
  const { visualNode: root } = buildLayout(
    tree,
    0, // depth
    0, // y
    null, // parent
    1, // moveNumber
    '0' // idPrefix
  );

  // Calculate dimensions
  const maxDepth = getMaxDepth(root);
  const width = maxDepth + 1; // +1 because depth is 0-indexed
  const finalHeight = maxY + 1;

  // Calculate viewBox
  const viewBox = calculateViewBox(width, finalHeight, TREE_PADDING);

  return {
    root,
    width,
    height: finalHeight,
    viewBox: {
      width: viewBox.width,
      height: viewBox.height,
    },
    nodeMap,
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Creates layout position for a node.
 *
 * @param x - Grid x position (depth)
 * @param y - Grid y position (variation)
 * @returns TreeNodeLayout with SVG coordinates
 */
function createNodeLayout(x: number, y: number): TreeNodeLayout {
  return {
    x,
    y,
    svgX: x * GRID_SIZE + GRID_OFFSET,
    svgY: y * GRID_SIZE + GRID_OFFSET,
  };
}

/**
 * Gets the maximum depth (x coordinate) in the tree.
 *
 * @param node - Root visual node
 * @returns Maximum depth
 */
function getMaxDepth(node: VisualTreeNode): number {
  if (node.children.length === 0) {
    return node.layout.x;
  }
  return Math.max(...node.children.map(getMaxDepth));
}

// ============================================================================
// Node Lookup Functions
// ============================================================================

/**
 * Finds a node by ID in the tree.
 * Uses the nodeMap for O(1) lookup.
 *
 * @param layout - Tree layout result
 * @param nodeId - ID to find
 * @returns VisualTreeNode or undefined
 */
export function findNodeById(
  layout: TreeLayoutResult,
  nodeId: string
): VisualTreeNode | undefined {
  return layout.nodeMap.get(nodeId);
}

/**
 * Computes the path from root to a specific node.
 * Returns array of node IDs from root to target.
 *
 * @param layout - Tree layout result
 * @param nodeId - Target node ID
 * @returns Array of node IDs (empty if node not found)
 */
export function computePathToNode(
  layout: TreeLayoutResult,
  nodeId: string
): string[] {
  const node = findNodeById(layout, nodeId);
  if (!node) {
    return [];
  }

  const path: string[] = [];
  let current: VisualTreeNode | null = node;

  while (current) {
    path.unshift(current.id);
    current = current.parent;
  }

  return path;
}

/**
 * Collects all nodes in the tree into a flat array.
 * Useful for iteration and rendering.
 *
 * @param root - Root visual node
 * @returns Array of all nodes
 */
export function collectAllNodes(root: VisualTreeNode): VisualTreeNode[] {
  const nodes: VisualTreeNode[] = [root];

  function collect(node: VisualTreeNode): void {
    for (const child of node.children) {
      nodes.push(child);
      collect(child);
    }
  }

  collect(root);
  return nodes;
}

/**
 * Gets the depth (distance from root) of a node.
 *
 * @param node - Visual tree node
 * @returns Depth (0 for root)
 */
export function getNodeDepth(node: VisualTreeNode): number {
  let depth = 0;
  let current: VisualTreeNode | null = node;

  while (current?.parent) {
    depth++;
    current = current.parent;
  }

  return depth;
}

// ============================================================================
// Edge Collection
// ============================================================================

/**
 * Collects all edges (parent-child pairs) in the tree.
 * Useful for rendering connecting lines.
 *
 * @param root - Root visual node
 * @returns Array of [parent, child] pairs
 */
export function collectEdges(
  root: VisualTreeNode
): Array<[VisualTreeNode, VisualTreeNode]> {
  const edges: Array<[VisualTreeNode, VisualTreeNode]> = [];

  function collect(node: VisualTreeNode): void {
    for (const child of node.children) {
      edges.push([node, child]);
      collect(child);
    }
  }

  collect(root);
  return edges;
}

/**
 * Collects edges that are part of the current path.
 *
 * @param root - Root visual node
 * @param currentPath - Array of node IDs in current path
 * @returns Array of [parent, child] pairs on the path
 */
export function collectPathEdges(
  root: VisualTreeNode,
  currentPath: string[]
): Array<[VisualTreeNode, VisualTreeNode]> {
  const pathSet = new Set(currentPath);
  const edges: Array<[VisualTreeNode, VisualTreeNode]> = [];

  function collect(node: VisualTreeNode): void {
    for (const child of node.children) {
      if (pathSet.has(node.id) && pathSet.has(child.id)) {
        edges.push([node, child]);
      }
      collect(child);
    }
  }

  collect(root);
  return edges;
}
