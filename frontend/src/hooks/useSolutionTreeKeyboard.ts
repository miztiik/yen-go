/**
 * useSolutionTreeKeyboard Hook
 * @module hooks/useSolutionTreeKeyboard
 *
 * Provides keyboard navigation for the solution tree.
 * Supports arrow keys for navigation per NFR-011-014.
 *
 * Covers: T055 - Keyboard navigation for SolutionTree
 */

import { useCallback, useEffect, useRef } from 'preact/hooks';
import type { TreeNodeData } from '@/components/SolutionTree/SolutionTree';

// ============================================================================
// Types
// ============================================================================

export interface UseSolutionTreeKeyboardOptions {
  /** Tree data structure */
  treeData: TreeNodeData | null;
  /** Current focused node ID */
  focusedNodeId: string | null;
  /** Handler when a node is selected */
  onNodeSelect?: (nodeId: string) => void;
  /** Handler when focus changes */
  onFocusChange?: (nodeId: string) => void;
  /** Whether keyboard navigation is enabled */
  enabled?: boolean;
}

export interface UseSolutionTreeKeyboardResult {
  /** Ref to attach to the tree container */
  containerRef: React.RefObject<HTMLDivElement>;
  /** Currently focused node ID */
  focusedNodeId: string | null;
  /** Move focus to next node */
  focusNext: () => void;
  /** Move focus to previous node */
  focusPrevious: () => void;
  /** Move focus to first child */
  focusFirstChild: () => void;
  /** Move focus to parent */
  focusParent: () => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Flatten tree into array of nodes with parent info
 */
function flattenTree(
  node: TreeNodeData,
  parentId: string | null = null
): Array<{ node: TreeNodeData; parentId: string | null }> {
  const result: Array<{ node: TreeNodeData; parentId: string | null }> = [
    { node, parentId },
  ];

  for (const child of node.children) {
    result.push(...flattenTree(child, node.id));
  }

  return result;
}

/**
 * Find a node by ID in the tree
 */
function findNode(tree: TreeNodeData, id: string): TreeNodeData | null {
  if (tree.id === id) return tree;
  
  for (const child of tree.children) {
    const found = findNode(child, id);
    if (found) return found;
  }
  
  return null;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook for keyboard navigation in the solution tree
 *
 * Arrow key bindings:
 * - ArrowDown: Move to next node (depth-first)
 * - ArrowUp: Move to previous node (depth-first)
 * - ArrowRight: Move to first child
 * - ArrowLeft: Move to parent
 * - Enter/Space: Select current node
 */
export function useSolutionTreeKeyboard({
  treeData,
  focusedNodeId,
  onNodeSelect,
  onFocusChange,
  enabled = true,
}: UseSolutionTreeKeyboardOptions): UseSolutionTreeKeyboardResult {
  const containerRef = useRef<HTMLDivElement>(null);

  // Flatten tree for linear navigation
  const flatNodes = treeData ? flattenTree(treeData) : [];

  // Get current index in flat list
  const getCurrentIndex = useCallback(() => {
    if (!focusedNodeId) return -1;
    return flatNodes.findIndex((n) => n.node.id === focusedNodeId);
  }, [flatNodes, focusedNodeId]);

  // Navigation functions
  const focusNext = useCallback(() => {
    const currentIndex = getCurrentIndex();
    if (currentIndex < flatNodes.length - 1) {
      const nextNode = flatNodes[currentIndex + 1];
      if (nextNode) {
        onFocusChange?.(nextNode.node.id);
      }
    }
  }, [getCurrentIndex, flatNodes, onFocusChange]);

  const focusPrevious = useCallback(() => {
    const currentIndex = getCurrentIndex();
    if (currentIndex > 0) {
      const prevNode = flatNodes[currentIndex - 1];
      if (prevNode) {
        onFocusChange?.(prevNode.node.id);
      }
    }
  }, [getCurrentIndex, flatNodes, onFocusChange]);

  const focusFirstChild = useCallback(() => {
    if (!focusedNodeId || !treeData) return;
    const currentNode = findNode(treeData, focusedNodeId);
    if (currentNode && currentNode.children.length > 0) {
      const firstChild = currentNode.children[0];
      if (firstChild) {
        onFocusChange?.(firstChild.id);
      }
    }
  }, [focusedNodeId, treeData, onFocusChange]);

  const focusParent = useCallback(() => {
    if (!focusedNodeId) return;
    const nodeInfo = flatNodes.find((n) => n.node.id === focusedNodeId);
    if (nodeInfo?.parentId) {
      onFocusChange?.(nodeInfo.parentId);
    }
  }, [focusedNodeId, flatNodes, onFocusChange]);

  // Handle keyboard events
  useEffect(() => {
    if (!enabled || !containerRef.current) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if focus is within container
      if (!containerRef.current?.contains(document.activeElement)) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          focusNext();
          break;
        case 'ArrowUp':
          e.preventDefault();
          focusPrevious();
          break;
        case 'ArrowRight':
          e.preventDefault();
          focusFirstChild();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          focusParent();
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          if (focusedNodeId) {
            onNodeSelect?.(focusedNodeId);
          }
          break;
        case 'Home':
          e.preventDefault();
          if (flatNodes.length > 0 && flatNodes[0]) {
            onFocusChange?.(flatNodes[0].node.id);
          }
          break;
        case 'End':
          e.preventDefault();
          if (flatNodes.length > 0) {
            const lastNode = flatNodes[flatNodes.length - 1];
            if (lastNode) {
              onFocusChange?.(lastNode.node.id);
            }
          }
          break;
      }
    };

    const container = containerRef.current;
    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    enabled,
    focusedNodeId,
    flatNodes,
    focusNext,
    focusPrevious,
    focusFirstChild,
    focusParent,
    onNodeSelect,
    onFocusChange,
  ]);

  // Focus management - scroll focused node into view
  useEffect(() => {
    if (!focusedNodeId || !containerRef.current) return;

    const focusedElement = containerRef.current.querySelector(
      `[data-testid="tree-node-${focusedNodeId}"]`
    );
    
    if (focusedElement instanceof HTMLElement) {
      focusedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      focusedElement.focus();
    }
  }, [focusedNodeId]);

  return {
    containerRef,
    focusedNodeId,
    focusNext,
    focusPrevious,
    focusFirstChild,
    focusParent,
  };
}

export default useSolutionTreeKeyboard;
