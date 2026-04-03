/**
 * Tree Visualization Constants
 * @module lib/tree/constants
 *
 * Configuration constants for SVG tree rendering.
 * All dimensions in pixels. Based on Besogo's tree panel.
 *
 * Feature: 056-solution-tree-visualization
 * Tasks: T002
 *
 * Constitution Compliance:
 * - X. Accessibility: WCAG contrast ratios, touch targets
 * - VI. Type Safety: All values typed with 'as const'
 */

// ============================================================================
// Grid & Layout
// ============================================================================

/**
 * Grid size in SVG units.
 * Each node occupies a GRID_SIZE x GRID_SIZE cell.
 * Value from Besogo's treePanel.js.
 */
export const GRID_SIZE = 120;

/**
 * Stone radius relative to grid size.
 * Reduced from Besogo's 0.43 to 0.35 for better visual spacing.
 */
export const STONE_RADIUS_RATIO = 0.35;

/**
 * Scale factor for SVG viewBox.
 * Reduces visual size while maintaining internal coordinates.
 * Default 0.25 = tree renders at 25% of full size.
 */
export const DEFAULT_SCALE = 0.25;

/**
 * Minimum padding around tree content in grid units.
 */
export const TREE_PADDING = 0.5;

// ============================================================================
// Colors
// ============================================================================

/**
 * Color palette for tree visualization.
 * WCAG AA compliant contrast ratios.
 */
export const COLORS = {
  /** Stone colors */
  stone: {
    black: '#1a1a1a',
    white: '#f5f5f5',
    blackStroke: '#000000',
    whiteStroke: '#666666',
  },

  /** Label text colors (on stones) */
  label: {
    onBlack: '#ffffff',
    onWhite: '#1a1a1a',
  },

  /** Path/edge colors */
  path: {
    default: '#666666',
    current: '#3b82f6', // Blue for current path
    variation: '#9ca3af', // Gray for variations
  },

  /** Node state colors */
  state: {
    current: '#3b82f6', // Blue highlight
    hover: '#60a5fa', // Lighter blue
    focus: '#2563eb', // Darker blue (focus ring)
    selected: '#dbeafe', // Very light blue background
  },

  /** Correctness indicators (FR-022) */
  correctness: {
    correct: '#16a34a', // Green for correct moves
    wrong: '#dc2626', // Red for wrong moves
    neutral: 'transparent', // No indicator
  },

  /** Background colors */
  background: {
    tree: '#fafafa',
    comment: '#ffffff',
    tooltip: '#1f2937',
  },

  /** Comment panel colors */
  comment: {
    text: '#374151',
    border: '#e5e7eb',
  },
} as const;

// ============================================================================
// Animation
// ============================================================================

/**
 * Animation timing configuration (FR-021).
 * All durations in milliseconds.
 */
export const ANIMATION = {
  /** Scroll animation duration */
  scrollDuration: 300,
  /** Scroll animation easing */
  scrollEasing: 'ease-out',
  /** Transition duration for highlights */
  highlightDuration: 150,
  /** Hover transition */
  hoverDuration: 100,
  /** Comment panel slide */
  panelSlideDuration: 200,
} as const;

// ============================================================================
// Accessibility (FR-019, FR-020)
// ============================================================================

/**
 * Accessibility configuration.
 */
export const ACCESSIBILITY = {
  /** Minimum touch target size in pixels (44x44pt per WCAG) */
  minTouchTarget: 44,

  /** Focus ring width in pixels */
  focusRingWidth: 3,

  /** Minimum contrast ratio (WCAG AA) */
  minContrastRatio: 4.5,

  /** ARIA labels for tree elements */
  ariaLabels: {
    tree: 'Solution tree navigation',
    node: (moveNum: number, coord: string, player: 'B' | 'W') =>
      `Move ${moveNum}: ${player === 'B' ? 'Black' : 'White'} at ${coord}`,
    currentNode: 'Current position',
    correctMove: 'Correct move',
    wrongMove: 'Wrong move',
  },

  /** Keyboard navigation keys */
  keys: {
    next: ['ArrowRight', 'ArrowDown', 'l', 'j'] as string[],
    prev: ['ArrowLeft', 'ArrowUp', 'h', 'k'] as string[],
    nextSibling: ['PageDown', 'n'] as string[],
    prevSibling: ['PageUp', 'p'] as string[],
    branchPoint: ['b', 'Backspace'] as string[],
    reset: ['Home', 'r'] as string[],
    end: ['End', 'e'] as string[],
  },
} as const;

// ============================================================================
// Path Rendering
// ============================================================================

/**
 * SVG path rendering configuration.
 */
export const PATH = {
  /** Stroke width for edges */
  strokeWidth: 2,
  /** Stroke width for current path */
  currentStrokeWidth: 3,
  /** Corner radius for rounded paths (future use) */
  cornerRadius: 0,
} as const;

// ============================================================================
// Tooltip / Coordinate Display (FR-023)
// ============================================================================

/**
 * Tooltip configuration for coordinate display.
 */
export const TOOLTIP = {
  /** Offset from cursor in pixels */
  offsetX: 10,
  offsetY: 10,
  /** Padding inside tooltip */
  padding: 8,
  /** Border radius */
  borderRadius: 4,
  /** Font size */
  fontSize: 12,
  /** Show delay in milliseconds */
  showDelay: 0,
  /** Hide delay in milliseconds */
  hideDelay: 0,
} as const;

// ============================================================================
// Comment Panel (FR-013)
// ============================================================================

/**
 * Comment panel configuration.
 */
export const COMMENT_PANEL = {
  /** Maximum width in pixels */
  maxWidth: 280,
  /** Padding in pixels */
  padding: 12,
  /** Border radius */
  borderRadius: 8,
  /** Distance from board in pixels */
  boardGap: 16,
} as const;

// ============================================================================
// Derived Values
// ============================================================================

/**
 * Stone radius in SVG units.
 */
export const STONE_RADIUS = GRID_SIZE * STONE_RADIUS_RATIO;

/**
 * Label font size relative to stone radius.
 */
export const LABEL_FONT_SIZE = STONE_RADIUS * 0.7;

/**
 * Offset from grid edge (half of grid size, centers stones).
 */
export const GRID_OFFSET = GRID_SIZE / 2;
