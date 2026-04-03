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
import { ChevronLeftIcon } from '../shared/icons';

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
  rightContent,
  testId = 'puzzle-set-header',
}: PuzzleSetHeaderProps): VNode {
  // Progress: use explicit value or derive from index
  const progressPct = progress ?? (totalPuzzles > 0 ? Math.round(((currentIndex + 1) / totalPuzzles) * 100) : 0);

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

        {/* Puzzle counter */}
        {totalPuzzles > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-bg-secondary)] px-3 py-1 text-xs font-semibold text-[var(--color-text-secondary)] tracking-wide whitespace-nowrap">
            {currentIndex + 1} / {totalPuzzles}
          </span>
        )}

        {/* Right content slot (stats, badges) */}
        {rightContent}
      </header>

      {/* Progress bar — thin strip below header */}
      {totalPuzzles > 0 && (
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

      {/* Filter strip (optional) */}
      {filterStrip && (
        <div
          className="px-3 py-2 bg-[var(--color-bg-elevated)] border-b border-[var(--color-panel-border)] overflow-visible"
          data-testid={`${testId}-filters`}
        >
          {filterStrip}
        </div>
      )}
    </div>
  );
}

export default PuzzleSetHeader;
