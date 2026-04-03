/**
 * PuzzleView Utilities
 * @module pages/PuzzleView/utils
 *
 * Helper functions for the PuzzleView module.
 * Extracted from PuzzleView.tsx for better modularity.
 */

import type { SolutionNodeWithComment } from './types';

/**
 * Get current player color from side
 */
export function sideToColor(side: 'B' | 'W'): 'black' | 'white' {
  return side === 'B' ? 'black' : 'white';
}

/**
 * Find the path of moves from root to a target node in the solution tree.
 * Returns array of moves (SGF coordinates) to reach the target.
 *
 * @param root - Solution tree root node
 * @param targetNodeId - Target node ID in format "{depth}-{move}"
 * @returns Array of moves to reach target, or null if not found
 */
export function findPathToNode(
  root: { move: string; children: Array<{ move: string; children: unknown[] }> },
  targetNodeId: string
): string[] | null {
  // Parse targetNodeId: format is "{depth}-{move}"
  const [depthStr, targetMove] = targetNodeId.split('-');
  const targetDepth = parseInt(depthStr ?? '0', 10);

  // BFS to find the path
  const queue: Array<{
    node: { move: string; children: Array<{ move: string; children: unknown[] }> };
    depth: number;
    path: string[];
  }> = [{ node: root, depth: 0, path: [] }];

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) break;
    const { node, depth, path } = current;

    // Check if this is the target node
    if (depth === targetDepth && node.move === targetMove) {
      return path;
    }

    // Add children to queue
    for (const child of node.children) {
      queue.push({
        node: child as { move: string; children: Array<{ move: string; children: unknown[] }> },
        depth: depth + 1,
        path: [...path, child.move],
      });
    }
  }

  return null;
}

/**
 * Convert currentPath (array of "{depth}-{move}" strings) to tree-index ID format.
 *
 * Tree-index format: "0" for root, "0-0" for first child, "0-0-1" for second grandchild, etc.
 * currentPath format: ["1-cc", "2-dd"] where depth is move number and move is SGF coord
 *
 * @param tree - Solution tree root
 * @param currentPath - Array of path node IDs in "{depth}-{move}" format
 * @returns Tree-index ID (e.g., "0-0-1") or "0" if at root
 */
export function pathToTreeNodeId(
  tree: { move: string; children: Array<{ move: string; children: unknown[] }> },
  currentPath: string[]
): string {
  if (currentPath.length === 0) {
    return '0'; // Root
  }
  
  let id = '0';
  let current: { move: string; children: Array<{ move: string; children: unknown[] }> } = tree;
  
  for (const pathId of currentPath) {
    // Extract move from "{depth}-{move}" format
    const parts = pathId.split('-');
    const move = parts.slice(1).join('-'); // Handle case where move contains '-'
    
    // Find child index with matching move
    const childIndex = current.children.findIndex(c => c.move === move);
    if (childIndex === -1) {
      // Move not found, return current position
      break;
    }
    
    id = `${id}-${childIndex}`;
    current = current.children[childIndex] as typeof current;
  }
  
  return id;
}

/**
 * Find the current node based on path and extract its comment.
 * @returns The node's comment and isCorrect status, or null if not found
 */
export function getCurrentNodeInfo(
  root: SolutionNodeWithComment,
  currentPath: string[]
): { comment: string | null; isCorrect: boolean; move: string; moveNumber: number } | null {
  if (currentPath.length === 0) {
    return null; // At root, no comment to show
  }

  // Navigate to current node
  let current: SolutionNodeWithComment = root;
  let lastMove = '';
  for (const pathId of currentPath) {
    const [, move] = pathId.split('-');
    const child = current.children.find(c => c.move === move);
    if (!child) return null;
    current = child;
    lastMove = move ?? '';
  }

  return {
    comment: current.comment ?? null,
    isCorrect: current.isCorrect !== false, // Default to correct if not specified
    move: lastMove,
    moveNumber: currentPath.length,
  };
}

/**
 * Get theme colors from CSS variables
 */
export const theme = {
  primary: 'var(--color-info)',
  primaryDark: 'var(--color-accent-hover)',
  primaryLight: 'var(--color-info-bg)',
  bgLight: 'var(--color-bg-primary)',
  bgWhite: 'var(--color-bg-elevated)',
  bgPanel: 'var(--color-bg-secondary)',
  text: 'var(--color-text-primary)',
  textSecondary: 'var(--color-text-secondary)',
  textMuted: 'var(--color-text-muted)',
  border: 'var(--color-panel-border)',
  borderLight: 'var(--color-card-border)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  error: 'var(--color-error)',
  board: 'var(--color-board-wood)',
};
