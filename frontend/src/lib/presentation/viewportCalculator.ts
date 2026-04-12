/**
 * Viewport Calculator
 * @module lib/presentation/viewportCalculator
 *
 * Calculates the optimal viewport (bounding box) for auto-cropping
 * the board to show only the relevant problem area.
 *
 * Constitution Compliance:
 * - V. No Browser AI: Pure geometric calculation
 * - II. Deterministic Builds: Same input → same output
 */

import type { Coordinate, BoardViewport, ViewportOptions } from '@models/SolutionPresentation';

/** Internal normalized options */
interface NormalizedOptions {
  padding: number;
  snapToEdge: boolean;
  minSize: number;
}

/** Normalize viewport options with defaults */
function normalizeOptions(options: ViewportOptions): NormalizedOptions {
  return {
    padding: options.padding ?? options.margin ?? 2,
    snapToEdge:
      options.snapToEdge ??
      (options.edgeSnapDistance !== undefined ? options.edgeSnapDistance > 0 : true),
    minSize: options.minSize ?? 7,
  };
}

/**
 * Calculate the optimal viewport for a set of stones.
 * The viewport includes a margin around stones and snaps to edges
 * when close to the board boundary.
 *
 * @param stones - Array of stone coordinates
 * @param boardSize - Size of the board (9, 13, or 19)
 * @param options - Viewport calculation options
 * @returns BoardViewport with bounding box and metadata
 *
 * @example
 * ```ts
 * // Corner problem - will auto-crop
 * const viewport = calculateViewport(
 *   [{ x: 0, y: 0 }, { x: 2, y: 1 }, { x: 1, y: 2 }],
 *   19
 * );
 * // viewport.minX === 0, viewport.maxX ~= 4-5 (with margin)
 *
 * // Full board problem - no crop
 * const fullViewport = calculateViewport(stones, 19);
 * // fullViewport.isFullBoard === true
 * ```
 */
export function calculateViewport(
  stones: readonly Coordinate[],
  boardSize: number,
  options: ViewportOptions = {}
): BoardViewport {
  const opts = normalizeOptions(options);
  const edgeSnapDistance = opts.snapToEdge ? 3 : 0;

  // Empty board = full board
  if (stones.length === 0) {
    return createFullBoardViewport(boardSize);
  }

  // Find bounding box of stones
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  for (const stone of stones) {
    minX = Math.min(minX, stone.x);
    maxX = Math.max(maxX, stone.x);
    minY = Math.min(minY, stone.y);
    maxY = Math.max(maxY, stone.y);
  }

  // Add padding
  minX = Math.max(0, minX - opts.padding);
  maxX = Math.min(boardSize - 1, maxX + opts.padding);
  minY = Math.max(0, minY - opts.padding);
  maxY = Math.min(boardSize - 1, maxY + opts.padding);

  // Snap to edges if enabled and close
  if (opts.snapToEdge) {
    if (minX <= edgeSnapDistance) {
      minX = 0;
    }
    if (minY <= edgeSnapDistance) {
      minY = 0;
    }
    if (maxX >= boardSize - 1 - edgeSnapDistance) {
      maxX = boardSize - 1;
    }
    if (maxY >= boardSize - 1 - edgeSnapDistance) {
      maxY = boardSize - 1;
    }
  }

  // Enforce minimum size
  let width = maxX - minX + 1;
  let height = maxY - minY + 1;

  if (width < opts.minSize) {
    const expand = Math.floor((opts.minSize - width) / 2);
    minX = Math.max(0, minX - expand);
    maxX = Math.min(boardSize - 1, minX + opts.minSize - 1);
    if (maxX - minX + 1 < opts.minSize && minX > 0) {
      minX = Math.max(0, maxX - opts.minSize + 1);
    }
    width = maxX - minX + 1;
  }

  if (height < opts.minSize) {
    const expand = Math.floor((opts.minSize - height) / 2);
    minY = Math.max(0, minY - expand);
    maxY = Math.min(boardSize - 1, minY + opts.minSize - 1);
    if (maxY - minY + 1 < opts.minSize && minY > 0) {
      minY = Math.max(0, maxY - opts.minSize + 1);
    }
    height = maxY - minY + 1;
  }

  // Check if effectively full board (more than 80% coverage)
  const coverage = (width * height) / (boardSize * boardSize);
  const isFullBoard = coverage >= 0.8;

  // If full board, return exact full board viewport
  if (isFullBoard) {
    return createFullBoardViewport(boardSize);
  }

  return {
    minX,
    maxX,
    minY,
    maxY,
    width,
    height,
    isFullBoard: false,
  };
}

/**
 * Create a full board viewport.
 */
export function createFullBoardViewport(boardSize: number): BoardViewport {
  return {
    minX: 0,
    maxX: boardSize - 1,
    minY: 0,
    maxY: boardSize - 1,
    width: boardSize,
    height: boardSize,
    isFullBoard: true,
  };
}

/**
 * Expand viewport to include additional points (e.g., solution moves).
 *
 * @param viewport - Current viewport
 * @param points - Additional points to include
 * @param boardSize - Board size for bounds checking
 * @param margin - Margin to add around new points
 * @returns Expanded viewport
 */
export function expandViewport(
  viewport: BoardViewport,
  points: readonly Coordinate[],
  boardSize: number,
  margin: number = 1
): BoardViewport {
  if (viewport.isFullBoard || points.length === 0) {
    return viewport;
  }

  let { minX, maxX, minY, maxY } = viewport;

  for (const point of points) {
    const newMinX = Math.max(0, point.x - margin);
    const newMaxX = Math.min(boardSize - 1, point.x + margin);
    const newMinY = Math.max(0, point.y - margin);
    const newMaxY = Math.min(boardSize - 1, point.y + margin);

    minX = Math.min(minX, newMinX);
    maxX = Math.max(maxX, newMaxX);
    minY = Math.min(minY, newMinY);
    maxY = Math.max(maxY, newMaxY);
  }

  // Check if now full board
  const width = maxX - minX + 1;
  const height = maxY - minY + 1;
  const coverage = (width * height) / (boardSize * boardSize);

  if (coverage >= 0.8) {
    return createFullBoardViewport(boardSize);
  }

  return { minX, maxX, minY, maxY, width, height, isFullBoard: false };
}

/**
 * Calculate the grid size of a viewport.
 * This is the larger dimension (width or height) for scaling.
 *
 * @param viewport - Viewport to measure
 * @returns Number of grid lines in the larger dimension
 */
export function getViewportGridSize(viewport: BoardViewport): number {
  const width = viewport.maxX - viewport.minX + 1;
  const height = viewport.maxY - viewport.minY + 1;
  return Math.max(width, height);
}

/**
 * Check if a coordinate is within the viewport.
 *
 * @param coord - Coordinate to check
 * @param viewport - Viewport bounds
 * @returns True if coordinate is within viewport
 */
export function isInViewport(coord: Coordinate, viewport: BoardViewport): boolean {
  return (
    coord.x >= viewport.minX &&
    coord.x <= viewport.maxX &&
    coord.y >= viewport.minY &&
    coord.y <= viewport.maxY
  );
}

/**
 * Transform a coordinate from board space to viewport space.
 * Used for rendering within a cropped view.
 *
 * @param coord - Board coordinate
 * @param viewport - Current viewport
 * @returns Transformed coordinate relative to viewport origin
 */
export function transformToViewport(coord: Coordinate, viewport: BoardViewport): Coordinate {
  return {
    x: coord.x - viewport.minX,
    y: coord.y - viewport.minY,
  };
}

/**
 * Transform a coordinate from viewport space to board space.
 *
 * @param coord - Viewport-relative coordinate
 * @param viewport - Current viewport
 * @returns Board coordinate
 */
export function transformFromViewport(coord: Coordinate, viewport: BoardViewport): Coordinate {
  return {
    x: coord.x + viewport.minX,
    y: coord.y + viewport.minY,
  };
}
