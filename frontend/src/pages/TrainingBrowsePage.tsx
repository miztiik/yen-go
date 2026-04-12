/**
 * TrainingBrowsePage — Level-based training browser (redesigned).
 * @module pages/TrainingBrowsePage
 *
 * Standardized layout using shared PuzzleCollectionCard:
 * - Left-aligned PageHeader with icon circle + title + stat badges
 * - Accent-bordered filter bar with tag dropdown
 * - PuzzleCollectionCard grid (same component as Collections/Techniques)
 * - Real puzzle counts from database; empty levels grayed out
 * - No level locking — all levels always open
 * - Visible Random Challenge button at bottom
 * - Responsive grid: 1 col mobile, 2 col tablet, 3 col desktop
 */

import type { FunctionalComponent } from 'preact';
import { useState, useEffect, useMemo, useCallback } from 'preact/hooks';
import { SKILL_LEVELS, type SkillLevel } from '@/models/collection';
import { FIRST_LEVEL } from '@/lib/levels/level-defaults';
import { getLevelCategory } from '@/lib/levels/categories';
import { PageLayout } from '@/components/Layout/PageLayout';
import { FilterBar, type FilterOption } from '@/components/shared/FilterBar';
import { FilterDropdown } from '@/components/shared/FilterDropdown';
import { ActiveFilterChip } from '@/components/shared/ActiveFilterChip';
import { EmptyFilterState } from '@/components/shared/EmptyFilterState';
import { EmptyState } from '@/components/shared/GoQuote';
import { GraduationCapIcon } from '@/components/shared/icons';
import { PuzzleCollectionCard } from '@/components/shared/PuzzleCollectionCard';
import { type MasteryLevel, getMasteryFromProgress } from '@/lib/mastery';
import { getAccentPalette } from '@/lib/accent-palette';
import { useCanonicalUrl } from '@/hooks/useCanonicalUrl';
import { useBrowseParams } from '@/hooks/useBrowseParams';
import { init as initDb } from '@/services/sqliteService';
import { getLevelCounts, getTagCounts, getFilterCounts } from '@/services/puzzleQueryService';
import {
  getOrderedTagCategories,
  getTagsByCategory,
  tagIdToSlug,
  getTagMeta,
  levelIdToSlug,
  levelSlugToId,
} from '@/services/configService';
import { buildDepthPresetOptions, depthPresetToRange } from '@/hooks/usePuzzleFilters';

// ============================================================================
// Types
// ============================================================================

export interface TrainingBrowsePageProps {
  /** Called when user selects a level to train. */
  onSelectLevel: (level: SkillLevel) => void;
  /** Called when user goes back home. */
  onNavigateHome: () => void;
  /** Called when user clicks Random Challenge button. */
  onNavigateRandom?: () => void;
}

interface TrainingProgress {
  byLevel: Record<string, { completed: number; total: number; accuracy: number }>;
  unlockedLevels: string[];
}

// ============================================================================
// Constants
// ============================================================================

const TRAINING_PROGRESS_KEY = 'yen-go-training-progress';

/** Accent palette — PURSIG Finding 12: shared utility */
const ACCENT = getAccentPalette('training');

const CATEGORY_OPTIONS: FilterOption[] = [
  { id: 'all', label: 'All Levels' },
  { id: 'beginner', label: 'Beginner (30k\u201310k)' },
  { id: 'intermediate', label: 'Intermediate (9k\u20131k)' },
  { id: 'advanced', label: 'Advanced (1d+)' },
];

// ============================================================================
// Helpers
// ============================================================================

function loadTrainingProgress(): TrainingProgress {
  try {
    const stored = localStorage.getItem(TRAINING_PROGRESS_KEY);
    if (stored) {
      return JSON.parse(stored) as TrainingProgress;
    }
  } catch {
    // Ignore parse errors
  }
  return { byLevel: {}, unlockedLevels: [FIRST_LEVEL] };
}

/**
 * Compute mastery level using accuracy-based calculation.
 * Uses shared getMasteryFromProgress from lib/mastery.
 */
function getLocalMastery(
  levelProgress: { completed: number; total: number; accuracy?: number } | undefined,
  snapshotTotal: number
): MasteryLevel {
  if (!levelProgress || snapshotTotal === 0) return 'new';
  return getMasteryFromProgress({
    completed: levelProgress.completed,
    total: snapshotTotal,
    accuracy: levelProgress.accuracy,
  });
}

// ============================================================================
// Component
// ============================================================================

export const TrainingBrowsePage: FunctionalComponent<TrainingBrowsePageProps> = ({
  onSelectLevel,
  onNavigateHome,
  onNavigateRandom,
}) => {
  const [progress, setProgress] = useState<TrainingProgress>({
    byLevel: {},
    unlockedLevels: [FIRST_LEVEL],
  });
  const { params: browseParams, setParam } = useBrowseParams({ cat: 'all' });
  const categoryFilter = browseParams.cat;

  // P3: URL-synced filter state
  const { filters, setFilters, clearFilters } = useCanonicalUrl();
  const filterTagIds = filters.t ?? [];
  const depthPreset = filters.dp ?? null;

  // Load level/tag counts from SQLite database
  const [dbReady, setDbReady] = useState(false);
  const [levelCounts, setLevelCountsData] = useState<Record<number, number>>({});
  const [hasTagData, setHasTagData] = useState(false);

  useEffect(() => {
    void initDb().then(() => {
      setLevelCountsData(getLevelCounts());
      setHasTagData(Object.keys(getTagCounts()).length > 0);
      setDbReady(true);
    });
  }, []);

  // Bridge filter state for the existing template code
  const filterState = {
    tagId: filterTagIds.length === 1 ? filterTagIds[0]! : null,
    tagOptionGroups: getOrderedTagCategories().map((cat) => ({
      label: cat.label,
      options: getTagsByCategory(cat.key).map((t) => ({
        id: String(t.id),
        label: t.name,
      })),
    })),
    setTagFromOption: (id: string | null) => {
      if (id === null || id === '') {
        setFilters({ t: [] });
        return;
      }
      const n = Number(id);
      if (!Number.isNaN(n)) setFilters({ t: [n] });
    },
    setTag: (id: number | null) => setFilters({ t: id === null ? [] : [id] }),
    selectedTagSlug: filterTagIds.length === 1 ? tagIdToSlug(filterTagIds[0]!) : null,
    selectedTagLabel:
      filterTagIds.length === 1 ? (getTagMeta(tagIdToSlug(filterTagIds[0]!))?.name ?? null) : null,
    hasActiveFilters: filterTagIds.length > 0,
    clearAll: clearFilters,
  };

  // Load progress on mount
  useEffect(() => {
    const loaded = loadTrainingProgress();
    setProgress(loaded);
  }, []);

  // Build slug → SQLite puzzle count map from level counts
  const levelCountMap = useMemo(() => {
    const map: Record<string, number> = {};
    for (const [idStr, count] of Object.entries(levelCounts)) {
      const slug = levelIdToSlug(Number(idStr));
      if (slug) map[slug] = count;
    }
    return map;
  }, [levelCounts]);

  // Depth preset options from cross-filtered counts
  const depthPresetOptions = useMemo(() => {
    if (!dbReady) return [];
    const depthRange = depthPresetToRange(depthPreset);
    const tagFilter = filterState.tagId !== null ? { tagIds: [filterState.tagId] } : {};
    const counts = getFilterCounts({
      ...tagFilter,
      ...depthRange,
    });
    return buildDepthPresetOptions(counts.depthPresets ?? {});
  }, [dbReady, depthPreset, filterState.tagId]);

  const handleDepthPresetChange = useCallback(
    (id: string) => {
      const newDp = id === depthPreset ? undefined : id;
      if (newDp !== undefined) setFilters({ dp: newDp });
      else setFilters({});
    },
    [depthPreset, setFilters]
  );

  // Filter levels by category
  const filteredLevels = useMemo(() => {
    let levels =
      categoryFilter === 'all'
        ? SKILL_LEVELS
        : SKILL_LEVELS.filter((level) => getLevelCategory(level.slug) === categoryFilter);

    // WP8 §8.3: When a tag or depth preset is selected, filter out levels with 0 matching puzzles
    if (dbReady && (filterState.tagId !== null || depthPreset)) {
      const depthRange = depthPresetToRange(depthPreset);
      const tagFilter2 = filterState.tagId !== null ? { tagIds: [filterState.tagId] } : {};
      const filtered = getFilterCounts({
        ...tagFilter2,
        ...depthRange,
      });
      levels = levels.filter((level) => {
        const id = levelSlugToId(level.slug);
        if (id === undefined) return false;
        return (filtered.levels[id] ?? 0) > 0;
      });
    }

    return levels;
  }, [categoryFilter, filterState.tagId, depthPreset, dbReady]);

  // WP8: Handle tag filter change (PURSIG Finding 13: internalized conversion)
  const handleTagChange = filterState.setTagFromOption;

  // Calculate stats
  const statsData = useMemo(() => {
    const completedLevels = Object.entries(progress.byLevel).filter(
      ([, p]) => p.total > 0 && p.completed >= p.total
    ).length;
    return [
      { label: 'Levels', value: SKILL_LEVELS.length },
      ...(completedLevels > 0 ? [{ label: 'Mastered', value: completedLevels }] : []),
    ];
  }, [progress]);

  const handleFilterChange = useCallback(
    (id: string) => {
      setParam('cat', id);
    },
    [setParam]
  );

  return (
    <PageLayout variant="single-column" mode="training">
      <PageLayout.Content>
        {/* ---- Header (Layer 1) — Matches Technique Focus layout ---- */}
        <div className="px-4 pb-4 pt-4" style={{ backgroundColor: ACCENT.light }}>
          <div className="mx-auto max-w-5xl">
            {/* Back button — left-aligned like Technique/Collections */}
            <button
              type="button"
              onClick={onNavigateHome}
              className="mb-3 inline-flex cursor-pointer items-center gap-1 rounded-lg border-none bg-transparent px-2 py-1.5 text-sm font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-elevated)] hover:text-[var(--color-text-primary)]"
              aria-label="Go back home"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M15 18l-6-6 6-6" />
              </svg>
              Back
            </button>

            {/* Title row: icon circle + title — same as Technique */}
            <div className="flex items-center gap-4">
              <div
                className="flex shrink-0 items-center justify-center rounded-full"
                style={{
                  width: '72px',
                  height: '72px',
                  backgroundColor: ACCENT.bg,
                  fontSize: '2rem',
                }}
              >
                <GraduationCapIcon size={36} />
              </div>
              <div>
                <h1
                  className="m-0 text-[var(--color-text-primary)]"
                  style={{ fontSize: '1.75rem', fontWeight: 800, lineHeight: 1.2 }}
                >
                  Training
                </h1>
                <p
                  className="m-0 mt-1 text-sm text-[var(--color-text-muted)]"
                  style={{ fontWeight: 500 }}
                >
                  Level-based progression — master at your own pace
                </p>
              </div>
            </div>

            {/* Stat badges — same visual treatment as Technique */}
            <div className="mt-4 flex flex-wrap gap-3" data-testid="training-stats">
              {statsData.map((stat) => (
                <span
                  key={stat.label}
                  className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider"
                  style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
                >
                  {stat.value} {stat.label}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* ---- Filter bar (Layer 2) — accent divider + Tag filter ---- */}
        <div
          className="px-4 py-3"
          style={{
            backgroundColor: 'var(--color-bg-elevated)',
            borderTop: `3px solid ${ACCENT.border}`,
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <FilterBar
                label="Filter by difficulty"
                options={CATEGORY_OPTIONS}
                selected={categoryFilter}
                onChange={handleFilterChange}
                testId="training-filter"
              />

              {/* WP8 §8.1: Tag FilterDropdown */}
              {hasTagData && (
                <FilterDropdown
                  label="Tag"
                  placeholder="All Tags"
                  groups={filterState.tagOptionGroups}
                  selected={filterState.tagId !== null ? String(filterState.tagId) : null}
                  onChange={handleTagChange}
                  testId="training-tag-filter"
                />
              )}

              {/* WP8 §8.11: Active filter chip */}
              {filterState.selectedTagSlug && (
                <ActiveFilterChip
                  label={filterState.selectedTagLabel ?? filterState.selectedTagSlug}
                  onDismiss={() => filterState.setTag(null)}
                  testId="training-tag-chip"
                />
              )}

              {/* Depth preset filter */}
              {depthPresetOptions.length > 0 && (
                <FilterBar
                  label="Filter by depth"
                  options={depthPresetOptions}
                  selected={depthPreset ?? ''}
                  onChange={handleDepthPresetChange}
                  testId="training-depth-filter"
                />
              )}
            </div>
          </div>
        </div>

        {/* ---- Content (Layer 3) ---- */}
        <div className="mx-auto w-full max-w-5xl flex-1 p-4">
          {filteredLevels.length === 0 && filterState.hasActiveFilters ? (
            <EmptyFilterState
              message="No levels have puzzles matching your tag filter"
              onClearFilters={filterState.clearAll}
              testId="training-empty-filter"
            />
          ) : filteredLevels.length === 0 ? (
            <EmptyState message="No levels match your filter" quoteMode="daily" />
          ) : (
            /* Grid layout — responsive: 1 col mobile, 2 col tablet, 3 col desktop */
            <div
              className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
              role="list"
              aria-label="Training levels"
            >
              {filteredLevels.map((level) => {
                const levelProgress = progress.byLevel[level.slug];
                const snapshotCount = levelCountMap[level.slug] ?? 0;
                const isEmpty = snapshotCount === 0;
                return (
                  <div key={level.slug} role="listitem">
                    <PuzzleCollectionCard
                      title={level.name}
                      subtitle={`${level.rankRange.min} – ${level.rankRange.max}`}
                      tags={[`${snapshotCount} puzzles`]}
                      progress={{ completed: levelProgress?.completed ?? 0, total: snapshotCount }}
                      mastery={getLocalMastery(levelProgress, snapshotCount)}
                      disabled={isEmpty}
                      onClick={() => onSelectLevel(level.slug)}
                      testId={`training-level-${level.slug}`}
                    />
                  </div>
                );
              })}
            </div>
          )}

          {/* Random Challenge — solid visible button, no glow */}
          {onNavigateRandom && (
            <div className="mt-10 flex justify-center pb-4">
              <button
                type="button"
                onClick={onNavigateRandom}
                className="inline-flex items-center gap-2 rounded-full px-8 py-3 text-base font-bold text-white shadow-md transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg cursor-pointer border-none"
                style={{
                  backgroundColor: 'var(--color-mode-training-text, #3b82f6)',
                }}
                data-testid="training-random-challenge"
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="16 3 21 3 21 8" />
                  <line x1="4" y1="20" x2="21" y2="3" />
                  <polyline points="21 16 21 21 16 21" />
                  <line x1="15" y1="15" x2="21" y2="21" />
                  <line x1="4" y1="4" x2="9" y2="9" />
                </svg>
                Random Challenge
              </button>
            </div>
          )}
        </div>
      </PageLayout.Content>
    </PageLayout>
  );
};

export default TrainingBrowsePage;
