import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  color?: string;
  className?: string;
}

/**
 * 2x2 grid icon for view toggle (grid mode).
 */
export function GridIcon({ size = 24, color = 'currentColor', className }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={color}
      className={className}
      aria-hidden="true"
    >
      <rect x="3" y="3" width="8" height="8" rx="1.5" />
      <rect x="13" y="3" width="8" height="8" rx="1.5" />
      <rect x="3" y="13" width="8" height="8" rx="1.5" />
      <rect x="13" y="13" width="8" height="8" rx="1.5" />
    </svg>
  );
}
