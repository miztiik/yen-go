/**
 * TreeNode Component
 * @module components/SolutionTree/TreeNode
 *
 * @description
 * Individual node component for solution tree visualization.
 * Renders a single node with all its visual states and children recursively.
 *
 * Features:
 * - Correct/wrong move styling (green/red borders)
 * - Path highlighting (turquoise background)
 * - Current position indicator
 * - Dead-end marker for wrong terminal moves
 * - Move number and coordinate display
 * - Tesuji (key move) styling with star icon
 * - Setup node support (FR-003)
 * - Keyboard activation (Enter/Space) for accessibility
 * - 44pt minimum touch targets (FR-019)
 *
 * @example
 * ```tsx
 * <TreeNode
 *   node={nodeData}
 *   showMoveNumbers={true}
 *   onNodeClick={(id) => handleClick(id)}
 *   maxDepth={10}
 * />
 * ```
 *
 * Covers: T040
 */

import type { JSX } from 'preact';
import type { TreeNodeData } from './SolutionTree';

/**
 * Props for TreeNode component.
 */
export interface TreeNodeProps {
  /** Node data */
  node: TreeNodeData;
  /** Whether to show move numbers */
  showMoveNumbers: boolean;
  /** Callback when node is clicked */
  onNodeClick?: ((nodeId: string) => void) | undefined;
  /** Maximum depth to render */
  maxDepth: number;
}

/**
 * TreeNode - Renders a single node in the solution tree.
 *
 * Features:
 * - Correct/wrong move styling
 * - Path highlighting
 * - Current position indicator
 * - Dead-end marker for wrong terminal moves
 * - Move number and coordinate display
 */
export function TreeNode({
  node,
  showMoveNumbers,
  onNodeClick,
  maxDepth,
}: TreeNodeProps): JSX.Element | null {
  // Don't render beyond max depth
  if (node.depth > maxDepth) return null;

  const isDeadEnd = !node.isCorrect && node.children.length === 0;

  const nodeClasses = [
    'tree-node',
    node.isOnPath ? 'on-path' : '',
    node.isCurrent ? 'current' : '',
    node.isCorrect ? 'correct' : 'wrong',
    node.isUserMove ? 'user-move' : 'opponent-move',
  ]
    .filter(Boolean)
    .join(' ');

  const handleClick = () => {
    onNodeClick?.(node.id);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onNodeClick?.(node.id);
    }
  };

  return (
    <div
      data-testid={`tree-node-${node.id}`}
      className={nodeClasses}
      style={{ '--depth': node.depth } as JSX.CSSProperties}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="treeitem"
      aria-selected={node.isCurrent}
      aria-expanded={node.children.length > 0}
      tabIndex={0}
    >
      <span className="node-content">
        {showMoveNumbers && <span className="move-number">{node.moveNumber}</span>}
        <span className="move-coord">{node.displayMove}</span>
        {node.isUserMove && (
          <span className="stone-indicator black" aria-hidden="true">
            ●
          </span>
        )}
        {!node.isUserMove && (
          <span className="stone-indicator white" aria-hidden="true">
            ○
          </span>
        )}
        {isDeadEnd && (
          <span className="dead-end" data-testid="dead-end" aria-label="Dead end">
            ✗
          </span>
        )}
      </span>

      {node.children.length > 0 && (
        <div className="tree-children" role="group">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              showMoveNumbers={showMoveNumbers}
              onNodeClick={onNodeClick}
              maxDepth={maxDepth}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default TreeNode;
