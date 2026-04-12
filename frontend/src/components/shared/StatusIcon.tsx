/**
 * Accessible Status Icon Component
 * @module components/shared/StatusIcon
 *
 * WCAG 2.1 AA compliant status indicator with icon and text fallback.
 * Covers: NFR-015, NFR-016, NFR-017
 */

import type { FunctionalComponent, JSX } from 'preact';
import { STATUS_ICONS, getStatusDisplay, srOnlyStyles } from '@/utils/accessibility';

export type StatusType = keyof typeof STATUS_ICONS;

export interface StatusIconProps {
  /** Status to display */
  status: StatusType;
  /** Show text alongside icon (for color-blind users) */
  showText?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Custom className */
  className?: string;
  /** Custom aria-label override */
  ariaLabel?: string;
}

const sizeMap = {
  sm: { icon: '1rem', text: '0.75rem', gap: '0.25rem' },
  md: { icon: '1.25rem', text: '0.875rem', gap: '0.375rem' },
  lg: { icon: '1.5rem', text: '1rem', gap: '0.5rem' },
};

/**
 * Accessible status icon with text fallback
 * Always includes screen-reader text, optionally shows visible text
 */
export const StatusIcon: FunctionalComponent<StatusIconProps> = ({
  status,
  showText = false,
  size = 'md',
  className = '',
  ariaLabel,
}) => {
  const display = getStatusDisplay(status);
  const sizes = sizeMap[size];

  const containerStyle: JSX.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: sizes.gap,
  };

  const iconStyle: JSX.CSSProperties = {
    fontSize: sizes.icon,
    lineHeight: 1,
  };

  const textStyle: JSX.CSSProperties = {
    fontSize: sizes.text,
    color: display.color,
    fontWeight: 500,
  };

  return (
    <span
      class={`status-icon status-icon--${status} ${className}`}
      style={containerStyle}
      role="img"
      aria-label={ariaLabel ?? display.ariaLabel}
    >
      <span style={iconStyle} aria-hidden="true">
        {display.icon}
      </span>
      {showText ? (
        <span style={textStyle}>{display.text}</span>
      ) : (
        // Screen reader only text when visual text is hidden
        <span style={srOnlyStyles as JSX.CSSProperties}>{display.text}</span>
      )}
    </span>
  );
};

/**
 * Strike indicator for Puzzle Rush
 * Shows X/max strikes with accessible labels
 */
export interface StrikeIndicatorProps {
  current: number;
  max: number;
  size?: 'sm' | 'md' | 'lg';
}

export const StrikeIndicator: FunctionalComponent<StrikeIndicatorProps> = ({
  current,
  max,
  size = 'md',
}) => {
  const sizes = sizeMap[size];

  const containerStyle: JSX.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: sizes.gap,
  };

  const strikeStyle = (isActive: boolean): JSX.CSSProperties => ({
    fontSize: sizes.icon,
    color: isActive ? 'var(--color-error)' : 'var(--color-neutral-300)',
    transition: 'color 0.2s ease',
  });

  const strikes = Array.from({ length: max }, (_, i) => i < current);

  return (
    <span
      class="strike-indicator"
      style={containerStyle}
      role="status"
      aria-label={`${current} of ${max} strikes`}
    >
      {strikes.map((isActive, index) => (
        <span key={index} style={strikeStyle(isActive)} aria-hidden="true">
          {isActive ? '✕' : '○'}
        </span>
      ))}
      <span style={srOnlyStyles as JSX.CSSProperties}>
        {current} of {max} strikes
      </span>
    </span>
  );
};

export default StatusIcon;
