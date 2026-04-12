/**
 * RandomPage — Random puzzle selection page.
 * @module pages/RandomPage
 *
 * Provides a random puzzle shuffle experience with:
 * - Level filter to focus on specific difficulties
 * - Prominent "Random Puzzle" action button
 * - Session stats (puzzles attempted, accuracy)
 *
 * Spec 129, Phase 10 — FR-050, FR-064
 */

import type { FunctionalComponent } from 'preact';
import { useState, useEffect, useMemo, useCallback } from 'preact/hooks';
import type { SkillLevel } from '@/models/collection';
import { getSkillLevelName } from '@/models/collection';
import { PageLayout } from '@/components/Layout/PageLayout';
import { FilterBar, type FilterOption } from '@/components/shared/FilterBar';
import { FilterDropdown } from '@/components/shared/FilterDropdown';
import { ActiveFilterChip } from '@/components/shared/ActiveFilterChip';
// EmptyFilterState removed — filter UI will be reconnected in P3 routing phase
import type { StatItem } from '@/components/shared/StatsBar';
import { Button } from '@/components/shared/Button';
import { PageHeader } from '@/components/shared/PageHeader';
import { DiceIcon } from '@/components/shared/icons';
import { type CategoryFilter, CATEGORY_OPTIONS, getCategoryLevels } from '@/lib/levels/categories';
import { getAccentPalette } from '@/lib/accent-palette';
import { levelSlugToId, levelIdToSlug, getTagsByCategory, getOrderedTagCategories, tagIdToSlug, getTagMeta } from '@/services/configService';
import { useCanonicalUrl } from '@/hooks/useCanonicalUrl';
import { buildDepthPresetOptions, depthPresetToRange } from '@/hooks/usePuzzleFilters';
import { getFilterCounts } from '@/services/puzzleQueryService';

// ============================================================================
// Props
// ============================================================================

export interface RandomPageProps {
  /** Callback when user requests a random puzzle at given level (and optional tag). */
  onSelectRandomPuzzle: (level: SkillLevel, tagSlug?: string) => void;
  /** Callback to navigate home. */
  onNavigateHome: () => void;
}

// ============================================================================
// Component
// ============================================================================

/** Accent palette — PURSIG Finding 12: shared utility */
const ACCENT = getAccentPalette('random');

export const RandomPage: FunctionalComponent<RandomPageProps> = ({
  onSelectRandomPuzzle,
  onNavigateHome,
}) => {
  // State — category is a UI grouping, level+tag unified in filterState (F13)
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all');
  const [sessionStats, setSessionStats] = useState({ puzzles: 0, correct: 0 });

  // P3: URL-synced filter state
  const { filters, setFilters, hasActiveFilters: urlHasActive, clearFilters } = useCanonicalUrl();
  const filterLevelIds = filters.l ?? [];
  const filterTagIds = filters.t ?? [];
  const depthPreset = filters.dp ?? null;

  const tagMasterEntries: readonly never[] = [];

  // Bridge filter state for the existing template code
  const filterState = {
    levelIds: [...filterLevelIds],
    tagIds: [...filterTagIds],
    setLevel: (id: number | null) => setFilters({ l: id === null ? [] : [id] }),
    setTag: (id: number | null) => setFilters({ t: id === null ? [] : [id] }),
    setTagFromOption: (id: string | null) => {
      if (id === null || id === '') { setFilters({ t: [] }); return; }
      const n = Number(id); if (!Number.isNaN(n)) setFilters({ t: [n] });
    },
    tagOptionGroups: getOrderedTagCategories().map(cat => ({
      label: cat.label,
      options: getTagsByCategory(cat.key).map(t => ({
        id: String(t.id), label: t.name,
      })),
    })),
    tagId: filterTagIds.length === 1 ? filterTagIds[0]! : null,
    levelId: filterLevelIds.length === 1 ? filterLevelIds[0]! : null,
    selectedLevelSlug: filterLevelIds.length === 1 ? levelIdToSlug(filterLevelIds[0]!) : null,
    selectedTagSlug: filterTagIds.length === 1 ? tagIdToSlug(filterTagIds[0]!) : null,
    selectedTagLabel: filterTagIds.length === 1 ? (getTagMeta(tagIdToSlug(filterTagIds[0]!))?.name ?? null) : null,
    hasActiveFilters: urlHasActive,
    clearAll: clearFilters,
  };

  // Load session stats from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('yen-go-random-session');
      if (stored) {
        const parsed = JSON.parse(stored) as { puzzles: number; correct: number };
        setSessionStats(parsed);
      }
    } catch {
      // Ignore parse errors
    }
  }, []);

  // Available levels based on category filter
  const availableLevels = useMemo(() => {
    return getCategoryLevels(categoryFilter);
  }, [categoryFilter]);

  // Stats for display
  const statItems: readonly StatItem[] = useMemo(() => {
    const accuracy =
      sessionStats.puzzles > 0
        ? Math.round((sessionStats.correct / sessionStats.puzzles) * 100)
        : 0;
    return [
      { label: 'Puzzles', value: sessionStats.puzzles.toString() },
      { label: 'Correct', value: sessionStats.correct.toString() },
      { label: 'Accuracy', value: `${accuracy}%` },
    ];
  }, [sessionStats]);

  // Handle category filter change — clears level when category changes
  const handleCategoryChange = useCallback((id: string) => {
    setCategoryFilter(id as CategoryFilter);
    filterState.setLevel(null); // Reset level when category changes
  }, [filterState.setLevel]);

  // F13: Level filter uses filterState (unified system). Build options from availableLevels.
  const handleLevelChange = useCallback((id: string) => {
    if (id === 'any') {
      filterState.setLevel(null);
    } else {
      const levelId = levelSlugToId(id);
      filterState.setLevel(levelId ?? null);
    }
  }, [filterState.setLevel]);

  // WP8: Handle tag filter change (PURSIG Finding 13: internalized conversion)
  const handleTagChange = filterState.setTagFromOption;

  // Depth preset options from cross-filtered counts
  const depthPresetOptions = useMemo(() => {
    const depthRange = depthPresetToRange(depthPreset);
    const levelFilter = filterState.levelId !== null ? { levelId: filterState.levelId } : {};
    const tagFilter = filterState.tagId !== null ? { tagIds: [filterState.tagId] } : {};
    const counts = getFilterCounts({
      ...levelFilter,
      ...tagFilter,
      ...depthRange,
    });
    return buildDepthPresetOptions(counts.depthPresets ?? {});
  }, [depthPreset, filterState.levelId, filterState.tagId]);

  const handleDepthPresetChange = useCallback((id: string) => {
    const newDp = id === depthPreset ? undefined : id;
    if (newDp !== undefined) setFilters({ dp: newDp }); else setFilters({});
  }, [depthPreset, setFilters]);

  // Derive selected level slug from filterState for display
  const selectedLevelSlug: string = filterState.selectedLevelSlug
    ? (filterState.selectedLevelSlug)
    : 'any';

  // Handle random puzzle button click — reads from unified filterState
  const handleRandomClick = useCallback(() => {
    let targetLevel: SkillLevel;

    if (filterState.levelId !== null && filterState.selectedLevelSlug) {
      // A specific level is selected via filterState
      targetLevel = filterState.selectedLevelSlug;
    } else {
      // Pick random from available levels
      const levels = availableLevels;
      if (levels.length === 0) return;
      const randomIndex = Math.floor(Math.random() * levels.length);
      const selected = levels[randomIndex];
      if (!selected) return;
      targetLevel = selected;
    }

    // C1: Pass selected tag slug to callback so app.tsx can filter by tag
    onSelectRandomPuzzle(targetLevel, filterState.selectedTagSlug ?? undefined);
  }, [filterState.levelId, filterState.selectedLevelSlug, filterState.selectedTagSlug, availableLevels, onSelectRandomPuzzle]);

  // Filtered level options based on category
  const filteredLevelOptions = useMemo(() => {
    const options: FilterOption[] = [{ id: 'any', label: 'Any Level' }];
    for (const level of availableLevels) {
      options.push({
        id: level,
        label: getSkillLevelName(level),
      });
    }
    return options;
  }, [availableLevels]);

  return (
    <PageLayout variant="single-column" mode="random">
      <PageLayout.Content>
        {/* Header — technique layout pattern */}
        <PageHeader
          title="Random"
          subtitle="Practice at your pace with randomly selected puzzles"
          icon={<DiceIcon size={36} />}
          stats={statItems.map(s => ({ label: s.label, value: s.value }))}
          onBack={onNavigateHome}
          accent={ACCENT}
          testId="random-header"
        />

        {/* Filter bar — accent divider top */}
        <div
          className="px-4 py-3"
          style={{
            backgroundColor: 'var(--color-bg-elevated)',
            borderTop: `3px solid ${ACCENT.border}`,
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <FilterBar
                label="Category filter"
                options={CATEGORY_OPTIONS}
                selected={categoryFilter}
                onChange={handleCategoryChange}
                testId="category-filter"
              />
              <FilterBar
                label="Level filter"
                options={filteredLevelOptions}
                selected={selectedLevelSlug}
                onChange={handleLevelChange}
                testId="level-filter"
              />

              {/* WP8 §8.10: Tag FilterDropdown */}
              {tagMasterEntries.length > 0 && (
                <FilterDropdown
                  label="Tag"
                  placeholder="All Tags"
                  groups={filterState.tagOptionGroups}
                  selected={filterState.tagId !== null ? String(filterState.tagId) : null}
                  onChange={handleTagChange}
                  testId="random-tag-filter"
                />
              )}

              {/* WP8 §8.11: Active tag filter chip */}
              {filterState.selectedTagSlug && (
                <ActiveFilterChip
                  label={filterState.selectedTagLabel ?? filterState.selectedTagSlug}
                  onDismiss={() => filterState.setTag(null)}
                  testId="random-tag-chip"
                />
              )}

              {/* Depth preset filter */}
              {depthPresetOptions.length > 0 && (
                <FilterBar
                  label="Filter by depth"
                  options={depthPresetOptions}
                  selected={depthPreset ?? ''}
                  onChange={handleDepthPresetChange}
                  testId="random-depth-filter"
                />
              )}
            </div>
          </div>
        </div>

        {/* Content (Layer 2) */}
        <div
          className="mx-auto w-full max-w-5xl flex-1 p-4"
          data-testid="random-page"
        >
          {/* Random Puzzle Action */}
          <section
            className="flex flex-col items-center gap-4 rounded-xl bg-[var(--color-bg-elevated)] p-8"
            data-testid="action-section"
          >
            <div className="text-center">
              <p className="mb-2 text-lg text-[var(--color-text-primary)]">
                Ready for a challenge?
              </p>
              <p className="text-sm text-[var(--color-text-muted)]">
                {selectedLevelSlug !== 'any'
                  ? `You'll get a ${getSkillLevelName(selectedLevelSlug)} puzzle`
                  : `Random puzzle from ${availableLevels.length} levels`}
              </p>
            </div>

            <Button
              onClick={handleRandomClick}
              variant="primary"
              size="lg"
              className="min-h-[56px] min-w-[200px] text-lg font-semibold"
              data-testid="random-button"
            >
              Get Random Puzzle
            </Button>
          </section>

          {/* Level Preview Cards */}
          <section className="mt-6 flex flex-col gap-4">
            <h2 className="text-lg font-medium text-[var(--color-text-primary)]">
              Available Levels ({availableLevels.length})
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
              {availableLevels.map((level) => (
                <button
                  type="button"
                  key={level}
                  onClick={() => onSelectRandomPuzzle(level, filterState.selectedTagSlug ?? undefined)}
                  className="flex flex-col gap-1 rounded-lg bg-[var(--color-bg-panel)] p-4 text-left transition-colors hover:bg-[var(--color-bg-secondary)]"
                  data-testid={`level-card-${level}`}
                >
                  <span className="font-medium text-[var(--color-text-primary)]">
                    {getSkillLevelName(level)}
                  </span>
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {level}
                  </span>
                </button>
              ))}
            </div>
          </section>

          {/* Help Text */}
          <p className="mt-6 text-center text-xs text-[var(--color-text-muted)]">
            Random puzzles are drawn from all available collections. Your session
            stats are saved locally and reset when you close the app.
          </p>
        </div>
      </PageLayout.Content>
    </PageLayout>
  );
};

export default RandomPage;
