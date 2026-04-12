import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Lock icon for locked/unavailable state (replaces 🔒) */
export function LockIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M4 7V5a4 4 0 0 1 8 0v2h1a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1Zm1.5 0h5V5a2.5 2.5 0 0 0-5 0v2Z" />
    </svg>
  );
}

/** Unlock icon for available/unlocked state (replaces 🔓) */
export function UnlockIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M10.5 5V4a2.5 2.5 0 0 0-5 0v3H3a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V8a1 1 0 0 0-1-1H7V4a1 1 0 0 1 2 0v1h1.5Z" />
    </svg>
  );
}
