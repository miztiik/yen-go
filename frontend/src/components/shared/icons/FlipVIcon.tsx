import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Flip vertical icon (replaces ↕) */
export function FlipVIcon({ size = 16, className }: IconProps): JSX.Element {
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
      <polyline points="8 7 12 3 16 7" />
      <polyline points="8 17 12 21 16 17" />
      <line x1="12" y1="3" x2="12" y2="21" />
      <line x1="3" y1="12" x2="21" y2="12" strokeDasharray="2 3" />
    </svg>
  );
}
