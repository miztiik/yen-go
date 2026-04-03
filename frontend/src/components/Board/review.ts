/**
 * Board review rendering for solution playback.
 * Renders move markers and animations for review mode.
 * @module components/Board/review
 */

import type { ReviewMove, ReviewState } from '../../lib/review/controller';
import type { Point } from '../../lib/sgf/coordinates';

/**
 * Review rendering options.
 */
export interface ReviewRenderOptions {
  /** Canvas context */
  ctx: CanvasRenderingContext2D;
  /** Cell size in pixels */
  cellSize: number;
  /** Board padding in pixels */
  padding: number;
  /** Whether to show move numbers */
  showMoveNumbers?: boolean;
  /** Whether to highlight the last move */
  highlightLast?: boolean;
  /** Animation progress for transitions (0-1) */
  animationProgress?: number;
}

/**
 * Colors for review rendering.
 */
const REVIEW_COLORS = {
  lastMove: {
    black: 'rgba(255, 87, 34, 0.8)', // Orange highlight on black
    white: 'rgba(33, 150, 243, 0.8)', // Blue highlight on white
  },
  moveNumber: {
    onBlack: '#fff',
    onWhite: '#000',
  },
  marker: {
    circle: 'rgba(255, 152, 0, 0.9)',
  },
};

/**
 * Convert board point to canvas coordinates.
 */
function toCanvasCoords(
  point: Point,
  cellSize: number,
  padding: number
): { x: number; y: number } {
  return {
    x: padding + point.x * cellSize,
    y: padding + point.y * cellSize,
  };
}

/**
 * Render a move number on a stone.
 */
function renderMoveNumber(
  ctx: CanvasRenderingContext2D,
  point: Point,
  moveNumber: number,
  stoneColor: 'B' | 'W',
  cellSize: number,
  padding: number
): void {
  const coords = toCanvasCoords(point, cellSize, padding);
  const textColor =
    stoneColor === 'B' ? REVIEW_COLORS.moveNumber.onBlack : REVIEW_COLORS.moveNumber.onWhite;

  ctx.save();
  ctx.font = `bold ${cellSize * 0.4}px sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = textColor;
  ctx.fillText(String(moveNumber), coords.x, coords.y);
  ctx.restore();
}

/**
 * Render a last-move marker (triangle or circle).
 */
function renderLastMoveMarker(
  ctx: CanvasRenderingContext2D,
  point: Point,
  stoneColor: 'B' | 'W',
  cellSize: number,
  padding: number,
  animationProgress = 1
): void {
  const coords = toCanvasCoords(point, cellSize, padding);
  const markerColor =
    stoneColor === 'B' ? REVIEW_COLORS.lastMove.black : REVIEW_COLORS.lastMove.white;
  const radius = cellSize * 0.2;

  // Pulse animation
  const pulseScale = 1 + Math.sin(animationProgress * Math.PI * 2) * 0.15;

  ctx.save();
  ctx.beginPath();
  ctx.arc(coords.x, coords.y, radius * pulseScale, 0, Math.PI * 2);
  ctx.fillStyle = markerColor;
  ctx.fill();
  ctx.restore();
}

/**
 * Render a single review move marker.
 */
export function renderReviewMove(
  move: ReviewMove,
  isLast: boolean,
  options: ReviewRenderOptions
): void {
  const { ctx, cellSize, padding, showMoveNumbers = true, highlightLast = true, animationProgress = 1 } = options;

  // Render last move marker
  if (isLast && highlightLast) {
    renderLastMoveMarker(ctx, move.point, move.color, cellSize, padding, animationProgress);
  }

  // Render move number
  if (showMoveNumbers) {
    renderMoveNumber(ctx, move.point, move.index + 1, move.color, cellSize, padding);
  }
}

/**
 * Render all moves up to the current position.
 */
export function renderReviewState(
  state: ReviewState,
  options: ReviewRenderOptions
): void {
  const { playedMoves } = state;

  // Render all moves with numbers
  playedMoves.forEach((move, idx) => {
    const isLast = idx === playedMoves.length - 1;
    renderReviewMove(move, isLast, options);
  });
}

/**
 * Animation state for smooth transitions.
 */
export interface ReviewAnimation {
  /** Start time of the animation */
  startTime: number;
  /** Duration in milliseconds */
  duration: number;
  /** The move being animated */
  move: ReviewMove;
  /** Callback when animation completes */
  onComplete?: () => void;
}

/**
 * Create a move animation.
 */
export function createMoveAnimation(
  move: ReviewMove,
  duration = 300,
  onComplete?: () => void
): ReviewAnimation {
  return {
    startTime: performance.now(),
    duration,
    move,
    ...(onComplete !== undefined && { onComplete }),
  };
}

/**
 * Get animation progress (0-1).
 */
export function getAnimationProgress(animation: ReviewAnimation): number {
  const elapsed = performance.now() - animation.startTime;
  const progress = Math.min(elapsed / animation.duration, 1);
  return progress;
}

/**
 * Check if animation is complete.
 */
export function isAnimationComplete(animation: ReviewAnimation): boolean {
  return getAnimationProgress(animation) >= 1;
}

/**
 * Stone placement animation (fade in + scale).
 */
export function renderStonePlacement(
  ctx: CanvasRenderingContext2D,
  point: Point,
  color: 'B' | 'W',
  cellSize: number,
  padding: number,
  progress: number
): void {
  const coords = toCanvasCoords(point, cellSize, padding);
  const radius = (cellSize / 2 - 1) * easeOutBack(progress);
  const alpha = progress;

  ctx.save();
  ctx.globalAlpha = alpha;

  // Stone gradient
  const gradient = ctx.createRadialGradient(
    coords.x - radius * 0.3,
    coords.y - radius * 0.3,
    0,
    coords.x,
    coords.y,
    radius
  );

  if (color === 'B') {
    gradient.addColorStop(0, '#555');
    gradient.addColorStop(1, '#000');
  } else {
    gradient.addColorStop(0, '#fff');
    gradient.addColorStop(1, '#ccc');
  }

  ctx.beginPath();
  ctx.arc(coords.x, coords.y, radius, 0, Math.PI * 2);
  ctx.fillStyle = gradient;
  ctx.fill();

  // Shadow for white stones
  if (color === 'W') {
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  ctx.restore();
}

/**
 * Easing function for bounce effect.
 */
function easeOutBack(x: number): number {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
}
