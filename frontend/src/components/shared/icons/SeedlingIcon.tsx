import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  color?: string;
  className?: string;
}

/**
 * Seedling / sprout icon for Learn Go page.
 * Colorful by default — uses Learning accent (teal/cyan).
 */
export function SeedlingIcon({
  size = 24,
  color = 'var(--color-mode-learning-border, #06b6d4)',
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
      {/* Stem */}
      <path d="M12 22V12" />
      {/* Right leaf */}
      <path d="M12 12C12 8 16 4 20 4C20 8 16 12 12 12" />
      {/* Left leaf */}
      <path d="M12 15C12 11 8 7 4 7C4 11 8 15 12 15" />
    </svg>
  );
}
