import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
  filled?: boolean;
  /** Semantic color: alive (red) or lost (gray). Overrides currentColor. */
  alive?: boolean;
}

/** Heart icon for lives/skip cost. Colorful: red when alive, gray when lost. */
export function HeartIcon({ size = 16, className, filled = true, alive }: IconProps): JSX.Element {
  // Determine color: if `alive` prop is provided, use semantic color; otherwise fall back to currentColor
  const color = alive === true ? '#ef4444' : alive === false ? '#9ca3af' : 'currentColor';
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={filled ? color : 'none'} stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  );
}
