/**
 * VariantStyleToggle
 * @module components/SolutionTree/VariantStyleToggle
 *
 * Radio group toggle for variant display style: children, siblings, or hidden.
 *
 * Spec 056, Tasks T038-T041
 * User Story 7: Variation Style Toggle
 */

import { type JSX } from 'preact';

/** Variant display modes */
export type VariantStyle = 'children' | 'siblings' | 'hidden';

export interface VariantStyleToggleProps {
  /** Currently selected variant style */
  value: VariantStyle;
  /** Callback when style changes */
  onChange: (style: VariantStyle) => void;
  /** Whether the toggle is disabled */
  disabled?: boolean;
  /** Optional CSS class */
  className?: string;
}

const options: Array<{ value: VariantStyle; label: string; icon: string }> = [
  { value: 'children', label: 'Children', icon: '🔽' },
  { value: 'siblings', label: 'Siblings', icon: '↔️' },
  { value: 'hidden', label: 'Hidden', icon: '👁️‍🗨️' },
];

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'inline-flex',
    gap: '2px',
    padding: '2px',
    backgroundColor: 'var(--color-neutral-100)',
    borderRadius: '8px',
    border: '1px solid var(--color-neutral-200)',
  },
  option: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '4px',
    padding: '6px 12px',
    fontSize: '13px',
    fontWeight: '500',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    backgroundColor: 'transparent',
    color: 'var(--color-text-secondary)',
    minWidth: '44px',
    minHeight: '44px',
    transition: 'all 150ms ease',
    whiteSpace: 'nowrap' as const,
  },
  optionActive: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '4px',
    padding: '6px 12px',
    fontSize: '13px',
    fontWeight: '600',
    border: 'none',
    borderRadius: '6px',
    cursor: 'default',
    backgroundColor: 'white',
    color: 'var(--color-text-primary)',
    minWidth: '44px',
    minHeight: '44px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    transition: 'all 150ms ease',
    whiteSpace: 'nowrap' as const,
  },
  optionDisabled: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '4px',
    padding: '6px 12px',
    fontSize: '13px',
    fontWeight: '500',
    border: 'none',
    borderRadius: '6px',
    cursor: 'not-allowed',
    backgroundColor: 'transparent',
    color: 'var(--color-text-muted)',
    minWidth: '44px',
    minHeight: '44px',
    opacity: 0.5,
    whiteSpace: 'nowrap' as const,
  },
};

/**
 * VariantStyleToggle
 *
 * A radio-group toggle for selecting how variations are displayed
 * on the board: children (default), siblings, or hidden.
 */
export function VariantStyleToggle({
  value,
  onChange,
  disabled = false,
  className,
}: VariantStyleToggleProps): JSX.Element {
  return (
    <div
      className={`variant-style-toggle ${className || ''}`}
      role="radiogroup"
      aria-label="Variant display style"
    >
      {options.map((opt) => {
        const isSelected = value === opt.value;

        const handleClick = () => {
          if (disabled || isSelected) return;
          onChange(opt.value);
        };

        const style = disabled
          ? styles.optionDisabled
          : isSelected
            ? styles.optionActive
            : styles.option;

        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={isSelected ? 'true' : 'false'}
            data-testid={`variant-option-${opt.value}`}
            disabled={disabled}
            tabIndex={isSelected ? 0 : -1}
            style={style}
            onClick={handleClick}
          >
            <span aria-hidden="true">{opt.icon}</span>
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export default VariantStyleToggle;
