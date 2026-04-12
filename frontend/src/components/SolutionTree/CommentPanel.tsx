/**
 * CommentPanel
 * @module components/SolutionTree/CommentPanel
 *
 * Displays the move comment (SGF C property) for the current tree node.
 * Reads cur_move.text on update events.
 *
 * Spec 125, Task T045
 * User Story 9: Solution Tree Exploration
 */

import { type JSX } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import type { Goban } from 'goban';

export interface CommentPanelProps {
  /**
   * Reference to the goban instance.
   */
  gobanRef: { current: Goban | null };

  /**
   * Optional CSS class.
   */
  className?: string;
}

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    padding: '12px',
    backgroundColor: 'var(--color-neutral-50)',
    borderRadius: '6px',
    border: '1px solid var(--color-neutral-200)',
    minHeight: '60px',
    fontSize: '14px',
    lineHeight: '1.5',
  },
  empty: {
    padding: '12px',
    backgroundColor: 'var(--color-neutral-50)',
    borderRadius: '6px',
    border: '1px solid var(--color-neutral-200)',
    minHeight: '60px',
    fontSize: '14px',
    lineHeight: '1.5',
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
  },
  title: {
    fontSize: '12px',
    fontWeight: 'bold',
    color: 'var(--color-text-secondary)',
    marginBottom: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  text: {
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  coordBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    fontSize: '12px',
    fontFamily: 'monospace',
    fontWeight: '600',
    backgroundColor: 'var(--color-neutral-200)',
    color: 'var(--color-text-primary)',
    borderRadius: '4px',
    marginBottom: '6px',
    letterSpacing: '0.5px',
  },
};

/**
 * CommentPanel
 *
 * Shows the comment associated with the current move in the solution tree.
 * Comments are stored in the SGF C[] property and provide pedagogical feedback.
 * Also displays the current move coordinate (e.g., "B: D4") when available.
 */
export function CommentPanel({ gobanRef, className }: CommentPanelProps): JSX.Element {
  const [comment, setComment] = useState<string>('');
  const [moveCoord, setMoveCoord] = useState<string>('');

  useEffect(() => {
    const goban = gobanRef.current;
    if (!goban) return;

    const updateComment = () => {
      const engine = (goban as unknown as { engine?: { cur_move?: MoveTreeNode } }).engine;
      const curMove = engine?.cur_move;

      if (curMove?.text) {
        setComment(curMove.text);
      } else {
        setComment('');
      }

      // Extract move coordinate (T024/T042c)
      const coord = extractMoveCoord(curMove);
      setMoveCoord(coord);
    };

    goban.on('update', updateComment);
    goban.on('cur_move', updateComment);

    // Initial update
    updateComment();

    return () => {
      goban.off('update', updateComment);
      goban.off('cur_move', updateComment);
    };
  }, [gobanRef]);

  if (!comment && !moveCoord) {
    return (
      <div
        className={className}
        style={styles.empty}
        data-testid="comment-panel"
        role="region"
        aria-label="Move comment"
        aria-live="polite"
        aria-atomic="true"
      >
        No comment for this move
      </div>
    );
  }

  return (
    <div
      className={className}
      style={styles.container}
      data-testid="comment-panel"
      role="region"
      aria-label="Move comment"
      aria-live="polite"
      aria-atomic="true"
    >
      {moveCoord && (
        <div style={styles.coordBadge} data-testid="move-coordinate">
          {moveCoord}
        </div>
      )}
      {comment && (
        <>
          <div style={styles.title}>Comment</div>
          <div style={styles.text}>{comment}</div>
        </>
      )}
    </div>
  );
}

/**
 * Extract a display coordinate from a goban MoveTreeNode.
 * Returns e.g. "B: D4" or "" if no move available.
 */
function extractMoveCoord(curMove: MoveTreeNode | undefined): string {
  if (!curMove) return '';

  const x = curMove.x;
  const y = curMove.y;
  const color = curMove.player;

  if (typeof x !== 'number' || typeof y !== 'number' || x < 0 || y < 0) return '';

  const letters = 'ABCDEFGHJKLMNOPQRST';
  const col = letters[x] || '?';
  const row = 19 - y;
  const colorLabel = color === 1 ? 'B' : color === 2 ? 'W' : '?';

  return `${colorLabel}: ${col}${row}`;
}

// Type helper
interface MoveTreeNode {
  text?: string;
  x?: number;
  y?: number;
  /** 1 = Black, 2 = White */
  player?: number;
}

export default CommentPanel;
