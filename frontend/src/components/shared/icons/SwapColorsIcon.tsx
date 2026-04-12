import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Swap colors icon — half-black half-white circle (replaces ◐) */
export function SwapColorsIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className={className}
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2a10 10 0 0 1 0 20" fill="currentColor" />
    </svg>
  );
}
