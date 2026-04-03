/**
 * SVG Board Constants and Utilities
 * @module components/Board/svg/constants
 *
 * Spec 118 - SVG Board Constants
 * Shared constants and utility functions for SVG board rendering
 */

import type { BoardSize } from '@models/puzzle';
import type { Coordinate } from '@models/puzzle';

/**
 * SVG rendering constants
 */
export const SVG_CONSTANTS = {
  /** Size of each cell in SVG units */
  CELL_SIZE: 80,
  /** Margin for coordinate labels */
  COORD_MARGIN: 60,
  /** Extra margin for padding */
  EXTRA_MARGIN: 20,
  /** Star point radius as ratio of cell size */
  STAR_POINT_RADIUS_RATIO: 0.12,
  /** Stone radius as ratio of cell size */
  STONE_RADIUS_RATIO: 0.46,
  /** Ghost stone opacity */
  HOVER_STONE_OPACITY: 0.4,
  /** Last move marker size ratio */
  LAST_MOVE_MARKER_RATIO: 0.25,
} as const;

/**
 * SVG color palette
 * Uses CSS custom properties where possible for theming
 */
export const SVG_COLORS = {
  // Board colors
  board: '#E3C076',
  boardShadow: 'rgba(0, 0, 0, 0.08)',
  grid: '#8B7355',
  starPoint: '#5C4A32',
  coordLabel: '#6B5B45',

  // Stone colors
  blackStone: '#1a1a1a',
  blackStoneHighlight: '#3a3a3a',
  whiteStone: '#f8f8f8',
  whiteStoneHighlight: '#ffffff',
  whiteStoneBorder: '#c0c0c0',

  // Markers
  lastMoveMarker: '#E84545',
  hintGlow: 'rgba(100, 180, 255, 0.6)',
  solutionCorrect: '#16A34A',
  solutionOptimal: '#16A34A',
  solutionWrong: '#DC2626',
  selfAtariWarning: '#E53E3E',

  // Opacity values
  hoverStone: 0.4,
  shadowOpacity: 0.32,
  highlightOpacity: 0.3,
} as const;

/**
 * Column labels (skip 'I' as is traditional in Go)
 */
export const COLUMN_LABELS = 'ABCDEFGHJKLMNOPQRST';

/**
 * Star point positions for different board sizes
 */
export const STAR_POINTS: Record<BoardSize, Coordinate[]> = {
  9: [
    { x: 2, y: 2 },
    { x: 6, y: 2 },
    { x: 4, y: 4 }, // tengen
    { x: 2, y: 6 },
    { x: 6, y: 6 },
  ],
  13: [
    { x: 3, y: 3 },
    { x: 9, y: 3 },
    { x: 6, y: 6 }, // tengen
    { x: 3, y: 9 },
    { x: 9, y: 9 },
  ],
  19: [
    { x: 3, y: 3 },
    { x: 9, y: 3 },
    { x: 15, y: 3 },
    { x: 3, y: 9 },
    { x: 9, y: 9 },
    { x: 15, y: 9 }, // tengen at center
    { x: 3, y: 15 },
    { x: 9, y: 15 },
    { x: 15, y: 15 },
  ],
};

/**
 * Convert board coordinate to SVG position
 * @param coord Board coordinate (0-based)
 * @returns SVG position in units
 */
export function svgPos(coord: number): number {
  return SVG_CONSTANTS.COORD_MARGIN + SVG_CONSTANTS.EXTRA_MARGIN + coord * SVG_CONSTANTS.CELL_SIZE;
}

/**
 * Calculate viewBox dimensions for SVG board
 * @param boardWidth Board width in cells
 * @param boardHeight Board height in cells
 * @param includeCoords Whether to include coordinate labels
 * @returns ViewBox string for SVG
 */
export function calculateViewBox(
  boardWidth: BoardSize,
  boardHeight: BoardSize,
  includeCoords: boolean = true
): string {
  const { CELL_SIZE, COORD_MARGIN, EXTRA_MARGIN } = SVG_CONSTANTS;

  if (!includeCoords) {
    // Just the board grid
    const width = (boardWidth - 1) * CELL_SIZE;
    const height = (boardHeight - 1) * CELL_SIZE;
    return `0 0 ${width} ${height}`;
  }

  // Include coordinate labels
  const width = (boardWidth - 1) * CELL_SIZE + 2 * (COORD_MARGIN + EXTRA_MARGIN);
  const height = (boardHeight - 1) * CELL_SIZE + 2 * (COORD_MARGIN + EXTRA_MARGIN);
  return `0 0 ${width} ${height}`;
}

/**
 * Calculate partial board viewport
 * For Phase 2: Partial Board Rendering
 *
 * @param boardSize Full board size
 * @param region Region to display (e.g., "top-left", "top-right")
 * @param visibleCells Number of cells to show in each direction
 * @returns ViewBox string for cropped viewport
 */
export function calculatePartialViewBox(
  boardSize: BoardSize,
  region: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center',
  visibleCells: number = 9
): string {
  const { CELL_SIZE, COORD_MARGIN } = SVG_CONSTANTS;

  // Calculate region offsets
  let startX = 0;
  let startY = 0;

  switch (region) {
    case 'top-left':
      startX = 0;
      startY = 0;
      break;
    case 'top-right':
      startX = boardSize - visibleCells;
      startY = 0;
      break;
    case 'bottom-left':
      startX = 0;
      startY = boardSize - visibleCells;
      break;
    case 'bottom-right':
      startX = boardSize - visibleCells;
      startY = boardSize - visibleCells;
      break;
    case 'center':
      startX = Math.floor((boardSize - visibleCells) / 2);
      startY = Math.floor((boardSize - visibleCells) / 2);
      break;
  }

  // Calculate SVG viewport
  const x = svgPos(startX) - COORD_MARGIN;
  const y = svgPos(startY) - COORD_MARGIN;
  const width = visibleCells * CELL_SIZE + 2 * COORD_MARGIN;
  const height = visibleCells * CELL_SIZE + 2 * COORD_MARGIN;

  return `${x} ${y} ${width} ${height}`;
}

/**
 * Type guard: Check if coordinate is within bounds
 */
export function isValidCoordinate(coord: Coordinate, boardSize: BoardSize): boolean {
  return coord.x >= 0 && coord.x < boardSize && coord.y >= 0 && coord.y < boardSize;
}

/**
 * Get star points for a given board size
 */
export function getStarPoints(boardSize: BoardSize): Coordinate[] {
  return STAR_POINTS[boardSize] || [];
}
