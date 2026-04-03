/**
 * GobanBoard — Renders a puzzle using the goban library.
 * @module components/GobanBoard/GobanBoard
 *
 * This component:
 * - Mounts SVGRenderer via useRef/useEffect (auto-fallback to GobanCanvas)
 * - Uses useGoban hook for goban lifecycle management
 * - Provides responsive sizing via ResizeObserver
 * - Applies Tailwind CSS for layout
 *
 * Spec 125, Task T030
 */

import type { FunctionComponent, JSX } from 'preact';
import { useRef, useLayoutEffect, useState, useCallback } from 'preact/hooks';
import { useGoban } from '../../hooks/useGoban';
import { usePuzzleState } from '../../hooks/usePuzzleState';
import { GobanContainer } from '../GobanContainer';
import type { TransformSettings } from '../../types/goban';

// ============================================================================
// Props
// ============================================================================

export interface GobanBoardProps {
  /** Raw SGF content for the puzzle */
  rawSgf: string;
  /** Optional transform settings */
  transforms?: TransformSettings;
  /** Optional: Container for solution tree rendering */
  moveTreeContainer?: HTMLElement;
  /** Callback when puzzle status changes */
  onStatusChange?: (status: string, moveCount: number) => void;
  /** Callback when puzzle is completed */
  onComplete?: (isCorrect: boolean, moveCount: number, timeMs: number) => void;
  /** Show coordinate labels */
  showCoordinates?: boolean;
  /** Additional CSS class */
  className?: string;
}

// ============================================================================
// Styles
// ============================================================================

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    position: 'relative',
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'var(--color-bg-secondary, #f5f5f5)',
    borderRadius: 'var(--radius-lg, 8px)',
    overflow: 'hidden',
  },
  boardWrapper: {
    position: 'relative',
    width: '100%',
    maxWidth: '600px',
    aspectRatio: '1',
  },
  boardDiv: {
    width: '100%',
    height: '100%',
  },
  statusOverlay: {
    position: 'absolute',
    top: '8px',
    right: '8px',
    padding: '4px 12px',
    borderRadius: '16px',
    fontSize: '14px',
    fontWeight: '600',
    opacity: 0.9,
  },
  correct: {
    backgroundColor: 'var(--color-success, #22c55e)',
    color: 'white',
  },
  wrong: {
    backgroundColor: 'var(--color-error, #ef4444)',
    color: 'white',
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--color-text-muted, #888)',
  },
};

// ============================================================================
// Component
// ============================================================================

/**
 * GobanBoard — Main puzzle board component using the goban library.
 *
 * @example
 * ```tsx
 * <GobanBoard
 *   rawSgf={puzzleSgf}
 *   onComplete={(isCorrect, moves, time) => console.log('Done!', isCorrect)}
 * />
 * ```
 */
export const GobanBoard: FunctionComponent<GobanBoardProps> = ({
  rawSgf,
  transforms,
  moveTreeContainer,
  onStatusChange,
  onComplete,
  className,
}) => {
  // Refs for DOM elements
  const containerRef = useRef<HTMLDivElement>(null);
  const treeContainerRef = useRef<HTMLDivElement | null>(
    (moveTreeContainer as HTMLDivElement) ?? null
  );

  // Track initialization
  const [isInitialized, setIsInitialized] = useState(false);

  // -------------------------------------------------------------------------
  // goban hook -- manages goban lifecycle (UI-032: no boardRef, creates gobanDiv)
  // -------------------------------------------------------------------------
  const { gobanRef, isReady, gobanDiv } = useGoban(
    rawSgf,
    treeContainerRef,
    transforms,
  );

  // -------------------------------------------------------------------------
  // Puzzle state — manages solve lifecycle
  // -------------------------------------------------------------------------
  const goban = isReady ? gobanRef.current : null;
  const {
    state: puzzleState,
    onGobanReady,
    elapsedMs,
  } = usePuzzleState(goban);

  // -------------------------------------------------------------------------
  // Callbacks: Status changes and completion
  // -------------------------------------------------------------------------
  const handleStatusChange = useCallback((status: string, moveCount: number): void => {
    onStatusChange?.(status, moveCount);
  }, [onStatusChange]);

  const handleComplete = useCallback((isCorrect: boolean): void => {
    const timeMs = elapsedMs ?? 0;
    onComplete?.(isCorrect, puzzleState.moveCount, timeMs);
  }, [onComplete, elapsedMs, puzzleState.moveCount]);

  // -------------------------------------------------------------------------
  // Effects: Initialize goban and track status
  // -------------------------------------------------------------------------
  useLayoutEffect(() => {
    if (isReady && !isInitialized) {
      setIsInitialized(true);
      onGobanReady();
    }
  }, [isReady, isInitialized, onGobanReady]);

  // Notify on status change
  useLayoutEffect(() => {
    handleStatusChange(puzzleState.status, puzzleState.moveCount);
  }, [puzzleState.status, puzzleState.moveCount, handleStatusChange]);

  // Notify on completion
  useLayoutEffect(() => {
    if (puzzleState.status === 'complete') {
      handleComplete(true);
    } else if (puzzleState.status === 'wrong') {
      handleComplete(false);
    }
  }, [puzzleState.status, handleComplete]);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  // Loading state (not yet ready or no SGF)
  if (!isReady || !rawSgf) {
    return (
      <div
        ref={containerRef}
        className={className}
        style={styles.container}
      >
        <div style={styles.loading}>
          Loading puzzle...
        </div>
      </div>
    );
  }

  // Status indicator style
  const getStatusStyle = (): JSX.CSSProperties | null => {
    if (puzzleState.status === 'correct') {
      return { ...styles.statusOverlay, ...styles.correct };
    }
    if (puzzleState.status === 'wrong') {
      return { ...styles.statusOverlay, ...styles.wrong };
    }
    return null;
  };

  const statusStyle = getStatusStyle();

  return (
    <div
      ref={containerRef}
      className={className}
      style={styles.container}
    >
      <div style={styles.boardWrapper}>
        {/* UI-001: GobanContainer mounts the goban_div */}
        <GobanContainer
          gobanDiv={gobanDiv}
          goban={goban}
        />

        {/* Status overlay (correct/wrong flash) */}
        {statusStyle && (
          <div style={statusStyle}>
            {puzzleState.status === 'correct' ? 'Correct!' : 'Wrong'}
          </div>
        )}
      </div>
    </div>
  );
};

export default GobanBoard;
