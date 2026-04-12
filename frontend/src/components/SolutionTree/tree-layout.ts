/**
 * Solution Tree Layout Algorithm
 * @module components/SolutionTree/tree-layout
 *
 * Ported from Besogo's treePanel.js
 * Uses reverse path building with intelligent bends.
 *
 * Feature: 123-solution-tree-rewrite
 *
 * Constitution Compliance:
 * - VI. Type Safety: Full TypeScript
 * - V. No Browser AI: Layout only, no move generation
 */

import type { SolutionNode } from '../../types/puzzle-internal';
import type { VisualTreeNode, TreeLayoutResult, TreeNodeLayout } from '../../types/tree';

// ============================================================================
// Constants (matching Besogo)
// ============================================================================

export const GRID_SIZE = 140;
const STONE_OFFSET = GRID_SIZE / 2; // 70
export const TREE_PADDING = 1;

// ============================================================================
// Coordinate Helpers
// ============================================================================

/**
 * Convert grid position to SVG coordinate.
 * Matches Besogo's svgPos function.
 */
function svgPos(gridPos: number): number {
  return gridPos * GRID_SIZE + STONE_OFFSET;
}

/**
 * Convert SGF coordinate to human-readable format (e.g., "ba" -> "B1").
 */
function formatCoord(move: string): string {
  if (!move || move.length < 2) return '';
  const col = move.charCodeAt(0) - 'a'.charCodeAt(0);
  const row = move.charCodeAt(1) - 'a'.charCodeAt(0);
  const colLetter = String.fromCharCode('A'.charCodeAt(0) + col);
  // SGF row 'a' is top (19 in 19x19), convert to 1-based from bottom
  return `${colLetter}${19 - row}`;
}

// ============================================================================
// Layout Computation
// ============================================================================

/**
 * Compute the visual tree layout from a solution tree.
 * Port of Besogo's recursiveTreeBuild placement logic.
 */
export function computeTreeLayout(root: SolutionNode): TreeLayoutResult {
  const nodeMap = new Map<string, VisualTreeNode>();
  const nextOpen: number[] = []; // nextOpen[x] = next available y at column x

  // Build tree recursively, tracking positions
  function buildNode(
    node: SolutionNode,
    x: number,
    suggestedY: number,
    parent: VisualTreeNode | null,
    moveNum: number
  ): VisualTreeNode {
    // Initialize nextOpen for this column if needed
    while (nextOpen.length <= x) {
      nextOpen.push(0);
    }

    // Find available position (max of suggested and next open)
    const y = Math.max(suggestedY, nextOpen[x] ?? 0);

    // Create layout
    const layout: TreeNodeLayout = {
      x,
      y,
      svgX: svgPos(x),
      svgY: svgPos(y),
    };

    // Create visual node
    const visual: VisualTreeNode = {
      id: parent ? `${parent.id}-${parent.children.length}` : '0',
      node,
      layout,
      parent,
      children: [],
      moveNumber: node.move ? moveNum : 0,
      displayCoord: node.move ? formatCoord(node.move) : '',
    };

    // Register in map
    nodeMap.set(visual.id, visual);

    // Process children
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i];
      if (!child) continue;
      const childY = nextOpen[x + 1] ?? y;
      const childMoveNum = child.move ? moveNum + 1 : moveNum;
      const childVisual = buildNode(child, x + 1, childY, visual, childMoveNum);
      visual.children.push(childVisual);
    }

    // Claim this position
    nextOpen[x] = y + 1;

    return visual;
  }

  const rootVisual = buildNode(root, 0, 0, null, root.move ? 1 : 0);

  // Calculate dimensions
  const maxX = Math.max(...Array.from({ length: nextOpen.length }, (_, i) => i));
  const maxY = Math.max(...nextOpen) - 1;

  const width = maxX + 1 + TREE_PADDING * 2;
  const height = Math.max(maxY + 1, 1) + TREE_PADDING * 2;

  return {
    root: rootVisual,
    width,
    height,
    viewBox: {
      width: width * GRID_SIZE,
      height: height * GRID_SIZE,
    },
    nodeMap,
  };
}

// ============================================================================
// Path Building (Besogo's connected path algorithm)
// ============================================================================

/**
 * SVG path element for a tree branch
 */
export interface BranchPath {
  /** SVG path 'd' attribute value */
  d: string;
  /** Whether this branch contains the current node */
  isCurrentPath: boolean;
}

/**
 * Build SVG paths for all branches in the tree.
 * Port of Besogo's recursiveTreeBuild path construction.
 *
 * Key insight: Paths are built from leaf to root as recursion unwinds,
 * using relative SVG commands (h, v, l) for connected lines.
 */
export function buildBranchPaths(layout: TreeLayoutResult, currentNodeId: string): BranchPath[] {
  const paths: BranchPath[] = [];

  // Get ancestors of current node for highlighting
  const currentAncestors = getAncestorIds(layout.nodeMap.get(currentNodeId));

  // Track next available position per column (for path calculation)
  const nextOpen: number[] = [];

  /**
   * Recursively build paths for a subtree.
   * Returns the path string for the main branch (first child path).
   */
  function buildPaths(node: VisualTreeNode): string {
    // Initialize nextOpen for this column
    while (nextOpen.length <= node.layout.x + 1) {
      nextOpen.push(0);
    }

    if (node.children.length === 0) {
      // LEAF: Start new path at this position
      return `m${node.layout.svgX},${node.layout.svgY}`;
    }

    // NON-LEAF: Process children first (DFS)

    // First child: continues main path
    const firstChild = node.children[0];
    if (!firstChild) {
      return `m${node.layout.svgX},${node.layout.svgY}`;
    }
    const firstChildPath = buildPaths(firstChild);
    const mainPath = firstChildPath + extendPath(node.layout, firstChild.layout, nextOpen);

    // Other children: create separate branch paths
    for (let i = 1; i < node.children.length; i++) {
      const child = node.children[i];
      const prevChild = node.children[i - 1];
      if (!child || !prevChild) continue;

      const prevChildY = prevChild.layout.y;
      const childPath = buildPaths(child);
      const fullPath =
        childPath + extendPathWithPrev(node.layout, child.layout, nextOpen, prevChildY);

      // Check if this branch contains current node
      const isCurrentPath = currentAncestors.has(node.id) && currentAncestors.has(child.id);

      paths.push({ d: fullPath, isCurrentPath });
    }

    // Claim position
    nextOpen[node.layout.x] = node.layout.y + 1;

    return mainPath;
  }

  // Start from root - the main path is added last
  const mainPath = buildPaths(layout.root);
  const firstRootChild = layout.root.children[0];
  const isMainCurrent: boolean =
    currentAncestors.has(layout.root.id) &&
    (layout.root.children.length === 0 ||
      (firstRootChild !== undefined && currentAncestors.has(firstRootChild.id)));

  paths.unshift({ d: mainPath, isCurrentPath: isMainCurrent });

  return paths;
}

/**
 * Create path segment from child back to parent.
 * Port of Besogo's extendPath function.
 */
function extendPath(parent: TreeNodeLayout, child: TreeNodeLayout, _nextOpen: number[]): string {
  const dy = parent.y - child.y; // How many rows up

  if (dy === 0) {
    // Same row: horizontal line back
    return `h-${GRID_SIZE}`;
  } else if (dy === -1) {
    // Child one row below: single diagonal up-left
    return `l-${GRID_SIZE},-${GRID_SIZE}`;
  } else {
    // Multi-row: diagonal + vertical + diagonal
    const half = GRID_SIZE / 2;
    const verticalDist = GRID_SIZE * (-dy - 1);
    return `l-${half},-${half}v-${verticalDist}l-${half},-${half}`;
  }
}

/**
 * Create path segment for variation branches.
 * Connects to the drop line from previous sibling.
 */
function extendPathWithPrev(
  parent: TreeNodeLayout,
  child: TreeNodeLayout,
  _nextOpen: number[],
  prevChildY: number
): string {
  const dy = parent.y - child.y;

  if (dy === 0) {
    return `h-${GRID_SIZE}`;
  } else if (dy === -1) {
    return `l-${GRID_SIZE},-${GRID_SIZE}`;
  } else if (prevChildY !== parent.y) {
    // Connect to previous variation's line
    const half = GRID_SIZE / 2;
    const verticalDist = GRID_SIZE * (child.y - prevChildY);
    return `l-${half},-${half}v-${verticalDist}`;
  } else {
    const half = GRID_SIZE / 2;
    const verticalDist = GRID_SIZE * (-dy - 1);
    return `l-${half},-${half}v-${verticalDist}l-${half},-${half}`;
  }
}

/**
 * Get set of ancestor IDs from a node up to root.
 */
function getAncestorIds(node: VisualTreeNode | undefined): Set<string> {
  const ids = new Set<string>();
  let current = node;
  while (current) {
    ids.add(current.id);
    current = current.parent ?? undefined;
  }
  return ids;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Collect all nodes in the tree (for rendering).
 */
export function collectAllNodes(root: VisualTreeNode): VisualTreeNode[] {
  const nodes: VisualTreeNode[] = [];

  function traverse(node: VisualTreeNode): void {
    nodes.push(node);
    for (const child of node.children) {
      traverse(child);
    }
  }

  traverse(root);
  return nodes;
}

/**
 * Get path from root to a specific node (IDs).
 */
export function getPathToNode(nodeMap: Map<string, VisualTreeNode>, nodeId: string): string[] {
  const node = nodeMap.get(nodeId);
  if (!node) return [];

  const path: string[] = [];
  let current: VisualTreeNode | null = node;
  while (current) {
    path.unshift(current.id);
    current = current.parent;
  }
  return path;
}
