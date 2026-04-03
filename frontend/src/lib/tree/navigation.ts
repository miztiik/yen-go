/**
 * Tree Navigation Functions
 * @module lib/tree/navigation
 *
 * Functions for navigating the solution tree.
 * Supports keyboard navigation and programmatic traversal.
 *
 * Feature: 056-solution-tree-visualization
 * Tasks: T015-T017 (Phase 4)
 *
 * Constitution Compliance:
 * - VI. Type Safety: Full TypeScript types
 * - X. Accessibility: Supports keyboard navigation
 */

import type { VisualTreeNode } from '../../types/tree';

// ============================================================================
// Sibling Navigation
// ============================================================================

/**
 * Finds the next sibling of a node.
 * Siblings are nodes with the same parent.
 *
 * @param node - Current node
 * @returns Next sibling or undefined if last/no siblings
 */
export function findNextSibling(
  node: VisualTreeNode
): VisualTreeNode | undefined {
  if (!node.parent) {
    return undefined;
  }

  const siblings = node.parent.children;
  const currentIndex = siblings.findIndex((s) => s.id === node.id);

  if (currentIndex < 0 || currentIndex >= siblings.length - 1) {
    return undefined;
  }

  return siblings[currentIndex + 1];
}

/**
 * Finds the previous sibling of a node.
 *
 * @param node - Current node
 * @returns Previous sibling or undefined if first/no siblings
 */
export function findPrevSibling(
  node: VisualTreeNode
): VisualTreeNode | undefined {
  if (!node.parent) {
    return undefined;
  }

  const siblings = node.parent.children;
  const currentIndex = siblings.findIndex((s) => s.id === node.id);

  if (currentIndex <= 0) {
    return undefined;
  }

  return siblings[currentIndex - 1];
}

// ============================================================================
// Branch Navigation
// ============================================================================

/**
 * Finds the previous branch point (node with multiple children).
 * Used for "go back to last decision point" navigation.
 *
 * @param node - Current node
 * @returns Branch point ancestor or root if none found
 */
export function findBranchPoint(
  node: VisualTreeNode
): VisualTreeNode | undefined {
  let current = node.parent;

  while (current) {
    // Branch point has more than one child
    if (current.children.length > 1) {
      return current;
    }
    current = current.parent;
  }

  // No branch point found, return root
  return undefined;
}

/**
 * Finds all branch points from current node to root.
 *
 * @param node - Current node
 * @returns Array of branch point nodes (nearest first)
 */
export function findAllBranchPoints(node: VisualTreeNode): VisualTreeNode[] {
  const branchPoints: VisualTreeNode[] = [];
  let current = node.parent;

  while (current) {
    if (current.children.length > 1) {
      branchPoints.push(current);
    }
    current = current.parent;
  }

  return branchPoints;
}

// ============================================================================
// Linear Navigation
// ============================================================================

/**
 * Finds the next node in the tree (first child).
 * Follows the main line (first variation).
 *
 * @param node - Current node
 * @returns First child or undefined if leaf
 */
export function findNextNode(node: VisualTreeNode): VisualTreeNode | undefined {
  return node.children[0];
}

/**
 * Finds the previous node (parent).
 *
 * @param node - Current node
 * @returns Parent or undefined if root
 */
export function findPrevNode(node: VisualTreeNode): VisualTreeNode | undefined {
  return node.parent ?? undefined;
}

/**
 * Finds the last node in the main line from current position.
 *
 * @param node - Starting node
 * @returns Last node (leaf) following main line
 */
export function findLastMainLineNode(node: VisualTreeNode): VisualTreeNode {
  let current = node;

  while (current.children.length > 0) {
    const firstChild = current.children[0];
    if (!firstChild) break;
    current = firstChild; // Follow first variation
  }

  return current;
}

/**
 * Finds the root node from any position.
 *
 * @param node - Any node in tree
 * @returns Root node
 */
export function findRoot(node: VisualTreeNode): VisualTreeNode {
  let current = node;

  while (current.parent) {
    current = current.parent;
  }

  return current;
}

// ============================================================================
// Path-based Navigation
// ============================================================================

/**
 * Finds a node by following a path of child indices from root.
 *
 * @param root - Root node
 * @param path - Array of child indices (e.g., [0, 1, 0] = first, second, first)
 * @returns Node at path or undefined if path is invalid
 */
export function findNodeByPath(
  root: VisualTreeNode,
  path: number[]
): VisualTreeNode | undefined {
  let current: VisualTreeNode = root;

  for (const index of path) {
    if (index < 0 || index >= current.children.length) {
      return undefined;
    }
    const nextNode = current.children[index];
    if (!nextNode) return undefined;
    current = nextNode;
  }

  return current;
}

/**
 * Gets the path (array of child indices) from root to a node.
 *
 * @param node - Target node
 * @returns Array of child indices from root
 */
export function getPathFromRoot(node: VisualTreeNode): number[] {
  const path: number[] = [];
  let current = node;

  while (current.parent) {
    const siblings = current.parent.children;
    const index = siblings.findIndex((s) => s.id === current.id);
    path.unshift(index);
    current = current.parent;
  }

  return path;
}

// ============================================================================
// Variation Counting
// ============================================================================

/**
 * Counts the number of variations at a node.
 *
 * @param node - Node to check
 * @returns Number of children (variations)
 */
export function countVariations(node: VisualTreeNode): number {
  return node.children.length;
}

/**
 * Checks if a node is a branch point (has multiple variations).
 *
 * @param node - Node to check
 * @returns True if node has more than one child
 */
export function isBranchPoint(node: VisualTreeNode): boolean {
  return node.children.length > 1;
}

/**
 * Checks if a node is a leaf (no children).
 *
 * @param node - Node to check
 * @returns True if node has no children
 */
export function isLeaf(node: VisualTreeNode): boolean {
  return node.children.length === 0;
}

/**
 * Checks if a node is on the main line (first variation at each branch).
 *
 * @param node - Node to check
 * @returns True if node is on main line
 */
export function isOnMainLine(node: VisualTreeNode): boolean {
  let current = node;

  while (current.parent) {
    const siblings = current.parent.children;
    const firstSibling = siblings[0];
    if (!firstSibling || firstSibling.id !== current.id) {
      return false;
    }
    current = current.parent;
  }

  return true;
}
