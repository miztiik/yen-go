/**
 * Solution Tree Component
 * @module components/SolutionTree/SolutionTree
 * 
 * @description
 * Visualizes the puzzle solution tree showing player's path and branches.
 * This component renders an accessible, interactive tree visualization with:
 * - Path highlighting to show current navigation path
 * - Click-to-navigate functionality (FR-006)
 * - Keyboard navigation support (FR-018)
 * - Accessibility features (ARIA labels, 44pt touch targets)
 * - Setup node support (FR-003)
 * - Tesuji (key move) highlighting (Spec 012)
 *
 * Constitution Compliance:
 * - V. No Browser AI: Only renders pre-computed solution tree
 * - IX. Accessibility: ARIA labels, keyboard support, touch targets
 *
 * Requirements Covered:
 * - FR-001 to FR-005: Tree Rendering
 * - FR-006 to FR-011: Navigation
 * - FR-018: Keyboard shortcuts
 * - FR-019: 44pt touch targets
 * - FR-020: WCAG AA contrast
 * - FR-021: Smooth scroll animation
 *
 * @example
 * ```tsx
 * <SolutionTree
 *   tree={solutionNode}
 *   currentPath={['0-cc', '1-dd']}
 *   onNodeClick={(id) => navigateTo(id)}
 *   showMoveNumbers={true}
 * />
 * ```
 *
 * @see SolutionTreeErrorBoundary - For error handling wrapper
 * @see TreeNode - Individual node rendering (TreeNode.tsx)
 * 
 * Covers: T039, T004-T020
 */

import type { JSX } from 'preact';
import { useMemo, useCallback } from 'preact/hooks';
import type { SolutionNode } from '@/types/puzzle-internal';
// Note: positionToSgf is available but not currently needed
import './SolutionTree.css';

/**
 * Node data for tree visualization.
 */
export interface TreeNodeData {
  /** Unique identifier */
  id: string;
  /** SGF move coordinate (e.g., 'cc') */
  move: string;
  /** Human-readable coordinate (e.g., 'C3') */
  displayMove: string;
  /** Whether this is a correct move */
  isCorrect: boolean;
  /** Whether this is a tesuji (key tactical move) - Spec 012 */
  isTesuji: boolean;
  /** Whether this is a setup node (no move, just placed stones) - FR-003 */
  isSetupNode: boolean;
  /** Whether this is on the current path */
  isOnPath: boolean;
  /** Whether this is the current position */
  isCurrent: boolean;
  /** Whether this is a user move (vs opponent response) */
  isUserMove: boolean;
  /** Depth in tree (for indentation) */
  depth: number;
  /** Move number in sequence */
  moveNumber: number;
  /** Child nodes */
  children: TreeNodeData[];
}

/**
 * Props for SolutionTree component.
 */
export interface SolutionTreeProps {
  /** Root of solution tree */
  tree: SolutionNode;
  /** IDs of nodes on current path */
  currentPath: string[];
  /** Callback when node is clicked */
  onNodeClick?: ((nodeId: string) => void) | undefined;
  /** Maximum depth to render */
  maxDepth?: number;
  /** Whether to show move numbers */
  showMoveNumbers?: boolean;
  /** Whether to show opponent responses */
  showResponses?: boolean;
  /** CSS class name */
  className?: string;
  /** 
   * Reveal mode for progressive disclosure (T3.2).
   * - 'progressive': Only show explored branches (nodes player has visited)
   * - 'full': Show entire solution tree (default, for completion/show answer)
   */
  revealMode?: 'progressive' | 'full';
  /** 
   * Set of node IDs that have been explored/visited.
   * Used when revealMode='progressive' to filter visible nodes.
   */
  exploredNodes?: Set<string>;
}

/**
 * Convert board position to human-readable coordinate.
 * e.g., (2, 2) with boardSize 9 -> 'C7'
 */
function positionToDisplay(sgfMove: string, boardSize: number = 9): string {
  if (!sgfMove || sgfMove.length !== 2) return '??';
  
  const x = sgfMove.charCodeAt(0) - 97; // 'a' = 0
  const y = sgfMove.charCodeAt(1) - 97;
  
  // Convert to standard Go notation (A-T, excluding I, 1-19 from bottom)
  const letters = 'ABCDEFGHJKLMNOPQRST'; // No 'I'
  const col = letters[x] || '?';
  const row = boardSize - y;
  
  return `${col}${row}`;
}

/**
 * Convert SolutionNode tree to TreeNodeData with path marking.
 * FR-003: Setup nodes (empty move) are marked with isSetupNode=true.
 */
function buildTreeData(
  node: SolutionNode,
  currentPath: Set<string>,
  depth: number,
  moveNumber: number,
  isUserMove: boolean
): TreeNodeData {
  const id = `${depth}-${node.move}`;
  const isOnPath = currentPath.has(id);
  const pathArray = Array.from(currentPath);
  const isCurrent = pathArray[pathArray.length - 1] === id;
  // FR-003: Detect setup nodes (no move, just placed stones)
  const isSetupNode = !node.move || node.move === '' || node.move === 'root';

  const data: TreeNodeData = {
    id,
    move: node.move,
    displayMove: isSetupNode ? '+' : positionToDisplay(node.move),
    isCorrect: node.isCorrect,
    isTesuji: node.isTesuji ?? false,
    isSetupNode,
    isOnPath,
    isCurrent,
    isUserMove,
    depth,
    moveNumber: isSetupNode ? 0 : moveNumber,
    children: [],
  };

  // Build children (alternating user/opponent)
  for (const child of node.children) {
    data.children.push(
      buildTreeData(
        child,
        currentPath,
        depth + 1,
        moveNumber + 1,
        !isUserMove // Alternate between user and opponent
      )
    );
  }

  return data;
}

/**
 * TreeNode component - renders a single node in the tree.
 */
function TreeNode({
  node,
  showMoveNumbers,
  onNodeClick,
  maxDepth,
  revealMode,
  exploredNodes,
}: {
  node: TreeNodeData;
  showMoveNumbers: boolean;
  onNodeClick?: ((nodeId: string) => void) | undefined;
  maxDepth: number;
  revealMode: 'progressive' | 'full';
  exploredNodes: Set<string>;
}): JSX.Element | null {
  // Don't render beyond max depth
  if (node.depth > maxDepth) return null;

  const isDeadEnd = !node.isCorrect && node.children.length === 0;

  // Build CSS classes - Spec 012: Added tesuji class, FR-003: Added setup-node class
  const nodeClasses = [
    'tree-node',
    node.isOnPath ? 'on-path' : '',
    node.isCurrent ? 'current' : '',
    node.isCorrect ? 'correct' : 'wrong',
    node.isTesuji ? 'tesuji' : '',
    node.isSetupNode ? 'setup-node' : '',
    node.isUserMove ? 'user-move' : 'opponent-move',
  ].filter(Boolean).join(' ');

  // Spec 012: Build ARIA label for accessibility
  const ariaLabel = [
    node.isSetupNode ? 'Setup position' : node.displayMove,
    !node.isCorrect ? 'Wrong move' : '',
    node.isTesuji ? 'Tesuji - key move' : '',
    isDeadEnd ? 'Dead end' : '',
  ].filter(Boolean).join(', ');

  /**
   * Handle keyboard activation for accessibility.
   * Enter/Space should activate the node like a click.
   */
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onNodeClick?.(node.id);
    }
  };

  // FR-002: Stone icons - black for user, white for opponent
  const stoneIcon = node.isSetupNode ? '+' : (node.isUserMove ? '●' : '○');

  return (
    <div
      data-testid={`tree-node-${node.id}`}
      className={nodeClasses}
      style={{ '--depth': node.depth } as JSX.CSSProperties}
      onClick={() => onNodeClick?.(node.id)}
      onKeyDown={handleKeyDown}
      role="treeitem"
      aria-label={ariaLabel}
      aria-selected={node.isCurrent}
      aria-expanded={node.children.length > 0}
      tabIndex={0}
      title={node.isSetupNode ? 'Setup position' : `${node.displayMove} (Move ${node.moveNumber})`}
    >
      <span className="node-content">
        {/* FR-002: Stone icon indicator */}
        <span className={`stone-icon ${node.isUserMove ? 'black' : 'white'}`} aria-hidden="true">
          {stoneIcon}
        </span>
        {showMoveNumbers && !node.isSetupNode && (
          <span className="move-number">{node.moveNumber}</span>
        )}
        <span className="move-coord">{node.displayMove}</span>
        {isDeadEnd && (
          <span className="dead-end" data-testid="dead-end" aria-label="Dead end">
            ✗
          </span>
        )}
      </span>
      
      {node.children.length > 0 && (
        <div className="tree-children" role="group">
          {node.children
            // T3.2: Filter children in progressive mode - only show explored nodes
            .filter((child) => revealMode === 'full' || exploredNodes.has(child.id))
            .map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              showMoveNumbers={showMoveNumbers}
              onNodeClick={onNodeClick}
              maxDepth={maxDepth}
              revealMode={revealMode}
              exploredNodes={exploredNodes}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * SolutionTree - Visualizes the puzzle solution tree.
 *
 * Shows:
 * - Current path through the tree
 * - Correct vs wrong moves
 * - Dead-end branches
 * - Move numbers and coordinates
 * - T3.2: Progressive reveal (only show explored branches during solving)
 */
export function SolutionTree({
  tree,
  currentPath,
  onNodeClick,
  maxDepth = 10,
  showMoveNumbers = true,
  className,
  revealMode = 'full',
  exploredNodes: exploredNodesProp,
}: SolutionTreeProps): JSX.Element {
  // Convert path array to set for O(1) lookups
  const pathSet = useMemo(() => new Set(currentPath), [currentPath]);

  // T3.2: Default exploredNodes to include root and current path when not provided
  const exploredNodes = useMemo(() => {
    if (exploredNodesProp) return exploredNodesProp;
    // By default, the current path is considered "explored"
    const explored = new Set<string>();
    explored.add('0-'); // Root is always visible
    explored.add('0-root'); // Root variant
    currentPath.forEach(id => explored.add(id));
    return explored;
  }, [exploredNodesProp, currentPath]);

  // Build tree data with path marking
  const treeData = useMemo(
    () => buildTreeData(tree, pathSet, 0, 1, true),
    [tree, pathSet]
  );

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      onNodeClick?.(nodeId);
    },
    [onNodeClick]
  );

  return (
    <div
      className={`solution-tree ${className ?? ''}`}
      data-testid="solution-tree"
      role="tree"
      aria-label="Solution tree"
    >
      <TreeNode
        node={treeData}
        showMoveNumbers={showMoveNumbers}
        onNodeClick={handleNodeClick}
        maxDepth={maxDepth}
        revealMode={revealMode}
        exploredNodes={exploredNodes}
      />
    </div>
  );
}

export default SolutionTree;
