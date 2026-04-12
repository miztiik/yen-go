/**
 * Board Viewport Hook
 * @module hooks/useBoardViewport
 *
 * Custom hook for managing board viewport/auto-crop state (FR-011 to FR-014).
 *
 * Constitution Compliance:
 * - V. No Browser AI: Pure geometric calculation
 * - VI. Type Safety: Strict TypeScript types
 */

import { useState, useCallback, useEffect } from 'preact/hooks';
import type { Coordinate, BoardViewport } from '@models/SolutionPresentation';
import {
  calculateViewport,
  createFullBoardViewport,
  expandViewport,
} from '@lib/presentation/viewportCalculator';

/**
 * Hook result for board viewport.
 */
export interface UseBoardViewportResult {
  /** Current viewport bounds */
  viewport: BoardViewport;
  /** Whether auto-crop is enabled */
  isAutoCropEnabled: boolean;
  /** Toggle between auto-crop and full board (FR-013) */
  toggleViewport: () => void;
  /** Force full board view */
  showFullBoard: () => void;
  /** Fit to problem area */
  fitToProblem: () => void;
  /** Recalculate viewport with new stones */
  recalculate: (stones: readonly Coordinate[]) => void;
  /** Expand viewport to include solution moves (FR-014) */
  expandToInclude: (points: readonly Coordinate[]) => void;
}

/**
 * Hook for managing board viewport/auto-crop.
 *
 * @param initialStones - Initial stone positions for auto-crop calculation
 * @param boardSize - Board size (9, 13, or 19)
 * @param margin - Margin around stones (default: 2)
 * @param autoEnable - Whether to auto-enable cropping on load (default: true)
 * @returns Viewport state and control functions
 *
 * @example
 * ```tsx
 * const { viewport, toggleViewport, isAutoCropEnabled } = useBoardViewport(
 *   puzzle.initialStones,
 *   puzzle.boardSize
 * );
 *
 * // In render:
 * <Board viewport={viewport} />
 * <button onClick={toggleViewport}>
 *   {isAutoCropEnabled ? 'Show Full Board' : 'Fit to Problem'}
 * </button>
 * ```
 */
export function useBoardViewport(
  initialStones: readonly Coordinate[],
  boardSize: number,
  margin: number = 2,
  autoEnable: boolean = true
): UseBoardViewportResult {
  // Calculate initial viewport
  const calculateInitialViewport = useCallback(
    (stones: readonly Coordinate[]): BoardViewport => {
      return calculateViewport(stones, boardSize, { margin });
    },
    [boardSize, margin]
  );

  // Store the "fitted" viewport (what auto-crop calculates)
  const [fittedViewport, setFittedViewport] = useState<BoardViewport>(() =>
    calculateInitialViewport(initialStones)
  );

  // Store whether we're currently showing fitted or full
  const [isAutoCropEnabled, setIsAutoCropEnabled] = useState<boolean>(() => {
    // Only enable auto-crop if the fitted viewport is actually cropped
    if (!autoEnable) return false;
    const fitted = calculateInitialViewport(initialStones);
    return !fitted.isFullBoard;
  });

  // Current viewport (either fitted or full)
  const viewport = isAutoCropEnabled ? fittedViewport : createFullBoardViewport(boardSize);

  // Recalculate when initial stones change
  useEffect(() => {
    const newFitted = calculateInitialViewport(initialStones);
    setFittedViewport(newFitted);
    // Re-enable auto-crop if there's meaningful cropping
    if (autoEnable && !newFitted.isFullBoard) {
      setIsAutoCropEnabled(true);
    }
  }, [initialStones, calculateInitialViewport, autoEnable]);

  // Toggle between fitted and full (FR-013)
  const toggleViewport = useCallback(() => {
    setIsAutoCropEnabled((prev) => !prev);
  }, []);

  const showFullBoard = useCallback(() => {
    setIsAutoCropEnabled(false);
  }, []);

  const fitToProblem = useCallback(() => {
    setIsAutoCropEnabled(true);
  }, []);

  // Recalculate with new stones
  const recalculate = useCallback(
    (stones: readonly Coordinate[]) => {
      const newFitted = calculateInitialViewport(stones);
      setFittedViewport(newFitted);
    },
    [calculateInitialViewport]
  );

  // Expand viewport to include additional points (FR-014)
  const expandToInclude = useCallback(
    (points: readonly Coordinate[]) => {
      setFittedViewport((prev) => expandViewport(prev, points, boardSize, 1));
    },
    [boardSize]
  );

  return {
    viewport,
    isAutoCropEnabled,
    toggleViewport,
    showFullBoard,
    fitToProblem,
    recalculate,
    expandToInclude,
  };
}

export default useBoardViewport;
