import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Sleep/inactive icon (replaces 💤) */
export function SleepIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M5 4h4L5 8h4M8 2h3l-3 4h3M2 7h5L2 12h5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
