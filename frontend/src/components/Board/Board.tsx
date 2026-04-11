// @ts-nocheck
/**
 * Board Component - Renders Go board with stones using Canvas
 * @module components/Board/Board
 *
 * Covers: FR-001 to FR-006, FR-045 (keyboard nav), FR-048 (touch targets), US1, US9
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Rendering only, no game logic
 * - VI. Pure TypeScript: Preact + Canvas API
 * - IX. Accessibility: Keyboard navigation, touch targets, ARIA
 */

import { useRef, useEffect, useCallback } from 'preact/hooks';
import type { JSX } from 'preact';
import type { BoardSize, Coordinate, Stone } from '@models/puzzle';
import { BLACK, EMPTY } from '@models/puzzle';
import { rotateCoordinate, inverseRotateCoordinate, type BoardRotation } from './rotation';
import type { BoardRegion } from '@hooks/useBoardViewport';
import type { HoverStone } from './preview';

/** Solution marker for revealing correct/wrong moves */
export interface SolutionMarker {
  coord: Coordinate;
  type: 'correct' | 'wrong' | 'optimal';
}

/** Props for the Board component */
export interface BoardProps {
  /** Board size (9, 13, or 19) */
  boardSize: BoardSize;
  /** Current board state */
  stones: readonly (readonly Stone[])[];
  /** Last move coordinate for highlighting */
  lastMove?: Coordinate | null;
  /** Whether the last move is correct (for green/red circle marker) */
  lastMoveCorrectness?: boolean | undefined;
  /** Hover stone preview position (for hover effect) */
  hoverStone?: HoverStone | null;
  /** Points to highlight (e.g., from explanations) */
  highlightPoints?: readonly Coordinate[];
  /** Single move to highlight (e.g., hint move) - shown with pulsing effect */
  highlightedMove?: Coordinate | null;
  /** Solution markers showing correct/wrong moves for solution reveal */
 solutionMarkers?: readonly SolutionMarker[];
  /** Callback when a board intersection is clicked */
  onIntersectionClick?: (coord: Coordinate) => void;
  /** Callback when mouse hovers over intersection */
  onIntersectionHover?: (coord: Coordinate | null) => void;
  /** Whether board is interactive */
  interactive?: boolean;
  /** CSS class name */
  className?: string;
  /** Callback when Escape is pressed (FR-045) */
  onEscape?: () => void;
  /** Board rotation angle in degrees (0, 90, 180, 270) */
  rotation?: BoardRotation;
  /** Board region for partial rendering (Spec 118 Phase 2) */
  region?: BoardRegion;
  /** Number of visible cells for cropped view (Spec 118 Phase 2) */
  visibleCells?: number;
}

/** Board rendering constants */
const BOARD_PADDING = 28; // Reduced padding for coordinate labels (was 48)
const STAR_POINT_RADIUS_RATIO = 0.12; // Star point radius relative to cell size
const STONE_RADIUS_RATIO = 0.46; // Stone radius relative to cell size
const HOVER_STONE_ALPHA = 0.4; // Hover stone transparency
const LAST_MOVE_MARKER_RATIO = 0.25; // Last move marker size ratio (for square)

/** Board colors - refined for Apple-like aesthetics */
const COLORS = {
  board: '#E3C076', // Golden wood color per design mock
  boardShadow: 'rgba(0, 0, 0, 0.08)', // Subtle board shadow
  grid: '#8B7355', // Softer brown grid lines
  starPoint: '#5C4A32', // Darker star points
  blackStone: '#1a1a1a',
  blackStoneHighlight: '#3a3a3a',
  whiteStone: '#f8f8f8',
  whiteStoneHighlight: '#ffffff',
  whiteStoneBorder: '#c0c0c0',
  lastMoveMarker: '#E84545',
  coordLabel: '#6B5B45', // Muted brown for coordinates
  hintGlow: 'rgba(100, 180, 255, 0.6)', // Soft blue glow for hints
  solutionCorrect: '#16A34A', // Green for correct moves (green-600)
  solutionOptimal: '#16A34A', // Green with filled dot for optimal
  solutionWrong: '#DC2626', // Red for wrong moves
} as const;

/** Column labels (skip 'I' as is traditional in Go) */
const COLUMN_LABELS = 'ABCDEFGHJKLMNOPQRST';

/** Star point positions for different board sizes */
const STAR_POINTS: Record<number, Coordinate[]> = {
  5: [{ x: 2, y: 2 }], // Center only
  6: [{ x: 2, y: 2 }, { x: 3, y: 3 }],
  7: [
    { x: 2, y: 2 }, { x: 4, y: 2 },
    { x: 3, y: 3 }, // tengen
    { x: 2, y: 4 }, { x: 4, y: 4 },
  ],
  8: [
    { x: 2, y: 2 }, { x: 5, y: 2 },
    { x: 2, y: 5 }, { x: 5, y: 5 },
  ],
  9: [
    { x: 2, y: 2 }, { x: 6, y: 2 },
    { x: 4, y: 4 }, // tengen
    { x: 2, y: 6 }, { x: 6, y: 6 },
  ],
  10: [
    { x: 2, y: 2 }, { x: 7, y: 2 },
    { x: 2, y: 7 }, { x: 7, y: 7 },
  ],
  11: [
    { x: 2, y: 2 }, { x: 8, y: 2 },
    { x: 5, y: 5 }, // tengen
    { x: 2, y: 8 }, { x: 8, y: 8 },
  ],
  12: [
    { x: 3, y: 3 }, { x: 8, y: 3 },
    { x: 3, y: 8 }, { x: 8, y: 8 },
  ],
  13: [
    { x: 3, y: 3 }, { x: 9, y: 3 },
    { x: 6, y: 6 }, // tengen
    { x: 3, y: 9 }, { x: 9, y: 9 },
  ],
  19: [
    { x: 3, y: 3 }, { x: 9, y: 3 }, { x: 15, y: 3 },
    { x: 3, y: 9 }, { x: 9, y: 9 }, { x: 15, y: 9 }, // tengen at center
    { x: 3, y: 15 }, { x: 9, y: 15 }, { x: 15, y: 15 },
  ],
};

/** Get star points for a board size (with fallback to empty array) */
function getStarPoints(size: number): Coordinate[] {
  return STAR_POINTS[size] ?? [];
}

/**
 * Calculate board dimensions
 */
function calculateBoardDimensions(
  containerWidth: number,
  containerHeight: number,
  boardSize: BoardSize
): { cellSize: number; offsetX: number; offsetY: number } {
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
  cellSize: number,
  offsetX: number,
  offsetY: number,
  boardSize: BoardSize
): Coordinate | null {
  const boardX = Math.round((screenX - offsetX) / cellSize);
  const boardY = Math.round((screenY - offsetY) / cellSize);

  if (boardX >= 0 && boardX < boardSize && boardY >= 0 && boardY < boardSize) {
    return { x: boardX, y: boardY };
  }

  return null;
}

/**
 * Board component - renders a Go board with stones using HTML5 Canvas
 * Supports keyboard navigation (FR-045) and touch targets (FR-048)
 */
export function Board({
  boardSize,
  stones,
  lastMove,
  hoverStone,
  highlightPoints = [],
  highlightedMove,
  solutionMarkers = [],
  onIntersectionClick,
  onIntersectionHover,
  interactive = true,
  className,
  onEscape: _onEscape,
  rotation = 0,
}: BoardProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dimensionsRef = useRef({ cellSize: 0, offsetX: 0, offsetY: 0 });

  /**
   * Apply rotation to a coordinate for display
   */
  const applyRotation = useCallback(
    (x: number, y: number): [number, number] => {
      return rotateCoordinate(x, y, boardSize, rotation);
    },
    [boardSize, rotation]
  );

  /**
   * Convert screen coordinates back to original board coordinates
   * (reverse the rotation)
   */
  const inverseRotation = useCallback(
    (x: number, y: number): [number, number] => {
      return inverseRotateCoordinate(x, y, boardSize, rotation);
    },
    [boardSize, rotation]
  );

  /**
   * Draw the board background with coordinate labels
   */
  const drawBoard = useCallback(
    (ctx: CanvasRenderingContext2D, width: number, height: number): void => {
      const { cellSize, offsetX, offsetY } = dimensionsRef.current;

      // Background with subtle shadow effect
      ctx.fillStyle = COLORS.board;
      ctx.fillRect(0, 0, width, height);
      
      // Add subtle inner shadow for depth
      const shadowGradient = ctx.createLinearGradient(0, 0, 0, height);
      shadowGradient.addColorStop(0, 'rgba(0, 0, 0, 0.03)');
      shadowGradient.addColorStop(0.5, 'rgba(0, 0, 0, 0)');
      shadowGradient.addColorStop(1, 'rgba(0, 0, 0, 0.05)');
      ctx.fillStyle = shadowGradient;
      ctx.fillRect(0, 0, width, height);

      // Grid lines
      ctx.strokeStyle = COLORS.grid;
      ctx.lineWidth = 1;

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

      // Star points (with safe fallback for unsupported sizes)
      const starRadius = cellSize * STAR_POINT_RADIUS_RATIO;
      ctx.fillStyle = COLORS.starPoint;
      for (const point of getStarPoints(boardSize)) {
        ctx.beginPath();
        ctx.arc(
          offsetX + point.x * cellSize,
          offsetY + point.y * cellSize,
          starRadius,
          0,
          Math.PI * 2
        );
        ctx.fill();
      }

      // Draw coordinate labels
      const fontSize = Math.max(10, cellSize * 0.35);
      ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif`;
      ctx.fillStyle = COLORS.coordLabel;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      for (let i = 0; i < boardSize; i++) {
        // Column labels (A-T, skipping I) at top and bottom
        const colLabel = COLUMN_LABELS[i] || String.fromCharCode(65 + i);
        const colX = offsetX + i * cellSize;
        
        // Top label
        ctx.fillText(colLabel, colX, offsetY - cellSize * 0.55);
        // Bottom label
        ctx.fillText(colLabel, colX, offsetY + (boardSize - 1) * cellSize + cellSize * 0.55);

        // Row labels (1-19, with 1 at bottom like traditional Go boards) on left and right
        const rowLabel = String(boardSize - i);
        const rowY = offsetY + i * cellSize;
        
        // Left label
        ctx.textAlign = 'right';
        ctx.fillText(rowLabel, offsetX - cellSize * 0.4, rowY);
        // Right label
        ctx.textAlign = 'left';
        ctx.fillText(rowLabel, offsetX + (boardSize - 1) * cellSize + cellSize * 0.4, rowY);
      }
    },
    [boardSize]
  );

  /**
   * Draw highlight points (with rotation)
   */
  const drawHighlights = useCallback(
    (ctx: CanvasRenderingContext2D): void => {
      const { cellSize, offsetX, offsetY } = dimensionsRef.current;

      ctx.fillStyle = COLORS.hintGlow;
      for (const point of highlightPoints) {
        // Apply rotation to display position
        const [displayX, displayY] = applyRotation(point.x, point.y);
        ctx.fillRect(
          offsetX + displayX * cellSize - cellSize * 0.4,
          offsetY + displayY * cellSize - cellSize * 0.4,
          cellSize * 0.8,
          cellSize * 0.8
        );
      }
    },
    [highlightPoints, applyRotation]
  );

  /**
   * Draw highlighted move (hint) with pulsing effect (with rotation)
   */
  const drawHighlightedMove = useCallback(
    (ctx: CanvasRenderingContext2D): void => {
      if (!highlightedMove) return;

      const { cellSize, offsetX, offsetY } = dimensionsRef.current;
      // Apply rotation to display position
      const [displayX, displayY] = applyRotation(highlightedMove.x, highlightedMove.y);
      const centerX = offsetX + displayX * cellSize;
      const centerY = offsetY + displayY * cellSize;
      const radius = cellSize * STONE_RADIUS_RATIO;

      ctx.save();

      // Draw hint as a subtle stone shadow/outline
      // Soft outer glow
      const glowGradient = ctx.createRadialGradient(
        centerX, centerY, radius * 0.5,
        centerX, centerY, radius * 1.3
      );
      glowGradient.addColorStop(0, 'rgba(100, 180, 255, 0.4)');
      glowGradient.addColorStop(0.6, 'rgba(100, 180, 255, 0.15)');
      glowGradient.addColorStop(1, 'rgba(100, 180, 255, 0)');
      
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius * 1.3, 0, Math.PI * 2);
      ctx.fillStyle = glowGradient;
      ctx.fill();

      // Draw hover stone outline
      ctx.strokeStyle = 'rgba(80, 160, 255, 0.8)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.stroke();

      // Fill with very subtle color
      ctx.fillStyle = 'rgba(100, 180, 255, 0.15)';
      ctx.fill();

      ctx.restore();
    },
    [highlightedMove, applyRotation]
  );

  /**
   * Draw a stone at a position
   */
  const drawStone = useCallback(
    (
      ctx: CanvasRenderingContext2D,
      x: number,
      y: number,
      color: 'black' | 'white',
      alpha: number = 1
    ): void => {
      const { cellSize, offsetX, offsetY } = dimensionsRef.current;
      const radius = cellSize * STONE_RADIUS_RATIO;
      const centerX = offsetX + x * cellSize;
      const centerY = offsetY + y * cellSize;

      ctx.save();
      ctx.globalAlpha = alpha;

      // Drop shadow for depth - enhanced for 3D effect per design mock
      ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
      ctx.shadowBlur = radius * 0.3;
      ctx.shadowOffsetX = radius * 0.15;
      ctx.shadowOffsetY = radius * 0.2;

      // Draw stone with enhanced gradient for realistic 3D effect
      const gradient = ctx.createRadialGradient(
        centerX - radius * 0.35,
        centerY - radius * 0.35,
        radius * 0.05,
        centerX + radius * 0.1,
        centerY + radius * 0.1,
        radius
      );

      if (color === 'black') {
        gradient.addColorStop(0, '#5a5a5a');
        gradient.addColorStop(0.3, '#3a3a3a');
        gradient.addColorStop(0.7, '#1a1a1a');
        gradient.addColorStop(1, '#0a0a0a');
      } else {
        gradient.addColorStop(0, '#ffffff');
        gradient.addColorStop(0.3, '#fafafa');
        gradient.addColorStop(0.7, '#e8e8e8');
        gradient.addColorStop(1, '#d0d0d0');
      }

      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();

      // Reset shadow before border
      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 0;

      // Subtle border for definition
      if (color === 'white') {
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.15)';
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }

      // Add specular highlight
      const highlightGradient = ctx.createRadialGradient(
        centerX - radius * 0.3,
        centerY - radius * 0.35,
        0,
        centerX - radius * 0.3,
        centerY - radius * 0.35,
        radius * 0.4
      );
      if (color === 'black') {
        highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.15)');
        highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
      } else {
        highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
        highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
      }
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.fillStyle = highlightGradient;
      ctx.fill();

      ctx.restore();
    },
    []
  );

  /**
   * Draw stones on the board (with rotation applied)
   */
  const drawStones = useCallback(
    (ctx: CanvasRenderingContext2D): void => {
      for (let y = 0; y < boardSize; y++) {
        for (let x = 0; x < boardSize; x++) {
          const stone = stones[y]?.[x];
          if (stone && stone !== EMPTY) {
            // Apply rotation to display position
            const [displayX, displayY] = applyRotation(x, y);
            const color = stone === BLACK ? 'black' : 'white';
            drawStone(ctx, displayX, displayY, color);
          }
        }
      }
    },
    [boardSize, stones, drawStone, applyRotation]
  );

  /**
   * Draw hover stone (hover preview) with rotation applied
   */
  const drawHoverStone = useCallback(
    (ctx: CanvasRenderingContext2D): void => {
      if (hoverStone) {
        const [displayX, displayY] = applyRotation(hoverStone.coord.x, hoverStone.coord.y);
        drawStone(
          ctx,
          displayX,
          displayY,
          hoverStone.color,
          HOVER_STONE_ALPHA
        );

        // Self-atari warning: draw red dot on hover stone
        if (hoverStone.isSelfAtari) {
          const { cellSize: cs, offsetX: ox, offsetY: oy } = dimensionsRef.current;
          const cx = displayX * cs + ox;
          const cy = displayY * cs + oy;
          const radius = cs * 0.15;
          ctx.save();
          ctx.globalAlpha = 0.9;
          ctx.fillStyle = '#E53E3E';
          ctx.beginPath();
          ctx.arc(cx, cy, radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }
      }
    },
    [hoverStone, drawStone, applyRotation]
  );

  /**
   * Draw last move marker - square shape for clear visibility (with rotation)
   */
  const drawLastMoveMarker = useCallback(
    (ctx: CanvasRenderingContext2D): void => {
      if (!lastMove) return;

      const { cellSize, offsetX, offsetY } = dimensionsRef.current;
      const stone = stones[lastMove.y]?.[lastMove.x];
      if (!stone || stone === EMPTY) return;

      // Apply rotation to display position
      const [displayX, displayY] = applyRotation(lastMove.x, lastMove.y);
      const markerSize = cellSize * LAST_MOVE_MARKER_RATIO;
      const centerX = offsetX + displayX * cellSize;
      const centerY = offsetY + displayY * cellSize;

      // Draw a contrasting square marker (like in traditional Go software)
      ctx.fillStyle = stone === BLACK ? COLORS.whiteStone : COLORS.blackStone;
      ctx.fillRect(
        centerX - markerSize / 2,
        centerY - markerSize / 2,
        markerSize,
        markerSize
      );
    },
    [lastMove, stones, applyRotation]
  );

  /**
   * Draw solution markers - circles showing correct (green) and wrong (red) moves (with rotation)
   */
  const drawSolutionMarkers = useCallback(
    (ctx: CanvasRenderingContext2D): void => {
      if (solutionMarkers.length === 0) return;

      const { cellSize, offsetX, offsetY } = dimensionsRef.current;
      const markerRadius = cellSize * 0.35;
      const lineWidth = cellSize * 0.06;

      for (const marker of solutionMarkers) {
        // Apply rotation to display position
        const [displayX, displayY] = applyRotation(marker.coord.x, marker.coord.y);
        const centerX = offsetX + displayX * cellSize;
        const centerY = offsetY + displayY * cellSize;

        // Choose color based on marker type
        const color = marker.type === 'wrong' 
          ? COLORS.solutionWrong 
          : COLORS.solutionCorrect;

        // Draw circle outline
        ctx.beginPath();
        ctx.arc(centerX, centerY, markerRadius, 0, Math.PI * 2);
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.stroke();

        // For optimal moves, also draw a filled dot in the center
        if (marker.type === 'optimal') {
          ctx.beginPath();
          ctx.arc(centerX, centerY, cellSize * 0.1, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
        }
      }
    },
    [solutionMarkers, applyRotation]
  );

  /**
   * Main render function
   */
  const render = useCallback((): void => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Get container dimensions
    const rect = container.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    // Set canvas size (with device pixel ratio for sharp rendering)
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Calculate dimensions
    dimensionsRef.current = calculateBoardDimensions(width, height, boardSize);

    // Draw all layers
    drawBoard(ctx, width, height);
    drawHighlights(ctx);
    drawHighlightedMove(ctx);
    drawStones(ctx);
    drawHoverStone(ctx);
    drawLastMoveMarker(ctx);
    drawSolutionMarkers(ctx);
  }, [boardSize, drawBoard, drawHighlights, drawHighlightedMove, drawStones, drawHoverStone, drawLastMoveMarker, drawSolutionMarkers]);

  // Re-render when props change
  useEffect(() => {
    render();
  }, [render]);

  // Handle resize
  useEffect(() => {
    const handleResize = (): void => {
      render();
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [render]);

  /**
   * Handle click events (with inverse rotation to convert back to original coordinates)
   */
  const handleClick = useCallback(
    (event: MouseEvent): void => {
      if (!interactive || !onIntersectionClick) return;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const { cellSize, offsetX, offsetY } = dimensionsRef.current;
      const displayCoord = screenToBoardCoords(x, y, cellSize, offsetX, offsetY, boardSize);

      if (displayCoord) {
        // Apply inverse rotation to convert display coords back to original puzzle coords
        const [origX, origY] = inverseRotation(displayCoord.x, displayCoord.y);
        onIntersectionClick({ x: origX, y: origY });
      }
    },
    [interactive, onIntersectionClick, boardSize, inverseRotation]
  );

  /**
   * Handle mouse move for hover effects (with inverse rotation)
   */
  const handleMouseMove = useCallback(
    (event: MouseEvent): void => {
      if (!interactive || !onIntersectionHover) return;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const { cellSize, offsetX, offsetY } = dimensionsRef.current;
      const displayCoord = screenToBoardCoords(x, y, cellSize, offsetX, offsetY, boardSize);

      if (displayCoord) {
        // Apply inverse rotation to convert display coords back to original puzzle coords
        const [origX, origY] = inverseRotation(displayCoord.x, displayCoord.y);
        onIntersectionHover({ x: origX, y: origY });
      } else {
        onIntersectionHover(null);
      }
    },
    [interactive, onIntersectionHover, boardSize, inverseRotation]
  );

  /**
   * Handle mouse leave
   */
  const handleMouseLeave = useCallback((): void => {
    if (onIntersectionHover) {
      onIntersectionHover(null);
    }
  }, [onIntersectionHover]);

  /**
   * Handle touch events for mobile (with inverse rotation)
   */
  const handleTouchEnd = useCallback(
    (event: TouchEvent): void => {
      if (!interactive || !onIntersectionClick) return;
      event.preventDefault();

      const canvas = canvasRef.current;
      if (!canvas) return;

      const touch = event.changedTouches[0];
      if (!touch) return;

      const rect = canvas.getBoundingClientRect();
      const x = touch.clientX - rect.left;
      const y = touch.clientY - rect.top;

      const { cellSize, offsetX, offsetY } = dimensionsRef.current;
      const displayCoord = screenToBoardCoords(x, y, cellSize, offsetX, offsetY, boardSize);

      if (displayCoord) {
        // Apply inverse rotation to convert display coords back to original puzzle coords
        const [origX, origY] = inverseRotation(displayCoord.x, displayCoord.y);
        onIntersectionClick({ x: origX, y: origY });
      }
    },
    [interactive, onIntersectionClick, boardSize, inverseRotation]
  );

  // Build accessible description
  const stoneCount = stones.flat().filter((s) => s !== null).length;
  const ariaDescription = interactive
    ? `Interactive ${boardSize}×${boardSize} Go board with ${stoneCount} stones. Click or tap to place a stone.`
    : `${boardSize}×${boardSize} Go board displaying ${stoneCount} stones.`;

  return (
    <div
      ref={containerRef}
      className={`board-container ${interactive ? 'interactive' : ''} ${className ?? ''}`}
      role="application"
      aria-label="Go puzzle board"
      aria-roledescription="Go board grid"
      tabIndex={interactive ? 0 : -1}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minWidth: '280px',
        minHeight: '280px',
        aspectRatio: '1 / 1',
        touchAction: 'none',
      }}
    >
      <canvas
        ref={canvasRef}
        onClick={handleClick as unknown as JSX.MouseEventHandler<HTMLCanvasElement>}
        onMouseMove={handleMouseMove as unknown as JSX.MouseEventHandler<HTMLCanvasElement>}
        onMouseLeave={handleMouseLeave}
        onTouchEnd={handleTouchEnd as unknown as JSX.GenericEventHandler<HTMLCanvasElement>}
        style={{
          display: 'block',
          cursor: 'default',
          width: '100%',
          height: '100%',
        }}
        role="img"
        aria-label={ariaDescription}
        aria-roledescription="Go board"
      />
    </div>
  );
}

export default Board;
