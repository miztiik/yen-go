/**
 * Ghost Stone Layer Component
 * @module components/Board/svg/GhostStoneLayer
 *
 * Renders a ghost (preview) stone on hover at 35% opacity.
 * Used to show where the player's stone would be placed.
 */

import type { JSX } from 'preact';
import { SVG_COLORS } from './constants';

export interface GhostStoneLayerProps {
  /** Position to show ghost stone (null = hide) */
  position: { x: number; y: number } | null;
  /** Stone color to show */
  color: 'black' | 'white';
  /** Board size (usually 19) */
  boardSize: number;
  /** Cell size in pixels */
  cellSize: number;
  /** Board padding/margin offset */
  offset: { x: number; y: number };
  /** Current rotation in degrees */
  rotation: number;
}

/** Ghost stone opacity - 35% as per design spec */
const GHOST_OPACITY = 0.35;

/**
 * GhostStoneLayer - Renders a semi-transparent stone preview on hover
 *
 * Features:
 * - 35% opacity for ghost effect
 * - Radial gradient for 3D appearance
 * - Supports board rotation
 * - pointer-events: none to not interfere with clicks
 *
 * This component should be rendered AFTER regular stones so it appears on top.
 */
export function GhostStoneLayer({
  position,
  color,
  boardSize,
  cellSize,
  offset,
  rotation,
}: GhostStoneLayerProps): JSX.Element | null {
  // Don't render if no position
  if (!position) {
    return null;
  }

  // Validate position is within bounds
  if (position.x < 0 || position.x >= boardSize || position.y < 0 || position.y >= boardSize) {
    return null;
  }

  // Calculate center position
  const cx = position.x * cellSize + offset.x;
  const cy = position.y * cellSize + offset.y;

  // Stone radius (same ratio as SvgStone)
  const radius = cellSize * 0.46;

  // Colors based on stone color
  const stoneColor = color === 'black' ? SVG_COLORS.blackStone : SVG_COLORS.whiteStone;
  const highlightColor =
    color === 'black' ? SVG_COLORS.blackStoneHighlight : SVG_COLORS.whiteStoneHighlight;

  // Unique gradient IDs to avoid conflicts
  const gradientId = `ghost-stone-gradient-${color}`;

  // Calculate rotation transform if needed
  const transformOriginX = (boardSize - 1) * cellSize * 0.5 + offset.x;
  const transformOriginY = (boardSize - 1) * cellSize * 0.5 + offset.y;
  const rotationTransform =
    rotation !== 0 ? `rotate(${rotation} ${transformOriginX} ${transformOriginY})` : undefined;

  return (
    <g
      class="ghost-stone-layer"
      style={{ pointerEvents: 'none' }}
      opacity={GHOST_OPACITY}
      transform={rotationTransform}
    >
      {/* Define radial gradient for 3D effect */}
      <defs>
        <radialGradient
          id={gradientId}
          cx="35%"
          cy="35%"
          r="60%"
          fx="30%"
          fy="30%"
        >
          <stop offset="0%" stop-color={highlightColor} />
          <stop offset="100%" stop-color={stoneColor} />
        </radialGradient>
      </defs>

      {/* Main ghost stone body with gradient */}
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        fill={`url(#${gradientId})`}
        stroke={color === 'white' ? SVG_COLORS.whiteStoneBorder : 'none'}
        stroke-width={color === 'white' ? 0.5 : 0}
      />

      {/* Additional highlight for extra 3D depth */}
      <circle
        cx={cx - radius * 0.3}
        cy={cy - radius * 0.3}
        r={radius * 0.15}
        fill={highlightColor}
        opacity="0.5"
      />
    </g>
  );
}

export default GhostStoneLayer;
