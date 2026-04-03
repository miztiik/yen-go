/**
 * Solution Tree View Component
 * @module components/SolutionTree/SolutionTreeView
 *
 * SVG-based visual tree rendering for solution exploration.
 * Ported from Besogo's treePanel.js with Preact/TypeScript.
 *
 * Feature: 123-solution-tree-rewrite
 *
 * Constitution Compliance:
 * - VI. Type Safety: Full TypeScript + Preact types
 * - IX. Accessibility: ARIA labels, keyboard navigation, touch targets
 * - V. No Browser AI: Rendering only, no move generation
 * - X. Apple-Inspired Minimalism: Clean SVG rendering
 */

import { JSX } from 'preact';
import { useState, useCallback, useMemo, useRef, useEffect } from 'preact/hooks';
import type { SolutionTreeViewProps, VisualTreeNode } from '../../types/tree';
import {
  computeTreeLayout,
  buildBranchPaths,
  collectAllNodes,
  GRID_SIZE,
  TREE_PADDING,
} from './tree-layout';
import './SolutionTreeView.css';

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_SCALE = 0.25;
const STONE_RADIUS = 45;

// Colors (matching CSS variables)
const COLORS = {
  stone: {
    black: '#1a1a1a',
    white: '#f5f5f5',
    blackStroke: '#000000',
    whiteStroke: '#666666',
  },
  label: {
    onBlack: '#ffffff',
    onWhite: '#1a1a1a',
  },
  marker: {
    current: '#00bcd4',  // Cyan - Besogo style
    hover: '#4dd0e1',    // Lighter cyan for hover
  },
  correctness: {
    correct: '#4CAF50',
    incorrect: '#f44336',
  },
  background: '#fafafa',
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get font size based on move number digits (FR-002).
 * Reduced sizes for cleaner appearance.
 */
function getFontSize(moveNumber: number): number {
  if (moveNumber < 10) return 42; // 1 digit
  if (moveNumber < 100) return 32; // 2 digits
  return 22; // 3 digits
}

/**
 * Get ARIA label for a node.
 */
function getNodeAriaLabel(node: VisualTreeNode): string {
  // Setup node
  if (node.moveNumber === 0 && node.parent === null) {
    return 'Setup position, initial stones';
  }
  
  // Pass move
  const move = node.node.move;
  if (move === '' || move === 'tt' || move === 'pass') {
    const color = node.node.player === 'B' ? 'Black' : 'White';
    return `Move ${node.moveNumber}: ${color} passes`;
  }
  
  // Regular move
  const color = node.node.player === 'B' ? 'Black' : 'White';
  return `Move ${node.moveNumber}: ${color} at ${node.displayCoord}`;
}

// ============================================================================
// Sub-Components
// ============================================================================

interface TreeNodeProps {
  node: VisualTreeNode;
  isSelected: boolean;
  isHovered: boolean;
  showCorrectness: boolean;
  onClick: (node: VisualTreeNode) => void;
  onHover: (node: VisualTreeNode | null) => void;
}

/**
 * Detect if a node is a pass move (SGF: B[] or W[] without coordinates).
 */
function isPassMove(node: VisualTreeNode): boolean {
  const move = node.node.move;
  return move === '' || move === 'tt' || move === 'pass';
}

/**
 * Detect if a node is a setup node (root with initial position).
 */
function isSetupNode(node: VisualTreeNode): boolean {
  return node.moveNumber === 0 && node.parent === null;
}

/**
 * Renders a single tree node (stone with label).
 */
function TreeNode({
  node,
  isSelected,
  isHovered,
  showCorrectness,
  onClick,
  onHover,
}: TreeNodeProps): JSX.Element {
  const { layout, moveNumber } = node;
  const { player, isCorrect } = node.node;

  const handleClick = useCallback(() => onClick(node), [onClick, node]);
  const handleMouseEnter = useCallback(() => onHover(node), [onHover, node]);
  const handleMouseLeave = useCallback(() => onHover(null), [onHover]);

  // Detect special node types
  const isPass = isPassMove(node);
  const isSetup = isSetupNode(node);
  const isSpecialNode = isPass || isSetup;

  // Stone appearance (grey for setup/pass, normal for moves)
  const isBlack = player === 'B';
  const fill = isSpecialNode ? '#999999' : (isBlack ? COLORS.stone.black : COLORS.stone.white);
  const stroke = isSpecialNode ? '#666666' : (isBlack ? COLORS.stone.blackStroke : COLORS.stone.whiteStroke);
  const labelColor = isSpecialNode ? '#ffffff' : (isBlack ? COLORS.label.onBlack : COLORS.label.onWhite);

  // Correctness indicator - never show on setup node (setup is neither correct nor wrong)
  const showCorrectnessRing = showCorrectness && isCorrect !== undefined && !isSetup;

  return (
    <g
      class={`tree-node ${isHovered ? 'tree-node-hovered' : ''} ${isSelected ? 'tree-node-selected' : ''}`}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      role="treeitem"
      tabIndex={isSelected ? 0 : -1}
      aria-label={getNodeAriaLabel(node)}
      aria-selected={isSelected}
      aria-current={isSelected ? 'true' : undefined}
      data-node-id={node.id}
      style={{ cursor: 'pointer' }}
    >
      {/* Correctness indicator ring (only when showCorrectness is true) */}
      {showCorrectnessRing && (
        <circle
          cx={layout.svgX}
          cy={layout.svgY}
          r={STONE_RADIUS + 10}
          fill="none"
          stroke={isCorrect ? COLORS.correctness.correct : COLORS.correctness.incorrect}
          strokeWidth={isCorrect ? 5 : 6}
          strokeDasharray={isCorrect ? 'none' : '10 5'}
          class={`tree-node-correctness ${isCorrect ? 'correct' : 'wrong'}`}
        />
      )}

      {/* Stone circle */}
      <circle
        cx={layout.svgX}
        cy={layout.svgY}
        r={STONE_RADIUS}
        fill={fill}
        stroke={stroke}
        strokeWidth={4}
        class={`tree-stone ${isSpecialNode ? 'tree-stone-special' : `tree-stone-${player}`}`}
      />

      {/* Setup node: dark "+" marker (FR-003) */}
      {isSetup && (
        <text
          x={layout.svgX}
          y={layout.svgY}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#333333"
          fontSize={50}
          fontWeight="700"
          class="tree-label tree-label-setup"
        >
          +
        </text>
      )}

      {/* Pass move: "P" label (FR-003) */}
      {isPass && !isSetup && (
        <text
          x={layout.svgX}
          y={layout.svgY}
          textAnchor="middle"
          dominantBaseline="central"
          fill={labelColor}
          fontSize={36}
          fontWeight="500"
          class="tree-label tree-label-pass"
        >
          P
        </text>
      )}

      {/* Move number label (regular moves) */}
      {moveNumber > 0 && !isPass && !isSetup && (
        <text
          x={layout.svgX}
          y={layout.svgY}
          textAnchor="middle"
          dominantBaseline="central"
          fill={labelColor}
          fontSize={getFontSize(moveNumber)}
          fontWeight="500"
          class="tree-label"
        >
          {moveNumber}
        </text>
      )}
    </g>
  );
}

// ============================================================================
// Navigation Toolbar
// ============================================================================

interface TreeNavigationToolbarProps {
  onFirst: () => void;
  onPrev: () => void;
  onNext: () => void;
  onLast: () => void;
  canGoPrev: boolean;
  canGoNext: boolean;
}

function TreeNavigationToolbar({
  onFirst,
  onPrev,
  onNext,
  onLast,
  canGoPrev,
  canGoNext,
}: TreeNavigationToolbarProps): JSX.Element {
  return (
    <div class="tree-nav-buttons">
      <button
        class="btn btn-icon"
        onClick={onFirst}
        disabled={!canGoPrev}
        aria-label="First move"
        title="First move (Home)"
      >
        ⏮
      </button>
      <button
        class="btn btn-icon"
        onClick={onPrev}
        disabled={!canGoPrev}
        aria-label="Previous move"
        title="Previous move (←)"
      >
        ◀
      </button>
      <button
        class="btn btn-icon"
        onClick={onNext}
        disabled={!canGoNext}
        aria-label="Next move"
        title="Next move (→)"
      >
        ▶
      </button>
      <button
        class="btn btn-icon"
        onClick={onLast}
        disabled={!canGoNext}
        aria-label="Last move"
        title="Last move (End)"
      >
        ⏭
      </button>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * SVG-based solution tree visualization component.
 * Ported from Besogo's treePanel.js.
 */
export function SolutionTreeView({
  tree,
  currentNodeId,
  onNodeSelect,
  onNavigate,
  showCorrectness = false,
  maxDepth: _maxDepth,
  scale = DEFAULT_SCALE,
  className = '',
}: SolutionTreeViewProps): JSX.Element {
  const svgRef = useRef<SVGSVGElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Compute layout (memoized - only recomputes on tree change)
  const layout = useMemo(() => computeTreeLayout(tree), [tree]);

  // Build paths (memoized - recomputes on tree or current change)
  const paths = useMemo(
    () => buildBranchPaths(layout, currentNodeId),
    [layout, currentNodeId]
  );

  // Collect all nodes for rendering
  const nodes = useMemo(() => collectAllNodes(layout.root), [layout]);

  // Find current node
  const currentNode = useMemo(
    () => layout.nodeMap.get(currentNodeId),
    [layout, currentNodeId]
  );

  // Hover state
  const [hoveredNode, setHoveredNode] = useState<VisualTreeNode | null>(null);

  // Screen reader announcement
  const [announcement, setAnnouncement] = useState<string>('');

  // Handle node click
  const handleNodeClick = useCallback(
    (node: VisualTreeNode) => {
      onNodeSelect(node.id, node.node);
    },
    [onNodeSelect]
  );

  // Handle hover
  const handleNodeHover = useCallback((node: VisualTreeNode | null) => {
    setHoveredNode(node);
  }, []);

  // Keyboard navigation - Besogo-aligned key mapping (spec 122 T1.K5)
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // CRITICAL: Prevent board rotation on arrow keys
      event.stopPropagation();

      if (!currentNode) return;

      let targetNode: VisualTreeNode | undefined;

      switch (event.key) {
        case 'ArrowLeft':
          // Previous move (parent) — Besogo: Left = parent
          targetNode = currentNode.parent ?? undefined;
          break;
        case 'ArrowRight':
          // Next move (first child) — Besogo: Right = first child
          targetNode = currentNode.children[0];
          break;
        case 'ArrowUp':
          // Previous sibling/variation — Besogo: Up = prev sibling
          if (currentNode.parent) {
            const siblings = currentNode.parent.children;
            const idx = siblings.indexOf(currentNode);
            if (idx > 0) {
              targetNode = siblings[idx - 1];
            }
          }
          break;
        case 'ArrowDown':
          // Next sibling/variation — Besogo: Down = next sibling
          if (currentNode.parent) {
            const siblings = currentNode.parent.children;
            const idx = siblings.indexOf(currentNode);
            if (idx < siblings.length - 1) {
              targetNode = siblings[idx + 1];
            }
          }
          break;
        case 'Home':
          // Go to root
          targetNode = layout.root;
          break;
        case 'End':
          // Go to last move in current line
          targetNode = currentNode;
          while (targetNode?.children[0]) {
            targetNode = targetNode.children[0];
          }
          break;
        case 'PageUp': {
          // Back 10 moves — Besogo: PageUp = back 10
          event.preventDefault();
          let node: VisualTreeNode | null | undefined = currentNode;
          for (let i = 0; i < 10 && node?.parent; i++) {
            node = node.parent;
          }
          targetNode = node ?? undefined;
          break;
        }
        case 'PageDown': {
          // Forward 10 moves — Besogo: PageDown = forward 10
          event.preventDefault();
          let node: VisualTreeNode | undefined = currentNode;
          for (let i = 0; i < 10 && node?.children[0]; i++) {
            node = node.children[0];
          }
          targetNode = node;
          break;
        }
      }

      if (targetNode && targetNode.id !== currentNodeId) {
        onNodeSelect(targetNode.id, targetNode.node);
        // Announce for screen readers
        const color = targetNode.node.player === 'B' ? 'Black' : 'White';
        setAnnouncement(`Move ${targetNode.moveNumber}: ${color} at ${targetNode.displayCoord}`);
      }
    },
    [currentNode, currentNodeId, layout.root, onNodeSelect]
  );

  // Navigation state
  const canGoPrev = currentNode?.parent !== null && currentNode !== undefined;
  const canGoNext = (currentNode?.children.length ?? 0) > 0;

  // Navigation handlers
  const handleFirst = useCallback(() => {
    if (onNavigate) {
      onNavigate({ type: 'RESET' });
    } else if (layout.root) {
      onNodeSelect(layout.root.id, layout.root.node);
    }
  }, [onNavigate, onNodeSelect, layout.root]);

  const handlePrev = useCallback(() => {
    if (onNavigate) {
      onNavigate({ type: 'PREV' });
    } else if (currentNode?.parent) {
      onNodeSelect(currentNode.parent.id, currentNode.parent.node);
    }
  }, [onNavigate, onNodeSelect, currentNode]);

  const handleNext = useCallback(() => {
    if (onNavigate) {
      onNavigate({ type: 'NEXT' });
    } else if (currentNode?.children[0]) {
      onNodeSelect(currentNode.children[0].id, currentNode.children[0].node);
    }
  }, [onNavigate, onNodeSelect, currentNode]);

  const handleLast = useCallback(() => {
    let node = currentNode;
    while (node?.children[0]) {
      node = node.children[0];
    }
    if (node && node.id !== currentNodeId) {
      onNodeSelect(node.id, node.node);
    }
  }, [onNodeSelect, currentNode, currentNodeId]);

  // Auto-scroll to current node (FR-006)
  useEffect(() => {
    if (!svgRef.current || !scrollContainerRef.current || !currentNode) return;

    const { svgX, svgY } = currentNode.layout;
    const container = scrollContainerRef.current;
    const containerRect = container.getBoundingClientRect();

    // Calculate scroll position to center the current node
    const targetX = svgX * scale - containerRect.width / 2 + GRID_SIZE * scale * TREE_PADDING;
    const targetY = svgY * scale - containerRect.height / 2 + GRID_SIZE * scale * TREE_PADDING;

    // Smooth scroll (guard for JSDOM in tests)
    if (typeof container.scrollTo === 'function') {
      container.scrollTo({
        left: Math.max(0, targetX),
        top: Math.max(0, targetY),
        behavior: 'smooth',
      });
    }
  }, [currentNode, scale]);

  // ViewBox calculation
  const viewBox = `${-TREE_PADDING * GRID_SIZE} ${-TREE_PADDING * GRID_SIZE} ${layout.viewBox.width} ${layout.viewBox.height}`;

  // Scaled dimensions
  const scaledWidth = layout.viewBox.width * scale;
  const scaledHeight = layout.viewBox.height * scale;

  return (
    <div class={`solution-tree-wrapper ${className}`}>
      {/* Screen reader announcements (live region) */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        class="sr-only"
        style={{ position: 'absolute', width: '1px', height: '1px', overflow: 'hidden', clip: 'rect(0,0,0,0)' }}
      >
        {announcement}
      </div>

      <div
        ref={scrollContainerRef}
        class="solution-tree-view smart-scroll"
        role="tree"
        aria-label="Solution tree navigation"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        <svg
          ref={svgRef}
          viewBox={viewBox}
          width={scaledWidth}
          height={scaledHeight}
          class="solution-tree-svg"
          aria-hidden="false"
        >
          {/* Background */}
          <rect
            x={-TREE_PADDING * GRID_SIZE}
            y={-TREE_PADDING * GRID_SIZE}
            width={layout.viewBox.width}
            height={layout.viewBox.height}
            fill={COLORS.background}
            class="tree-background"
          />

          {/* Paths layer (render first, behind nodes) - Besogo connected paths */}
          <g class="tree-paths">
            {paths.map((path, i) => (
              <path
                key={i}
                d={path.d}
                class={path.isCurrentPath ? 'path-current' : 'path-default'}
              />
            ))}
          </g>

          {/* Nodes layer */}
          <g class="tree-nodes">
            {nodes.map((node) => (
              <TreeNode
                key={node.id}
                node={node}
                isSelected={node.id === currentNodeId}
                isHovered={hoveredNode?.id === node.id}
                showCorrectness={showCorrectness}
                onClick={handleNodeClick}
                onHover={handleNodeHover}
              />
            ))}
          </g>
        </svg>
      </div>

      {/* Navigation toolbar */}
      <TreeNavigationToolbar
        onFirst={handleFirst}
        onPrev={handlePrev}
        onNext={handleNext}
        onLast={handleLast}
        canGoPrev={canGoPrev}
        canGoNext={canGoNext}
      />
    </div>
  );
}

export default SolutionTreeView;
