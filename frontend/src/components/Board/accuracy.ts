/**
 * Touch accuracy improvements for the Go board.
 * Implements snap-to-intersection and visual feedback.
 * @module components/Board/accuracy
 */

import type { Coordinate } from '../../types/puzzle';

/**
 * Touch accuracy configuration.
 */
export interface AccuracyConfig {
  /** Snap radius as fraction of cell size (0-0.5) */
  readonly snapRadius: number;
  /** Show preview stone before placement */
  readonly showPreview: boolean;
  /** Minimum confidence for snap (0-1) */
  readonly minConfidence: number;
  /** Enable magnifier for precise placement */
  readonly enableMagnifier: boolean;
  /** Magnifier scale factor */
  readonly magnifierScale: number;
}

/**
 * Default accuracy configuration.
 */
export const DEFAULT_ACCURACY_CONFIG: AccuracyConfig = {
  snapRadius: 0.4,
  showPreview: true,
  minConfidence: 0.6,
  enableMagnifier: false,
  magnifierScale: 2.0,
};

/**
 * Snap result.
 */
export interface SnapResult {
  /** Snapped coordinate */
  readonly coordinate: Coordinate;
  /** Distance from touch point to intersection (0-1, normalized) */
  readonly distance: number;
  /** Confidence level (0-1, higher = more certain) */
  readonly confidence: number;
  /** Whether snap was successful */
  readonly snapped: boolean;
}

/**
 * Preview stone state.
 */
export interface PreviewState {
  /** Whether preview is visible */
  readonly visible: boolean;
  /** Preview coordinate */
  readonly coordinate: Coordinate | null;
  /** Preview color */
  readonly color: 'black' | 'white';
  /** Preview opacity (0-1) */
  readonly opacity: number;
}

/**
 * Create initial preview state.
 */
export function createPreviewState(): PreviewState {
  return {
    visible: false,
    coordinate: null,
    color: 'black',
    opacity: 0.5,
  };
}

/**
 * Calculate snap-to-intersection.
 *
 * @param touchX - Touch X position relative to board
 * @param touchY - Touch Y position relative to board
 * @param cellSize - Cell size in pixels
 * @param boardSize - Number of lines (9, 13, 19)
 * @param config - Accuracy configuration
 * @returns Snap result
 */
export function snapToIntersection(
  touchX: number,
  touchY: number,
  cellSize: number,
  boardSize: number,
  config: AccuracyConfig = DEFAULT_ACCURACY_CONFIG
): SnapResult {
  // Calculate nearest intersection
  const col = Math.round(touchX / cellSize);
  const row = Math.round(touchY / cellSize);

  // Clamp to board bounds
  const clampedCol = Math.max(0, Math.min(boardSize - 1, col));
  const clampedRow = Math.max(0, Math.min(boardSize - 1, row));

  // Calculate intersection center
  const intersectionX = clampedCol * cellSize;
  const intersectionY = clampedRow * cellSize;

  // Calculate distance from touch to intersection
  const dx = touchX - intersectionX;
  const dy = touchY - intersectionY;
  const pixelDistance = Math.sqrt(dx * dx + dy * dy);

  // Normalize distance to cell size
  const normalizedDistance = pixelDistance / cellSize;

  // Calculate confidence (inverse of distance, clamped)
  const confidence = Math.max(0, Math.min(1, 1 - normalizedDistance / config.snapRadius));

  // Determine if snap is successful
  const snapped =
    normalizedDistance <= config.snapRadius * cellSize / cellSize &&
    confidence >= config.minConfidence;

  return {
    coordinate: { row: clampedRow, col: clampedCol },
    distance: normalizedDistance,
    confidence,
    snapped,
  };
}

/**
 * Find nearest valid intersection for a touch point.
 *
 * @param touchX - Touch X position (client coordinates)
 * @param touchY - Touch Y position (client coordinates)
 * @param canvasRect - Canvas bounding rectangle
 * @param cellSize - Cell size in pixels
 * @param boardSize - Board size (9, 13, 19)
 * @param coordMargin - Margin for coordinate labels
 * @param occupiedPositions - Set of occupied positions as "row,col" strings
 * @returns Nearest valid coordinate or null
 */
export function findNearestValidIntersection(
  touchX: number,
  touchY: number,
  canvasRect: DOMRect,
  cellSize: number,
  boardSize: number,
  coordMargin: number = 24,
  occupiedPositions: Set<string> = new Set()
): Coordinate | null {
  // Convert to board-relative coordinates
  const boardX = touchX - canvasRect.left - coordMargin;
  const boardY = touchY - canvasRect.top - coordMargin;

  // Get initial snap
  const snap = snapToIntersection(boardX, boardY, cellSize, boardSize);

  // Check if position is valid (not occupied)
  const posKey = `${snap.coordinate.row},${snap.coordinate.col}`;
  if (!occupiedPositions.has(posKey) && snap.snapped) {
    return snap.coordinate;
  }

  // If snapped position is occupied, search nearby
  if (snap.snapped && occupiedPositions.has(posKey)) {
    const { row, col } = snap.coordinate;
    const neighbors: Coordinate[] = [
      { row: row - 1, col },
      { row: row + 1, col },
      { row, col: col - 1 },
      { row, col: col + 1 },
    ];

    // Filter valid neighbors
    const validNeighbors = neighbors.filter((n) => {
      if (n.row < 0 || n.row >= boardSize || n.col < 0 || n.col >= boardSize) {
        return false;
      }
      const key = `${n.row},${n.col}`;
      return !occupiedPositions.has(key);
    });

    // Find nearest valid neighbor
    if (validNeighbors.length > 0) {
      let nearest = validNeighbors[0];
      if (validNeighbors.length > 1) {
        let minDist = Infinity;
        for (const n of validNeighbors) {
          const nx = n.col * cellSize;
          const ny = n.row * cellSize;
          const dist = Math.sqrt((boardX - nx) ** 2 + (boardY - ny) ** 2);
          if (dist < minDist) {
            minDist = dist;
            nearest = n;
          }
        }
      }
      return nearest!;
    }
  }

  return snap.snapped ? snap.coordinate : null;
}

/**
 * Magnifier state.
 */
export interface MagnifierState {
  /** Whether magnifier is visible */
  readonly visible: boolean;
  /** Center position X */
  readonly centerX: number;
  /** Center position Y */
  readonly centerY: number;
  /** Radius */
  readonly radius: number;
  /** Scale factor */
  readonly scale: number;
}

/**
 * Create magnifier state.
 */
export function createMagnifierState(
  visible: boolean = false,
  x: number = 0,
  y: number = 0,
  config: AccuracyConfig = DEFAULT_ACCURACY_CONFIG
): MagnifierState {
  return {
    visible,
    centerX: x,
    centerY: y,
    radius: 60,
    scale: config.magnifierScale,
  };
}

/**
 * Calculate magnifier position to avoid finger obstruction.
 *
 * @param touchX - Touch X position
 * @param touchY - Touch Y position
 * @param canvasWidth - Canvas width
 * @param canvasHeight - Canvas height
 * @param magnifierRadius - Magnifier radius
 * @returns Offset position for magnifier
 */
export function calculateMagnifierPosition(
  touchX: number,
  touchY: number,
  canvasWidth: number,
  canvasHeight: number,
  magnifierRadius: number = 60
): { x: number; y: number } {
  // Position magnifier above and to the side of touch point
  const offsetY = -magnifierRadius * 2 - 20;
  let offsetX = 0;

  // Adjust horizontal position to stay in bounds
  if (touchX < magnifierRadius * 2) {
    offsetX = magnifierRadius;
  } else if (touchX > canvasWidth - magnifierRadius * 2) {
    offsetX = -magnifierRadius;
  }

  // Calculate final position
  let x = touchX + offsetX;
  let y = touchY + offsetY;

  // Keep magnifier in bounds
  x = Math.max(magnifierRadius, Math.min(canvasWidth - magnifierRadius, x));
  y = Math.max(magnifierRadius, Math.min(canvasHeight - magnifierRadius, y));

  return { x, y };
}

/**
 * Touch accuracy manager.
 */
export class TouchAccuracyManager {
  private config: AccuracyConfig;
  private previewState: PreviewState;
  private magnifierState: MagnifierState;

  constructor(config: Partial<AccuracyConfig> = {}) {
    this.config = { ...DEFAULT_ACCURACY_CONFIG, ...config };
    this.previewState = createPreviewState();
    this.magnifierState = createMagnifierState();
  }

  /**
   * Get preview state.
   */
  getPreviewState(): PreviewState {
    return this.previewState;
  }

  /**
   * Get magnifier state.
   */
  getMagnifierState(): MagnifierState {
    return this.magnifierState;
  }

  /**
   * Update preview based on touch position.
   */
  updatePreview(
    touchX: number,
    touchY: number,
    canvasRect: DOMRect,
    cellSize: number,
    boardSize: number,
    coordMargin: number,
    color: 'black' | 'white',
    occupiedPositions: Set<string> = new Set()
  ): void {
    if (!this.config.showPreview) {
      this.previewState = createPreviewState();
      return;
    }

    const coordinate = findNearestValidIntersection(
      touchX,
      touchY,
      canvasRect,
      cellSize,
      boardSize,
      coordMargin,
      occupiedPositions
    );

    if (coordinate) {
      // Calculate confidence for opacity
      const boardX = touchX - canvasRect.left - coordMargin;
      const boardY = touchY - canvasRect.top - coordMargin;
      const snap = snapToIntersection(boardX, boardY, cellSize, boardSize, this.config);

      this.previewState = {
        visible: true,
        coordinate,
        color,
        opacity: 0.3 + snap.confidence * 0.4,
      };
    } else {
      this.previewState = createPreviewState();
    }
  }

  /**
   * Update magnifier.
   */
  updateMagnifier(
    visible: boolean,
    touchX: number = 0,
    touchY: number = 0,
    canvasWidth: number = 0,
    canvasHeight: number = 0
  ): void {
    if (!this.config.enableMagnifier || !visible) {
      this.magnifierState = { ...this.magnifierState, visible: false };
      return;
    }

    const position = calculateMagnifierPosition(
      touchX,
      touchY,
      canvasWidth,
      canvasHeight
    );

    this.magnifierState = {
      visible: true,
      centerX: position.x,
      centerY: position.y,
      radius: 60,
      scale: this.config.magnifierScale,
    };
  }

  /**
   * Clear preview and magnifier.
   */
  clear(): void {
    this.previewState = createPreviewState();
    this.magnifierState = createMagnifierState();
  }

  /**
   * Process touch and get final coordinate.
   */
  processTouch(
    touchX: number,
    touchY: number,
    canvasRect: DOMRect,
    cellSize: number,
    boardSize: number,
    coordMargin: number,
    occupiedPositions: Set<string> = new Set()
  ): Coordinate | null {
    return findNearestValidIntersection(
      touchX,
      touchY,
      canvasRect,
      cellSize,
      boardSize,
      coordMargin,
      occupiedPositions
    );
  }
}

/**
 * Create touch accuracy manager.
 */
export function createTouchAccuracyManager(
  config?: Partial<AccuracyConfig>
): TouchAccuracyManager {
  return new TouchAccuracyManager(config);
}
