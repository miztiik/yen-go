import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Flip horizontal icon (replaces ↔) */
export function FlipHIcon({ size = 16, className }: IconProps): JSX.Element {
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
      <polyline points="7 8 3 12 7 16" />
      <polyline points="17 8 21 12 17 16" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="12" y1="3" x2="12" y2="21" strokeDasharray="2 3" />
    </svg>
  );
}
