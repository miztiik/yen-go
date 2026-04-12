import type { FunctionalComponent, JSX } from 'preact';
import type { TechniqueStats } from '../../models/collection';
import { ProgressBar } from '../shared/ProgressBar';
import { type MasteryLevel, MASTERY_LABELS, getMasteryFromAccuracy } from '@/lib/mastery';
import { TesujiIcon } from '../shared/icons/TesujiIcon';
import { TechniqueKeyIcon } from '../shared/icons/TechniqueKeyIcon';
import { ObjectiveFlagIcon } from '../shared/icons/ObjectiveFlagIcon';

export interface TechniqueInfo {
  id: string;
  name: string;
  category: 'tesuji' | 'technique' | 'objective';
  description: string;
  puzzleCount: number;
}

export interface TechniqueCardProps {
  technique: TechniqueInfo;
  stats: TechniqueStats | undefined;
  onSelect: (techniqueId: string) => void;
}

/** Category display config: SVG icon component + label */
const CATEGORY_CONFIG: Record<string, { icon: JSX.Element; label: string }> = {
  tesuji: { icon: <TesujiIcon size={24} />, label: 'Tesuji' },
  technique: { icon: <TechniqueKeyIcon size={24} />, label: 'Technique' },
  objective: { icon: <ObjectiveFlagIcon size={24} />, label: 'Objective' },
};

/**
 * Accent palette using cascade variable with mode-specific fallback.
 * When data-mode="technique", --color-accent-* cascades set these.
 * Fallback uses technique colors directly for standalone use.
 */
const ACCENT = {
  text: 'var(--color-accent, var(--color-mode-technique-text))',
  light: 'var(--color-accent-light, var(--color-mode-technique-light))',
  bg: 'var(--color-accent-bg, var(--color-mode-technique-bg))',
  border: 'var(--color-accent-border, var(--color-mode-technique-border))',
} as const;

/**
 * Card displaying a single technique with its stats and mastery level.
 *
 * Visual DNA inherited from HomeTile: rounded-3xl, 6px accent bottom border,
 * translateY hover lift, stat badge mastery, category icon circles.
 */
export const TechniqueCard: FunctionalComponent<TechniqueCardProps> = ({
  technique,
  stats,
  onSelect,
}) => {
  const accuracy =
    stats && stats.attempted > 0 ? Math.round((stats.correct / stats.attempted) * 100) : 0;

  // Use accuracy-based mastery from shared lib
  const masteryLevel = getMasteryFromAccuracy(
    accuracy,
    stats?.attempted ?? 0,
    technique.puzzleCount
  );
  const masteryStyle = getMasteryStyle(masteryLevel);
  const category = CATEGORY_CONFIG[technique.category] ?? {
    icon: <TesujiIcon size={24} />,
    label: 'Tesuji',
  };
  const iconCircleClass = getIconCircleClass(masteryLevel);
  const isEmpty = technique.puzzleCount === 0;

  return (
    <button
      type="button"
      onClick={() => !isEmpty && onSelect(technique.id)}
      disabled={isEmpty}
      aria-disabled={isEmpty}
      className={`technique-card flex flex-col rounded-3xl border-b-[6px] border-l-0 border-r-0 border-t-0 border-b-[var(--color-accent-border,var(--color-mode-technique-border))] bg-[var(--color-bg-panel)] p-6 text-left shadow-md transition-all duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] ${isEmpty ? 'cursor-default opacity-45 grayscale-[30%]' : 'cursor-pointer hover:-translate-y-1 hover:shadow-xl active:scale-[0.98]'}`}
    >
      {/* Header: title + category icon */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          {/* Mastery stat badge — hidden when disabled/empty */}
          {!isEmpty && (
            <span
              className="mb-2 inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[0.6875rem] font-bold uppercase tracking-wider"
              style={masteryStyle}
            >
              {MASTERY_LABELS[masteryLevel]}
            </span>
          )}
          <h3 className="m-0 text-lg font-bold leading-tight text-[var(--color-text-primary)]">
            {technique.name}
          </h3>
        </div>

        {/* Category icon in colored circle — visual state changes with mastery */}
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-xl transition-all duration-300 ${iconCircleClass}`}
          aria-label={category.label}
        >
          {category.icon}
        </div>
      </div>

      {/* Description */}
      <p className="m-0 mt-2 text-sm font-medium leading-relaxed text-[var(--color-text-muted)]">
        {technique.description}
      </p>

      {/* Stats row + progress */}
      <div className="mt-auto pt-4">
        {/* Puzzle count badge — same visual as HomeTile tags */}
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center rounded-lg bg-[var(--color-bg-secondary)] px-3 py-1.5 text-xs font-bold text-[var(--color-text-secondary)]">
            {technique.puzzleCount} {technique.puzzleCount === 1 ? 'puzzle' : 'puzzles'}
          </span>

          {stats && stats.attempted > 0 && (
            <>
              <span className="text-xs font-semibold text-[var(--color-text-muted)]">
                {stats.attempted} solved
              </span>
              <span
                className={`text-xs font-bold ${
                  accuracy >= 70
                    ? 'text-[var(--color-success)]'
                    : accuracy >= 50
                      ? 'text-[var(--color-warning)]'
                      : 'text-[var(--color-error)]'
                }`}
              >
                {accuracy}%
              </span>
            </>
          )}
        </div>

        {/* Progress bar — shared ProgressBar component */}
        <ProgressBar
          solved={stats?.attempted ?? 0}
          total={technique.puzzleCount}
          mode="technique"
          className="mt-3"
        />
      </div>
    </button>
  );
};

/**
 * Mastery badge styles using the accent color palette — same visual treatment
 * as HomeTile stat badges. Uses cascade vars with mode-specific fallbacks.
 * 'Begin' uses outline/ghost style; others use filled style.
 */
function getMasteryStyle(level: MasteryLevel): JSX.CSSProperties {
  switch (level) {
    case 'new':
    case 'started':
      return {
        backgroundColor: 'transparent',
        color: ACCENT.text,
        border: `1px solid ${ACCENT.border}`,
      };
    case 'learning':
      return {
        backgroundColor: ACCENT.bg,
        color: ACCENT.text,
      };
    case 'practiced':
      return {
        backgroundColor: ACCENT.border,
        color: 'var(--color-bg-panel)',
      };
    case 'proficient':
      return {
        backgroundColor: ACCENT.text,
        color: 'var(--color-bg-panel)',
      };
    case 'mastered':
      return {
        backgroundColor: ACCENT.text,
        color: 'var(--color-bg-panel)',
      };
  }
}

/**
 * Icon circle visual treatment based on mastery state.
 * Unstarted: muted opacity. In-progress: normal. Proficient+: accent ring.
 */
function getIconCircleClass(level: MasteryLevel): string {
  switch (level) {
    case 'new':
      return 'bg-[var(--color-accent-light,var(--color-mode-technique-light))] opacity-50';
    case 'started':
    case 'learning':
    case 'practiced':
      return 'bg-[var(--color-accent-light,var(--color-mode-technique-light))]';
    case 'proficient':
    case 'mastered':
      return 'bg-[var(--color-accent-light,var(--color-mode-technique-light))] ring-2 ring-[var(--color-accent)]';
  }
}

export default TechniqueCard;
