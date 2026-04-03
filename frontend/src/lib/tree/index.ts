/**
 * Tree Visualization Library - Barrel Export
 * @module lib/tree
 *
 * Exports all tree-related utilities for solution tree rendering.
 *
 * Feature: 056-solution-tree-visualization
 * Tasks: T004
 */

// Constants
export {
  GRID_SIZE,
  STONE_RADIUS,
  STONE_RADIUS_RATIO,
  DEFAULT_SCALE,
  TREE_PADDING,
  LABEL_FONT_SIZE,
  GRID_OFFSET,
  COLORS,
  ANIMATION,
  ACCESSIBILITY,
  PATH,
  TOOLTIP,
  COMMENT_PANEL,
} from './constants';

// SVG Utilities
export {
  createStoneAttributes,
  createLabelAttributes,
  createPathData,
  createPathAttributes,
  createCurrentMarkerAttributes,
  createHoverMarkerAttributes,
  createCorrectnessIndicatorAttributes,
  gridToSvg,
  svgToGrid,
  sgfToDisplayCoord,
  calculateViewBox,
  isClickOnNode,
  findNodeAtPosition,
} from './svg-utils';

// Layout (to be implemented in T005-T008)
export {
  computeTreeLayout,
  findNodeById,
  computePathToNode,
  collectAllNodes,
  getNodeDepth,
} from './layout';

// Navigation (to be implemented in Phase 4)
export {
  findNextSibling,
  findPrevSibling,
  findBranchPoint,
  findNextNode,
  findPrevNode,
} from './navigation';
