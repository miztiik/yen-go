import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Flip diagonal icon (replaces ⤢) */
export function FlipDiagIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polyline points="5 9 3 3 9 5" />
      <polyline points="19 15 21 21 15 19" />
      <line x1="3" y1="3" x2="21" y2="21" />
      <line x1="3" y1="21" x2="21" y2="3" strokeDasharray="2 3" opacity="0.4" />
    </svg>
  );
}
