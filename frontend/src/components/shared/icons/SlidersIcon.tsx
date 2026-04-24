import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  color?: string;
  className?: string;
}

/**
 * Horizontal sliders icon — used as the affordance for the View Options
 * panel (board flip / rotate / swap colors / coordinates / zoom). Replaces
 * the dated "VIEW OPTIONS ⌄" disclosure card on mobile (Phase 5).
 */
export function SlidersIcon({
  size = 24,
  color = 'currentColor',
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
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="18" x2="20" y2="18" />
      <circle cx="9" cy="6" r="2" fill="var(--color-bg-elevated, #fff)" />
      <circle cx="16" cy="12" r="2" fill="var(--color-bg-elevated, #fff)" />
      <circle cx="11" cy="18" r="2" fill="var(--color-bg-elevated, #fff)" />
    </svg>
  );
}
