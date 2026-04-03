/**
 * Tree Keyboard Navigation Hook
 * @module hooks/useTreeKeyboard
 *
 * Provides keyboard navigation for the solution tree.
 * Restored and improved from deleted useSolutionTreeKeyboard.ts
 *
 * Spec: 122-frontend-comprehensive-refactor
 * Tasks: T1.1, T1.2
 *
 * Key bindings:
 * - ArrowDown: Next node (first child, depth-first)
 * - ArrowUp: Previous node (parent)
 * - ArrowRight: First child
 * - ArrowLeft: Parent
 * - Home: Go to root
 * - End: Go to last node in main line
 * - Enter/Space: Select current node
 *
 * CRITICAL: Prevents board rotation bug - uses stopPropagation
 */

import { useCallback, useRef } from 'preact/hooks';
import type { VisualTreeNode, TreeLayoutResult } from '../types/tree';
import {
  findNextNode,
  findPrevNode,
  findRoot,
  findLastMainLineNode,
  findNextSibling,
  findPrevSibling,
} from '../lib/tree/navigation';

/**
 * Options for useTreeKeyboard hook
 */
export interface UseTreeKeyboardOptions {
  /** Current layout result from computeTreeLayout */
  layout: TreeLayoutResult;
  /** Currently focused/selected node */
  currentNode: VisualTreeNode;
  /** Callback when navigation changes the current node */
  onNavigate: (node: VisualTreeNode) => void;
  /** Callback when Enter/Space is pressed on current node */
  onSelect?: (node: VisualTreeNode) => void;
  /** Whether keyboard navigation is enabled (default: true) */
  enabled?: boolean;
}

/**
 * Result of useTreeKeyboard hook
 */
export interface UseTreeKeyboardResult {
  /** Keydown event handler to attach to container element */
  handleKeyDown: (event: KeyboardEvent) => void;
  /** Ref for the container element that receives focus */
  containerRef: preact.RefObject<HTMLDivElement>;
  /** Programmatically focus the tree container */
  focus: () => void;
}

/**
 * Hook for keyboard navigation in solution tree.
 *
 * Usage:
 * ```tsx
 * const { handleKeyDown, containerRef } = useTreeKeyboard({
 *   layout,
 *   currentNode,
 *   onNavigate: (node) => dispatch({ type: 'GOTO', node }),
 * });
 *
 * return (
 *   <div ref={containerRef} onKeyDown={handleKeyDown} tabIndex={0}>
 *     <SolutionTreeSvg ... />
 *   </div>
 * );
 * ```
 */
export function useTreeKeyboard(
  options: UseTreeKeyboardOptions
): UseTreeKeyboardResult {
  const { 
    layout, 
    currentNode, 
    onNavigate, 
    onSelect,
    enabled = true 
  } = options;
  
  const containerRef = useRef<HTMLDivElement>(null);

  /**
   * Navigate to a target node if it exists
   */
  const navigateTo = useCallback(
    (target: VisualTreeNode | undefined) => {
      if (target && enabled) {
        onNavigate(target);
      }
    },
    [onNavigate, enabled]
  );

  /**
   * Find the last node in depth-first order from the current node
   */
  const findLastNode = useCallback((): VisualTreeNode => {
    return findLastMainLineNode(findRoot(currentNode));
  }, [currentNode]);

  /**
   * Find next node in depth-first order (down the tree)
   * Prefers first child, then next sibling, then parent's next sibling
   */
  const findNextDepthFirst = useCallback(
    (node: VisualTreeNode): VisualTreeNode | undefined => {
      // First, try first child
      if (node.children.length > 0) {
        return node.children[0];
      }

      // Then, try next sibling
      const nextSibling = findNextSibling(node);
      if (nextSibling) {
        return nextSibling;
      }

      // Finally, go up and try parent's next sibling
      let current: VisualTreeNode | null = node.parent;
      while (current) {
        const parentNextSibling = findNextSibling(current);
        if (parentNextSibling) {
          return parentNextSibling;
        }
        current = current.parent;
      }

      return undefined;
    },
    []
  );

  /**
   * Find previous node in depth-first order (up the tree)
   * Goes to previous sibling's last descendant, or parent
   */
  const findPrevDepthFirst = useCallback(
    (node: VisualTreeNode): VisualTreeNode | undefined => {
      // Try previous sibling
      const prevSibling = findPrevSibling(node);
      if (prevSibling) {
        // Go to the last node in that sibling's subtree
        return findLastMainLineNode(prevSibling);
      }

      // Otherwise, go to parent
      return node.parent ?? undefined;
    },
    []
  );

  /**
   * Main keyboard event handler
   * CRITICAL: Prevents event propagation to avoid board rotation bug
   */
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Ignore if modifier keys are pressed (allow browser shortcuts)
      if (event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }

      let handled = false;
      let target: VisualTreeNode | undefined;

      switch (event.key) {
        case 'ArrowDown':
          // Next in depth-first order
          target = findNextDepthFirst(currentNode);
          handled = true;
          break;

        case 'ArrowUp':
          // Previous in depth-first order
          target = findPrevDepthFirst(currentNode);
          handled = true;
          break;

        case 'ArrowRight':
          // First child (descend)
          target = findNextNode(currentNode);
          handled = true;
          break;

        case 'ArrowLeft':
          // Parent (ascend)
          target = findPrevNode(currentNode);
          handled = true;
          break;

        case 'Home':
          // Go to root
          target = layout.root;
          handled = true;
          break;

        case 'End':
          // Go to last node in main line
          target = findLastNode();
          handled = true;
          break;

        case 'Enter':
        case ' ':
          // Select current node
          if (onSelect) {
            onSelect(currentNode);
          }
          handled = true;
          break;

        case 'Tab':
          // Let Tab work normally for focus navigation
          return;

        default:
          return;
      }

      if (handled) {
        // CRITICAL: Stop propagation to prevent board rotation
        event.preventDefault();
        event.stopPropagation();

        if (target) {
          navigateTo(target);
        }
      }
    },
    [
      enabled,
      currentNode,
      layout.root,
      findNextDepthFirst,
      findPrevDepthFirst,
      findLastNode,
      navigateTo,
      onSelect,
    ]
  );

  /**
   * Programmatically focus the tree container
   */
  const focus = useCallback(() => {
    containerRef.current?.focus();
  }, []);

  return {
    handleKeyDown,
    containerRef,
    focus,
  };
}

export default useTreeKeyboard;
