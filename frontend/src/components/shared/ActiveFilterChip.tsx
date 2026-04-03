/**
 * ActiveFilterChip — dismissible inline chip showing an active filter.
 * @module components/shared/ActiveFilterChip
 *
 * Renders inline in the filter strip (right-aligned, not below).
 * Pill-shaped with accent coloring and an "×" dismiss button.
 *
 * Spec: plan-compact-schema-filtering.md §5.3 Active Filter Chip
 */

import type { FunctionalComponent } from 'preact';

// ============================================================================
// Types
// ============================================================================

export interface ActiveFilterChipProps {
  /** Display label for the active filter (e.g., "Ladder"). */
  readonly label: string;
  /** Called when user dismisses this filter. */
  readonly onDismiss: () => void;
  /** Optional CSS class. */
  readonly className?: string;
  /** Optional test ID. */
  readonly testId?: string;
}

// ============================================================================
// Component
// ============================================================================

export const ActiveFilterChip: FunctionalComponent<ActiveFilterChipProps> = ({
  label,
  onDismiss,
  className = '',
  testId,
}) => {
  // Finding 16: Removed redundant onKeyDown — <button> natively fires onClick on Enter/Space.

  return (
    <button
      type="button"
      onClick={onDismiss}
      aria-label={`Remove ${label} filter`}
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 ${className}`}
      style={{
        backgroundColor: 'color-mix(in srgb, var(--color-accent, #059669) 10%, transparent)',
        color: 'var(--color-accent, #059669)',
        border: '1px solid color-mix(in srgb, var(--color-accent, #059669) 30%, transparent)',
      }}
      data-testid={testId}
    >
      <span>{label}</span>
      <span aria-hidden="true" className="ml-0.5 text-xs leading-none">×</span>
    </button>
  );
};

export default ActiveFilterChip;
