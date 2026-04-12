/**
 * EmptyFilterState — shown when active filters produce zero matching puzzles.
 * @module components/shared/EmptyFilterState
 *
 * Displays a clear "No puzzles match" message with a "Clear filters" action.
 *
 * Spec: plan-compact-schema-filtering.md WP8 §8.16
 */

import type { FunctionalComponent } from 'preact';
import { GoTipDisplay } from '../Loading/GoTipDisplay';
import type { GoTip } from '../Loading/GoTipDisplay';
import { getBootConfigs } from '../../boot';

// ============================================================================
// Types
// ============================================================================

export interface ContentTypeMismatchInfo {
  /** Name of the currently active content type (e.g., "Practice") */
  readonly activeTypeName: string;
  /** Available types with their counts */
  readonly availableTypes: ReadonlyArray<{ readonly name: string; readonly count: number }>;
  /** Callback to reset content type to "All Types" */
  readonly onShowAllTypes: () => void;
}

export interface EmptyFilterStateProps {
  /** Optional custom message. Defaults to "No puzzles match your filters". */
  readonly message?: string;
  /** Called when user clicks "Clear filters". */
  readonly onClearFilters: () => void;
  /** Optional test ID. */
  readonly testId?: string;
  /** Optional level slug for filtering tips. */
  readonly level?: string;
  /** When provided, shows content-type specific messaging instead of generic. */
  readonly contentTypeInfo?: ContentTypeMismatchInfo;
}

// ============================================================================
// Component
// ============================================================================

export const EmptyFilterState: FunctionalComponent<EmptyFilterStateProps> = ({
  message = 'No puzzles match your filters',
  onClearFilters,
  testId,
  level,
  contentTypeInfo,
}) => {
  // Get Go tips from boot config for display during empty states
  let tips: GoTip[] = [];
  try {
    tips = getBootConfigs().tips as GoTip[];
  } catch {
    /* boot not ready */
  }

  const displayMessage = contentTypeInfo
    ? `No ${contentTypeInfo.activeTypeName} puzzles in this collection.`
    : message;

  const subtitle =
    contentTypeInfo && contentTypeInfo.availableTypes.length > 0
      ? contentTypeInfo.availableTypes
          .map((t) => `${t.count} ${t.name} puzzles available`)
          .join(' · ')
      : 'Try adjusting your filters or clear them to see all puzzles.';

  return (
    <div
      className="flex flex-col items-center justify-center gap-4 py-16 text-center"
      data-testid={testId ?? 'empty-filter-state'}
    >
      {/* Go tip — educational content while waiting */}
      {tips.length > 0 && (
        <div className="mb-4 self-stretch max-w-lg mx-auto">
          <GoTipDisplay tips={tips} {...(level != null && { level })} />
        </div>
      )}

      <div>
        <p className="text-base font-medium text-[var(--color-text-primary)]">{displayMessage}</p>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">{subtitle}</p>
      </div>
      <div className="flex items-center gap-2">
        {contentTypeInfo && (
          <button
            type="button"
            onClick={contentTypeInfo.onShowAllTypes}
            className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] px-5 py-2 text-sm font-semibold text-[var(--color-text-primary)] transition-colors duration-200 hover:bg-[var(--color-bg-secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 cursor-pointer min-h-[44px]"
            data-testid="show-all-types-button"
          >
            Show all types
          </button>
        )}
        <button
          type="button"
          onClick={onClearFilters}
          className="inline-flex items-center gap-1.5 rounded-full border-none px-5 py-2 text-sm font-semibold text-white transition-colors duration-200 hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 cursor-pointer min-h-[44px]"
          style={{
            backgroundColor: 'var(--color-accent)',
          }}
          data-testid="clear-filters-button"
        >
          {contentTypeInfo ? 'Clear all filters' : 'Clear filters'}
        </button>
      </div>
    </div>
  );
};

export default EmptyFilterState;
