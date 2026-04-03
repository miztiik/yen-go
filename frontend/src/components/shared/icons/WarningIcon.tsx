import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Warning triangle icon (replaces ⚠️) */
export function WarningIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" className={className} aria-hidden="true">
      <path d="M8 1.45l6.93 12.1a.5.5 0 0 1-.43.75H1.5a.5.5 0 0 1-.43-.75L8 1.45Zm0 1.1L2.14 13.3h11.72L8 2.55ZM7.5 6h1v4h-1V6Zm0 5h1v1h-1v-1Z" />
    </svg>
  );
}
