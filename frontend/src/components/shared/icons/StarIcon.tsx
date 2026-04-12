import type { JSX } from 'preact';

interface StarIconProps {
  size?: number;
  className?: string;
  style?: JSX.CSSProperties;
  /** When true, renders as a filled star. Default: false (outline only). */
  filled?: boolean;
}

/**
 * Star SVG icon — used for quality rating display.
 * Supports both filled and outline variants via the `filled` prop.
 */
export function StarIcon({
  size = 16,
  className,
  style,
  filled = false,
}: StarIconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
    >
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );
}
