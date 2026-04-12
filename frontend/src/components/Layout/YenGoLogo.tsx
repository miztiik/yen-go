/**
 * Yen-Go Logo Component
 *
 * SVG logo representing the Yen-Go brand - a Go stone with subtle gradient.
 * Used in header (32px), splash screen (48px), and as favicon (16px).
 *
 * Spec 127 US11: References shared SVG source (public/icon.svg).
 * The inline SVG is kept for fast rendering without an extra network request,
 * but the shared SVG file is the canonical branding source.
 */

export interface YenGoLogoProps {
  /** Logo size in pixels. Default: 32 */
  size?: number;
  /** Optional CSS class */
  className?: string;
  /** Whether to show just the stone (true) or stone with text (false) */
  iconOnly?: boolean;
  /** Accessible label */
  ariaLabel?: string;
}

/**
 * Yen-Go Logo - A stylized Go stone representing the app brand.
 * Canonical source: public/icon.svg
 */
export function YenGoLogo({
  size = 32,
  className = '',
  iconOnly: _iconOnly = true,
  ariaLabel = 'yen·go',
}: YenGoLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label={ariaLabel}
    >
      <title>{ariaLabel}</title>

      <defs>
        <radialGradient id="stoneGradient" cx="35%" cy="30%" r="60%" fx="35%" fy="30%">
          <stop offset="0%" stopColor="#4a4a4a" />
          <stop offset="50%" stopColor="#2a2a2a" />
          <stop offset="100%" stopColor="#1a1a1a" />
        </radialGradient>
        <radialGradient id="highlightGradient" cx="30%" cy="25%" r="40%" fx="30%" fy="25%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.25)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0)" />
        </radialGradient>
        <filter id="stoneShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="1" dy="2" stdDeviation="2" floodOpacity="0.3" />
        </filter>
      </defs>

      <circle cx="24" cy="24" r="20" fill="url(#stoneGradient)" filter="url(#stoneShadow)" />
      <circle cx="24" cy="24" r="20" fill="url(#highlightGradient)" />
      <circle cx="16" cy="16" r="4" fill="rgba(255,255,255,0.15)" />
    </svg>
  );
}

/**
 * Logo with text variant - Used in header when space permits.
 * Branding: "yen·go" — lowercase, serif font, middle dot (U+00B7) with accent color.
 */
export function YenGoLogoWithText({
  size = 32,
  className = '',
}: {
  size?: number;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <YenGoLogo size={size} />
      <span
        className="lowercase tracking-wide font-light text-[var(--color-text-primary)]"
        style={{
          fontSize: `${size * 0.75}px`,
          fontFamily: '"Cormorant Garamond", "Playfair Display", Georgia, serif',
        }}
      >
        yen<span className="font-light text-[var(--color-accent)]">·</span>go
      </span>
    </div>
  );
}

export default YenGoLogo;
