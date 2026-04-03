/**
 * Grid rendering utilities for Go board
 * @module components/Board/grid
 *
 * Covers: FR-001 (Display board), FR-003 (Grid display)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Grid rendering only
 * - VI. Pure TypeScript: Canvas API
 */

import type { BoardSize } from '@models/puzzle';

/** Grid rendering constants */
const GRID_LINE_WIDTH = 1;

/** Board colors for grid */
const GRID_COLORS = {
  line: '#8B7355', // Softer brown grid lines
  board: '#E8C882', // Warmer golden wood color
  coordLabel: '#6B5B45', // Muted brown for coordinates
  shadow: 'rgba(0, 0, 0, 0.03)',
} as const;

/** Column labels (skip 'I' as is traditional in Go) */
const COLUMN_LABELS = 'ABCDEFGHJKLMNOPQRST';

/**
 * Board dimensions calculated from container
 */
export interface BoardDimensions {
  cellSize: number;
  offsetX: number;
  offsetY: number;
}

/**
 * Draw the board background
 * @param ctx - Canvas rendering context
 * @param width - Canvas width
 * @param height - Canvas height
 */
export function drawBoardBackground(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): void {
  // Background with subtle shadow effect
  ctx.fillStyle = GRID_COLORS.board;
  ctx.fillRect(0, 0, width, height);

  // Add subtle inner shadow for depth
  const shadowGradient = ctx.createLinearGradient(0, 0, 0, height);
  shadowGradient.addColorStop(0, GRID_COLORS.shadow);
  shadowGradient.addColorStop(0.5, 'rgba(0, 0, 0, 0)');
  shadowGradient.addColorStop(1, 'rgba(0, 0, 0, 0.05)');
  ctx.fillStyle = shadowGradient;
  ctx.fillRect(0, 0, width, height);
}

/**
 * Draw grid lines on the board
 * @param ctx - Canvas rendering context
 * @param boardSize - Size of the board (9, 13, or 19)
 * @param dimensions - Board dimensions (cellSize, offsetX, offsetY)
 */
export function drawGridLines(
  ctx: CanvasRenderingContext2D,
  boardSize: BoardSize,
  dimensions: BoardDimensions
): void {
  const { cellSize, offsetX, offsetY } = dimensions;

  ctx.strokeStyle = GRID_COLORS.line;
  ctx.lineWidth = GRID_LINE_WIDTH;

  for (let i = 0; i < boardSize; i++) {
    // Vertical lines
    ctx.beginPath();
    ctx.moveTo(offsetX + i * cellSize, offsetY);
    ctx.lineTo(offsetX + i * cellSize, offsetY + (boardSize - 1) * cellSize);
    ctx.stroke();

    // Horizontal lines
    ctx.beginPath();
    ctx.moveTo(offsetX, offsetY + i * cellSize);
    ctx.lineTo(offsetX + (boardSize - 1) * cellSize, offsetY + i * cellSize);
    ctx.stroke();
  }
}

/**
 * Draw coordinate labels around the board
 * @param ctx - Canvas rendering context
 * @param boardSize - Size of the board (9, 13, or 19)
 * @param dimensions - Board dimensions (cellSize, offsetX, offsetY)
 */
export function drawCoordinateLabels(
  ctx: CanvasRenderingContext2D,
  boardSize: BoardSize,
  dimensions: BoardDimensions
): void {
  const { cellSize, offsetX, offsetY } = dimensions;

  const fontSize = Math.max(10, cellSize * 0.35);
  ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif`;
  ctx.fillStyle = GRID_COLORS.coordLabel;
  ctx.textBaseline = 'middle';

  for (let i = 0; i < boardSize; i++) {
    // Column labels (A-T, skipping I) at top and bottom
    const colLabel = COLUMN_LABELS[i] || String.fromCharCode(65 + i);
    const colX = offsetX + i * cellSize;

    // Top label
    ctx.textAlign = 'center';
    ctx.fillText(colLabel, colX, offsetY - cellSize * 0.55);
    // Bottom label
    ctx.fillText(colLabel, colX, offsetY + (boardSize - 1) * cellSize + cellSize * 0.55);

    // Row labels (1-19, with 1 at bottom like traditional Go boards)
    const rowLabel = String(boardSize - i);
    const rowY = offsetY + i * cellSize;

    // Left label
    ctx.textAlign = 'right';
    ctx.fillText(rowLabel, offsetX - cellSize * 0.4, rowY);
    // Right label
    ctx.textAlign = 'left';
    ctx.fillText(rowLabel, offsetX + (boardSize - 1) * cellSize + cellSize * 0.4, rowY);
  }
}

/**
 * Draw complete grid (background + lines + labels)
 * @param ctx - Canvas rendering context
 * @param width - Canvas width
 * @param height - Canvas height
 * @param boardSize - Size of the board (9, 13, or 19)
 * @param dimensions - Board dimensions (cellSize, offsetX, offsetY)
 */
export function drawGrid(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  boardSize: BoardSize,
  dimensions: BoardDimensions
): void {
  drawBoardBackground(ctx, width, height);
  drawGridLines(ctx, boardSize, dimensions);
  drawCoordinateLabels(ctx, boardSize, dimensions);
}
