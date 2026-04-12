/**
 * Accessible Button Component
 * @module components/shared/Button
 *
 * Covers: FR-046 (ARIA labels), FR-048 (touch targets), US9
 *
 * Constitution Compliance:
 * - IX. Accessibility: WCAG 2.1 AA, touch targets, screen reader support
 */

import type { JSX, ComponentChildren } from 'preact';
import { forwardRef } from 'preact/compat';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends Omit<JSX.HTMLAttributes<HTMLButtonElement>, 'size' | 'disabled'> {
  /** Button variant for styling */
  variant?: ButtonVariant;
  /** Button size */
  size?: ButtonSize;
  /** Whether button is loading */
  loading?: boolean;
  /** Icon to show before text */
  leftIcon?: ComponentChildren;
  /** Icon to show after text */
  rightIcon?: ComponentChildren;
  /** Full width button */
  fullWidth?: boolean;
  /** Button content */
  children?: ComponentChildren;
  /** Whether button is disabled */
  disabled?: boolean;
}

/** Button style mappings */
const variantStyles: Record<ButtonVariant, JSX.CSSProperties> = {
  primary: {
    backgroundColor: 'var(--color-accent, #e94560)',
    color: 'white',
    border: 'none',
  },
  secondary: {
    backgroundColor: 'var(--color-bg-secondary, #16213e)',
    color: 'var(--color-text-primary, #1D1B16)',
    border: '1px solid var(--color-text-secondary, #a0a0a0)',
  },
  danger: {
    backgroundColor: 'var(--color-error, #e94560)',
    color: 'white',
    border: 'none',
  },
  ghost: {
    backgroundColor: 'transparent',
    color: 'var(--color-text-primary, #1D1B16)',
    border: '1px solid transparent',
  },
};

const sizeStyles: Record<ButtonSize, JSX.CSSProperties> = {
  sm: {
    padding: '0.5rem 1rem',
    fontSize: 'var(--font-size-sm, 0.875rem)',
    minHeight: '36px',
    minWidth: '36px',
  },
  md: {
    padding: '0.75rem 1.5rem',
    fontSize: 'var(--font-size-md, 1rem)',
    minHeight: 'var(--touch-target-min, 44px)',
    minWidth: 'var(--touch-target-min, 44px)',
  },
  lg: {
    padding: '1rem 2rem',
    fontSize: 'var(--font-size-lg, 1.25rem)',
    minHeight: '52px',
    minWidth: '52px',
  },
};

/**
 * Accessible button component with ARIA support
 * Meets WCAG 2.1 AA requirements for touch targets and screen readers
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    props,
    ref
  ) {
    const {
      variant = 'primary',
      size = 'md',
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      children,
      className,
      style,
      disabled,
      'aria-label': ariaLabel,
      'aria-describedby': ariaDescribedBy,
      ...restProps
    } = props;
    const isDisabled = disabled === true || loading;
    // Only spread style if it's a plain object (not a signal)
    const styleObj: JSX.CSSProperties = typeof style === 'object' && style !== null && !('value' in style)
      ? (style)
      : {};

    const buttonStyle: JSX.CSSProperties = {
      ...variantStyles[variant],
      ...sizeStyles[size],
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.5rem',
      borderRadius: 'var(--border-radius, 8px)',
      cursor: isDisabled ? 'not-allowed' : 'pointer',
      opacity: isDisabled ? 0.6 : 1,
      transition: 'background-color 0.2s, opacity 0.2s, transform 0.1s',
      fontWeight: 500,
      textDecoration: 'none',
      lineHeight: 1.5,
      width: fullWidth ? '100%' : 'auto',
      ...styleObj,
    };

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-bg-primary)] ${typeof className === 'string' ? className : ''}`}
        style={buttonStyle}
        aria-label={ariaLabel}
        aria-describedby={ariaDescribedBy}
        aria-disabled={isDisabled}
        aria-busy={loading}
        {...restProps}
      >
        {loading ? (
          <span
            role="status"
            aria-label="Loading"
            style={{
              display: 'inline-block',
              width: '1em',
              height: '1em',
              border: '2px solid currentColor',
              borderRightColor: 'transparent',
              borderRadius: '50%',
              animation: 'button-spin 0.75s linear infinite',
            }}
          />
        ) : (
          leftIcon
        )}
        {children}
        {!loading && rightIcon}
      </button>
    );
  }
);

export default Button;
