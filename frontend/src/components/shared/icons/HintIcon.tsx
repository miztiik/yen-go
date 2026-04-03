import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
  /** Whether hints are available (amber/gold) or depleted (gray). */
  available?: boolean;
  /** Hints remaining (drives count number and progressive dimming). */
  count?: number;
}

/**
 * Lightbulb hint icon with count inside the dome.
 * Progressive dimming as hints are used:
 *   3+ → full opacity
 *   2  → 85%
 *   1  → 65%
 *   0  → 40%
 */
export function HintIcon({ size = 16, className, available, count }: IconProps): JSX.Element {
  const color = available === true ? '#f59e0b' : available === false ? '#9ca3af' : 'currentColor';
  const opacity = count === undefined ? 1 : count >= 3 ? 1 : count === 2 ? 0.85 : count === 1 ? 0.65 : 0.4;

  return (
    <svg
      width={size} height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ opacity }}
    >
      {/* Bulb dome */}
      <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
      {/* Bulb base */}
      <path d="M9 18h6" />
      <path d="M10 22h4" />

      {/* Count inside bulb dome */}
      {count !== undefined && count > 0 && (
        <text
          x="12" y="9"
          textAnchor="middle"
          dominantBaseline="central"
          fill={color}
          stroke="none"
          fontSize="10"
          fontWeight="700"
          fontFamily="system-ui, sans-serif"
        >
          {count}
        </text>
      )}
    </svg>
  );
}
