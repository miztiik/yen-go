// @ts-nocheck
/**
 * SVG Stone Component
 * @module components/Board/svg/SvgStone
 *
 * Spec 118 - T1.1: Create SvgStone Component
 * Renders individual Go stones with shadows and 3D highlights
 * Based on Besogo reference for realistic stone appearance
 */

import type { JSX } from 'preact';
import { SVG_COLORS, SVG_CONSTANTS, svgPos } from './constants';

export interface SvgStoneProps {
  /** Board X coordinate (0-based) */
  x: number;
  /** Board Y coordinate (0-based) */
  y: number;
  /** Stone color */
  color: 'black' | 'white';
  /** Whether this is a ghost stone (preview) */
  isGhost?: boolean;
  /** Whether this is the last move */
  isLastMove?: boolean;
  /** Whether the last move is correct (for green/red marker) */
  moveCorrectness?: boolean | undefined;
  /** Optional CSS class */
  className?: string;
}

/**
 * SVG defs for stone gradients and filters
 * These should be included once in the parent SVG
 */
export function StoneDefs(): JSX.Element {
  return (
    <defs>
      {/* Shadow blur filter */}
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
  );
}

/**
 * SVGStone - Renders a single Go stone with 3D appearance
 *
 * Features:
 * - Radial gradient for 3D appearance
 * - Highlight positioned at top-left (~30%) for light source effect
 * - Automatic shadow rendering with blur filter
 * - Ghost stone support (semi-transparent)
 * - Last move marker
 */
export function SvgStone({
  x,
  y,
  color,
  isGhost = false,
  isLastMove = false,
  moveCorrectness,
  className = '',
}: SvgStoneProps): JSX.Element {
  const cx = svgPos(x);
  const cy = svgPos(y);
  const radius = SVG_CONSTANTS.CELL_SIZE * SVG_CONSTANTS.STONE_RADIUS_RATIO;

  // Use gradient fills for 3D appearance
  const gradientId = color === 'black' ? 'url(#black-stone-gradient)' : 'url(#white-stone-gradient)';
  const highlightId = color === 'black' ? 'url(#black-stone-highlight)' : 'url(#white-stone-highlight)';

  const opacity = isGhost ? SVG_COLORS.ghostStone : 1;

  return (
    <g class={`svg-stone stone-${color} ${isGhost ? 'ghost' : ''} ${className}`} opacity={opacity}>
      {/* Shadow - offset down-right with blur */}
      {!isGhost && (
        <circle
          cx={cx + 2}
          cy={cy + 4}
          r={radius + 1}
          fill="black"
          opacity="0.32"
          filter="url(#stone-shadow-blur)"
        />
      )}

      {/* Main stone body with radial gradient */}
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        fill={gradientId}
        stroke={color === 'white' ? SVG_COLORS.whiteStoneBorder : 'none'}
        stroke-width={color === 'white' ? 0.5 : 0}
      />

      {/* Highlight overlay for enhanced 3D effect */}
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        fill={highlightId}
      />

      {/* Last move marker - ring with correctness color */}
      {isLastMove && (
        <circle
          cx={cx}
          cy={cy}
          r={radius * 0.55}
          fill="none"
          stroke={moveCorrectness === undefined 
            ? SVG_COLORS.lastMoveMarker 
            : moveCorrectness 
              ? SVG_COLORS.solutionCorrect 
              : SVG_COLORS.solutionWrong}
          stroke-width="3"
        />
      )}
    </g>
  );
}

export default SvgStone;
