import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Lightning bolt icon for streak / consecutive correct answers */
export function StreakIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" className={className} aria-hidden="true">
      <path d="M9.5 1L4 8.5H7.5L6 15L12 7.5H8.5L9.5 1Z" />
    </svg>
  );
}
