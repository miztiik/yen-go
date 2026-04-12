/**
 * Hooks index
 * @module hooks
 */

export { useStreak, type UseStreakReturn } from './useStreak';
export { useHints, type HintState, type HintActions, type UseHintsResult } from './useHints';
export { useSettings, type UseSettingsReturn } from './useSettings';
export { useDebounce } from './useDebounce';
// useFilterState removed — replaced by SQLite query system
export { useMediaQuery, useIsDesktop, useIsMobile } from './useMediaQuery';
export { useCanonicalUrl, type UseCanonicalUrlResult } from './useCanonicalUrl';
export {
  usePuzzleFilters,
  type UsePuzzleFiltersResult,
  type PuzzleFilterOptions,
} from './usePuzzleFilters';
// useSolutionAnimation removed in spec 124 dead code cleanup
// useExploreMode removed in spec 124 dead code cleanup
// useBoardViewport removed in spec 129 dead code cleanup
// useTreeNavigation removed in spec 123-solution-tree-rewrite
// Tree types removed in spec 129 (types/tree.ts deleted — legacy engine)
