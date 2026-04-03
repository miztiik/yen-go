import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  color?: string;
  className?: string;
}

/**
 * Dice icon for Random Challenge page header.
 * Colorful by default — uses Random accent (indigo).
 */
export function DiceIcon({
  size = 24,
  color = 'var(--color-mode-random-border, #6366f1)',
  className,
}: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <rect x="2" y="2" width="20" height="20" rx="3" ry="3" />
      <circle cx="8" cy="8" r="1.5" fill={color} stroke="none" />
      <circle cx="16" cy="8" r="1.5" fill={color} stroke="none" />
      <circle cx="8" cy="16" r="1.5" fill={color} stroke="none" />
      <circle cx="16" cy="16" r="1.5" fill={color} stroke="none" />
      <circle cx="12" cy="12" r="1.5" fill={color} stroke="none" />
    </svg>
  );
}
