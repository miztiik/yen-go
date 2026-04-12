import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/**
 * Coordinate axis icon for coordinate toggle — OGS style (T05)
 *
 * Reproduces the OGS ogs-coordinates glyph: an L-shaped corner with
 * "A" below the horizontal axis and "9" left of the vertical axis,
 * representing board coordinate labels.
 */
export function CoordsIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
      {/* L-shaped coordinate axes */}
      <path
        d="M11 5 L11 16 L21 16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* "9" label left of vertical axis */}
      <text
        x="4"
        y="7"
        fill="currentColor"
        stroke="none"
        fontSize="10"
        fontWeight="700"
        fontFamily="system-ui, sans-serif"
        textAnchor="middle"
        dominantBaseline="middle"
      >
        9
      </text>
      {/* "A" label below horizontal axis */}
      <text
        x="15"
        y="22.5"
        fill="currentColor"
        stroke="none"
        fontSize="11"
        fontWeight="700"
        fontFamily="system-ui, sans-serif"
        textAnchor="middle"
        dominantBaseline="middle"
      >
        A
      </text>
    </svg>
  );
}
