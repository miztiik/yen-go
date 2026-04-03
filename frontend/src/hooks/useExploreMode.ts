/**
 * Explore Mode Hook
 * @module hooks/useExploreMode
 *
 * Custom hook for managing explore/navigate mode state.
 * Shows valid (green) and invalid (red) move hints (FR-007 to FR-010).
 *
 * Constitution Compliance:
 * - V. No Browser AI: Uses pre-computed solution tree
 * - VI. Type Safety: Strict TypeScript types
 */

import { useState, useCallback, useMemo } from 'preact/hooks';
import type {
  Coordinate,
  ExploreHint,
  ExploreState,
} from '@models/SolutionPresentation';
import {
  getExploreHintsFromTree,
  type SolutionTreeNode,
} from '@lib/presentation/exploreHints';

/**
 * Hook result for explore mode.
 */
export interface UseExploreModeResult {
  /** Current explore state */
  state: ExploreState;
  /** Toggle explore mode on/off */
  toggleExplore: () => void;
  /** Enable explore mode */
  enableExplore: () => void;
  /** Disable explore mode */
  disableExplore: () => void;
  /** Update hints for current tree position */
  updateHints: (currentNode: SolutionTreeNode | null) => void;
  /** Add a move to the current path */
  addToPath: (coord: Coordinate) => void;
  /** Reset the path */
  resetPath: () => void;
  /** Check if a specific coordinate is valid */
  isValidMove: (coord: Coordinate) => boolean;
  /** Check if a specific coordinate is invalid */
  isInvalidMove: (coord: Coordinate) => boolean;
}

/**
 * Hook for managing explore mode state.
 *
 * @param initialActive - Whether explore mode starts active (default: false)
 * @returns Explore mode state and control functions
 *
 * @example
 * ```tsx
 * const { state, toggleExplore, updateHints } = useExploreMode();
 *
 * // Update hints when tree position changes
 * useEffect(() => {
 *   updateHints(currentTreeNode);
 * }, [currentTreeNode]);
 *
 * // In render:
 * {state.isActive && state.hints.map(hint => (
 *   <HintMarker coord={hint.coord} isValid={hint.isValid} />
 * ))}
 * ```
 */
export function useExploreMode(initialActive: boolean = false): UseExploreModeResult {
  const [isActive, setIsActive] = useState(initialActive);
  const [hints, setHints] = useState<ExploreHint[]>([]);
  const [currentPath, setCurrentPath] = useState<Coordinate[]>([]);

  // Build maps for quick lookup
  const { validSet, invalidSet } = useMemo(() => {
    const validSet = new Set<string>();
    const invalidSet = new Set<string>();

    for (const hint of hints) {
      const key = `${hint.coord.x},${hint.coord.y}`;
      if (hint.isValid) {
        validSet.add(key);
      } else {
        invalidSet.add(key);
      }
    }

    return { validSet, invalidSet };
  }, [hints]);

  // Toggle explore mode (FR-010)
  const toggleExplore = useCallback(() => {
    setIsActive((prev) => !prev);
  }, []);

  const enableExplore = useCallback(() => {
    setIsActive(true);
  }, []);

  const disableExplore = useCallback(() => {
    setIsActive(false);
  }, []);

  // Update hints based on current tree node (FR-007, FR-008, FR-009)
  const updateHints = useCallback((currentNode: SolutionTreeNode | null) => {
    if (!currentNode) {
      setHints([]);
      return;
    }

    const result = getExploreHintsFromTree(currentNode);
    setHints(result.hints);
  }, []);

  // Path management
  const addToPath = useCallback((coord: Coordinate) => {
    setCurrentPath((prev) => [...prev, coord]);
  }, []);

  const resetPath = useCallback(() => {
    setCurrentPath([]);
  }, []);

  // Coordinate checking
  const isValidMove = useCallback(
    (coord: Coordinate): boolean => {
      return validSet.has(`${coord.x},${coord.y}`);
    },
    [validSet]
  );

  const isInvalidMove = useCallback(
    (coord: Coordinate): boolean => {
      return invalidSet.has(`${coord.x},${coord.y}`);
    },
    [invalidSet]
  );

  // Build state object
  const state: ExploreState = {
    isActive,
    hints,
    currentPath,
  };

  return {
    state,
    toggleExplore,
    enableExplore,
    disableExplore,
    updateHints,
    addToPath,
    resetPath,
    isValidMove,
    isInvalidMove,
  };
}

export default useExploreMode;
