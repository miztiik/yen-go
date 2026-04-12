import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Chevron-right icon for forward navigation (mirrors ChevronLeftIcon) */
export function ChevronRightIcon({ size = 20, className }: IconProps): JSX.Element {
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
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}
