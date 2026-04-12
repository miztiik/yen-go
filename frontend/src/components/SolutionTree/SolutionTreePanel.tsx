/**
 * SolutionTreePanel
 * @module components/SolutionTree/SolutionTreePanel
 *
 * Mounts goban's built-in move tree visualization container.
 * The tree renders automatically when connected to a goban instance.
 *
 * Spec 125, Task T042
 * User Story 9: Solution Tree Exploration
 */

import { type JSX } from 'preact';
import { useRef, useEffect } from 'preact/hooks';
import type { Goban } from 'goban';
import { WarningIcon } from '../shared/icons/WarningIcon';

export interface SolutionTreePanelProps {
  /**
   * The goban instance to connect the tree to.
   * The tree will auto-render when the engine updates.
   */
  gobanRef: { current: Goban | null };

  /**
   * Whether the tree panel is visible/enabled.
   * Use this to hide the tree during active solving.
   */
  isVisible?: boolean;

  /**
   * Optional CSS class for container styling.
   */
  className?: string;
}

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    width: '100%',
    minHeight: '150px',
    maxHeight: '300px',
    overflow: 'auto',
    backgroundColor: 'var(--color-bg-tertiary)',
    borderRadius: '8px',
    border: '1px solid var(--color-neutral-300)',
  },
  hidden: {
    display: 'none',
  },
  treeCanvas: {
    width: '100%',
    minHeight: '100%',
  },
  message: {
    padding: '16px',
    textAlign: 'center',
    color: 'var(--color-text-secondary)',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px 16px',
    backgroundColor: 'var(--color-neutral-50)',
    borderRadius: '8px',
    border: '1px solid var(--color-neutral-200)',
    minHeight: '120px',
  },
  emptyIcon: {
    fontSize: '32px',
    marginBottom: '8px',
  },
  emptyText: {
    fontSize: '14px',
    fontWeight: '600',
    color: 'var(--color-text-primary)',
    marginBottom: '4px',
  },
  emptySubtext: {
    fontSize: '12px',
    color: 'var(--color-text-muted)',
  },
  errorState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px 16px',
    backgroundColor: 'var(--color-danger-light, #fef2f2)',
    borderRadius: '8px',
    border: '1px solid var(--color-danger-solid, #ef4444)',
    minHeight: '120px',
  },
  errorIcon: {
    fontSize: '32px',
    marginBottom: '8px',
  },
  errorText: {
    fontSize: '14px',
    fontWeight: '600',
    color: 'var(--color-danger-solid, #dc2626)',
  },
};

/**
 * SolutionTreePanel
 *
 * Renders goban's built-in solution tree visualization.
 * The tree shows:
 * - Correct moves with green rings
 * - Wrong moves with red rings
 * - Comments with blue rings
 * - Current node highlighted
 * - Click-to-navigate syncs board
 */
export function SolutionTreePanel({
  gobanRef,
  isVisible = true,
  className,
}: SolutionTreePanelProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const goban = gobanRef.current;
    const container = containerRef.current;

    if (!goban || !container || !isVisible) {
      return;
    }

    // goban's tree visualization is set up via the move_tree_container config
    // during goban initialization. If we need to dynamically attach/detach,
    // we'd need to reinitialize goban with this container.
    //
    // For now, this component provides the container ref that should be
    // passed to useGoban for initial configuration.
    //
    // The tree auto-renders and auto-updates when engine.cur_move changes.

    // Trigger a tree redraw if needed
    if (
      typeof (goban as unknown as { move_tree_redraw?: () => void }).move_tree_redraw === 'function'
    ) {
      (goban as unknown as { move_tree_redraw: () => void }).move_tree_redraw();
    }
  }, [gobanRef, isVisible]);

  const containerStyle: JSX.CSSProperties = {
    ...styles.container,
    ...(isVisible ? {} : styles.hidden),
  };

  return (
    <div
      ref={containerRef}
      className={className}
      style={containerStyle}
      data-testid="solution-tree-panel"
      role="region"
      aria-label="Solution tree"
    >
      {/* goban renders its canvas-based tree visualization here */}
      {!isVisible && (
        <div style={styles.message} data-testid="tree-hidden-message">
          Complete the puzzle to explore the solution tree
        </div>
      )}
    </div>
  );
}

/**
 * EmptyTreeState
 *
 * Shown when puzzle has no variations (root-only).
 * T053: Empty state for root-only puzzles.
 */
export function EmptyTreeState({ className }: { className?: string }): JSX.Element {
  return (
    <div
      className={className}
      style={styles.emptyState}
      data-testid="tree-empty-state"
      role="status"
    >
      <div style={styles.emptyIcon} aria-hidden="true">
        🌳
      </div>
      <div style={styles.emptyText}>No variations to explore</div>
      <div style={styles.emptySubtext}>This puzzle has a single solution path.</div>
    </div>
  );
}

/**
 * TreeErrorState
 *
 * Shown when the tree cannot be rendered (malformed SGF, goban error).
 * T054: Error state for malformed tree.
 */
export function TreeErrorState({
  className,
  message,
}: {
  className?: string;
  message?: string;
}): JSX.Element {
  return (
    <div
      className={className}
      style={styles.errorState}
      data-testid="tree-error-state"
      role="alert"
    >
      <div style={styles.errorIcon} aria-hidden="true">
        <WarningIcon size={20} />
      </div>
      <div style={styles.errorText}>{message || 'Unable to display solution tree'}</div>
    </div>
  );
}

export default SolutionTreePanel;
