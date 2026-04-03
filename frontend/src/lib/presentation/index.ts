/**
 * Presentation Library Index
 * @module lib/presentation
 *
 * Re-exports all presentation utilities for solution display.
 */

export {
  buildNumberedSequence,
  formatCollisionCaption,
  getMovesAtFrame,
  getCollisionsAtFrame,
  getNumberTextColor,
  extractMovesFromPath,
  type SolutionMove,
} from './numberedSolution';

export {
  calculateViewport,
  createFullBoardViewport,
  expandViewport,
  getViewportGridSize,
  isInViewport,
  transformToViewport,
  transformFromViewport,
} from './viewportCalculator';

export {
  getExploreHints,
  getExploreHintsFromTree,
  getOptimalMove,
  isMoveValid,
  type SolutionTreeNode,
  type ExploreHintsResult,
} from './exploreHints';
