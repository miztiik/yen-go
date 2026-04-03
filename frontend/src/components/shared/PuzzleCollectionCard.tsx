/**
 * PuzzleCollectionCard — shared card component for collection/technique lists.
 * @module components/shared/PuzzleCollectionCard
 *
 * Apple-inspired card with:
 * - Tailwind-only styling (no inline styles)
 * - Theme-aware CSS custom properties
 * - Subtle shadow hover (no translateY)
 * - Keyboard accessible (Enter/Space)
 * - 44px minimum touch target
 *
 * Spec 129, T062 — FR-044, FR-047, FR-064
 */

import type { FunctionalComponent, JSX } from 'preact';
import { useCallback } from 'preact/hooks';
import { ProgressBar } from './ProgressBar';
import { type MasteryLevel, MASTERY_LABELS } from '@/lib/mastery';

// Re-export for backward compatibility
export type { MasteryLevel } from '@/lib/mastery';
export { MASTERY_LABELS, getMasteryFromPercent, getMasteryFromProgress } from '@/lib/mastery';

export interface PuzzleCollectionCardProps {
  /** Card title (e.g., technique name, collection name). */
  title: string;
  /** Optional subtitle (e.g., category, description). */
  subtitle?: string;
  /** Tags to display as pills. */
  tags?: readonly string[];
  /** Progress: completed / total. */
  progress?: { completed: number; total: number };
  /** Mastery level for badge. */
  mastery?: MasteryLevel;
  /** Click handler. */
  onClick?: () => void;
  /** Optional CSS class. */
  className?: string;
  /** Test ID. */
  testId?: string;
  /** When true, card is non-interactive with reduced opacity ("Coming Soon"). */
  disabled?: boolean;
}

// ============================================================================
// Component Helpers
// ============================================================================

/**
 * Mastery badge opacity mapping (single accent color at varying opacities).
 * FR-068: Single color system, not 5 different colors.
 */
const MASTERY_OPACITY: Record<MasteryLevel, string> = {
  new: 'opacity-30',
  started: 'opacity-40',
  learning: 'opacity-50',
  practiced: 'opacity-65',
  proficient: 'opacity-80',
  mastered: 'opacity-100',
};

// ============================================================================
// Component
// ============================================================================

export const PuzzleCollectionCard: FunctionalComponent<PuzzleCollectionCardProps> = ({
  title,
  subtitle,
  tags,
  progress,
  mastery,
  onClick,
  className = '',
  testId,
  disabled = false,
}) => {
  const handleKeyDown = useCallback(
    (e: JSX.TargetedKeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick?.();
      }
    },
    [onClick],
  );

  const hasProgress = progress && progress.total > 0;

  return (
    <div
      role={disabled ? undefined : 'button'}
      tabIndex={!disabled && onClick ? 0 : undefined}
      onClick={disabled ? undefined : onClick}
      onKeyDown={!disabled && onClick ? handleKeyDown : undefined}
      className={`
        rounded-3xl bg-[var(--color-bg-panel)] shadow-md
        border-b-[6px] border-l-0 border-r-0 border-t-0 border-b-[var(--color-accent-border,var(--color-accent))]
        transition-all duration-300 ease-out
        flex flex-col h-full
        ${disabled
          ? 'opacity-45 grayscale-[30%] cursor-not-allowed'
          : 'hover:shadow-xl hover:ring-2 hover:ring-[var(--color-accent)]/30 active:scale-[0.98] cursor-pointer'
        }
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]
        select-none
        min-h-[44px] p-6
        ${className}
      `}
      data-testid={testId}
      aria-label={`${title}${disabled ? ', coming soon' : hasProgress ? `, ${progress.completed} of ${progress.total} solved` : ''}`}
      aria-disabled={disabled || undefined}
    >
      {/* Title row */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="m-0 truncate text-lg font-bold text-[var(--color-text-primary)]">
            {title}
          </h3>
          {subtitle && (
            <p className="m-0 mt-0.5 truncate text-sm text-[var(--color-text-muted)]">
              {subtitle}
            </p>
          )}
        </div>

        {/* Mastery badge — hidden when card is disabled */}
        {mastery && !disabled && (
          <span
            className={`
              inline-flex shrink-0 items-center rounded-full
              px-2.5 py-0.5 text-xs font-medium
              ${mastery === 'new' || mastery === 'started'
                ? 'border border-[var(--color-accent)] bg-transparent text-[var(--color-accent)] opacity-60'
                : `bg-[var(--color-accent)] text-[var(--color-bg-panel)] ${MASTERY_OPACITY[mastery]}`
              }
            `}
          >
            {MASTERY_LABELS[mastery]}
          </span>
        )}
      </div>

      {/* Tags */}
      {tags && tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-[var(--color-bg-secondary)] px-2 py-0.5 text-xs text-[var(--color-text-secondary)]"
            >
              {tag}
            </span>
          ))}
          {tags.length > 3 && (
            <span className="rounded-full bg-[var(--color-bg-secondary)] px-2 py-0.5 text-xs text-[var(--color-text-muted)]">
              +{tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Spacer — pushes progress section to bottom of equal-height cards */}
      <div className="flex-1" />

      {/* Progress bar — uses shared ProgressBar component */}
      {disabled ? (
        <p className="m-0 mt-3 text-xs italic text-[var(--color-text-muted)]">Coming Soon</p>
      ) : hasProgress ? (
        <ProgressBar
          solved={progress.completed}
          total={progress.total}
          className="mt-3"
        />
      ) : progress && progress.total === 0 ? (
        <p className="m-0 mt-3 text-xs italic text-[var(--color-text-muted)]">Ready to begin</p>
      ) : null}
    </div>
  );
};

export default PuzzleCollectionCard;
