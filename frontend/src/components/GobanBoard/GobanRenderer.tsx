/**
 * GobanRenderer — Pure goban board rendering component.
 * @module components/GobanBoard/GobanRenderer
 *
 * This component only handles DOM mounting and responsive sizing.
 * State management (puzzle status, events) is done externally via
 * useGoban and usePuzzleState hooks at the parent level.
 *
 * Use GobanBoard for a self-contained component with internal state.
 * Use GobanRenderer when you need to lift state to a parent component.
 *
 * Spec 125, Task T032
 */

import type { FunctionComponent, JSX } from 'preact';
import type { MutableRef } from 'preact/hooks';
import type { GobanInstance } from '../../hooks/useGoban';
import type { PuzzleStatus } from '../../hooks/usePuzzleState';

// ============================================================================
// Props
// ============================================================================

export interface GobanRendererProps {
  /** Ref to the board container div (used by useGoban) */
  boardRef: MutableRef<HTMLDivElement | null>;
  /** Whether goban is ready (from useGoban) */
  isReady: boolean;
  /** Current puzzle status (for overlay display) */
  status?: PuzzleStatus;
  /** goban instance (for direct access if needed) */
  goban?: GobanInstance | null;
  /** Show loading indicator when not ready */
  showLoading?: boolean;
  /** Additional CSS class */
  className?: string;
}

// ============================================================================
// Styles
// ============================================================================

const styles = {
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
  } as JSX.CSSProperties,

  boardWrapper: {
    position: 'relative',
    width: '100%',
    maxWidth: '600px',
    aspectRatio: '1',
  } as JSX.CSSProperties,

  boardDiv: {
    width: '100%',
    height: '100%',
  } as JSX.CSSProperties,

  statusOverlay: {
    position: 'absolute',
    top: '8px',
    right: '8px',
    padding: '4px 12px',
    borderRadius: '16px',
    fontSize: '14px',
    fontWeight: '600',
    opacity: 0.9,
    pointerEvents: 'none',
  } as JSX.CSSProperties,

  correct: {
    backgroundColor: 'var(--color-success, #22c55e)',
    color: 'white',
  } as JSX.CSSProperties,

  wrong: {
    backgroundColor: 'var(--color-error, #ef4444)',
    color: 'white',
  } as JSX.CSSProperties,

  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--color-text-muted, #888)',
    padding: '24px',
  } as JSX.CSSProperties,
};

// ============================================================================
// Component
// ============================================================================

/**
 * GobanRenderer — Pure rendering component for goban board.
 *
 * This is a presentational component that receives all state from props.
 * Parent component should use useGoban to create the board reference
 * and pass the boardRef down.
 *
 * @example
 * ```tsx
 * const boardRef = useRef<HTMLDivElement>(null);
 * const { gobanRef, isReady } = useGoban(rawSgf, boardRef, null);
 *
 * <GobanRenderer
 *   boardRef={boardRef}
 *   isReady={isReady}
 *   status={puzzleState.status}
 * />
 * ```
 */
export const GobanRenderer: FunctionComponent<GobanRendererProps> = ({
  boardRef,
  isReady,
  status,
  showLoading = true,
  className,
}) => {
  // -------------------------------------------------------------------------
  // Render: Loading state
  // -------------------------------------------------------------------------
  if (!isReady && showLoading) {
    return (
      <div className={className} style={styles.container}>
        <div style={styles.loading}>Loading puzzle...</div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render: Status overlay style
  // -------------------------------------------------------------------------
  const getStatusOverlay = (): JSX.Element | null => {
    if (status === 'correct') {
      return <div style={{ ...styles.statusOverlay, ...styles.correct }}>✓ Correct!</div>;
    }
    if (status === 'wrong') {
      return <div style={{ ...styles.statusOverlay, ...styles.wrong }}>✗ Wrong</div>;
    }
    return null;
  };

  // -------------------------------------------------------------------------
  // Render: Board
  // -------------------------------------------------------------------------
  return (
    <div className={className} style={styles.container}>
      <div style={styles.boardWrapper}>
        {/* goban mounts into this div */}
        <div
          ref={boardRef}
          style={styles.boardDiv}
          data-testid="goban-board"
          aria-label="Go puzzle board"
          role="application"
        />

        {/* Status overlay (correct/wrong flash) */}
        {getStatusOverlay()}
      </div>
    </div>
  );
};

export default GobanRenderer;
