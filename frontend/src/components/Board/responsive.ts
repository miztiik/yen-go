/**
 * Responsive board sizing utilities.
 * Handles dynamic sizing based on viewport and container.
 * @module components/Board/responsive
 */

/**
 * Board size constraints.
 */
export interface BoardSizeConstraints {
  /** Minimum board size in pixels */
  readonly minSize: number;
  /** Maximum board size in pixels */
  readonly maxSize: number;
  /** Padding around the board in pixels */
  readonly padding: number;
}

/**
 * Default size constraints.
 */
export const DEFAULT_SIZE_CONSTRAINTS: BoardSizeConstraints = {
  minSize: 280,
  maxSize: 600,
  padding: 16,
};

/**
 * Calculated board dimensions.
 */
export interface BoardDimensions {
  /** Board width in pixels */
  readonly width: number;
  /** Board height in pixels */
  readonly height: number;
  /** Cell size in pixels */
  readonly cellSize: number;
  /** Stone radius in pixels */
  readonly stoneRadius: number;
  /** Line width in pixels */
  readonly lineWidth: number;
  /** Star point radius in pixels */
  readonly starPointRadius: number;
  /** Coordinate font size in pixels */
  readonly coordFontSize: number;
}

/**
 * Calculate board dimensions based on container size.
 *
 * @param containerWidth - Container width in pixels
 * @param containerHeight - Container height in pixels
 * @param boardSize - Number of lines (9, 13, or 19)
 * @param constraints - Size constraints
 * @returns Calculated board dimensions
 */
export function calculateBoardDimensions(
  containerWidth: number,
  containerHeight: number,
  boardSize: number = 9,
  constraints: BoardSizeConstraints = DEFAULT_SIZE_CONSTRAINTS
): BoardDimensions {
  const { minSize, maxSize, padding } = constraints;

  // Calculate available space
  const availableWidth = containerWidth - padding * 2;
  const availableHeight = containerHeight - padding * 2;
  const available = Math.min(availableWidth, availableHeight);

  // Clamp to constraints
  const size = Math.max(minSize, Math.min(maxSize, available));

  // Calculate cell size based on board size
  // Leave room for coordinates
  const coordMargin = 24;
  const playableSize = size - coordMargin * 2;
  const cellSize = playableSize / (boardSize - 1);

  // Calculate derived sizes
  const stoneRadius = cellSize * 0.45;
  const lineWidth = Math.max(1, cellSize * 0.04);
  const starPointRadius = cellSize * 0.12;
  const coordFontSize = Math.max(10, cellSize * 0.35);

  return {
    width: size,
    height: size,
    cellSize,
    stoneRadius,
    lineWidth,
    starPointRadius,
    coordFontSize,
  };
}

/**
 * Get optimal board size for viewport.
 * Takes into account available space and other UI elements.
 *
 * @param viewportWidth - Viewport width
 * @param viewportHeight - Viewport height
 * @param headerHeight - Height of header/nav
 * @param footerHeight - Height of footer/controls
 * @returns Optimal board size
 */
export function getOptimalBoardSize(
  viewportWidth: number,
  viewportHeight: number,
  headerHeight: number = 60,
  footerHeight: number = 120
): number {
  const availableHeight = viewportHeight - headerHeight - footerHeight;
  const availableWidth = viewportWidth;

  const size = Math.min(availableWidth, availableHeight);

  // Apply constraints
  return Math.max(
    DEFAULT_SIZE_CONSTRAINTS.minSize,
    Math.min(DEFAULT_SIZE_CONSTRAINTS.maxSize, size - DEFAULT_SIZE_CONSTRAINTS.padding * 2)
  );
}

/**
 * Responsive board sizing hook state.
 */
export interface ResponsiveBoardState {
  /** Current board dimensions */
  readonly dimensions: BoardDimensions;
  /** Whether board is in portrait mode */
  readonly isPortrait: boolean;
  /** Whether touch mode is active */
  readonly isTouchMode: boolean;
  /** Device pixel ratio */
  readonly pixelRatio: number;
}

/**
 * Create responsive board state.
 *
 * @param containerWidth - Container width
 * @param containerHeight - Container height
 * @param boardSize - Number of lines
 * @returns Responsive board state
 */
export function createResponsiveBoardState(
  containerWidth: number,
  containerHeight: number,
  boardSize: number = 9
): ResponsiveBoardState {
  const dimensions = calculateBoardDimensions(
    containerWidth,
    containerHeight,
    boardSize
  );

  const isPortrait = containerHeight > containerWidth;
  const isTouchMode = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  const pixelRatio = window.devicePixelRatio || 1;

  return {
    dimensions,
    isPortrait,
    isTouchMode,
    pixelRatio,
  };
}

/**
 * Calculate canvas resolution for high-DPI displays.
 *
 * @param displayWidth - Display width in CSS pixels
 * @param displayHeight - Display height in CSS pixels
 * @param pixelRatio - Device pixel ratio
 * @returns Canvas dimensions
 */
export function calculateCanvasResolution(
  displayWidth: number,
  displayHeight: number,
  pixelRatio: number = window.devicePixelRatio || 1
): {
  canvasWidth: number;
  canvasHeight: number;
  scale: number;
} {
  return {
    canvasWidth: Math.floor(displayWidth * pixelRatio),
    canvasHeight: Math.floor(displayHeight * pixelRatio),
    scale: pixelRatio,
  };
}

/**
 * Get breakpoint category based on width.
 */
export type BreakpointCategory = 'mobile' | 'tablet' | 'desktop';

/**
 * Determine breakpoint category.
 *
 * @param width - Viewport width
 * @returns Breakpoint category
 */
export function getBreakpointCategory(width: number): BreakpointCategory {
  if (width < 480) return 'mobile';
  if (width < 768) return 'tablet';
  return 'desktop';
}

/**
 * Breakpoint-specific board configuration.
 */
export interface BreakpointConfig {
  /** Board size percentage of viewport */
  readonly boardSizePercent: number;
  /** Show coordinates */
  readonly showCoordinates: boolean;
  /** Control panel position */
  readonly controlPosition: 'bottom' | 'side';
}

/**
 * Get breakpoint-specific configuration.
 */
export function getBreakpointConfig(category: BreakpointCategory): BreakpointConfig {
  switch (category) {
    case 'mobile':
      return {
        boardSizePercent: 95,
        showCoordinates: false, // Save space on mobile
        controlPosition: 'bottom',
      };
    case 'tablet':
      return {
        boardSizePercent: 80,
        showCoordinates: true,
        controlPosition: 'bottom',
      };
    case 'desktop':
      return {
        boardSizePercent: 70,
        showCoordinates: true,
        controlPosition: 'side',
      };
  }
}
