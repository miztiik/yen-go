import type { JSX } from 'preact';

interface TrophyIconProps {
  size?: number;
  className?: string;
  style?: JSX.CSSProperties;
}

/**
 * Trophy SVG icon — used for level completion celebrations.
 * Replaces party popper emoji per project convention (no emojis in production UI).
 */
export function TrophyIcon({ size = 24, className, style }: TrophyIconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
    >
      {/* cup */}
      <path d="M6 9a6 6 0 0 0 12 0V3H6v6Z" />
      {/* left handle */}
      <path d="M6 5H4a2 2 0 0 0-2 2v1a4 4 0 0 0 4 4" />
      {/* right handle */}
      <path d="M18 5h2a2 2 0 0 1 2 2v1a4 4 0 0 1-4 4" />
      {/* stem */}
      <path d="M12 15v3" />
      {/* base */}
      <path d="M8 21h8" />
      <path d="M8 21a1 1 0 0 1-1-1v-1a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1" />
      {/* sparkle lines */}
      <line x1="12" y1="1" x2="12" y2="0" />
      <line x1="9" y1="1.5" x2="8.5" y2="0.5" />
      <line x1="15" y1="1.5" x2="15.5" y2="0.5" />
    </svg>
  );
}
