/**
 * Board highlight rendering for hints.
 * Renders visual highlight regions on the board canvas.
 * @module components/Board/highlight
 */

import type { HighlightRegion } from '../../lib/hints/progressive';
import type { Point } from '../../lib/sgf/coordinates';

/**
 * Highlight rendering options.
 */
export interface HighlightOptions {
  /** Canvas context to render on */
  ctx: CanvasRenderingContext2D;
  /** Size of each cell in pixels */
  cellSize: number;
  /** Board padding in pixels */
  padding: number;
  /** Animation progress (0-1) */
  animationProgress?: number;
}

/**
 * Default highlight colors.
 */
const HIGHLIGHT_COLORS = {
  area: {
    fill: 'rgba(255, 193, 7, 0.3)',
    stroke: 'rgba(255, 152, 0, 0.8)',
  },
  point: {
    fill: 'rgba(76, 175, 80, 0.4)',
    stroke: 'rgba(56, 142, 60, 0.9)',
  },
};

/**
 * Convert board coordinates to canvas coordinates.
 */
function toCanvasCoords(point: Point, cellSize: number, padding: number): { x: number; y: number } {
  return {
    x: padding + point.x * cellSize,
    y: padding + point.y * cellSize,
  };
}

/**
 * Render an area highlight (circular region).
 */
function renderAreaHighlight(
  ctx: CanvasRenderingContext2D,
  region: HighlightRegion,
  options: HighlightOptions
): void {
  const { cellSize, padding, animationProgress = 1 } = options;
  const center = toCanvasCoords(region.center, cellSize, padding);
  const radius = region.radius * cellSize;

  // Animate the radius with a pulse effect
  const pulseScale = 1 + Math.sin(animationProgress * Math.PI * 2) * 0.1;
  const animatedRadius = radius * pulseScale;

  ctx.save();
  ctx.globalAlpha = 0.8;

  // Fill
  ctx.beginPath();
  ctx.arc(center.x, center.y, animatedRadius, 0, Math.PI * 2);
  ctx.fillStyle = HIGHLIGHT_COLORS.area.fill;
  ctx.fill();

  // Stroke
  ctx.strokeStyle = HIGHLIGHT_COLORS.area.stroke;
  ctx.lineWidth = 2;
  ctx.setLineDash([5, 5]);
  ctx.stroke();

  ctx.restore();
}

/**
 * Render a point highlight (single intersection).
 */
function renderPointHighlight(
  ctx: CanvasRenderingContext2D,
  region: HighlightRegion,
  options: HighlightOptions
): void {
  const { cellSize, padding, animationProgress = 1 } = options;
  const center = toCanvasCoords(region.center, cellSize, padding);
  const radius = cellSize * 0.4;

  // Pulse animation
  const pulseScale = 1 + Math.sin(animationProgress * Math.PI * 4) * 0.2;
  const animatedRadius = radius * pulseScale;

  ctx.save();

  // Outer glow
  ctx.beginPath();
  ctx.arc(center.x, center.y, animatedRadius * 1.5, 0, Math.PI * 2);
  ctx.fillStyle = HIGHLIGHT_COLORS.point.fill;
  ctx.fill();

  // Inner circle
  ctx.beginPath();
  ctx.arc(center.x, center.y, animatedRadius, 0, Math.PI * 2);
  ctx.fillStyle = HIGHLIGHT_COLORS.point.stroke;
  ctx.globalAlpha = 0.7;
  ctx.fill();

  // Center marker
  ctx.beginPath();
  ctx.arc(center.x, center.y, animatedRadius * 0.3, 0, Math.PI * 2);
  ctx.fillStyle = '#fff';
  ctx.globalAlpha = 1;
  ctx.fill();

  ctx.restore();
}

/**
 * Render a highlight region on the board.
 */
export function renderHighlight(
  region: HighlightRegion,
  options: HighlightOptions
): void {
  const { ctx } = options;

  ctx.save();

  switch (region.type) {
    case 'area':
      renderAreaHighlight(ctx, region, options);
      break;
    case 'point':
      renderPointHighlight(ctx, region, options);
      break;
    default:
      // Default to area highlight
      renderAreaHighlight(ctx, region, options);
  }

  ctx.restore();
}

/**
 * Clear highlight from canvas (by redrawing the board).
 * Note: This should be called before re-rendering the board.
 */
export function clearHighlight(_ctx: CanvasRenderingContext2D): void {
  // Highlights are rendered on top, so clearing requires a full board redraw
  // This is just a placeholder - actual clearing happens in the board render cycle
}

/**
 * Create a highlight animation frame renderer.
 * Returns a function that can be called with animation progress (0-1).
 */
export function createHighlightAnimator(
  region: HighlightRegion,
  options: Omit<HighlightOptions, 'animationProgress'>
): (progress: number) => void {
  return (progress: number) => {
    renderHighlight(region, { ...options, animationProgress: progress });
  };
}
