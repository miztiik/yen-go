// @ts-nocheck
/**
 * SVG Board Components
 * @module components/Board/svg
 *
 * Internal SVG components used by BoardSvg
 */

export { SvgGrid } from './SvgGrid';
export { SvgStone, StoneDefs, type SvgStoneProps } from './SvgStone';
export { SvgMarkers } from './SvgMarkers';
export { SvgCoordLabels } from './SvgCoordLabels';
export { GhostStoneLayer, type GhostStoneLayerProps } from './GhostStoneLayer';

// Constants and utilities
export {
  SVG_CONSTANTS,
  SVG_COLORS,
  COLUMN_LABELS,
  STAR_POINTS,
  svgPos,
  calculateViewBox,
  calculatePartialViewBox,
  isValidCoordinate,
  getStarPoints,
} from './constants';
