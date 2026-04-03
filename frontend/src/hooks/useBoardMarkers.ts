/**
 * useBoardMarkers Hook
 * @module hooks/useBoardMarkers
 *
 * Listens to goban update events and sets colored circle markers
 * on the board to indicate correct (green) and wrong (red) moves
 * at branch points.
 *
 * Spec 125, Task T043
 * User Story 9: Solution Tree Exploration
 */

import { useEffect, useCallback, useState } from 'preact/hooks';
import type { Goban } from 'goban';

/**
 * Color scheme for board markers.
 * Green = correct move, Red = wrong move
 */
const MARKER_COLORS = {
  correct: '#33ff33',
  wrong: '#ff3333',
  neutral: '#3333ff',
} as const;

export interface BoardMarker {
  x: number;
  y: number;
  color: string;
  type: 'correct' | 'wrong' | 'neutral';
}

export interface UseBoardMarkersResult {
  /**
   * Current markers on the board.
   */
  markers: BoardMarker[];

  /**
   * Whether markers are being shown.
   */
  showingMarkers: boolean;

  /**
   * Toggle marker visibility.
   */
  toggleMarkers: () => void;

  /**
   * Force refresh markers from current tree state.
   */
  refreshMarkers: () => void;
}

/**
 * useBoardMarkers
 *
 * Manages colored circle markers on the goban board to show
 * correct/wrong moves at the current branch point.
 *
 * @param gobanRef Reference to the goban instance
 * @param enabled Whether markers should be shown (e.g., in review mode)
 */
export function useBoardMarkers(
  gobanRef: { current: Goban | null },
  enabled: boolean = false
): UseBoardMarkersResult {
  const [markers, setMarkers] = useState<BoardMarker[]>([]);
  const [showingMarkers, setShowingMarkers] = useState(enabled);

  const calculateMarkers = useCallback(() => {
    const goban = gobanRef.current;
    if (!goban || !showingMarkers) {
      return [];
    }

    const newMarkers: BoardMarker[] = [];

    // Access the engine and current move
    const engine = (goban as unknown as { engine?: { cur_move?: MoveTreeNode } }).engine;
    const curMove = engine?.cur_move;

    if (!curMove) {
      return [];
    }

    // Get branches from current move
    const branches = curMove.branches || [];

    for (const branch of branches) {
      if (typeof branch.x === 'number' && typeof branch.y === 'number') {
        let type: BoardMarker['type'] = 'neutral';
        let color: string = MARKER_COLORS.neutral;

        if (branch.correct_answer) {
          type = 'correct';
          color = MARKER_COLORS.correct;
        } else if (branch.wrong_answer) {
          type = 'wrong';
          color = MARKER_COLORS.wrong;
        }

        newMarkers.push({
          x: branch.x,
          y: branch.y,
          color,
          type,
        });
      }
    }

    return newMarkers;
  }, [gobanRef, showingMarkers]);

  const refreshMarkers = useCallback(() => {
    const newMarkers = calculateMarkers();
    setMarkers(newMarkers);

    const goban = gobanRef.current;
    if (!goban || !showingMarkers) {
      return;
    }

    // Use goban's setColoredCircles to show markers
    const circles: Record<string, string> = {};
    for (const marker of newMarkers) {
      const coord = String.fromCharCode(97 + marker.x) + String.fromCharCode(97 + marker.y);
      circles[coord] = marker.color;
    }

    if (typeof (goban as unknown as GobanWithCircles).setColoredCircles === 'function') {
      (goban as unknown as GobanWithCircles).setColoredCircles(circles);
    }
  }, [gobanRef, showingMarkers, calculateMarkers]);

  const toggleMarkers = useCallback(() => {
    setShowingMarkers((prev) => !prev);
  }, []);

  // Listen for goban update events
  useEffect(() => {
    const goban = gobanRef.current;
    if (!goban || !enabled) {
      return;
    }

    const handleUpdate = () => {
      if (showingMarkers) {
        refreshMarkers();
      }
    };

    goban.on('update', handleUpdate);

    // Also refresh when cur_move changes
    const handleCurMove = () => {
      if (showingMarkers) {
        refreshMarkers();
      }
    };
    goban.on('cur_move', handleCurMove);

    // Initial refresh
    refreshMarkers();

    return () => {
      goban.off('update', handleUpdate);
      goban.off('cur_move', handleCurMove);

      // Clear markers on cleanup
      if (typeof (goban as unknown as GobanWithCircles).setColoredCircles === 'function') {
        (goban as unknown as GobanWithCircles).setColoredCircles({});
      }
    };
  }, [gobanRef, enabled, showingMarkers, refreshMarkers]);

  // Sync showingMarkers with enabled prop
  useEffect(() => {
    setShowingMarkers(enabled);
  }, [enabled]);

  return {
    markers,
    showingMarkers,
    toggleMarkers,
    refreshMarkers,
  };
}

// Type helpers for goban internal structure
interface MoveTreeNode {
  x?: number;
  y?: number;
  correct_answer?: boolean;
  wrong_answer?: boolean;
  text?: string;
  branches?: MoveTreeNode[];
  trunk_next?: MoveTreeNode;
  parent?: MoveTreeNode;
}

interface GobanWithCircles {
  setColoredCircles: (circles: Record<string, string>) => void;
}

export default useBoardMarkers;
