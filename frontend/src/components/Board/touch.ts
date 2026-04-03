/**
 * Touch event handlers for the Go board.
 * Handles touch-based stone placement with accuracy improvements.
 * @module components/Board/touch
 */

import type { Coordinate } from '../../types/puzzle';

/**
 * Touch event state.
 */
export interface TouchState {
  /** Whether touch is active */
  readonly isActive: boolean;
  /** Start position */
  readonly startX: number;
  readonly startY: number;
  /** Current position */
  readonly currentX: number;
  readonly currentY: number;
  /** Touch identifier */
  readonly touchId: number | null;
  /** Time when touch started */
  readonly startTime: number;
}

/**
 * Create initial touch state.
 */
export function createTouchState(): TouchState {
  return {
    isActive: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    touchId: null,
    startTime: 0,
  };
}

/**
 * Touch configuration.
 */
export interface TouchConfig {
  /** Minimum tap duration in ms (to distinguish from scroll) */
  readonly minTapDuration: number;
  /** Maximum tap duration in ms (longer = long press) */
  readonly maxTapDuration: number;
  /** Maximum movement in pixels for a tap */
  readonly maxTapMovement: number;
  /** Long press threshold in ms */
  readonly longPressThreshold: number;
  /** Enable haptic feedback */
  readonly hapticFeedback: boolean;
}

/**
 * Default touch configuration.
 */
export const DEFAULT_TOUCH_CONFIG: TouchConfig = {
  minTapDuration: 50,
  maxTapDuration: 500,
  maxTapMovement: 10,
  longPressThreshold: 500,
  hapticFeedback: true,
};

/**
 * Touch result type.
 */
export type TouchResultType = 'tap' | 'longPress' | 'drag' | 'cancel';

/**
 * Touch result.
 */
export interface TouchResult {
  /** Type of touch action */
  readonly type: TouchResultType;
  /** Board coordinate (if applicable) */
  readonly coordinate: Coordinate | null;
  /** Client position */
  readonly clientX: number;
  readonly clientY: number;
}

/**
 * Convert client coordinates to board coordinate.
 *
 * @param clientX - Client X position
 * @param clientY - Client Y position
 * @param canvasRect - Canvas bounding rect
 * @param boardSize - Number of lines (9, 13, 19)
 * @param cellSize - Cell size in pixels
 * @param coordMargin - Margin for coordinates
 * @returns Board coordinate or null if outside board
 */
export function clientToBoardCoordinate(
  clientX: number,
  clientY: number,
  canvasRect: DOMRect,
  boardSize: number,
  cellSize: number,
  coordMargin: number = 24
): Coordinate | null {
  // Calculate position relative to canvas
  const relX = clientX - canvasRect.left;
  const relY = clientY - canvasRect.top;

  // Account for coordinate margin
  const boardX = relX - coordMargin;
  const boardY = relY - coordMargin;

  // Calculate grid position (round to nearest intersection)
  const col = Math.round(boardX / cellSize);
  const row = Math.round(boardY / cellSize);

  // Check bounds
  if (col < 0 || col >= boardSize || row < 0 || row >= boardSize) {
    return null;
  }

  return { row, col };
}

/**
 * Calculate distance between two points.
 */
function distance(x1: number, y1: number, x2: number, y2: number): number {
  const dx = x2 - x1;
  const dy = y2 - y1;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Touch event handler class.
 */
export class TouchHandler {
  private state: TouchState;
  private config: TouchConfig;
  private longPressTimer: number | null = null;
  private onTap: ((coord: Coordinate) => void) | null = null;
  private onLongPress: ((coord: Coordinate) => void) | null = null;

  constructor(config: Partial<TouchConfig> = {}) {
    this.config = { ...DEFAULT_TOUCH_CONFIG, ...config };
    this.state = createTouchState();
  }

  /**
   * Set tap handler.
   */
  setTapHandler(handler: (coord: Coordinate) => void): void {
    this.onTap = handler;
  }

  /**
   * Set long press handler.
   */
  setLongPressHandler(handler: (coord: Coordinate) => void): void {
    this.onLongPress = handler;
  }

  /**
   * Handle touch start event.
   */
  handleTouchStart(
    event: TouchEvent,
    canvasRect: DOMRect,
    boardSize: number,
    cellSize: number
  ): void {
    if (event.touches.length !== 1) {
      return; // Only handle single touch
    }

    const touch = event.touches[0];
    if (!touch) return;

    // Prevent default to avoid scrolling
    event.preventDefault();

    this.state = {
      isActive: true,
      startX: touch.clientX,
      startY: touch.clientY,
      currentX: touch.clientX,
      currentY: touch.clientY,
      touchId: touch.identifier,
      startTime: Date.now(),
    };

    // Set up long press timer
    this.cancelLongPress();
    this.longPressTimer = window.setTimeout(() => {
      if (this.state.isActive) {
        const coord = clientToBoardCoordinate(
          this.state.currentX,
          this.state.currentY,
          canvasRect,
          boardSize,
          cellSize
        );
        if (coord && this.onLongPress) {
          this.triggerHaptic();
          this.onLongPress(coord);
        }
      }
    }, this.config.longPressThreshold);
  }

  /**
   * Handle touch move event.
   */
  handleTouchMove(event: TouchEvent): void {
    if (!this.state.isActive) return;

    const touch = Array.from(event.touches).find(
      (t) => t.identifier === this.state.touchId
    );
    if (!touch) return;

    this.state = {
      ...this.state,
      currentX: touch.clientX,
      currentY: touch.clientY,
    };

    // Cancel long press if moved too far
    const moved = distance(
      this.state.startX,
      this.state.startY,
      this.state.currentX,
      this.state.currentY
    );
    if (moved > this.config.maxTapMovement) {
      this.cancelLongPress();
    }
  }

  /**
   * Handle touch end event.
   */
  handleTouchEnd(
    _event: TouchEvent,
    canvasRect: DOMRect,
    boardSize: number,
    cellSize: number
  ): TouchResult | null {
    if (!this.state.isActive) return null;

    this.cancelLongPress();

    const duration = Date.now() - this.state.startTime;
    const moved = distance(
      this.state.startX,
      this.state.startY,
      this.state.currentX,
      this.state.currentY
    );

    // Reset state
    const finalX = this.state.currentX;
    const finalY = this.state.currentY;
    this.state = createTouchState();

    // Determine touch result
    const coord = clientToBoardCoordinate(
      finalX,
      finalY,
      canvasRect,
      boardSize,
      cellSize
    );

    // Check for valid tap
    if (
      duration >= this.config.minTapDuration &&
      duration <= this.config.maxTapDuration &&
      moved <= this.config.maxTapMovement
    ) {
      if (coord && this.onTap) {
        this.triggerHaptic();
        this.onTap(coord);
      }
      return {
        type: 'tap',
        coordinate: coord,
        clientX: finalX,
        clientY: finalY,
      };
    }

    // Check for drag
    if (moved > this.config.maxTapMovement) {
      return {
        type: 'drag',
        coordinate: coord,
        clientX: finalX,
        clientY: finalY,
      };
    }

    return {
      type: 'cancel',
      coordinate: null,
      clientX: finalX,
      clientY: finalY,
    };
  }

  /**
   * Handle touch cancel event.
   */
  handleTouchCancel(): void {
    this.cancelLongPress();
    this.state = createTouchState();
  }

  /**
   * Cancel long press timer.
   */
  private cancelLongPress(): void {
    if (this.longPressTimer !== null) {
      clearTimeout(this.longPressTimer);
      this.longPressTimer = null;
    }
  }

  /**
   * Trigger haptic feedback if supported and enabled.
   */
  private triggerHaptic(): void {
    if (this.config.hapticFeedback && 'vibrate' in navigator) {
      navigator.vibrate(10);
    }
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    this.cancelLongPress();
    this.onTap = null;
    this.onLongPress = null;
  }
}

/**
 * Create a touch handler.
 */
export function createTouchHandler(config?: Partial<TouchConfig>): TouchHandler {
  return new TouchHandler(config);
}

/**
 * Check if device supports touch — delegates to interaction.ts lazy detection.
 * @deprecated Use isTouchDevice from interaction.ts instead
 */
export function isTouchDevice(): boolean {
  // Use lazy detection from interaction.ts via re-import would create circular dep.
  // Keep this as a simple check for internal use only.
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

/**
 * Check if device is primarily touch (no mouse).
 */
export function isPrimaryTouchDevice(): boolean {
  return isTouchDevice() && !matchMedia('(pointer: fine)').matches;
}
