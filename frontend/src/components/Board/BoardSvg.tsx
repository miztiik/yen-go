// @ts-nocheck
/**
 * BoardSvg Component - Renders Go board with stones using SVG
 * @module components/Board/BoardSvg
 *
 * Spec 118 - T1.5: Main BoardSvg Component
 * SVG-based board rendering as alternative to Canvas
 *
 * Features:
 * - Same BoardProps interface as Board.tsx for drop-in replacement
 * - CSS theming support via CSS variables
 * - Better accessibility with ARIA labels on individual elements
 * - DevTools-friendly (inspect individual stones)
 * - Automatic scaling with SVG viewBox
 *
 * Covers: FR-001 to FR-006, FR-045 (keyboard nav), FR-048 (touch targets), US1, US9
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Rendering only, no game logic
 * - VI. Pure TypeScript: Preact + SVG
 * - IX. Accessibility: Keyboard navigation, ARIA labels
 */

import { useCallback, useMemo } from 'preact/hooks';
import type { JSX } from 'preact';
import type { BoardProps } from './Board';
import { EMPTY } from '@models/puzzle';
import { SvgStone } from './svg/SvgStone';
import { SvgGrid } from './svg/SvgGrid';
import { SvgCoordLabels } from './svg/SvgCoordLabels';
import { SvgMarkers } from './svg/SvgMarkers';
import { ViewportIndicator } from './ViewportIndicator';
import { SVG_CONSTANTS, SVG_COLORS, calculateViewBox, svgPos } from './svg/constants';
import { rotateCoordinate, inverseRotateCoordinate } from './rotation';
import { useBoardViewport } from '@hooks/useBoardViewport';

/**
 * BoardSvg - SVG-based Go board rendering
 *
 * Drop-in replacement for Canvas-based Board component.
 * Uses same props interface for compatibility.
 */
export function BoardSvg({
  boardSize,
  stones,
  lastMove,
  lastMoveCorrectness,
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
  region,
  visibleCells,
}: BoardProps): JSX.Element {
  // Calculate viewport bounds for partial rendering (Phase 2)
  const viewport = useBoardViewport(boardSize, region, visibleCells);

  // Calculate viewBox dimensions
  const viewBox = useMemo(() => {
    if (!viewport.isCropped) {
      return calculateViewBox(boardSize, boardSize, true);
    }

    // Cropped viewBox for partial rendering
    const { minX, maxX, minY, maxY } = viewport;
    const width = (maxX - minX + 1) * SVG_CONSTANTS.CELL_SIZE + 2 * SVG_CONSTANTS.COORD_MARGIN;
    const height = (maxY - minY + 1) * SVG_CONSTANTS.CELL_SIZE + 2 * SVG_CONSTANTS.COORD_MARGIN;
    const x = svgPos(minX) - SVG_CONSTANTS.COORD_MARGIN;
    const y = svgPos(minY) - SVG_CONSTANTS.COORD_MARGIN;
    return `${x} ${y} ${width} ${height}`;
  }, [viewport, boardSize]);

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
   */
  const inverseRotation = useCallback(
    (x: number, y: number): [number, number] => {
      return inverseRotateCoordinate(x, y, boardSize, rotation);
    },
    [boardSize, rotation]
  );

  /**
   * Handle click on board intersection
   */
  const handleIntersectionClick = useCallback(
    (x: number, y: number) => {
      if (!interactive || !onIntersectionClick) return;

      const [origX, origY] = inverseRotation(x, y);
      onIntersectionClick({ x: origX, y: origY });
    },
    [interactive, onIntersectionClick, inverseRotation]
  );

  /**
   * Handle hover on board intersection
   */
  const handleIntersectionHover = useCallback(
    (x: number, y: number, isEntering: boolean) => {
      if (!interactive || !onIntersectionHover) return;

      if (isEntering) {
        const [origX, origY] = inverseRotation(x, y);
        onIntersectionHover({ x: origX, y: origY });
      } else {
        onIntersectionHover(null);
      }
    },
    [interactive, onIntersectionHover, inverseRotation]
  );

  // Render stones with rotation applied
  const renderedStones = useMemo(() => {
    const stoneElements: JSX.Element[] = [];

    for (let y = 0; y < boardSize; y++) {
      for (let x = 0; x < boardSize; x++) {
        const stone = stones[y]?.[x];
        if (!stone || stone === EMPTY) continue;

        const [rotX, rotY] = applyRotation(x, y);
        const isLast = !!(lastMove && lastMove.x === x && lastMove.y === y);
        const stoneColor = stone === -1 ? 'black' : 'white';

        stoneElements.push(
          <SvgStone
            key={`stone-${x}-${y}`}
            x={rotX}
            y={rotY}
            color={stoneColor}
            isLastMove={isLast}
            moveCorrectness={isLast ? lastMoveCorrectness : undefined}
          />
        );
      }
    }

    return stoneElements;
  }, [boardSize, stones, lastMove, lastMoveCorrectness, applyRotation]);

  // Hover stone rendered in a separate layer (Besogo pattern: hoverGroup at 35% opacity)
  const hoverStoneElement = useMemo(() => {
    if (!hoverStone) return null;
    const [rotX, rotY] = applyRotation(hoverStone.coord.x, hoverStone.coord.y);
    return (
      <g class="hover-stone-layer" style={{ pointerEvents: 'none' }} opacity={0.35}>
        <SvgStone
          key="hover-stone"
          x={rotX}
          y={rotY}
          color={hoverStone.color}
        />
        {hoverStone.isSelfAtari && (
          <circle
            cx={svgPos(rotX)}
            cy={svgPos(rotY)}
            r={SVG_CONSTANTS.CELL_SIZE * 0.15}
            fill={SVG_COLORS.selfAtariWarning}
            opacity={0.9}
          />
        )}
      </g>
    );
  }, [hoverStone, applyRotation]);

  // Create invisible hit targets for click/touch interaction
  const hitTargets = useMemo(() => {
    const targets: JSX.Element[] = [];

    for (let y = 0; y < boardSize; y++) {
      for (let x = 0; x < boardSize; x++) {
        const cx = svgPos(x);
        const cy = svgPos(y);
        const hitSize = SVG_CONSTANTS.CELL_SIZE * 0.9;

        targets.push(
          <rect
            key={`hit-${x}-${y}`}
            x={cx - hitSize / 2}
            y={cy - hitSize / 2}
            width={hitSize}
            height={hitSize}
            fill="transparent"
            cursor="default"
            onClick={() => handleIntersectionClick(x, y)}
            onMouseEnter={() => handleIntersectionHover(x, y, true)}
            onMouseLeave={() => handleIntersectionHover(x, y, false)}
            aria-label={`Intersection ${String.fromCharCode(65 + x)}${boardSize - y}`}
          />
        );
      }
    }

    return targets;
  }, [boardSize, interactive, handleIntersectionClick, handleIntersectionHover]);

  return (
    <div
      className={`board-container svg-board ${className || ''}`}
      role="application"
      aria-label={`${boardSize}x${boardSize} Go board`}
      tabIndex={interactive ? 0 : -1}
    >
      <svg
        viewBox={viewBox}
        width="100%"
        height="100%"
        class="board-svg"
        role="img"
        aria-label={`Go board with ${stones.flat().filter(Boolean).length} stones`}
      >
        {/* SVG Definitions - Filters and gradients */}
        <defs>
          {/* Blur filter for stone shadows */}
          <filter id="stone-shadow-blur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" />
          </filter>

          {/* Black stone radial gradient - dark gray center to black edges */}
          <radialGradient
            id="black-stone-gradient"
            cx="30%"
            cy="30%"
            r="60%"
            fx="30%"
            fy="30%"
          >
            <stop offset="0%" stop-color="#4a4a4a" />
            <stop offset="50%" stop-color="#2a2a2a" />
            <stop offset="100%" stop-color="#0a0a0a" />
          </radialGradient>

          {/* White stone radial gradient - white center to light gray edges */}
          <radialGradient
            id="white-stone-gradient"
            cx="30%"
            cy="30%"
            r="60%"
            fx="30%"
            fy="30%"
          >
            <stop offset="0%" stop-color="#ffffff" />
            <stop offset="50%" stop-color="#f0f0f0" />
            <stop offset="100%" stop-color="#d0d0d0" />
          </radialGradient>

          {/* White stone highlight - bright spot at top-left */}
          <radialGradient
            id="white-stone-highlight"
            cx="35%"
            cy="35%"
            r="30%"
            fx="35%"
            fy="35%"
          >
            <stop offset="0%" stop-color="#ffffff" stop-opacity="0.9" />
            <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
          </radialGradient>

          {/* Black stone highlight - subtle shine at top-left */}
          <radialGradient
            id="black-stone-highlight"
            cx="35%"
            cy="35%"
            r="25%"
            fx="35%"
            fy="35%"
          >
            <stop offset="0%" stop-color="#ffffff" stop-opacity="0.25" />
            <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
          </radialGradient>
        </defs>

        {/* Board background */}
        <rect x="0" y="0" width="100%" height="100%" fill={SVG_COLORS.board} />

        {/* Grid lines and star points */}
        <SvgGrid boardSize={boardSize} />

        {/* Coordinate labels - viewport-aware */}
        <SvgCoordLabels boardSize={boardSize} viewport={viewport} />

        {/* Stones */}
        <g class="stones-layer">{renderedStones}</g>

        {/* Hover stone layer (Besogo: separate group, 35% opacity, pointer-events: none) */}
        {hoverStoneElement}

        {/* Markers (hints, solution feedback) */}
        <SvgMarkers
          lastMove={lastMove}
          highlightedMove={highlightedMove}
          highlightPoints={highlightPoints}
          solutionMarkers={solutionMarkers}
        />

        {/* Viewport indicators for partial board rendering */}
        <ViewportIndicator viewport={viewport} boardSize={boardSize} />

        {/* Invisible hit targets for interaction */}
        <g class="hit-targets">{hitTargets}</g>
      </svg>
    </div>
  );
}

export default BoardSvg;
