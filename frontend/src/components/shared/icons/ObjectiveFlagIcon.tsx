import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  color?: string;
  className?: string;
}

/**
 * Flag icon for Objective category in TechniqueCard.
 * Replaces U+1F3F3 (🏳) emoji. Represents goals.
 * Color: blue (#3b82f6)
 */
export function ObjectiveFlagIcon({
  size = 24,
  color = '#3b82f6',
  className,
}: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"
        fill={color}
        fillOpacity="0.15"
      />
      <line x1="4" y1="22" x2="4" y2="3" />
    </svg>
  );
}
