/**
 * FilterBar — shared segmented control with pill buttons.
 * @module components/shared/FilterBar
 *
 * Replaces native `<select>` with accessible pill-button group.
 * - Accent-colored active pill, elevated inactive
 * - 44px minimum touch targets
 * - Keyboard navigable: native button Enter/Space behavior
 * - aria-checked on active pill (radiogroup pattern)
 *
 * Spec 129, T064 — FR-044, FR-046, FR-064, FR-065
 */

import type { FunctionalComponent } from 'preact';
import { useCallback, useRef } from 'preact/hooks';

// ============================================================================
// Types
// ============================================================================

export interface FilterOption {
  /** Unique option ID (passed to onChange). */
  id: string;
  /** Display label. */
  label: string;
  /** Optional count badge (e.g., puzzle count from master index). */
  count?: number;
  /** Optional tooltip text shown on hover (e.g., "Beginner (25k–21k)"). WP8 §8.18. */
  tooltip?: string | undefined;
}

export interface FilterBarProps {
  /** Label for the filter group (for screen readers). */
  label: string;
  /** Available filter options. */
  options: readonly FilterOption[];
  /** Currently selected option ID(s). String for single-select, string[] for multi-select. */
  selected: string | readonly string[];
  /** Called when user selects/toggles an option. */
  onChange: (id: string) => void;
  /** Enable multi-select mode (toggle on/off, multiple active). */
  multiSelect?: boolean;
  /** Optional CSS class. */
  className?: string;
  /** Test ID prefix — each pill gets `{testId}-{option.id}`. */
  testId?: string;
}

// ============================================================================
// Component
// ============================================================================

export const FilterBar: FunctionalComponent<FilterBarProps> = ({
  label,
  options,
  selected,
  onChange,
  multiSelect = false,
  className = '',
  testId,
}) => {
  const groupRef = useRef<HTMLDivElement>(null);

  // Normalize selected to a Set for consistent lookup
  const selectedSet = typeof selected === 'string'
    ? new Set([selected])
    : new Set(selected);

  // PURSIG Finding 5: Roving tabindex — ArrowLeft/Right move focus + select
  const handleGroupKeyDown = useCallback((e: KeyboardEvent) => {
    const enabledOpts = options.filter(o => o.count !== 0);
    if (enabledOpts.length === 0) return;
    const activeId = (e.target as HTMLElement)?.getAttribute?.('data-option-id') ?? '';
    const currentIdx = enabledOpts.findIndex(o => o.id === activeId);
    let nextIdx: number;

    switch (e.key) {
      case 'ArrowRight':
      case 'ArrowDown':
        e.preventDefault();
        nextIdx = (currentIdx + 1) % enabledOpts.length;
        break;
      case 'ArrowLeft':
      case 'ArrowUp':
        e.preventDefault();
        nextIdx = (currentIdx - 1 + enabledOpts.length) % enabledOpts.length;
        break;
      case 'Home':
        e.preventDefault();
        nextIdx = 0;
        break;
      case 'End':
        e.preventDefault();
        nextIdx = enabledOpts.length - 1;
        break;
      case 'Enter':
      case ' ': {
        // F1: Handle Enter/Space at group level to avoid double-fire from per-button onKeyDown.
        // Native button click handles it in real browsers; this ensures JSDOM compat.
        e.preventDefault();
        const target = e.target as HTMLElement;
        const optId = target?.getAttribute?.('data-option-id');
        if (optId) onChange(optId);
        return;
      }
      default:
        return;
    }

    const nextOpt = enabledOpts[nextIdx];
    if (nextOpt) {
      onChange(nextOpt.id);
      const btn = groupRef.current?.querySelector(
        `[data-option-id="${nextOpt.id}"]`,
      ) as HTMLElement | null;
      btn?.focus();
    }
  }, [options, selected, onChange]);

  return (
    <div
      ref={groupRef}
      role={multiSelect ? 'group' : 'radiogroup'}
      aria-label={label}
      className={`flex flex-wrap gap-2 ${className}`}
      data-testid={testId}
      onKeyDown={handleGroupKeyDown}
    >
      {options.map((opt) => {
        const isActive = selectedSet.has(opt.id);
        const isDisabled = opt.count === 0;
        return (
          <button
            key={opt.id}
            type="button"
            role={multiSelect ? 'checkbox' : 'radio'}
            aria-checked={isActive}
            disabled={isDisabled || undefined}
            tabIndex={isActive ? 0 : -1}
            title={opt.tooltip}
            data-option-id={opt.id}
            onClick={() => {
              if (!isDisabled) onChange(opt.id);
            }}
            className="inline-flex min-h-[44px] cursor-pointer items-center justify-center gap-1 rounded-full px-4 text-sm transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
            style={
              isDisabled
                ? {
                    backgroundColor: 'var(--color-bg-elevated, #fff)',
                    color: 'var(--color-text-primary, #2C1810)',
                    fontWeight: 500,
                    border: '1px solid var(--color-border, #d4c9b8)',
                  }
                : isActive
                  ? {
                      backgroundColor: 'var(--color-accent, #059669)',
                      color: 'var(--color-bg-panel, #fff)',
                      fontWeight: 600,
                      border: '1px solid var(--color-accent, #059669)',
                    }
                  : {
                      backgroundColor: 'var(--color-bg-elevated, #fff)',
                      color: 'var(--color-text-primary, #2C1810)',
                      fontWeight: 500,
                      border: '1px solid var(--color-border, #d4c9b8)',
                    }
            }
            data-testid={testId ? `${testId}-${opt.id}` : undefined}
          >
            {opt.label}
            {opt.count != null && (
              <span className={`text-xs ${isActive ? '' : 'opacity-75'}`}>{opt.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default FilterBar;
