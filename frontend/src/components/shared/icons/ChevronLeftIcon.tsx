import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Chevron-left icon for back navigation (replaces ← Unicode) */
export function ChevronLeftIcon({ size = 20, className }: IconProps): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}
