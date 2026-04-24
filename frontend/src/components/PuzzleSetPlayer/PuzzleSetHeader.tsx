/**
 * PuzzleSetHeader — Unified compact toolbar header for puzzle set pages.
 *
 * Option A layout: Single row with back button, title, puzzle counter, and optional filter toggle.
 * Below: thin progress bar + active filter chips (when filters are on).
 *
 * Used by CollectionViewPage, TrainingViewPage, and TechniqueBrowsePage.
 * The AppHeader above this already provides gear/settings and user profile icons.
 *
 * @module components/PuzzleSetPlayer/PuzzleSetHeader
 */

import type { VNode, ComponentChildren } from 'preact';
import { useState } from 'preact/hooks';
import { ChevronLeftIcon } from '../shared/icons';
import { BottomSheet } from '../shared/BottomSheet';
import { SettingsGear } from '../Layout/SettingsGear';
import {
  UI_HEADER_DROP_COUNTER,
  UI_FILTERS_IN_SHEET,
  UI_HEADER_DROP_PROGRESS_BAR,
} from '../../services/featureFlags';

// ============================================================================
// Types
// ============================================================================

export interface PuzzleSetHeaderProps {
  /** Title displayed in the header (collection name, level name, etc.) */
  title: string;
  /** Optional subtitle (rank range, puzzle count, etc.) */
  subtitle?: string;
  /** Current puzzle index (0-based) */
  currentIndex: number;
  /** Total puzzles in the set */
  totalPuzzles: number;
  /** Callback for back navigation */
  onBack?: () => void;
  /** Back label for aria (default: "Back") */
  backLabel?: string;
  /** Progress percentage (0-100). If not provided, computed from currentIndex/totalPuzzles. */
  progress?: number;
  /** Optional filter strip content (rendered below the main toolbar row) */
  filterStrip?: ComponentChildren;
  /** Optional active filter count for the Filters trigger badge (sheet mode only). */
  activeFilterCount?: number;
  /** Optional right-side content (stats, badges, etc.) */
  rightContent?: ComponentChildren;
  /** Test ID prefix */
  testId?: string;
}

// ============================================================================
// Component
// ============================================================================

export function PuzzleSetHeader({
  title,
  subtitle,
  currentIndex,
  totalPuzzles,
  onBack,
  backLabel = 'Back',
  progress,
  filterStrip,
  activeFilterCount,
  rightContent,
  testId = 'puzzle-set-header',
}: PuzzleSetHeaderProps): VNode {
  // Progress: use explicit value or derive from index
  const progressPct =
    progress ?? (totalPuzzles > 0 ? Math.round(((currentIndex + 1) / totalPuzzles) * 100) : 0);

  // Phase 2: Filters live inside a BottomSheet by default. Flip
  // UI_FILTERS_IN_SHEET to false in services/featureFlags.ts to revert to the
  // legacy inline strip below the header.
  const useSheet = UI_FILTERS_IN_SHEET && filterStrip !== undefined && filterStrip !== null;
  const [filtersOpen, setFiltersOpen] = useState(false);
  const filterCount = activeFilterCount ?? 0;

  return (
    <div data-testid={testId}>
      {/* Main toolbar row */}
      <header className="flex items-center gap-2 bg-[var(--color-bg-elevated)] px-3 py-2 border-b border-[var(--color-panel-border)]">
        {/* Back button */}
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full border-none bg-transparent text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-secondary)] cursor-pointer"
            aria-label={backLabel}
          >
            <ChevronLeftIcon size={16} />
          </button>
        )}

        {/* Title + subtitle */}
        <div className="flex-1 min-w-0">
          <h1 className="m-0 truncate text-sm font-semibold text-[var(--color-text-primary)] leading-tight">
            {title}
          </h1>
          {subtitle && (
            <span className="text-xs text-[var(--color-text-muted)] leading-tight">{subtitle}</span>
          )}
        </div>

        {/* Puzzle counter — hidden under UI_HEADER_DROP_COUNTER (Phase 1 chrome shrink).
         * The same counter is shown inside ProblemNav in the sidebar; duplicating it
         * here just consumed header width without adding information. */}
        {!UI_HEADER_DROP_COUNTER && totalPuzzles > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-bg-secondary)] px-3 py-1 text-xs font-semibold text-[var(--color-text-secondary)] tracking-wide whitespace-nowrap">
            {currentIndex + 1} / {totalPuzzles}
          </span>
        )}

        {/* Phase 2: Filters trigger lives in the toolbar, not below it. */}
        {useSheet && (
          <button
            type="button"
            onClick={() => setFiltersOpen(true)}
            className="filters-trigger"
            aria-label={
              filterCount > 0 ? `Filters, ${filterCount} active` : 'Open filters'
            }
            aria-haspopup="dialog"
            aria-expanded={filtersOpen}
            data-active={filterCount > 0}
            data-testid={`${testId}-filters-trigger`}
          >
            Filters
            {filterCount > 0 && (
              <span className="filters-trigger-count" aria-hidden="true">
                {filterCount}
              </span>
            )}
          </button>
        )}

        {/* Right content slot (stats, badges) */}
        {rightContent}

        {/* Phase 5 (F5): On mobile, AppHeader is hidden when compact, so the
         * settings gear has to live somewhere reachable. Park it at the right
         * of this toolbar, mobile-only. Desktop keeps the gear in AppHeader. */}
        <div className="md:hidden flex items-center" data-testid={`${testId}-mobile-actions`}>
          <SettingsGear />
        </div>
      </header>

      {/* Progress bar — thin strip below header.
       * Phase 4: hidden when UI_HEADER_DROP_PROGRESS_BAR is on; ProblemNav in
       * the sidebar already shows a richer "Solved: X/Y (Z%)" bar. To revert,
       * flip the flag back to false in services/featureFlags.ts. */}
      {!UI_HEADER_DROP_PROGRESS_BAR && totalPuzzles > 0 && (
        <div
          className="h-1 bg-[var(--color-bg-secondary)]"
          role="progressbar"
          aria-valuenow={progressPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Puzzle progress: ${currentIndex + 1} of ${totalPuzzles}`}
          data-testid={`${testId}-progress`}
        >
          <div
            className="h-full rounded-full transition-all duration-300 ease-out"
            style={{
              width: `${progressPct}%`,
              backgroundColor: 'var(--color-accent)',
            }}
          />
        </div>
      )}

      {/* Filter strip — legacy inline rendering when sheet flag is OFF. */}
      {filterStrip && !useSheet && (
        <div
          className="px-3 py-2 bg-[var(--color-bg-elevated)] border-b border-[var(--color-panel-border)] overflow-visible"
          data-testid={`${testId}-filters`}
        >
          {filterStrip}
        </div>
      )}

      {/* Filter strip — sheet rendering. */}
      {useSheet && (
        <BottomSheet
          isOpen={filtersOpen}
          onClose={() => setFiltersOpen(false)}
          title="Filters"
          testId={`${testId}-filters-sheet`}
          footer={
            <button
              type="button"
              onClick={() => setFiltersOpen(false)}
              className="filters-trigger"
              data-active="true"
              data-testid={`${testId}-filters-sheet-done`}
            >
              Done
            </button>
          }
        >
          <div data-testid={`${testId}-filters`}>{filterStrip}</div>
        </BottomSheet>
      )}
    </div>
  );
}

export default PuzzleSetHeader;
