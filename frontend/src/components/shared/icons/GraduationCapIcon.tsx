import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  color?: string;
  className?: string;
}

/**
 * Graduation cap icon for Training page header.
 * Colorful by default — uses Training accent (blue).
 */
export function GraduationCapIcon({
  size = 24,
  color = 'var(--color-mode-training-border, #3b82f6)',
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
      <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
      <path d="M6 12v5c0 1.66 2.69 3 6 3s6-1.34 6-3v-5" />
    </svg>
  );
}
