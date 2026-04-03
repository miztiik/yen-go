/**
 * BoardCanvas Component - Core Canvas-based Go board renderer
 * @module components/Board/BoardCanvas
 *
 * Covers: FR-001 (Display board), FR-003 (Grid), FR-004 (Stones), FR-045 (Accessibility)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Canvas rendering, delegates to grid/hoshi/stones
 * - VI. Pure TypeScript: Preact + Canvas API (NO WGo.js)
 * - IX. Accessibility: Touch targets, ARIA labels
 */

import { useRef, useEffect, useCallback } from 'preact/hooks';
import type { JSX } from 'preact';
import type { BoardSize, Coordinate, Stone } from '@models/puzzle';
import { EMPTY } from '@models/puzzle';
import { drawGrid, type BoardDimensions } from './grid';
import { drawStarPoints } from './hoshi';
import { drawStones, drawHoverStone, drawLastMoveMarker } from './stones';

/** Board padding for coordinate labels */
const BOARD_PADDING = 48;

/** Props for the BoardCanvas component */
export interface BoardCanvasProps {
  /** Board size (9, 13, or 19) */
  boardSize: BoardSize;
  /** Current board state - 2D array of stones */
  stones: readonly (readonly Stone[])[];
  /** Last move coordinate for highlighting */
  lastMove?: Coordinate | null;
  /** Ghost stone preview position (hover effect) */
  ghostStone?: { coord: Coordinate; color: 'black' | 'white' } | null;
  /** Points to highlight (e.g., from hints) */
  highlightPoints?: readonly Coordinate[];
  /** Callback when an intersection is clicked */
  onIntersectionClick?: (coord: Coordinate) => void;
  /** Callback when mouse hovers over intersection */
  onIntersectionHover?: (coord: Coordinate | null) => void;
  /** Whether the board is interactive */
  interactive?: boolean;
  /** CSS class name */
  className?: string;
  /** Width override (defaults to container width) */
  width?: number;
  /** Height override (defaults to container height) */
  height?: number;
}

/**
 * Calculate board dimensions from container size
 */
function calculateDimensions(
  containerWidth: number,
  containerHeight: number,
  boardSize: BoardSize
): BoardDimensions {
  const minDimension = Math.min(containerWidth, containerHeight);
  const boardWidth = minDimension - BOARD_PADDING * 2;
  const cellSize = boardWidth / (boardSize - 1);
  const offsetX = (containerWidth - boardWidth) / 2;
  const offsetY = (containerHeight - boardWidth) / 2;

  return { cellSize, offsetX, offsetY };
}

/**
 * Convert screen coordinates to board coordinates
 */
function screenToBoardCoords(
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
 * Draw highlight points on the board
 */
function drawHighlights(
  ctx: CanvasRenderingContext2D,
  highlights: readonly Coordinate[],
  dimensions: BoardDimensions
): void {
  if (highlights.length === 0) return;

  const { cellSize, offsetX, offsetY } = dimensions;

  ctx.fillStyle = 'rgba(100, 180, 255, 0.3)';
  for (const point of highlights) {
    ctx.fillRect(
      offsetX + point.x * cellSize - cellSize * 0.4,
      offsetY + point.y * cellSize - cellSize * 0.4,
      cellSize * 0.8,
      cellSize * 0.8
    );
  }
}

/**
 * BoardCanvas - Core Go board renderer using HTML5 Canvas
 *
 * This component handles all board rendering using the Canvas API.
 * It delegates to specialized modules for grid, hoshi, and stone rendering.
 *
 * Features:
 * - Responsive sizing
 * - High-DPI support
 * - Touch and mouse interaction
 * - Ghost stone preview
 * - Last move marker
 * - Highlight points
 */
export function BoardCanvas({
  boardSize,
  stones,
  lastMove,
  ghostStone,
  highlightPoints = [],
  onIntersectionClick,
  onIntersectionHover,
  interactive = true,
  className,
  width,
  height,
}: BoardCanvasProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dimensionsRef = useRef<BoardDimensions>({ cellSize: 0, offsetX: 0, offsetY: 0 });

  /**
   * Main render function - draws the complete board
   */
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Get dimensions
    const containerWidth = width ?? container.clientWidth;
    const containerHeight = height ?? container.clientHeight;

    // Handle high-DPI displays
    const dpr = window.devicePixelRatio || 1;
    canvas.width = containerWidth * dpr;
    canvas.height = containerHeight * dpr;
    canvas.style.width = `${containerWidth}px`;
    canvas.style.height = `${containerHeight}px`;
    ctx.scale(dpr, dpr);

    // Calculate dimensions
    dimensionsRef.current = calculateDimensions(containerWidth, containerHeight, boardSize);

    // Clear canvas
    ctx.clearRect(0, 0, containerWidth, containerHeight);

    // Draw board layers
    drawGrid(ctx, containerWidth, containerHeight, boardSize, dimensionsRef.current);
    drawStarPoints(ctx, boardSize, dimensionsRef.current);
    drawHighlights(ctx, highlightPoints, dimensionsRef.current);
    drawStones(ctx, boardSize, stones, dimensionsRef.current);

    // Draw last move marker
    if (lastMove) {
      const stone = stones[lastMove.y]?.[lastMove.x];
      if (stone && stone !== EMPTY) {
        const stoneColor = stone === -1 ? 'black' : 'white';
        drawLastMoveMarker(ctx, lastMove, stoneColor, dimensionsRef.current);
      }
    }

    // Draw ghost stone
    if (ghostStone) {
      drawHoverStone(ctx, ghostStone.coord, ghostStone.color, dimensionsRef.current);
    }
  }, [boardSize, stones, lastMove, ghostStone, highlightPoints, width, height]);

  // Re-render when dependencies change
  useEffect(() => {
    render();
  }, [render]);

  // Handle resize
  useEffect(() => {
    const handleResize = () => render();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [render]);

  /**
   * Handle mouse/touch events
   */
  const handleInteraction = useCallback(
    (event: MouseEvent | TouchEvent, isClick: boolean) => {
      if (!interactive) return;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      let clientX: number;
      let clientY: number;

      if ('touches' in event) {
        const touch = event.touches[0] || event.changedTouches[0];
        if (!touch) return;
        clientX = touch.clientX;
        clientY = touch.clientY;
      } else {
        clientX = event.clientX;
        clientY = event.clientY;
      }

      const screenX = clientX - rect.left;
      const screenY = clientY - rect.top;

      const coord = screenToBoardCoords(
        screenX,
        screenY,
        dimensionsRef.current,
        boardSize
      );

      if (isClick && coord && onIntersectionClick) {
        onIntersectionClick(coord);
      } else if (!isClick && onIntersectionHover) {
        onIntersectionHover(coord);
      }
    },
    [boardSize, interactive, onIntersectionClick, onIntersectionHover]
  );

  const handleClick = useCallback(
    (event: MouseEvent) => handleInteraction(event, true),
    [handleInteraction]
  );

  const handleMouseMove = useCallback(
    (event: MouseEvent) => handleInteraction(event, false),
    [handleInteraction]
  );

  const handleMouseLeave = useCallback(() => {
    if (onIntersectionHover) {
      onIntersectionHover(null);
    }
  }, [onIntersectionHover]);

  const handleTouchStart = useCallback(
    (event: TouchEvent) => {
      // Prevent scrolling when touching the board
      event.preventDefault();
      handleInteraction(event, true);
    },
    [handleInteraction]
  );

  return (
    <div
      ref={containerRef}
      className={`board-canvas-container ${className ?? ''}`}
      style={{
        width: width ? `${width}px` : '100%',
        height: height ? `${height}px` : '100%',
        position: 'relative',
        touchAction: 'none', // Prevent browser touch handling
      }}
      role="application"
      aria-label={`${boardSize}x${boardSize} Go board`}
    >
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        onTouchStart={handleTouchStart}
        style={{
          display: 'block',
          cursor: interactive ? 'pointer' : 'default',
        }}
        aria-hidden="true" // Canvas content is decorative, interaction via container
      />
    </div>
  );
}

export default BoardCanvas;
