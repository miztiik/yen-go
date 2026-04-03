/**
 * BreadcrumbTrail
 * @module components/SolutionTree/BreadcrumbTrail
 *
 * Shows the current path through the solution tree as a breadcrumb trail.
 * Reads cur_move path to root on update events.
 *
 * Spec 125, Task T044
 * User Story 9: Solution Tree Exploration
 */

import { type JSX } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import type { Goban } from 'goban';

export interface BreadcrumbItem {
  /** Move number (0 = root) */
  moveNumber: number;
  /** Coordinate string (e.g., "D4") or "Start" for root */
  label: string;
  /** The tree node reference for navigation */
  nodeRef: unknown;
}

export interface BreadcrumbTrailProps {
  /**
   * Reference to the goban instance.
   */
  gobanRef: { current: Goban | null };

  /**
   * Callback when a breadcrumb is clicked.
   */
  onNavigate?: (moveNumber: number) => void;

  /**
   * Optional CSS class.
   */
  className?: string;
}

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
    alignItems: 'center',
    padding: '8px',
    fontSize: '14px',
    fontFamily: 'monospace',
    backgroundColor: 'var(--color-neutral-50)',
    borderRadius: '4px',
    overflowX: 'auto',
  },
  crumb: {
    padding: '4px 8px',
    backgroundColor: 'var(--color-neutral-200)',
    borderRadius: '3px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    minHeight: '44px',
    minWidth: '44px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: 'none',
    font: 'inherit',
    fontFamily: 'monospace',
    fontSize: '14px',
  },
  crumbActive: {
    padding: '4px 8px',
    backgroundColor: 'var(--color-info-solid)',
    color: 'white',
    borderRadius: '3px',
    fontWeight: 'bold',
    whiteSpace: 'nowrap',
    minHeight: '44px',
    minWidth: '44px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: 'none',
    font: 'inherit',
    fontFamily: 'monospace',
    fontSize: '14px',
  },
  separator: {
    color: 'var(--color-text-muted)',
    padding: '0 2px',
  },
};

/**
 * Convert SGF coordinate to display format.
 */
function coordToDisplay(x: number, y: number): string {
  if (x < 0 || y < 0) return '?';
  // A-T (skip I) for x, 1-19 for y (inverted)
  const letters = 'ABCDEFGHJKLMNOPQRST';
  const col = letters[x] || '?';
  const row = 19 - y;
  return `${col}${row}`;
}

/**
 * BreadcrumbTrail
 *
 * Shows the path from root to current move as clickable breadcrumbs.
 */
export function BreadcrumbTrail({
  gobanRef,
  onNavigate,
  className,
}: BreadcrumbTrailProps): JSX.Element {
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([]);

  const buildBreadcrumbs = useCallback(() => {
    const goban = gobanRef.current;
    if (!goban) {
      return [];
    }

    const engine = (goban as unknown as { engine?: { cur_move?: MoveTreeNode } }).engine;
    const curMove = engine?.cur_move;

    if (!curMove) {
      return [{ moveNumber: 0, label: 'Start', nodeRef: null }];
    }

    // Walk from current move to root
    const path: BreadcrumbItem[] = [];
    let node: MoveTreeNode | undefined = curMove;

    // Count moves from root
    let temp: MoveTreeNode | undefined = curMove;
    while (temp?.parent) {
      temp = temp.parent;
    }

    // Build path from root to current
    const nodes: MoveTreeNode[] = [];
    node = curMove;
    while (node) {
      nodes.unshift(node);
      node = node.parent;
    }

    nodes.forEach((n, i) => {
      if (i === 0) {
        path.push({ moveNumber: 0, label: 'Start', nodeRef: n });
      } else if (typeof n.x === 'number' && typeof n.y === 'number') {
        path.push({
          moveNumber: i,
          label: coordToDisplay(n.x, n.y),
          nodeRef: n,
        });
      }
    });

    return path;
  }, [gobanRef]);

  const handleClick = useCallback(
    (item: BreadcrumbItem) => {
      const goban = gobanRef.current;
      if (!goban) return;

      // Navigate to the node
      if (item.moveNumber === 0) {
        // Go to start
        if (typeof (goban as unknown as GobanNav).showFirst === 'function') {
          (goban as unknown as GobanNav).showFirst();
        }
      } else if (item.nodeRef) {
        // Jump to specific node
        const engine = (goban as unknown as { engine?: GobanEngine }).engine;
        if (engine && typeof engine.jumpTo === 'function') {
          engine.jumpTo(item.nodeRef);
        }
      }

      onNavigate?.(item.moveNumber);
    },
    [gobanRef, onNavigate]
  );

  useEffect(() => {
    const goban = gobanRef.current;
    if (!goban) return;

    const handleUpdate = () => {
      setBreadcrumbs(buildBreadcrumbs());
    };

    goban.on('update', handleUpdate);
    goban.on('cur_move', handleUpdate);

    // Initial build
    setBreadcrumbs(buildBreadcrumbs());

    return () => {
      goban.off('update', handleUpdate);
      goban.off('cur_move', handleUpdate);
    };
  }, [gobanRef, buildBreadcrumbs]);

  if (breadcrumbs.length === 0) {
    return <div className={className} style={styles.container}>Start</div>;
  }

  return (
    <nav
      className={className}
      style={styles.container}
      aria-label="Move history"
      data-testid="breadcrumb-trail"
    >
      {breadcrumbs.map((crumb, index) => (
        <span key={crumb.moveNumber}>
          {index > 0 && <span style={styles.separator}>→</span>}
          <button
            type="button"
            style={index === breadcrumbs.length - 1 ? styles.crumbActive : styles.crumb}
            onClick={() => handleClick(crumb)}
            aria-current={index === breadcrumbs.length - 1 ? 'step' : undefined}
          >
            {crumb.label}
          </button>
        </span>
      ))}
    </nav>
  );
}

// Type helpers
interface MoveTreeNode {
  x?: number;
  y?: number;
  parent?: MoveTreeNode;
}

interface GobanNav {
  showFirst: () => void;
}

interface GobanEngine {
  jumpTo: (node: unknown) => void;
}

export default BreadcrumbTrail;
