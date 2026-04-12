import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  color?: string;
  className?: string;
}

/**
 * Tesuji icon — lightning spark for tactical patterns.
 * Replaces U+26A1 (⚡) emoji in TechniqueCard category config.
 * Color: amber/orange (#f59e0b)
 */
export function TesujiIcon({ size = 24, color = '#f59e0b', className }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={color}
      stroke="none"
      className={className}
      aria-hidden="true"
    >
      <path d="M13 2L4.09 12.63a1 1 0 0 0 .78 1.62H11l-1 7.25a.5.5 0 0 0 .86.44L19.91 11.37a1 1 0 0 0-.78-1.62H13l1-7.25a.5.5 0 0 0-.86-.44L13 2z" />
    </svg>
  );
}
