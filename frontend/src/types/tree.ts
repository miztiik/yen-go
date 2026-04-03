/**
 * Tree Visualization Types
 * @module types/tree
 *
 * Types for the graphical solution tree visualization.
 * Ported from Besogo's tree panel approach.
 *
 * Feature: 056-solution-tree-visualization
 * Tasks: T001
 *
 * Constitution Compliance:
 * - VI. Type Safety: Full TypeScript strict mode compliance
 * - V. No Browser AI: Types for rendering only, no move generation
 */

import type { SolutionNode } from './puzzle-internal';

// ============================================================================
// Layout Types
// ============================================================================

/**
 * Layout position for a tree node in SVG coordinate space.
 */
export interface TreeNodeLayout {
  /** Column index (depth from root, 0-based) */
  x: number;
  /** Row index (variation position, 0-based) */
  y: number;
  /** SVG x-coordinate (computed: x * GRID_SIZE + OFFSET) */
  svgX: number;
  /** SVG y-coordinate (computed: y * GRID_SIZE + OFFSET) */
  svgY: number;
}

/**
 * Visual tree node combining solution data with layout.
 * Created by computeTreeLayout() for rendering.
 */
export interface VisualTreeNode {
  /** Unique identifier (e.g., "0", "0-1", "0-1-2" for depth-sibling path) */
  id: string;
  /** Reference to underlying solution node */
  node: SolutionNode;
  /** Layout position in SVG space */
  layout: TreeNodeLayout;
  /** Parent node reference (null for root) */
  parent: VisualTreeNode | null;
  /** Child nodes */
  children: VisualTreeNode[];
  /** Cached move number for display (1-based) */
  moveNumber: number;
  /** Human-readable coordinate (e.g., "C3") */
  displayCoord: string;
}

/**
 * Result of tree layout computation.
 * Contains the visual tree and metadata for rendering.
 */
export interface TreeLayoutResult {
  /** Root of the visual tree */
  root: VisualTreeNode;
  /** Total width in grid units */
  width: number;
  /** Total height in grid units */
  height: number;
  /** SVG viewBox dimensions (scaled) */
  viewBox: {
    width: number;
    height: number;
  };
  /** Map from node ID to VisualTreeNode for O(1) lookup */
  nodeMap: Map<string, VisualTreeNode>;
}

// ============================================================================
// Navigation Types
// ============================================================================

/**
 * Tree navigation state.
 * Tracks current position and history for back-tracking.
 */
export interface TreeNavigationState {
  /** Currently selected node */
  current: VisualTreeNode;
  /** Navigation history for back-tracking (stack) */
  history: VisualTreeNode[];
  /** Path from root to current (IDs for highlighting) */
  currentPath: string[];
}

/**
 * Navigation actions for tree traversal.
 * Used by useTreeNavigation hook.
 */
export type NavigationAction =
  | { type: 'GOTO'; node: VisualTreeNode }
  | { type: 'GOTO_ID'; nodeId: string }
  | { type: 'NEXT' }
  | { type: 'PREV' }
  | { type: 'NEXT_SIBLING' }
  | { type: 'PREV_SIBLING' }
  | { type: 'BRANCH_POINT' }
  | { type: 'RESET' };

// ============================================================================
// Variant Style Types (P3 Feature)
// ============================================================================

/**
 * How to display variations on the board.
 * Controls what variation markers appear.
 */
export type VariantDisplayMode = 'children' | 'siblings' | 'hidden';

/**
 * Variant style configuration.
 * Controls how variations are displayed on board and tree.
 */
export interface VariantStyle {
  /** Which variations to show */
  mode: VariantDisplayMode;
  /** Whether to show markers on board */
  showOnBoard: boolean;
}

// ============================================================================
// Component Props Types
// ============================================================================

/**
 * Props for SolutionTreeView component.
 * Main tree visualization component.
 */
export interface SolutionTreeViewProps {
  /** Root of solution tree (from SGF parser) */
  tree: SolutionNode;
  /** ID of the currently selected node */
  currentNodeId: string;
  /** Callback when user clicks a node */
  onNodeSelect: (nodeId: string, node: SolutionNode) => void;
  /** Callback when user navigates via keyboard */
  onNavigate?: (action: NavigationAction) => void;
  /** Show green/red correctness indicators (default: false) */
  showCorrectness?: boolean;
  /** Maximum depth to render (default: unlimited) */
  maxDepth?: number;
  /** Scale factor for SVG rendering (default: 0.25) */
  scale?: number;
  /** CSS class name for container */
  className?: string;
}

/**
 * Props for useTreeNavigation hook.
 */
export interface UseTreeNavigationOptions {
  /** Root of solution tree */
  tree: SolutionNode;
  /** Initial node ID (default: root) */
  initialNodeId?: string;
  /** Callback when navigation changes */
  onChange?: (state: TreeNavigationState) => void;
}

/**
 * Return type for useTreeNavigation hook.
 */
export interface UseTreeNavigationResult {
  /** Current navigation state */
  state: TreeNavigationState;
  /** Computed layout */
  layout: TreeLayoutResult;
  /** Navigate to a specific node by ID */
  goTo: (nodeId: string) => void;
  /** Navigate to next node (first child) */
  next: () => void;
  /** Navigate to previous node (parent) */
  prev: () => void;
  /** Navigate to next sibling */
  nextSibling: () => void;
  /** Navigate to previous sibling */
  prevSibling: () => void;
  /** Navigate to previous branch point */
  toBranchPoint: () => void;
  /** Reset to root */
  reset: () => void;
  /** Dispatch a navigation action */
  dispatch: (action: NavigationAction) => void;

  // ============================================================================
  // Computed Properties (restored from HEAD merge)
  // ============================================================================

  /** Current move number (1-based) */
  moveNumber: number;
  /** Comment at current node (if any) */
  comment: string | null;
  /** Whether current node has siblings */
  hasSiblings: boolean;
  /** Whether current node is at a branch point (has multiple children) */
  isAtBranchPoint: boolean;
  /** Sibling nodes of current position */
  siblings: VisualTreeNode[];
}

// ============================================================================
// SVG Element Types
// ============================================================================

/**
 * Attributes for an SVG stone circle.
 */
export interface StoneAttributes {
  cx: number;
  cy: number;
  r: number;
  fill: string;
  stroke?: string;
  strokeWidth?: number;
}

/**
 * Attributes for an SVG text label.
 */
export interface LabelAttributes {
  x: number;
  y: number;
  textAnchor: string;
  dominantBaseline: string;
  fill: string;
  fontSize: number;
  fontWeight?: string;
}

/**
 * Attributes for a selection/current marker.
 */
export interface MarkerAttributes {
  x: number;
  y: number;
  width: number;
  height: number;
  fill: string;
  opacity: number;
  rx?: number;
  stroke?: string;
  strokeWidth?: number;
}
