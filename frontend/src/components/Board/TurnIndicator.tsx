/**
 * TurnIndicator Component - Shows whose turn it is
 * @module components/Board/TurnIndicator
 *
 * Covers: FR-007 (Turn indicator display)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Turn display separate from board
 * - IX. Accessibility: Clear visual and text indication
 */

import type { JSX } from 'preact';

/**
 * Props for TurnIndicator component
 */
export interface TurnIndicatorProps {
  /** Current player color */
  color: 'black' | 'white';
  /** Optional label (e.g., "Your turn") */
  label?: string;
  /** Size of the indicator (default: medium) */
  size?: 'small' | 'medium' | 'large';
  /** Additional CSS class */
  className?: string;
  /** Show as compact inline element */
  compact?: boolean;
}

/**
 * Size mappings for the stone indicator
 */
const SIZE_MAP = {
  small: 16,
  medium: 24,
  large: 32,
} as const;

/**
 * TurnIndicator - Visual indicator of current player
 *
 * Displays a stone-like circle with the current player's color
 * and optional label text.
 */
export function TurnIndicator({
  color,
  label,
  size = 'medium',
  className = '',
  compact = false,
}: TurnIndicatorProps): JSX.Element {
  const stoneSize = SIZE_MAP[size];
  const colorLabel = color === 'black' ? 'Black' : 'White';
  const displayLabel = label ?? `${colorLabel} to play`;

  const containerStyle: JSX.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: compact ? '6px' : '10px',
    padding: compact ? '4px 8px' : '8px 12px',
    borderRadius: '8px',
    backgroundColor: 'var(--turn-indicator-bg, #f5f5f5)',
    fontSize: size === 'small' ? '12px' : size === 'large' ? '16px' : '14px',
    fontWeight: 500,
  };

  const stoneStyle: JSX.CSSProperties = {
    width: `${stoneSize}px`,
    height: `${stoneSize}px`,
    borderRadius: '50%',
    background:
      color === 'black'
        ? 'radial-gradient(circle at 30% 30%, #4a4a4a, #000000)'
        : 'radial-gradient(circle at 30% 30%, #ffffff, #e0e0e0)',
    border: color === 'white' ? '1px solid #ccc' : 'none',
    boxShadow: '1px 1px 2px rgba(0,0,0,0.3)',
    flexShrink: 0,
  };

  return (
    <div
      className={`turn-indicator ${className}`}
      style={containerStyle}
      role="status"
      aria-live="polite"
      aria-label={displayLabel}
    >
      <div
        className="turn-indicator-stone"
        style={stoneStyle}
        aria-hidden="true"
      />
      {!compact && (
        <span className="turn-indicator-label">{displayLabel}</span>
      )}
    </div>
  );
}

/**
 * Minimal turn indicator - just the stone
 */
export function TurnStone({
  color,
  size = 'medium',
  className = '',
}: Pick<TurnIndicatorProps, 'color' | 'size' | 'className'>): JSX.Element {
  const stoneSize = SIZE_MAP[size];
  const colorLabel = color === 'black' ? 'Black' : 'White';

  const stoneStyle: JSX.CSSProperties = {
    width: `${stoneSize}px`,
    height: `${stoneSize}px`,
    borderRadius: '50%',
    background:
      color === 'black'
        ? 'radial-gradient(circle at 30% 30%, #4a4a4a, #000000)'
        : 'radial-gradient(circle at 30% 30%, #ffffff, #e0e0e0)',
    border: color === 'white' ? '1px solid #ccc' : 'none',
    boxShadow: '1px 1px 2px rgba(0,0,0,0.3)',
    display: 'inline-block',
  };

  return (
    <span
      className={`turn-stone ${className}`}
      style={stoneStyle}
      role="img"
      aria-label={`${colorLabel} stone`}
    />
  );
}

/**
 * Animated turn indicator with pulse effect
 */
export function AnimatedTurnIndicator({
  color,
  label,
  size = 'medium',
  className = '',
}: TurnIndicatorProps): JSX.Element {
  const stoneSize = SIZE_MAP[size];
  const colorLabel = color === 'black' ? 'Black' : 'White';
  const displayLabel = label ?? `${colorLabel} to play`;

  const containerStyle: JSX.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 12px',
    borderRadius: '8px',
    backgroundColor: 'var(--turn-indicator-bg, #f5f5f5)',
    fontSize: size === 'small' ? '12px' : size === 'large' ? '16px' : '14px',
    fontWeight: 500,
  };

  const stoneContainerStyle: JSX.CSSProperties = {
    position: 'relative',
    width: `${stoneSize}px`,
    height: `${stoneSize}px`,
  };

  const stoneStyle: JSX.CSSProperties = {
    width: '100%',
    height: '100%',
    borderRadius: '50%',
    background:
      color === 'black'
        ? 'radial-gradient(circle at 30% 30%, #4a4a4a, #000000)'
        : 'radial-gradient(circle at 30% 30%, #ffffff, #e0e0e0)',
    border: color === 'white' ? '1px solid #ccc' : 'none',
    boxShadow: '1px 1px 2px rgba(0,0,0,0.3)',
    position: 'relative',
    zIndex: 1,
  };

  const pulseStyle: JSX.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    borderRadius: '50%',
    backgroundColor: color === 'black' ? 'rgba(0,0,0,0.3)' : 'rgba(255,255,255,0.5)',
    animation: 'turn-pulse 1.5s ease-in-out infinite',
  };

  return (
    <div
      className={`turn-indicator animated ${className}`}
      style={containerStyle}
      role="status"
      aria-live="polite"
      aria-label={displayLabel}
    >
      <div style={stoneContainerStyle}>
        <div className="turn-pulse" style={pulseStyle} aria-hidden="true" />
        <div className="turn-stone" style={stoneStyle} aria-hidden="true" />
      </div>
      <span className="turn-indicator-label">{displayLabel}</span>
      <style>{`
        @keyframes turn-pulse {
          0% {
            transform: scale(1);
            opacity: 0.5;
          }
          50% {
            transform: scale(1.4);
            opacity: 0;
          }
          100% {
            transform: scale(1);
            opacity: 0.5;
          }
        }
      `}</style>
    </div>
  );
}

export default TurnIndicator;
