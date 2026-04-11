// @ts-nocheck
/**
 * Board component exports
 * @module components/Board
 *
 * Spec 118 - T1.9: Board export
 * Spec 127 US8: Removed feature flags dependency — canvas is default.
 */

import { Board as BoardCanvasComponent } from './Board';
import { BoardSvg } from './BoardSvg';

// Main board component — Canvas is the default renderer.
// SVG board is available via direct import for future use.
export const Board = BoardCanvasComponent;
export type { BoardProps } from './Board';

// Direct exports for explicit usage or testing
export { BoardCanvas, type BoardCanvasProps } from './BoardCanvas';
export { BoardSvg };

// Other board components
export { TurnIndicator, TurnStone, AnimatedTurnIndicator, type TurnIndicatorProps } from './TurnIndicator';
export { BoardControls, type BoardControlsProps } from './BoardControls';
export { default } from './Board';

// Grid rendering utilities
export {
  drawBoardBackground,
  drawGridLines,
  drawCoordinateLabels,
  drawGrid,
  type BoardDimensions,
} from './grid';

// Star point (hoshi) utilities
export {
  STAR_POINTS,
  isStarPoint,
  getStarPoints,
  drawStarPoint,
  drawStarPoints,
  getTengen,
} from './hoshi';

// Stone rendering utilities
export {
  drawStone,
  drawHoverStone,
  drawStones,
  drawLastMoveMarker,
  drawStoneNumber,
  stoneToColor,
} from './stones';

// Interaction utilities
export {
  validatePlacement,
  screenToBoardCoord,
  boardToScreenCoord,
  findNearestIntersection,
  isTouchDevice,
  shouldEnableHover,
  createPlacementHandler,
  type InteractionMode,
  type PlacementResult,
  type InteractionConfig,
  type TouchData,
} from './interaction';

// Preview utilities (hover stone)
export {
  calculateHoverStone,
  createPreviewManager,
  getPreviewState,
  shouldEnablePreview,
  debouncePreview,
  throttlePreview,
  type HoverStone,
  type PreviewConfig,
  type PreviewManager,
  type PreviewState,
} from './preview';

// Feedback utilities
export {
  createFeedbackManager,
  drawCorrectFeedback,
  drawIncorrectFeedback,
  drawFeedback,
  calculateShakeOffset,
  triggerHapticFeedback,
  getFeedbackAnimation,
  FEEDBACK_CLASSES,
  FEEDBACK_KEYFRAMES,
  DEFAULT_ANIMATION_CONFIG,
  type FeedbackType,
  type FeedbackState,
  type FeedbackManager,
  type AnimationConfig,
} from './feedback';

// Animation utilities
export {
  createAnimationManager,
  drawCapturingStone,
  drawCaptureAnimations,
  drawPlacingStone,
  drawHighlightAnimation,
  drawAllAnimations,
  createAnimationLoop,
  getCaptureProgress,
  easing,
  type StoneAnimation,
  type AnimationManager,
} from './animations';
