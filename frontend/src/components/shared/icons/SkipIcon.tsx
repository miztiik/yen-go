import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Skip/forward icon (double chevron) */
export function SkipIcon({ size = 16, className }: IconProps): JSX.Element {
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
      <polyline points="6 17 11 12 6 7" />
      <polyline points="13 17 18 12 13 7" />
    </svg>
  );
}
