/**
 * ClearAllFiltersButton — shown inline in filter strip when 2+ filters are active.
 * @module components/shared/ClearAllFiltersButton
 *
 * Spec: plan-compact-schema-filtering.md WP8 §8.12
 * UX Expert #4: Only visible when activeFilterCount >= 2.
 */

import type { FunctionalComponent } from 'preact';

// ============================================================================
// Types
// ============================================================================

export interface ClearAllFiltersButtonProps {
  /** Called when user clicks "Clear all". */
  readonly onClear: () => void;
  /** Optional test ID. */
  readonly testId?: string;
}

// ============================================================================
// Component
// ============================================================================

export const ClearAllFiltersButton: FunctionalComponent<ClearAllFiltersButtonProps> = ({
  onClear,
  testId,
}) => {
  return (
    <button
      type="button"
      onClick={onClear}
      className="inline-flex items-center gap-1 rounded-full border-none bg-transparent px-2.5 py-1 text-xs font-medium text-[var(--color-text-muted)] transition-colors duration-200 hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 cursor-pointer min-h-[44px]"
      aria-label="Clear all filters"
      data-testid={testId ?? 'clear-all-filters'}
    >
      <span aria-hidden="true" className="text-xs">
        ×
      </span>
      Clear all
    </button>
  );
};

export default ClearAllFiltersButton;
