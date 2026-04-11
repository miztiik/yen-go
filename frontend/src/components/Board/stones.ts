// @ts-nocheck
/**
 * Stone rendering utilities for Go board
 * @module components/Board/stones
 *
 * Covers: FR-001 (Display board), FR-004 (Display stones)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Stone rendering only
 * - VI. Pure TypeScript: Canvas API
 */

import type { BoardSize, Coordinate, Stone } from '@models/puzzle';
import { BLACK, WHITE, EMPTY } from '@models/puzzle';
import type { BoardDimensions } from './grid';

/** Stone radius relative to cell size */
const STONE_RADIUS_RATIO = 0.46;

/** Ghost stone transparency */
const GHOST_STONE_ALPHA = 0.4;

/** Stone colors with gradient stops */
const STONE_COLORS = {
  black: {
    highlight: '#5a5a5a',
    mid: '#3a3a3a',
    dark: '#1a1a1a',
    base: '#0a0a0a',
    specularAlpha: 0.15,
  },
  white: {
    highlight: '#ffffff',
    mid: '#fafafa',
    dark: '#e8e8e8',
    base: '#d0d0d0',
    border: 'rgba(0, 0, 0, 0.15)',
    specularAlpha: 0.6,
  },
  shadow: 'rgba(0, 0, 0, 0.35)',
} as const;

/**
 * Draw a single stone with 3D gradient effect
 * @param ctx - Canvas rendering context
 * @param coord - Stone position
 * @param color - Stone color ('black' or 'white')
 * @param dimensions - Board dimensions
 * @param alpha - Opacity (0-1, default 1)
 */
export function drawStone(
  ctx: CanvasRenderingContext2D,
  coord: Coordinate,
  color: 'black' | 'white',
  dimensions: BoardDimensions,
  alpha: number = 1
): void {
  const { cellSize, offsetX, offsetY } = dimensions;
  const radius = cellSize * STONE_RADIUS_RATIO;
  const centerX = offsetX + coord.x * cellSize;
  const centerY = offsetY + coord.y * cellSize;

  ctx.save();
  ctx.globalAlpha = alpha;

  // Drop shadow for depth
  ctx.shadowColor = STONE_COLORS.shadow;
  ctx.shadowBlur = radius * 0.25;
  ctx.shadowOffsetX = radius * 0.1;
  ctx.shadowOffsetY = radius * 0.15;

  // Main stone gradient for 3D effect
  const gradient = ctx.createRadialGradient(
    centerX - radius * 0.35,
    centerY - radius * 0.35,
    radius * 0.05,
    centerX + radius * 0.1,
    centerY + radius * 0.1,
    radius
  );

  if (color === 'black') {
    gradient.addColorStop(0, STONE_COLORS.black.highlight);
    gradient.addColorStop(0.3, STONE_COLORS.black.mid);
    gradient.addColorStop(0.7, STONE_COLORS.black.dark);
    gradient.addColorStop(1, STONE_COLORS.black.base);
  } else {
    gradient.addColorStop(0, STONE_COLORS.white.highlight);
    gradient.addColorStop(0.3, STONE_COLORS.white.mid);
    gradient.addColorStop(0.7, STONE_COLORS.white.dark);
    gradient.addColorStop(1, STONE_COLORS.white.base);
  }

  // Draw stone body
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.fillStyle = gradient;
  ctx.fill();

  // Reset shadow before border
  ctx.shadowColor = 'transparent';
  ctx.shadowBlur = 0;
  ctx.shadowOffsetX = 0;
  ctx.shadowOffsetY = 0;

  // Subtle border for white stones
  if (color === 'white') {
    ctx.strokeStyle = STONE_COLORS.white.border;
    ctx.lineWidth = 0.5;
    ctx.stroke();
  }

  // Specular highlight
  const highlightGradient = ctx.createRadialGradient(
    centerX - radius * 0.3,
    centerY - radius * 0.35,
    0,
    centerX - radius * 0.3,
    centerY - radius * 0.35,
    radius * 0.4
  );

  const specularAlpha =
    color === 'black'
      ? STONE_COLORS.black.specularAlpha
      : STONE_COLORS.white.specularAlpha;

  highlightGradient.addColorStop(0, `rgba(255, 255, 255, ${specularAlpha})`);
  highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.fillStyle = highlightGradient;
  ctx.fill();

  ctx.restore();
}

/**
 * Draw a ghost stone (transparent preview)
 * @param ctx - Canvas rendering context
 * @param coord - Stone position
 * @param color - Stone color ('black' or 'white')
 * @param dimensions - Board dimensions
 */
export function drawGhostStone(
  ctx: CanvasRenderingContext2D,
  coord: Coordinate,
  color: 'black' | 'white',
  dimensions: BoardDimensions
): void {
  drawStone(ctx, coord, color, dimensions, GHOST_STONE_ALPHA);
}

/**
 * Draw all stones on the board
 * @param ctx - Canvas rendering context
 * @param boardSize - Size of the board
 * @param stones - 2D array of stones
 * @param dimensions - Board dimensions
 */
export function drawStones(
  ctx: CanvasRenderingContext2D,
  boardSize: BoardSize,
  stones: readonly (readonly Stone[])[],
  dimensions: BoardDimensions
): void {
  for (let y = 0; y < boardSize; y++) {
    for (let x = 0; x < boardSize; x++) {
      const stone = stones[y]?.[x];
      if (stone && stone !== EMPTY) {
        const color = stoneToColor(stone);
        if (color) {
          drawStone(ctx, { x, y }, color, dimensions);
        }
      }
    }
  }
}

/**
 * Draw a last move marker (square indicator)
 * @param ctx - Canvas rendering context
 * @param coord - Last move coordinate
 * @param stoneColor - Color of the stone at that position
 * @param dimensions - Board dimensions
 */
export function drawLastMoveMarker(
  ctx: CanvasRenderingContext2D,
  coord: Coordinate,
  stoneColor: 'black' | 'white',
  dimensions: BoardDimensions
): void {
  const { cellSize, offsetX, offsetY } = dimensions;
  const markerSize = cellSize * 0.25;
  const centerX = offsetX + coord.x * cellSize;
  const centerY = offsetY + coord.y * cellSize;

  // Draw contrasting square marker
  ctx.fillStyle = stoneColor === 'black' ? '#f8f8f8' : '#1a1a1a';
  ctx.fillRect(
    centerX - markerSize / 2,
    centerY - markerSize / 2,
    markerSize,
    markerSize
  );
}

/**
 * Draw a stone number (for review mode)
 * @param ctx - Canvas rendering context
 * @param coord - Stone position
 * @param number - Move number to display
 * @param stoneColor - Color of the stone
 * @param dimensions - Board dimensions
 */
export function drawStoneNumber(
  ctx: CanvasRenderingContext2D,
  coord: Coordinate,
  number: number,
  stoneColor: 'black' | 'white',
  dimensions: BoardDimensions
): void {
  const { cellSize, offsetX, offsetY } = dimensions;
  const centerX = offsetX + coord.x * cellSize;
  const centerY = offsetY + coord.y * cellSize;

  // Calculate font size based on number of digits
  const digits = String(number).length;
  const fontSize = Math.max(8, cellSize * (digits > 2 ? 0.3 : 0.4));

  ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif`;
  ctx.fillStyle = stoneColor === 'black' ? '#ffffff' : '#000000';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(String(number), centerX, centerY);
}

/**
 * Convert stone enum to rendering color
 * @param stone - Stone value
 * @returns 'black', 'white', or null if empty
 */
export function stoneToColor(stone: Stone): 'black' | 'white' | null {
  if (stone === BLACK) return 'black';
  if (stone === WHITE) return 'white';
  return null;
}
