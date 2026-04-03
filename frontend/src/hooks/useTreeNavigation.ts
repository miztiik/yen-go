/**
 * Tree Navigation Hook
 * @module hooks/useTreeNavigation
 *
 * React hook for managing tree navigation state.
 * Handles current position, history, and keyboard navigation.
 *
 * Feature: 056-solution-tree-visualization
 * Tasks: T009, T015, T016
 *
 * Constitution Compliance:
 * - VI. Type Safety: Full TypeScript types
 * - X. Accessibility: Keyboard navigation support
 */

import { useState, useCallback, useMemo, useEffect } from 'preact/hooks';
import type {
  TreeNavigationState,
  NavigationAction,
  UseTreeNavigationOptions,
  UseTreeNavigationResult,
  VisualTreeNode,
} from '../types/tree';
import {
  computeTreeLayout,
  findNodeById,
  computePathToNode,
} from '../lib/tree/layout';
import {
  findNextNode,
  findPrevNode,
  findNextSibling,
  findPrevSibling,
  findBranchPoint,
  findRoot,
  isBranchPoint,
} from '../lib/tree/navigation';
import { ACCESSIBILITY } from '../lib/tree/constants';

/**
 * Hook for managing tree navigation state.
 *
 * @param options - Configuration options
 * @returns Navigation state and actions
 */
export function useTreeNavigation(
  options: UseTreeNavigationOptions
): UseTreeNavigationResult {
  const { tree, initialNodeId, onChange } = options;

  // Compute layout (memoized to avoid recomputation)
  const layout = useMemo(() => computeTreeLayout(tree), [tree]);

  // Get initial node
  const initialNode = useMemo(() => {
    if (initialNodeId) {
      const found = findNodeById(layout, initialNodeId);
      if (found) return found;
    }
    return layout.root;
  }, [layout, initialNodeId]);

  // Navigation state
  const [state, setState] = useState<TreeNavigationState>(() => ({
    current: initialNode,
    history: [],
    currentPath: computePathToNode(layout, initialNode.id),
  }));

  // Update state when tree changes
  useEffect(() => {
    const newNode = initialNodeId
      ? findNodeById(layout, initialNodeId) ?? layout.root
      : layout.root;

    setState({
      current: newNode,
      history: [],
      currentPath: computePathToNode(layout, newNode.id),
    });
  }, [layout, initialNodeId]);

  // Notify on change
  useEffect(() => {
    onChange?.(state);
  }, [state, onChange]);

  // Navigation action dispatcher
  const dispatch = useCallback(
    (action: NavigationAction) => {
      setState((prev) => {
        let nextNode: VisualTreeNode | undefined;

        switch (action.type) {
          case 'GOTO':
            nextNode = action.node;
            break;

          case 'GOTO_ID': {
            nextNode = findNodeById(layout, action.nodeId);
            break;
          }

          case 'NEXT':
            nextNode = findNextNode(prev.current);
            break;

          case 'PREV':
            nextNode = findPrevNode(prev.current);
            break;

          case 'NEXT_SIBLING':
            nextNode = findNextSibling(prev.current);
            break;

          case 'PREV_SIBLING':
            nextNode = findPrevSibling(prev.current);
            break;

          case 'BRANCH_POINT':
            nextNode = findBranchPoint(prev.current);
            break;

          case 'RESET':
            nextNode = findRoot(prev.current);
            break;

          default:
            return prev;
        }

        if (!nextNode || nextNode.id === prev.current.id) {
          return prev;
        }

        return {
          current: nextNode,
          history:
            action.type === 'PREV' || action.type === 'BRANCH_POINT'
              ? prev.history
              : [...prev.history, prev.current],
          currentPath: computePathToNode(layout, nextNode.id),
        };
      });
    },
    [layout]
  );

  // Convenience methods
  const goTo = useCallback(
    (nodeId: string) => dispatch({ type: 'GOTO_ID', nodeId }),
    [dispatch]
  );

  const next = useCallback(() => dispatch({ type: 'NEXT' }), [dispatch]);

  const prev = useCallback(() => dispatch({ type: 'PREV' }), [dispatch]);

  const nextSibling = useCallback(
    () => dispatch({ type: 'NEXT_SIBLING' }),
    [dispatch]
  );

  const prevSibling = useCallback(
    () => dispatch({ type: 'PREV_SIBLING' }),
    [dispatch]
  );

  const toBranchPoint = useCallback(
    () => dispatch({ type: 'BRANCH_POINT' }),
    [dispatch]
  );

  const reset = useCallback(() => dispatch({ type: 'RESET' }), [dispatch]);

  // ============================================================================
  // Computed Properties (restored from HEAD merge)
  // ============================================================================

  /** Current move number (1-based, from VisualTreeNode) */
  const moveNumber = state.current.moveNumber;

  /** Comment at current node (if any) */
  const comment = state.current.node.comment ?? null;

  /** Whether current node has siblings */
  const hasSiblings = useMemo(() => {
    if (!state.current.parent) return false;
    return state.current.parent.children.length > 1;
  }, [state.current]);

  /** Whether current node is at a branch point (has multiple children) */
  const isAtBranchPoint = useMemo(
    () => isBranchPoint(state.current),
    [state.current]
  );

  /** Sibling nodes of current position */
  const siblings = useMemo(() => {
    if (!state.current.parent) return [];
    return state.current.parent.children;
  }, [state.current]);

  return {
    state,
    layout,
    goTo,
    next,
    prev,
    nextSibling,
    prevSibling,
    toBranchPoint,
    reset,
    dispatch,
    // Computed properties
    moveNumber,
    comment,
    hasSiblings,
    isAtBranchPoint,
    siblings,
  };
}

/**
 * Hook for handling keyboard navigation in the tree.
 *
 * @param dispatch - Navigation action dispatcher
 * @param enabled - Whether keyboard navigation is enabled (default: true)
 */
export function useTreeKeyboardNavigation(
  dispatch: (action: NavigationAction) => void,
  enabled = true
): void {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      const key = event.key;
      const keys = ACCESSIBILITY.keys;

      // Check each navigation action
      if (keys.next.includes(key)) {
        event.preventDefault();
        dispatch({ type: 'NEXT' });
      } else if (keys.prev.includes(key)) {
        event.preventDefault();
        dispatch({ type: 'PREV' });
      } else if (keys.nextSibling.includes(key)) {
        event.preventDefault();
        dispatch({ type: 'NEXT_SIBLING' });
      } else if (keys.prevSibling.includes(key)) {
        event.preventDefault();
        dispatch({ type: 'PREV_SIBLING' });
      } else if (keys.branchPoint.includes(key)) {
        event.preventDefault();
        dispatch({ type: 'BRANCH_POINT' });
      } else if (keys.reset.includes(key)) {
        event.preventDefault();
        dispatch({ type: 'RESET' });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dispatch, enabled]);
}
