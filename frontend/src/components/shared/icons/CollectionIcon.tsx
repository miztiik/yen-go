import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Folder-with-stone icon for puzzle collections — stone fills with page accent color */
export function CollectionIcon({ size = 20, className }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {/* Folder body */}
      <path d="M3 6a1 1 0 0 1 1-1h5l2 2h8a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6z" />
      {/* Go stone — uses page accent (purple/blue/green per context) */}
      <circle cx="12" cy="13" r="3" fill="var(--color-accent, currentColor)" stroke="none" />
    </svg>
  );
}
