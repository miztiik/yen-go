import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Double chevron right icon for "jump to last" navigation (» symbol) */
export function DoubleChevronRightIcon({ size = 20, className }: IconProps): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <polyline points="13 18 19 12 13 6" />
      <polyline points="5 18 11 12 5 6" />
    </svg>
  );
}
