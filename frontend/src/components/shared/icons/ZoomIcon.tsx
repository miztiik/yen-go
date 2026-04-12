import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Expand/maximize icon — OGS-style outward diagonal arrows (T04) */
export function ZoomIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* Top-left arrow */}
      <line x1="9" y1="9" x2="3" y2="3" />
      <polyline points="3 8 3 3 8 3" />
      {/* Top-right arrow */}
      <line x1="15" y1="9" x2="21" y2="3" />
      <polyline points="16 3 21 3 21 8" />
      {/* Bottom-left arrow */}
      <line x1="9" y1="15" x2="3" y2="21" />
      <polyline points="8 21 3 21 3 16" />
      {/* Bottom-right arrow */}
      <line x1="15" y1="15" x2="21" y2="21" />
      <polyline points="21 16 21 21 16 21" />
    </svg>
  );
}
