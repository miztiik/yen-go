import type { FunctionalComponent, JSX } from 'preact';
import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import { Button } from '../components/shared/Button';
import { PuzzleSetPlayer } from '../components/PuzzleSetPlayer';
import type { HeaderInfo, SummaryInfo } from '../components/PuzzleSetPlayer';
import { PuzzleSetHeader } from '../components/PuzzleSetPlayer/PuzzleSetHeader';
import { TrainingPuzzleLoader } from '../services/puzzleLoaders';
import { getAccuracyColorClass } from '../lib/accuracy-color';
import type { SkillLevel } from '../models/collection';
import { getSkillLevelInfo, SKILL_LEVELS } from '../models/collection';
import { saveTrainingProgress } from '../components/Training/trainingProgressUtils';
import { levelSlugToId } from '../services/configService';
import { usePuzzleFilters } from '../hooks/usePuzzleFilters';
import { FilterDropdown } from '../components/shared/FilterDropdown';
import { ActiveFilterChip } from '../components/shared/ActiveFilterChip';
import { ClearAllFiltersButton } from '../components/shared/ClearAllFiltersButton';
import { EmptyFilterState } from '../components/shared/EmptyFilterState';
import { TrophyIcon } from '../components/shared/icons/TrophyIcon';
import { ContentTypeFilter } from '../components/shared/ContentTypeFilter';
import { useContentType } from '../hooks/useContentType';

export interface TrainingViewPageProps {
  /** Selected training level */
  level: SkillLevel;
  /** Starting puzzle index (0-based, from URL offset). */
  startIndex?: number;
  /** Callback to navigate home */
  onNavigateHome: () => void;
  /** Callback to navigate back to training selection */
  onNavigateTraining: () => void;
}

/**
 * Training page for level-based puzzle practice.
 * Thin wrapper around PuzzleSetPlayer — delegates puzzle loading,
 * navigation, and SolverView rendering to the shared component.
 * Provides training-specific header (progress bar, accuracy, tag filters)
 * and level-complete summary via render props.
 *
 * Filter infrastructure matches CollectionViewPage for visual consistency.
 */
export const TrainingViewPage: FunctionalComponent<TrainingViewPageProps> = ({
  level,
  startIndex = 0,
  onNavigateHome,
  onNavigateTraining,
}) => {
  const levelInfo = getSkillLevelInfo(level);
  const [completedCount, setCompletedCount] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [totalPuzzles, setTotalPuzzles] = useState(0);

  const accuracy = completedCount > 0 ? Math.round((correctCount / completedCount) * 100) : 0;
  const percentComplete = totalPuzzles > 0 ? Math.round((completedCount / totalPuzzles) * 100) : 0;
  const isNextLevelUnlocked = percentComplete >= 70;

  // Resolve level slug to query key for filter infrastructure
  const queryKey = useMemo(() => {
    const numericId = levelSlugToId(level);
    return numericId !== undefined ? `l${numericId}` : null;
  }, [level]);

  // Load filter options from database (tag distributions within this level)
  const {
    isLoaded: filtersLoaded,
    filterOptions,
    tagIds: filterTagIds,
    setTag: filterSetTag,
    setTagFromOption: filterSetTagFromOption,
    selectedTagSlug,
    selectedTagLabel,
    hasActiveFilters,
    activeFilterCount,
    clearFilters,
    setOffset: urlSetOffset,
    setId: urlSetId,
  } = usePuzzleFilters(queryKey);

  // Global content-type preference
  const { contentType, setContentType } = useContentType();

  // Convenience accessors for filter state
  const filterState = {
    tagIds: [...filterTagIds],
    tagOptionGroups: filterOptions.tagOptionGroups.map((g) => ({
      label: g.label,
      options: [...g.options],
    })),
    tagId: filterTagIds.length === 1 ? filterTagIds[0]! : null,
    selectedTagSlug,
    selectedTagLabel,
    hasActiveFilters,
    activeFilterCount,
    setTag: filterSetTag,
    setTagFromOption: filterSetTagFromOption,
    clearAll: clearFilters,
  };

  // Tag dropdown groups (reuse database distributions directly)
  const tagDropdownGroups = useMemo(() => {
    return filterState.tagOptionGroups.map((g) => ({
      label: g.label,
      options: g.options.map((o) => {
        const opt: { id: string; label: string; count?: number } = { id: o.id, label: o.label };
        if (o.count !== undefined) opt.count = o.count;
        return opt;
      }),
    }));
  }, [filterState.tagOptionGroups]);

  const handleTagChange = filterState.setTagFromOption;

  // Create loader for this training level (re-creates when tag/ct filters change)
  const loader = useMemo(
    () => new TrainingPuzzleLoader(level, filterTagIds, contentType),
    [level, filterTagIds, contentType]
  );

  // Track total puzzles once loader is ready
  useEffect(() => {
    // Poll loader status until ready (loader.load() is called by PuzzleSetPlayer)
    const interval = setInterval(() => {
      const total = loader.getTotal();
      if (total > 0) {
        setTotalPuzzles(total);
        clearInterval(interval);
      }
    }, 100);
    return () => clearInterval(interval);
  }, [loader]);

  // Save progress whenever it changes
  useEffect(() => {
    if (completedCount > 0 && totalPuzzles > 0) {
      saveTrainingProgress(level, completedCount, totalPuzzles, accuracy);
    }
  }, [completedCount, totalPuzzles, accuracy, level]);

  // Track puzzle completion for accuracy
  const handlePuzzleComplete = useCallback((_puzzleId: string, isCorrect: boolean) => {
    setCompletedCount((c) => c + 1);
    if (isCorrect) {
      setCorrectCount((c) => c + 1);
    }
  }, []);

  // URL tracking for deep-linking/sharing (matches CollectionViewPage)
  const handlePuzzleChange = useCallback(
    (puzzleId: string | null, index?: number) => {
      if (index === undefined) return;
      urlSetOffset(index);
      urlSetId(puzzleId ?? undefined);
    },
    [urlSetOffset, urlSetId]
  );

  // Navigate to next level
  const handleNextLevel = useCallback(() => {
    const currentLevelIndex = SKILL_LEVELS.findIndex((l) => l.slug === level);
    if (currentLevelIndex >= 0 && currentLevelIndex < SKILL_LEVELS.length - 1) {
      onNavigateTraining();
    } else {
      onNavigateHome();
    }
  }, [level, onNavigateTraining, onNavigateHome]);

  // Build filter strip content — matches CollectionViewPage layout
  const hasTags = filterOptions.tagOptionGroups.flatMap((g) => g.options).length > 0;
  const filterStripContent =
    filtersLoaded && hasTags ? (
      <div className="flex flex-wrap items-center gap-2" data-testid="training-filter-strip">
        {/* Content type global filter */}
        <ContentTypeFilter
          counts={filterOptions.contentTypeOptions.reduce<Record<number, number>>((acc, o) => {
            if (o.count !== undefined) acc[Number(o.id)] = o.count;
            return acc;
          }, {})}
        />

        {/* Visual separator between content-type and tag filters */}
        <div className="hidden sm:block w-px h-6 self-center bg-[var(--color-border)] mx-1" />

        {/* Tag FilterDropdown */}
        <FilterDropdown
          label="Tag"
          placeholder="All Tags"
          groups={tagDropdownGroups}
          selected={filterState.tagId !== null ? String(filterState.tagId) : null}
          onChange={handleTagChange}
          testId="training-tag-filter"
        />

        {/* Active filter chips + clear button */}
        <div className="ml-auto flex items-center gap-1.5">
          {filterState.selectedTagSlug && (
            <ActiveFilterChip
              label={filterState.selectedTagLabel ?? filterState.selectedTagSlug}
              onDismiss={() => filterState.setTag(null)}
              testId="training-tag-chip"
            />
          )}
          {filterState.activeFilterCount >= 2 && (
            <ClearAllFiltersButton onClear={filterState.clearAll} testId="training-clear-all" />
          )}
        </div>

        {/* Next level unlocked indicator */}
        {percentComplete >= 70 && percentComplete < 100 && (
          <div className="text-xs font-medium text-[var(--color-success)]">
            Next level unlocked!
          </div>
        )}
      </div>
    ) : percentComplete >= 70 && percentComplete < 100 ? (
      <div className="text-xs font-medium text-[var(--color-success)]">Next level unlocked!</div>
    ) : undefined;

  // Training header — matches CollectionViewPage's PuzzleSetHeader pattern
  // with stats badges in rightContent and filter strip below.
  const renderHeader = useCallback(
    (info: HeaderInfo): JSX.Element => {
      const statsContent = (
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-bg-secondary)] px-2.5 py-1 text-xs font-semibold text-[var(--color-text-secondary)] whitespace-nowrap">
            {completedCount}/{info.totalPuzzles}
            <span className="text-[var(--color-text-muted)] font-normal">solved</span>
          </span>
          <span
            className={`inline-flex items-center gap-1 rounded-full bg-[var(--color-bg-secondary)] px-2.5 py-1 text-xs font-semibold whitespace-nowrap ${getAccuracyColorClass(accuracy)}`}
          >
            {accuracy}%<span className="text-[var(--color-text-muted)] font-normal">accuracy</span>
          </span>
        </div>
      );

      return (
        <PuzzleSetHeader
          title={`Training: ${levelInfo?.name ?? level}`}
          {...(levelInfo
            ? { subtitle: `${levelInfo.rankRange.min} – ${levelInfo.rankRange.max}` }
            : {})}
          currentIndex={info.currentIndex}
          totalPuzzles={info.totalPuzzles}
          progress={percentComplete}
          {...(info.onBack ? { onBack: info.onBack } : {})}
          backLabel="Back to training"
          rightContent={statsContent}
          {...(filterStripContent ? { filterStrip: filterStripContent } : {})}
          testId="training-header"
        />
      );
    },
    [levelInfo, level, completedCount, accuracy, percentComplete, filterStripContent]
  );

  // Empty filter state — when tag/content-type filter produces zero results
  const hasAnyFilter = filterState.hasActiveFilters || contentType > 0;

  const contentTypeInfo =
    contentType > 0
      ? (() => {
          const typeNames: Record<number, string> = {
            1: 'Curated',
            2: 'Practice',
            3: 'Training Lab',
          };
          const availableTypes = filterOptions.contentTypeOptions
            .filter(
              (opt) => opt.id !== '0' && opt.id !== String(contentType) && (opt.count ?? 0) > 0
            )
            .map((opt) => ({ name: opt.label, count: opt.count ?? 0 }));
          return {
            activeTypeName: typeNames[contentType] ?? 'selected',
            availableTypes,
            onShowAllTypes: () => setContentType(0),
          };
        })()
      : undefined;

  const handleClearAllFilters = () => {
    filterState.clearAll();
    setContentType(0);
  };

  const renderEmptyWithFilters = hasAnyFilter
    ? () => (
        <>
          {renderHeader({
            name: `Training: ${levelInfo?.name ?? level}`,
            currentIndex: 0,
            totalPuzzles: 0,
            completedCount: 0,
            onBack: onNavigateTraining,
          })}
          <EmptyFilterState
            onClearFilters={handleClearAllFilters}
            testId="training-empty-filter"
            {...(contentTypeInfo ? { contentTypeInfo } : {})}
          />
        </>
      )
    : undefined;

  // Level-complete summary screen
  const renderSummary = useCallback(
    (info: SummaryInfo): JSX.Element => {
      return (
        <div className="mx-auto flex w-full max-w-[800px] flex-1 flex-col items-center justify-center px-4 py-8">
          <div className="flex w-full max-w-[400px] flex-col items-center gap-6 rounded-lg bg-[var(--color-bg-primary)] p-8 text-center shadow-md">
            <TrophyIcon size={64} className="text-[var(--color-success)]" />

            <div>
              <h2 className="m-0 text-xl font-bold text-[var(--color-success)]">Level Complete!</h2>
              <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                You've completed {levelInfo?.name} training!
              </p>
            </div>

            {/* Final stats */}
            <div className="flex w-full gap-6 rounded-md bg-[var(--color-bg-secondary)] p-4">
              <div className="flex-1 text-center">
                <div className="text-xl font-bold text-[var(--color-text-primary)]">
                  {correctCount}/{info.completedCount}
                </div>
                <div className="text-sm text-[var(--color-text-muted)]">Correct</div>
              </div>
              <div className="flex-1 text-center">
                <div className={`text-xl font-bold ${getAccuracyColorClass(accuracy)}`}>
                  {accuracy}%
                </div>
                <div className="text-sm text-[var(--color-text-muted)]">Accuracy</div>
              </div>
            </div>

            {/* Next level unlocked message */}
            {isNextLevelUnlocked && (
              <div className="rounded-md bg-[color-mix(in_srgb,var(--color-success)_15%,transparent)] px-4 py-2 text-sm text-[var(--color-success)]">
                Next level unlocked!
              </div>
            )}

            {/* Actions */}
            <div className="flex w-full gap-2">
              <Button variant="secondary" onClick={onNavigateHome} className="flex-1">
                Go Home
              </Button>
              {isNextLevelUnlocked ? (
                <Button variant="primary" onClick={handleNextLevel} className="flex-1">
                  Next Level →
                </Button>
              ) : (
                <Button variant="primary" onClick={info.onBack} className="flex-1">
                  Practice More
                </Button>
              )}
            </div>
          </div>
        </div>
      );
    },
    [levelInfo, correctCount, accuracy, isNextLevelUnlocked, onNavigateHome, handleNextLevel]
  );

  return (
    <PuzzleSetPlayer
      loader={loader}
      startIndex={startIndex}
      onBack={onNavigateTraining}
      onPuzzleComplete={handlePuzzleComplete}
      onPuzzleChange={handlePuzzleChange}
      renderHeader={renderHeader}
      {...(renderEmptyWithFilters ? { renderEmpty: renderEmptyWithFilters } : {})}
      renderSummary={renderSummary}
      mode="training"
    />
  );
};

export default TrainingViewPage;
