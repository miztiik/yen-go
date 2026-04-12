import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Double chevron left icon for "jump to first" navigation (« symbol) */
export function DoubleChevronLeftIcon({ size = 20, className }: IconProps): JSX.Element {
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
      <polyline points="11 18 5 12 11 6" />
      <polyline points="19 18 13 12 19 6" />
    </svg>
  );
}
