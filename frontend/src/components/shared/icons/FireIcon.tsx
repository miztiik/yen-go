import type { JSX } from 'preact';

interface IconProps {
  size?: number;
  className?: string;
}

/** Fire icon for streak / rush mode branding */
export function FireIcon({ size = 16, className }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M8 1C8 1 3 6 3 10a5 5 0 0 0 10 0C13 6 8 1 8 1Zm0 12.5A3.5 3.5 0 0 1 4.5 10c0-2.1 2-5.1 3.5-7 1.5 1.9 3.5 4.9 3.5 7A3.5 3.5 0 0 1 8 13.5Z" />
    </svg>
  );
}
