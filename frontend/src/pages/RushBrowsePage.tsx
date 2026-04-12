/**
 * RushBrowsePage — Full-page Puzzle Rush browse experience.
 * @module pages/RushBrowsePage
 *
 * Shows duration cards (3/5/10 min), level + tag filters with
 * cascading counts from master indexes, available puzzle estimate,
 * personal best, and session rules.
 *
 * Follows technique layout pattern: PageHeader + content grid.
 * Accent: Rose (#f43f5e), mode="rush".
 *
 * Phase R1 — Rush Play Enhancement
 */

import type { FunctionalComponent } from 'preact';
import { useState, useMemo, useCallback } from 'preact/hooks';
import { PageLayout } from '@/components/Layout/PageLayout';
import { PageHeader } from '@/components/shared/PageHeader';
import { FilterBar } from '@/components/shared/FilterBar';
import { FilterDropdown } from '@/components/shared/FilterDropdown';
import { LightningIcon } from '@/components/shared/icons';
import { useCanonicalUrl } from '@/hooks/useCanonicalUrl';
import { useMasterIndexes } from '@/hooks/useMasterIndexes';
import { getAllLevels, getOrderedTagCategories, getTagsByCategory } from '@/services/configService';
import type { RushDuration } from '@/types/goban';

// ============================================================================
// Types
// ============================================================================

export interface RushBrowsePageProps {
  /** Called when user selects a duration and starts the rush */
  onStartRush: (duration: RushDuration, levelId: number | null, tagId: number | null) => void;
  /** Called when user goes back home */
  onNavigateHome: () => void;
  /** Current best score */
  bestScore?: number | null;
}

// ============================================================================
// Constants
// ============================================================================

const ACCENT = {
  text: 'var(--color-accent, var(--color-mode-rush-text))',
  light: 'var(--color-accent-light, var(--color-mode-rush-light))',
  bg: 'var(--color-accent-bg, var(--color-mode-rush-bg))',
  border: 'var(--color-accent-border, var(--color-mode-rush-border))',
} as const;

interface DurationOption {
  minutes: number;
  seconds: number;
  label: string;
  description: string;
}

const DURATION_OPTIONS: DurationOption[] = [
  {
    minutes: 3,
    seconds: 180,
    label: '3 Minutes',
    description: 'Quick sprint — perfect for warm-ups',
  },
  {
    minutes: 5,
    seconds: 300,
    label: '5 Minutes',
    description: 'The classic challenge — balanced pace',
  },
  {
    minutes: 10,
    seconds: 600,
    label: '10 Minutes',
    description: 'Marathon mode — test your endurance',
  },
];

/** Valid custom duration steps in seconds.
 * 30-second steps from 1:00 to 5:00, then 60-second steps from 6:00 to 30:00.
 */
const CUSTOM_DURATION_STEPS: number[] = (() => {
  const steps: number[] = [];
  for (let s = 60; s <= 300; s += 30) steps.push(s);
  for (let s = 360; s <= 1800; s += 60) steps.push(s);
  return steps;
})();

/** Format seconds as human-readable duration (e.g., "7:30" or "12:00"). */
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${mins}:${secs.toString().padStart(2, '0')}` : `${mins}:00`;
}

/** Minimum puzzle count before showing low-count warning. */
const LOW_PUZZLE_THRESHOLD = 20;

// ============================================================================
// Component
// ============================================================================

export const RushBrowsePage: FunctionalComponent<RushBrowsePageProps> = ({
  onStartRush,
  onNavigateHome,
  bestScore,
}) => {
  // P3: URL-synced filter state
  const { filters, setFilters, clearFilters } = useCanonicalUrl();
  const filterLevelIds = filters.l ?? [];
  const filterTagIds = filters.t ?? [];
  // Wire masterLoaded to real SQLite puzzle-count data (T14)
  const { levelMasterEntries, isLoading: masterLoading } = useMasterIndexes();
  const masterLoaded = !masterLoading && levelMasterEntries.length > 0;

  // Build filter options from config (enriched with puzzle counts from SQLite)
  const allLevels = getAllLevels();
  const totalCount = levelMasterEntries.reduce((sum, e) => sum + e.count, 0);
  const filterState = {
    levelId: filterLevelIds.length === 1 ? filterLevelIds[0]! : null,
    tagId: filterTagIds.length === 1 ? filterTagIds[0]! : null,
    levelOptions: [
      { id: 'all', label: 'All', count: masterLoaded ? totalCount : undefined } as {
        id: string;
        label: string;
        count?: number;
        tooltip?: string;
      },
      ...allLevels.map((l) => {
        const masterEntry = levelMasterEntries.find((e) => e.id === l.id);
        return {
          id: String(l.id),
          label: l.name,
          count: masterEntry?.count,
          tooltip: `${l.name} (${l.rankRange.min}\u2013${l.rankRange.max})`,
        } as { id: string; label: string; count?: number; tooltip?: string };
      }),
    ],
    tagOptionGroups: getOrderedTagCategories().map((cat) => ({
      label: cat.label,
      options: getTagsByCategory(cat.key).map((t) => ({
        id: String(t.id),
        label: t.name,
      })),
    })),
    setLevelFromOption: (id: string | null) => {
      if (id === null || id === '' || id === 'all') {
        setFilters({ l: [] });
        return;
      }
      const n = Number(id);
      if (!Number.isNaN(n)) setFilters({ l: [n] });
    },
    setTagFromOption: (id: string | null) => {
      if (id === null || id === '') {
        setFilters({ t: [] });
        return;
      }
      const n = Number(id);
      if (!Number.isNaN(n)) setFilters({ t: [n] });
    },
    hasActiveFilters: filterLevelIds.length > 0 || filterTagIds.length > 0,
    clearAll: clearFilters,
  };

  // ── Available puzzle count (intersection estimate) ─────────────────
  const availableCount = useMemo(() => {
    if (!masterLoaded) return null;
    if (filterState.levelId !== null) {
      const opt = filterState.levelOptions.find((o) => o.id === String(filterState.levelId));
      return opt?.count ?? 0;
    }
    // No level selected — "All" count (cascaded by tag selection)
    return filterState.levelOptions[0]?.count ?? 0;
  }, [masterLoaded, filterState.levelId, filterState.levelOptions]);

  const isLowCount =
    availableCount !== null && availableCount < LOW_PUZZLE_THRESHOLD && availableCount > 0;
  const isZeroCount = availableCount === 0;

  // ── Custom duration state ──────────────────────────────────────────
  const [showCustomSlider, setShowCustomSlider] = useState(false);
  const [customSliderIndex, setCustomSliderIndex] = useState(
    CUSTOM_DURATION_STEPS.indexOf(420) // default 7 min
  );
  const customSeconds = CUSTOM_DURATION_STEPS[customSliderIndex] ?? 420;

  // ── Stats for header ───────────────────────────────────────────────
  const stats = useMemo(() => {
    const items = [];
    if (bestScore && bestScore > 0) {
      items.push({ label: 'Best Score', value: bestScore });
    }
    return items;
  }, [bestScore]);

  // ── Handlers ───────────────────────────────────────────────────────
  const handleDurationClick = useCallback(
    (duration: number) => {
      setShowCustomSlider(false);
      onStartRush(duration, filterState.levelId, filterState.tagId);
    },
    [onStartRush, filterState.levelId, filterState.tagId]
  );

  const handleCustomToggle = useCallback(() => {
    setShowCustomSlider((prev) => !prev);
  }, []);

  const handleCustomStart = useCallback(() => {
    onStartRush(customSeconds, filterState.levelId, filterState.tagId);
  }, [onStartRush, customSeconds, filterState.levelId, filterState.tagId]);

  return (
    <PageLayout variant="single-column" mode="rush">
      <PageLayout.Content>
        {/* Header — technique layout pattern */}
        <PageHeader
          title="Puzzle Rush"
          subtitle="Solve as many puzzles as you can before time runs out"
          icon={<LightningIcon size={36} />}
          stats={stats}
          onBack={onNavigateHome}
          accent={ACCENT}
          testId="rush-header"
        />

        {/* Accent divider */}
        <div className="h-[3px]" style={{ backgroundColor: ACCENT.border }} />

        {/* Content */}
        <div className="mx-auto w-full max-w-5xl flex-1 p-4">
          {/* ── Duration cards ─────────────────────────────────────── */}
          <h2 className="m-0 mb-4 text-sm font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
            Choose Your Duration
          </h2>

          <div className="grid gap-4 grid-cols-1 md:grid-cols-3">
            {DURATION_OPTIONS.map((option) => (
              <button
                key={option.minutes}
                type="button"
                onClick={() => handleDurationClick(option.seconds)}
                disabled={isZeroCount}
                className="flex cursor-pointer flex-col gap-3 rounded-3xl border-b-[6px] border-l-0 border-r-0 border-t-0 bg-[var(--color-bg-panel)] p-6 text-left shadow-md transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-xl active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-md"
                style={{ borderBottomColor: ACCENT.border }}
                data-testid={`rush-duration-${option.minutes}`}
                role="button"
              >
                {/* Duration display */}
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl"
                    style={{ backgroundColor: ACCENT.bg }}
                  >
                    <span className="text-2xl font-extrabold" style={{ color: ACCENT.text }}>
                      {option.minutes}
                    </span>
                  </div>
                  <div>
                    <h3 className="m-0 text-lg font-bold text-[var(--color-text-primary)]">
                      {option.label}
                    </h3>
                    <p className="m-0 mt-0.5 text-sm text-[var(--color-text-muted)]">
                      {option.description}
                    </p>
                  </div>
                </div>

                {/* Play indicator */}
                <span
                  className="self-end rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider"
                  style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
                >
                  Play
                </span>
              </button>
            ))}
          </div>

          {/* ── Custom Duration ───────────────────────────────────── */}
          <div className="mt-4">
            <button
              type="button"
              onClick={handleCustomToggle}
              disabled={isZeroCount}
              className="flex w-full cursor-pointer items-center justify-between rounded-2xl border-2 bg-[var(--color-bg-panel)] px-6 py-4 text-left shadow-sm transition-all duration-200 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                borderColor: showCustomSlider
                  ? 'var(--color-accent, var(--color-mode-rush-border))'
                  : 'var(--color-border, #d4c9b8)',
              }}
              data-testid="rush-duration-custom"
            >
              <div>
                <h3 className="m-0 text-base font-bold text-[var(--color-text-primary)]">
                  Custom Duration
                </h3>
                <p className="m-0 mt-0.5 text-sm text-[var(--color-text-muted)]">
                  Set your own time (1–30 min)
                </p>
              </div>
              <span
                className="rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider"
                style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
              >
                {showCustomSlider ? formatDuration(customSeconds) : 'Custom'}
              </span>
            </button>

            {/* Slider (visible when custom selected) */}
            {showCustomSlider && (
              <div
                className="mt-3 rounded-xl bg-[var(--color-bg-elevated)] p-6"
                data-testid="rush-custom-slider"
              >
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-sm font-semibold text-[var(--color-text-secondary)]">
                    Duration
                  </span>
                  <span
                    className="text-2xl font-extrabold"
                    style={{ color: ACCENT.text }}
                    data-testid="rush-custom-value"
                  >
                    {formatDuration(customSeconds)}
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={CUSTOM_DURATION_STEPS.length - 1}
                  value={customSliderIndex}
                  onInput={(e) =>
                    setCustomSliderIndex(Number((e.target as HTMLInputElement).value))
                  }
                  className="w-full accent-[var(--color-accent)]"
                  style={{ height: '44px' }}
                  aria-label="Custom duration slider"
                  aria-valuemin={1}
                  aria-valuemax={30}
                  aria-valuenow={Math.round(customSeconds / 60)}
                  aria-valuetext={formatDuration(customSeconds)}
                  data-testid="rush-custom-range"
                />
                <div className="mt-1 flex justify-between text-xs text-[var(--color-text-muted)]">
                  <span>1 min</span>
                  <span>5 min</span>
                  <span>15 min</span>
                  <span>30 min</span>
                </div>
                <button
                  type="button"
                  onClick={handleCustomStart}
                  disabled={isZeroCount}
                  className="mt-4 w-full min-h-[48px] cursor-pointer rounded-xl border-none px-6 py-3 text-base font-bold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  style={{
                    backgroundColor: 'var(--color-accent, var(--color-mode-rush-text))',
                    color: 'var(--color-bg-panel, #fff)',
                  }}
                  data-testid="rush-custom-start"
                >
                  Start Rush — {formatDuration(customSeconds)}
                </button>
              </div>
            )}
          </div>

          {/* ── Filter section ────────────────────────────────────── */}
          {masterLoaded && (
            <div
              className="mt-8 rounded-xl bg-[var(--color-bg-elevated)] p-6"
              data-testid="rush-filters"
            >
              <h2 className="m-0 mb-1 text-sm font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                Customize Your Challenge
              </h2>
              <p className="m-0 mb-4 text-xs text-[var(--color-text-muted)]">
                Optional — defaults to all levels and techniques
              </p>

              {/* Level filter (pill bar) */}
              <div className="mb-4">
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                  Difficulty Level
                </label>
                <FilterBar
                  label="Filter by difficulty level"
                  options={filterState.levelOptions}
                  selected={filterState.levelId !== null ? String(filterState.levelId) : 'all'}
                  onChange={filterState.setLevelFromOption}
                  testId="rush-level-filter"
                />
              </div>

              {/* Tag filter (dropdown) */}
              <div className="mb-4">
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                  Technique
                </label>
                <FilterDropdown
                  label="Filter by technique"
                  placeholder="All Techniques"
                  groups={filterState.tagOptionGroups}
                  selected={filterState.tagId !== null ? String(filterState.tagId) : null}
                  onChange={filterState.setTagFromOption}
                  testId="rush-tag-filter"
                />
              </div>

              {/* Available puzzle count */}
              {availableCount !== null && (
                <div className="mt-3" data-testid="rush-available-count">
                  {isZeroCount ? (
                    <p className="m-0 text-sm font-medium text-[var(--color-error)]">
                      No puzzles match your filters — try broadening your selection
                    </p>
                  ) : isLowCount ? (
                    <p
                      className="m-0 text-sm font-medium"
                      style={{ color: 'var(--color-warning, #d97706)' }}
                    >
                      ~{availableCount.toLocaleString()} puzzles available — consider broadening
                      filters for a better experience
                    </p>
                  ) : (
                    <p className="m-0 text-sm text-[var(--color-text-muted)]">
                      ~{availableCount.toLocaleString()} puzzles available
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Rules reminder ────────────────────────────────────── */}
          <div className="mt-8 rounded-xl bg-[var(--color-bg-elevated)] p-6">
            <h3 className="m-0 mb-3 text-sm font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
              How It Works
            </h3>
            <ul className="m-0 list-none space-y-2 p-0 text-sm text-[var(--color-text-secondary)]">
              <li className="flex items-center gap-2">
                <span
                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                  style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
                >
                  1
                </span>
                Puzzles are served one after another — solve as many as you can
              </li>
              <li className="flex items-center gap-2">
                <span
                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                  style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
                >
                  2
                </span>
                Each wrong answer costs a life — 3 lives total
              </li>
              <li className="flex items-center gap-2">
                <span
                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                  style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
                >
                  3
                </span>
                Build streaks for bonus points — consecutive correct answers multiply your score
              </li>
            </ul>
          </div>
        </div>
      </PageLayout.Content>
    </PageLayout>
  );
};

export default RushBrowsePage;
