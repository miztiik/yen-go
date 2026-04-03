/**
 * Star point (hoshi) rendering utilities for Go board
 * @module components/Board/hoshi
 *
 * Covers: FR-001 (Display board), FR-003 (Grid display with star points)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Hoshi rendering only
 * - VI. Pure TypeScript: Canvas API
 */

import type { BoardSize, Coordinate } from '@models/puzzle';
import type { BoardDimensions } from './grid';

/** Star point radius relative to cell size */
const STAR_POINT_RADIUS_RATIO = 0.12;

/** Star point color */
const STAR_POINT_COLOR = '#5C4A32';

/**
 * Star point positions for different board sizes
 * Traditional Go board star point placements
 */
export const STAR_POINTS: Record<BoardSize, Coordinate[]> = {
  9: [
    { x: 2, y: 2 },
    { x: 6, y: 2 },
    { x: 4, y: 4 }, // tengen (center)
    { x: 2, y: 6 },
    { x: 6, y: 6 },
  ],
  13: [
    { x: 3, y: 3 },
    { x: 9, y: 3 },
    { x: 6, y: 6 }, // tengen (center)
    { x: 3, y: 9 },
    { x: 9, y: 9 },
  ],
  19: [
    { x: 3, y: 3 },
    { x: 9, y: 3 },
    { x: 15, y: 3 },
    { x: 3, y: 9 },
    { x: 9, y: 9 }, // tengen (center)
    { x: 15, y: 9 },
    { x: 3, y: 15 },
    { x: 9, y: 15 },
    { x: 15, y: 15 },
  ],
};

/**
 * Check if a position is a star point (hoshi)
 * @param boardSize - Size of the board (9, 13, or 19)
 * @param coord - Coordinate to check
 * @returns true if the position is a star point
 */
export function isStarPoint(boardSize: BoardSize, coord: Coordinate): boolean {
  const starPoints = STAR_POINTS[boardSize];
  return starPoints.some((sp) => sp.x === coord.x && sp.y === coord.y);
}

/**
 * Get star point positions for a board size
 * @param boardSize - Size of the board (9, 13, or 19)
 * @returns Array of star point coordinates
 */
export function getStarPoints(boardSize: BoardSize): readonly Coordinate[] {
  return STAR_POINTS[boardSize];
}

/**
 * Draw a single star point
 * @param ctx - Canvas rendering context
 * @param coord - Star point coordinate
 * @param dimensions - Board dimensions
 */
export function drawStarPoint(
  ctx: CanvasRenderingContext2D,
  coord: Coordinate,
  dimensions: BoardDimensions
): void {
  const { cellSize, offsetX, offsetY } = dimensions;
  const radius = cellSize * STAR_POINT_RADIUS_RATIO;

  ctx.fillStyle = STAR_POINT_COLOR;
  ctx.beginPath();
  ctx.arc(
    offsetX + coord.x * cellSize,
    offsetY + coord.y * cellSize,
    radius,
    0,
    Math.PI * 2
  );
  ctx.fill();
}

/**
 * Draw all star points for a board size
 * @param ctx - Canvas rendering context
 * @param boardSize - Size of the board (9, 13, or 19)
 * @param dimensions - Board dimensions
 */
export function drawStarPoints(
  ctx: CanvasRenderingContext2D,
  boardSize: BoardSize,
  dimensions: BoardDimensions
): void {
  const starPoints = getStarPoints(boardSize);

  for (const point of starPoints) {
    drawStarPoint(ctx, point, dimensions);
  }
}

/**
 * Get tengen (center) position for a board size
 * @param boardSize - Size of the board (9, 13, or 19)
 * @returns Center coordinate
 */
export function getTengen(boardSize: BoardSize): Coordinate {
  const center = Math.floor(boardSize / 2);
  return { x: center, y: center };
}
