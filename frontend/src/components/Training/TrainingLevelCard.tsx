/**
 * TrainingLevelCard — Rich per-level card for the Training page.
 * @module components/Training/TrainingLevelCard
 *
 * Grid mode: accent left-border, level number, name, rank range, progress bar.
 *   - Equal height via min-h + flex fill for consistent grid alignment.
 *   - DAN levels get a small inline badge (not a floating ribbon).
 *   - Expert card gets dark bg + gold accents.
 * List mode: compact single-row with number, title, rank, progress bar.
 *
 * Spec 132, Phase 12 — Training Page Redesign
 */

import type { FunctionalComponent, JSX } from 'preact';
import { LEVELS } from '../../lib/levels/config';
import type { ViewMode } from './ViewToggle';

export interface TrainingLevelCardProps {
  /** 1-based ordinal index (e.g., 1 for Novice) */
  index: number;
  /** Level slug (e.g., "novice", "low-dan") */
  slug: string;
  /** Display name (e.g., "Novice") */
  name: string;
  /** Short rank label (e.g., "30k") */
  shortName: string;
  /** Rank range (e.g., { min: "30k", max: "26k" }) */
  rankRange: { min: string; max: string };
  /** Level description */
  description: string;
  /** Progress data */
  progress: { completed: number; total: number };
  /** View mode */
  viewMode: ViewMode;
  /** Click handler */
  onClick: () => void;
  /** Test ID */
  testId?: string;
}

/** Levels that show a DAN badge — derived from config (ID >= 210 = dan levels) */
const DAN_LEVELS = new Set<string>(LEVELS.filter((l) => l.id >= 210).map((l) => l.slug));

/** Expert level gets special dark treatment — last level in config */
const isExpert = (slug: string): boolean => slug === LEVELS[LEVELS.length - 1]!.slug;

/**
 * Per-level color mapping using existing CSS var tokens.
 */
function getLevelColors(slug: string): {
  primary: string;
  bg: string;
  text: string;
  border: string;
} {
  return {
    primary: `var(--color-level-${slug})`,
    bg: `var(--color-level-${slug}-bg)`,
    text: `var(--color-level-${slug}-text)`,
    border: `var(--color-level-${slug}-border)`,
  };
}

// ============================================================================
// Grid Card
// ============================================================================

function GridCard({
  index,
  slug,
  name,
  rankRange,
  description,
  progress,
  onClick,
  testId,
}: TrainingLevelCardProps): JSX.Element {
  const colors = getLevelColors(slug);
  const pct = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;
  const hasDan = DAN_LEVELS.has(slug);
  const expert = isExpert(slug);

  return (
    <button
      type="button"
      onClick={onClick}
      className={`group relative flex w-full h-full min-h-[200px] cursor-pointer flex-col overflow-hidden rounded-3xl text-left transition-all duration-300 hover:-translate-y-1 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] ${
        expert
          ? 'bg-[var(--color-neutral-800)] shadow-[var(--shadow-xl)]'
          : 'bg-[var(--color-card-bg)] shadow-[var(--shadow-md)] hover:shadow-[var(--shadow-xl)]'
      }`}
      style={{
        borderBottom: `6px solid ${expert ? colors.primary : colors.primary}`,
      }}
      data-testid={testId}
    >
      {/* Card content */}
      <div className="flex flex-1 flex-col p-5">
        {/* Top row: level number + name + DAN badge */}
        <div className="flex items-baseline gap-2">
          {/* Level number */}
          <span
            className="text-2xl font-extrabold leading-none"
            style={{ color: expert ? colors.primary : colors.primary }}
          >
            {index}
          </span>
          <h3
            className={`m-0 text-lg font-bold leading-tight ${
              expert ? 'text-white' : 'text-[var(--color-text-primary)]'
            }`}
          >
            {name}
          </h3>
          {hasDan && (
            <span
              className="ml-auto rounded-full px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider"
              style={{
                backgroundColor: expert
                  ? `color-mix(in srgb, ${colors.primary} 20%, transparent)`
                  : `color-mix(in srgb, ${colors.primary} 15%, transparent)`,
                color: expert ? colors.primary : colors.primary,
              }}
            >
              DAN
            </span>
          )}
        </div>

        {/* Rank range */}
        <p
          className="m-0 mt-1 text-xs font-bold"
          style={{ color: expert ? colors.primary : colors.primary }}
        >
          {rankRange.min} – {rankRange.max}
        </p>

        {/* Description */}
        <p
          className={`m-0 mt-2 text-sm leading-relaxed line-clamp-2 ${
            expert ? 'text-[var(--color-neutral-400)]' : 'text-[var(--color-text-muted)]'
          }`}
        >
          {description}
        </p>

        {/* Spacer to push progress to bottom */}
        <div className="flex-1" />

        {/* Progress bar + stats */}
        <div className="mt-4">
          <div
            className="h-2 w-full overflow-hidden rounded-full"
            style={{
              backgroundColor: expert ? 'var(--color-neutral-700)' : 'var(--color-bg-secondary)',
            }}
          >
            <div
              className="h-2 rounded-full transition-[width] duration-500"
              style={{
                width: `${pct}%`,
                backgroundColor: expert ? colors.primary : colors.primary,
              }}
            />
          </div>
          <div
            className={`mt-1.5 flex items-center justify-between text-xs font-medium ${
              expert ? 'text-[var(--color-neutral-500)]' : 'text-[var(--color-text-muted)]'
            }`}
          >
            <span>
              {pct >= 100 ? 'Completed' : progress.completed > 0 ? 'In progress' : 'Ready to begin'}
            </span>
            <span style={{ color: expert ? colors.primary : colors.primary }}>{pct}%</span>
          </div>
        </div>
      </div>
    </button>
  );
}

// ============================================================================
// List Card
// ============================================================================

function ListCard({
  index,
  slug,
  name,
  rankRange,
  progress,
  onClick,
  testId,
}: TrainingLevelCardProps): JSX.Element {
  const colors = getLevelColors(slug);
  const pct = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;
  const expert = isExpert(slug);
  const hasDan = DAN_LEVELS.has(slug);

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full cursor-pointer items-center gap-3 rounded-2xl px-4 py-3.5 text-left transition-all duration-300 hover:shadow-[var(--shadow-md)] active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] ${
        expert
          ? 'bg-[var(--color-neutral-800)] shadow-[var(--shadow-md)]'
          : 'bg-[var(--color-card-bg)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-lg)]'
      }`}
      style={{
        borderBottom: `4px solid ${expert ? colors.primary : colors.primary}`,
      }}
      data-testid={testId}
    >
      {/* Level number */}
      <span
        className="w-6 shrink-0 text-center text-lg font-extrabold"
        style={{ color: expert ? colors.primary : colors.primary }}
      >
        {index}
      </span>

      {/* Title + rank range */}
      <div className="flex-1 min-w-0">
        <span
          className={`text-sm font-bold ${expert ? 'text-white' : 'text-[var(--color-text-primary)]'}`}
        >
          {name}
        </span>
        {hasDan && (
          <span
            className="ml-1.5 rounded-full px-1.5 py-0.5 text-[9px] font-extrabold uppercase tracking-wider"
            style={{
              backgroundColor: expert
                ? `color-mix(in srgb, ${colors.primary} 20%, transparent)`
                : `color-mix(in srgb, ${colors.primary} 15%, transparent)`,
              color: expert ? colors.primary : colors.primary,
            }}
          >
            DAN
          </span>
        )}
        <span
          className="ml-2 text-xs font-medium"
          style={{ color: expert ? colors.primary : colors.primary }}
        >
          {rankRange.min} – {rankRange.max}
        </span>
      </div>

      {/* Mini progress bar */}
      <div className="w-24 shrink-0">
        <div
          className="h-1.5 w-full overflow-hidden rounded-full"
          style={{
            backgroundColor: expert ? 'var(--color-neutral-700)' : 'var(--color-bg-secondary)',
          }}
        >
          <div
            className="h-1.5 rounded-full"
            style={{
              width: `${pct}%`,
              backgroundColor: expert ? colors.primary : colors.primary,
            }}
          />
        </div>
      </div>

      {/* Percentage */}
      <span
        className="w-10 text-right text-xs font-bold"
        style={{ color: expert ? colors.primary : colors.primary }}
      >
        {pct}%
      </span>
    </button>
  );
}

// ============================================================================
// Exported Component
// ============================================================================

/**
 * TrainingLevelCard — renders grid or list mode based on viewMode prop.
 */
export const TrainingLevelCard: FunctionalComponent<TrainingLevelCardProps> = (props) => {
  if (props.viewMode === 'list') {
    return <ListCard {...props} />;
  }
  return <GridCard {...props} />;
};

export default TrainingLevelCard;
