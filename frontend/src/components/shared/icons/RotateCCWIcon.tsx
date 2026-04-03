import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Rotate counter-clockwise icon (circular arrow, mirrored CW) */
export function RotateCCWIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
    </svg>
  );
}
