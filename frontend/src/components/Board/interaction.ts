// @ts-nocheck
/**
 * Board interaction - click/tap stone placement handling
 * @module components/Board/interaction
 *
 * Covers: FR-005 (Single tap placement), FR-006 (Touch-friendly)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Interaction logic separate from rendering
 * - IX. Accessibility: Touch targets, keyboard support considerations
 */

import type { Coordinate, BoardSize, Stone, ReadonlyBoardState } from '../../types';

/**
 * Interaction mode for the board
 */
export type InteractionMode =
  | 'play' // Normal play mode - place stones
  | 'review' // Review mode - no placement
  | 'disabled'; // Board is disabled

/**
 * Result of a placement attempt
 */
export interface PlacementResult {
  /** Whether placement is allowed */
  allowed: boolean;
  /** Coordinate of placement */
  coord: Coordinate;
  /** Reason if not allowed */
  reason?: 'occupied' | 'out_of_bounds' | 'disabled' | 'review_mode';
}

/**
 * Configuration for interaction handling
 */
export interface InteractionConfig {
  /** Board size */
  boardSize: BoardSize;
  /** Current board state */
  stones: ReadonlyBoardState;
  /** Interaction mode */
  mode: InteractionMode;
  /** Minimum touch target size in pixels */
  minTouchTarget?: number;
}

/** Default minimum touch target size (per FR-006) */
const DEFAULT_MIN_TOUCH_TARGET = 44;

/**
 * Check if a coordinate is within board bounds
 */
export function isWithinBounds(coord: Coordinate, boardSize: BoardSize): boolean {
  return coord.x >= 0 && coord.x < boardSize && coord.y >= 0 && coord.y < boardSize;
}

/**
 * Check if an intersection is occupied
 * Updated for Besogo pattern: Stone is now -1/0/1, not 'black'/'white'/'empty'
 */
export function isOccupied(
  coord: Coordinate,
  stones: ReadonlyBoardState
): boolean {
  const stone = stones[coord.y]?.[coord.x];
  // Besogo pattern: EMPTY = 0 (falsy), BLACK = -1, WHITE = 1 (truthy)
  return stone !== undefined && !!stone;
}

/**
 * Get the stone at a coordinate (if any)
 */
export function getStoneAt(
  coord: Coordinate,
  stones: ReadonlyBoardState
): Stone | undefined {
  return stones[coord.y]?.[coord.x];
}

/**
 * Validate a placement attempt
 *
 * @param coord - Target coordinate
 * @param config - Interaction configuration
 * @returns Placement result with allowed status and reason
 */
export function validatePlacement(
  coord: Coordinate,
  config: InteractionConfig
): PlacementResult {
  const { boardSize, stones, mode } = config;

  // Check mode
  if (mode === 'disabled') {
    return { allowed: false, coord, reason: 'disabled' };
  }

  if (mode === 'review') {
    return { allowed: false, coord, reason: 'review_mode' };
  }

  // Check bounds
  if (!isWithinBounds(coord, boardSize)) {
    return { allowed: false, coord, reason: 'out_of_bounds' };
  }

  // Check occupation
  if (isOccupied(coord, stones)) {
    return { allowed: false, coord, reason: 'occupied' };
  }

  return { allowed: true, coord };
}

/**
 * Touch event data
 */
export interface TouchData {
  /** X coordinate of touch */
  clientX: number;
  /** Y coordinate of touch */
  clientY: number;
  /** Touch identifier */
  identifier?: number;
  /** Whether this is a touch device */
  isTouch: boolean;
}

/**
 * Extract touch data from a mouse or touch event
 */
export function extractTouchData(event: MouseEvent | TouchEvent): TouchData | null {
  if ('touches' in event) {
    // Touch event
    const touch = event.touches[0] || event.changedTouches[0];
    if (!touch) return null;
    return {
      clientX: touch.clientX,
      clientY: touch.clientY,
      identifier: touch.identifier,
      isTouch: true,
    };
  }
  // Mouse event
  return {
    clientX: event.clientX,
    clientY: event.clientY,
    isTouch: false,
  };
}

/**
 * Board dimensions for coordinate calculation
 */
export interface BoardDimensions {
  /** Size of each cell */
  cellSize: number;
  /** X offset from canvas edge to first intersection */
  offsetX: number;
  /** Y offset from canvas edge to first intersection */
  offsetY: number;
}

/**
 * Convert screen coordinates to board coordinates
 *
 * @param screenX - X position relative to canvas
 * @param screenY - Y position relative to canvas
 * @param dimensions - Board dimensions
 * @param boardSize - Board size
 * @returns Board coordinate or null if out of bounds
 */
export function screenToBoardCoord(
  screenX: number,
  screenY: number,
  dimensions: BoardDimensions,
  boardSize: BoardSize
): Coordinate | null {
  const { cellSize, offsetX, offsetY } = dimensions;

  const boardX = Math.round((screenX - offsetX) / cellSize);
  const boardY = Math.round((screenY - offsetY) / cellSize);

  if (boardX >= 0 && boardX < boardSize && boardY >= 0 && boardY < boardSize) {
    return { x: boardX, y: boardY };
  }

  return null;
}

/**
 * Convert board coordinates to screen coordinates
 *
 * @param coord - Board coordinate
 * @param dimensions - Board dimensions
 * @returns Screen position {x, y}
 */
export function boardToScreenCoord(
  coord: Coordinate,
  dimensions: BoardDimensions
): { x: number; y: number } {
  const { cellSize, offsetX, offsetY } = dimensions;
  return {
    x: offsetX + coord.x * cellSize,
    y: offsetY + coord.y * cellSize,
  };
}

/**
 * Calculate distance from touch point to nearest intersection
 *
 * @param screenX - Screen X position
 * @param screenY - Screen Y position
 * @param coord - Board coordinate
 * @param dimensions - Board dimensions
 * @returns Distance in pixels
 */
export function distanceToIntersection(
  screenX: number,
  screenY: number,
  coord: Coordinate,
  dimensions: BoardDimensions
): number {
  const intersection = boardToScreenCoord(coord, dimensions);
  const dx = screenX - intersection.x;
  const dy = screenY - intersection.y;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Check if a touch point is close enough to an intersection to register
 *
 * @param screenX - Screen X position
 * @param screenY - Screen Y position
 * @param dimensions - Board dimensions
 * @param boardSize - Board size
 * @param tolerance - Maximum distance to register (default: half cell size)
 * @returns Nearest coordinate if within tolerance, null otherwise
 */
export function findNearestIntersection(
  screenX: number,
  screenY: number,
  dimensions: BoardDimensions,
  boardSize: BoardSize,
  tolerance?: number
): Coordinate | null {
  const coord = screenToBoardCoord(screenX, screenY, dimensions, boardSize);
  if (!coord) return null;

  const maxDistance = tolerance ?? dimensions.cellSize / 2;
  const distance = distanceToIntersection(screenX, screenY, coord, dimensions);

  return distance <= maxDistance ? coord : null;
}

/**
 * Check if touch target size is sufficient
 *
 * @param cellSize - Current cell size
 * @param minTarget - Minimum touch target (default 44px per WCAG)
 * @returns true if touch targets are large enough
 */
export function isTouchTargetSufficient(
  cellSize: number,
  minTarget: number = DEFAULT_MIN_TOUCH_TARGET
): boolean {
  return cellSize >= minTarget;
}

/**
 * Calculate recommended board size for touch
 *
 * @param containerWidth - Container width
 * @param containerHeight - Container height
 * @param boardSize - Board size
 * @param minTouchTarget - Minimum touch target
 * @param padding - Board padding
 * @returns Recommended dimensions or null if insufficient space
 */
export function calculateTouchFriendlySize(
  containerWidth: number,
  containerHeight: number,
  boardSize: BoardSize,
  minTouchTarget: number = DEFAULT_MIN_TOUCH_TARGET,
  padding: number = 48
): { width: number; height: number; cellSize: number } | null {
  // Minimum size needed for touch-friendly cells
  const minBoardSize = (boardSize - 1) * minTouchTarget + padding * 2;

  const availableSize = Math.min(containerWidth, containerHeight);
  if (availableSize < minBoardSize) {
    // Container too small for proper touch targets
    // Return best effort dimensions
    const cellSize = (availableSize - padding * 2) / (boardSize - 1);
    return {
      width: availableSize,
      height: availableSize,
      cellSize,
    };
  }

  // Use available space
  const cellSize = (availableSize - padding * 2) / (boardSize - 1);
  return {
    width: availableSize,
    height: availableSize,
    cellSize,
  };
}

/**
 * Create a placement handler function
 *
 * @param config - Interaction configuration
 * @param onPlace - Callback when placement is valid
 * @param onInvalidPlace - Optional callback for invalid placement
 * @returns Handler function for placement events
 */
export function createPlacementHandler(
  config: InteractionConfig,
  onPlace: (coord: Coordinate) => void,
  onInvalidPlace?: (result: PlacementResult) => void
): (coord: Coordinate) => void {
  return (coord: Coordinate) => {
    const result = validatePlacement(coord, config);

    if (result.allowed) {
      onPlace(coord);
    } else if (onInvalidPlace) {
      onInvalidPlace(result);
    }
  };
}

/**
 * Lazy touch detection — Besogo pattern (spec 122 T1.F1)
 *
 * Besogo enables hover by default and only disables it when someone
 * actually touches the screen. This prevents false positives on
 * touchscreen laptops where users primarily use a mouse.
 *
 * The eager `isTouchDevice()` check was broken on Windows laptops
 * with touchscreens because `navigator.maxTouchPoints > 0` is true
 * even when the user is using a mouse.
 */
let _touchDetected = false;

// Register a one-time global touchstart listener
if (typeof window !== 'undefined') {
  window.addEventListener(
    'touchstart',
    () => {
      _touchDetected = true;
    },
    { once: true, passive: true }
  );
}

/**
 * Returns true only after a real touch event has been observed.
 * Unlike the old eager check, this won't return true just because
 * the device has touch capability — it waits for actual touch input.
 */
export function isTouchDevice(): boolean {
  return _touchDetected;
}

/**
 * Check if hover effects should be enabled.
 * Hover is enabled by default and only disabled after a real touch event.
 */
export function shouldEnableHover(): boolean {
  return !_touchDetected;
}
