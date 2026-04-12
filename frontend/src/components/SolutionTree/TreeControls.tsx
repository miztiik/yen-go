/**
 * TreeControls
 * @module components/SolutionTree/TreeControls
 *
 * Keyboard and button controls for navigating the solution tree.
 * Shortcuts: ← prev, → next, ↑/↓ siblings, Home/first
 *
 * Spec 125, Task T046
 * User Story 9: Solution Tree Exploration
 */

import { type JSX } from 'preact';
import { useEffect, useCallback } from 'preact/hooks';
import type { Goban } from 'goban';

export interface TreeControlsProps {
  /**
   * Reference to the goban instance.
   */
  gobanRef: { current: Goban | null };

  /**
   * Whether keyboard shortcuts are enabled.
   * Disable during puzzle solving to prevent cheating.
   */
  keyboardEnabled?: boolean;

  /**
   * Optional CSS class.
   */
  className?: string;
}

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    gap: '8px',
    padding: '8px',
    backgroundColor: 'var(--color-neutral-50)',
    borderRadius: '6px',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  button: {
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid var(--color-neutral-300)',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    minWidth: '44px',
    minHeight: '44px',
    justifyContent: 'center',
  },
  buttonDisabled: {
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid var(--color-neutral-300)',
    borderRadius: '4px',
    backgroundColor: 'var(--color-neutral-100)',
    cursor: 'not-allowed',
    color: 'var(--color-text-muted)',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    minWidth: '44px',
    minHeight: '44px',
    justifyContent: 'center',
  },
  shortcutHint: {
    fontSize: '10px',
    color: 'var(--color-text-secondary)',
    marginLeft: '4px',
  },
};

/**
 * TreeControls
 *
 * Provides buttons and keyboard shortcuts for navigating the solution tree.
 */
export function TreeControls({
  gobanRef,
  keyboardEnabled = true,
  className,
}: TreeControlsProps): JSX.Element {
  const showFirst = useCallback(() => {
    const goban = gobanRef.current;
    if (!goban) return;

    if (typeof (goban as unknown as GobanNav).showFirst === 'function') {
      (goban as unknown as GobanNav).showFirst();
    }
  }, [gobanRef]);

  const showPrevious = useCallback(() => {
    const goban = gobanRef.current;
    if (!goban) return;

    if (typeof (goban as unknown as GobanNav).showPrevious === 'function') {
      (goban as unknown as GobanNav).showPrevious();
    }
  }, [gobanRef]);

  const showNext = useCallback(() => {
    const goban = gobanRef.current;
    if (!goban) return;

    if (typeof (goban as unknown as GobanNav).showNext === 'function') {
      (goban as unknown as GobanNav).showNext();
    }
  }, [gobanRef]);

  const prevSibling = useCallback(() => {
    const goban = gobanRef.current;
    if (!goban) return;

    const engine = (goban as unknown as { engine?: { cur_move?: MoveTreeNode } }).engine;
    const curMove = engine?.cur_move;

    if (curMove && typeof curMove.prevSibling === 'function') {
      const prev = curMove.prevSibling();
      if (prev && engine && typeof (engine as GobanEngine).jumpTo === 'function') {
        (engine as GobanEngine).jumpTo(prev);
      }
    }
  }, [gobanRef]);

  const nextSibling = useCallback(() => {
    const goban = gobanRef.current;
    if (!goban) return;

    const engine = (goban as unknown as { engine?: { cur_move?: MoveTreeNode } }).engine;
    const curMove = engine?.cur_move;

    if (curMove && typeof curMove.nextSibling === 'function') {
      const next = curMove.nextSibling();
      if (next && engine && typeof (engine as GobanEngine).jumpTo === 'function') {
        (engine as GobanEngine).jumpTo(next);
      }
    }
  }, [gobanRef]);

  // Keyboard shortcuts
  useEffect(() => {
    if (!keyboardEnabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          showPrevious();
          break;
        case 'ArrowRight':
          e.preventDefault();
          showNext();
          break;
        case 'ArrowUp':
          e.preventDefault();
          prevSibling();
          break;
        case 'ArrowDown':
          e.preventDefault();
          nextSibling();
          break;
        case 'Home':
          e.preventDefault();
          showFirst();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [keyboardEnabled, showFirst, showPrevious, showNext, prevSibling, nextSibling]);

  return (
    <div
      className={className}
      style={styles.container}
      role="toolbar"
      aria-label="Solution tree navigation"
      data-testid="tree-controls"
    >
      <button
        type="button"
        style={styles.button}
        onClick={showFirst}
        aria-label="Go to start"
        title="Go to start (Home)"
      >
        ⏮<span style={styles.shortcutHint}>Home</span>
      </button>

      <button
        type="button"
        style={styles.button}
        onClick={showPrevious}
        aria-label="Previous move"
        title="Previous move (←)"
      >
        ←<span style={styles.shortcutHint}>←</span>
      </button>

      <button
        type="button"
        style={styles.button}
        onClick={showNext}
        aria-label="Next move"
        title="Next move (→)"
      >
        →<span style={styles.shortcutHint}>→</span>
      </button>

      <button
        type="button"
        style={styles.button}
        onClick={prevSibling}
        aria-label="Previous variation"
        title="Previous variation (↑)"
      >
        ↑ Var<span style={styles.shortcutHint}>↑</span>
      </button>

      <button
        type="button"
        style={styles.button}
        onClick={nextSibling}
        aria-label="Next variation"
        title="Next variation (↓)"
      >
        ↓ Var<span style={styles.shortcutHint}>↓</span>
      </button>
    </div>
  );
}

// Type helpers
interface MoveTreeNode {
  prevSibling?: () => MoveTreeNode | null;
  nextSibling?: () => MoveTreeNode | null;
}

interface GobanNav {
  showFirst: () => void;
  showPrevious: () => boolean;
  showNext: () => boolean;
}

interface GobanEngine {
  jumpTo: (node: unknown) => void;
}

export default TreeControls;
