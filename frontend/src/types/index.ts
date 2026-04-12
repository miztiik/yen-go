/**
 * Type definitions index
 * Re-exports all types for convenient importing
 * @module types
 */

// Puzzle types
export type {
  SgfCoord,
  BoardCorner,
  BoardRegion,
  Side,
  SkillLevel,
  PuzzleTag,
  Puzzle,
  PuzzleWithId,
  StoneColor,
  Coordinate as PuzzleCoordinate,
} from './puzzle';

// Board types removed in spec 129 (legacy engine — use goban types instead)

// Level types removed in spec 129 (use models/level.ts instead)

// Progress types
export type {
  BoardTheme,
  UserPreferences,
  PuzzleCompletion,
  RushScore,
  AvgTimeByDifficulty,
  Statistics,
  StatisticsBySkillLevel,
  StreakData,
  UserProgress,
} from './progress';
export {
  DEFAULT_PREFERENCES,
  DEFAULT_STATISTICS,
  DEFAULT_STREAK_DATA,
  createDefaultProgress,
  PROGRESS_SCHEMA_VERSION,
} from './progress';

// Achievement types removed in spec 129 (use models/achievement.ts instead)

// Source registry types removed in UI overhaul phase-5 dead code cleanup
// Internal puzzle types (SGF-native format)
export type {
  Position,
  BoardState as InternalBoardState,
  SolutionNode,
  SolutionPath,
  PuzzleStatus,
  PuzzleNavItem,
  PuzzleHints,
  InternalPuzzle,
  PuzzleSet,
} from './puzzle-internal';
export { isPuzzleStatus, isValidPosition, createSolutionNode } from './puzzle-internal';

// Index types — entry types + daily types (SQLite-centric architecture)
export type {
  LevelEntry,
  TagEntry,
  CollectionEntry,
  ViewEntry,
  LevelMasterEntry,
  TagMasterEntry,
  CollectionMasterEntry,
  DailyStandard,
  DailyTimed,
  DailyIndex,
  DailyPuzzleEntry,
} from './indexes';
export { isDailyIndex } from './indexes';

// Storage types (localStorage)
export type {
  PuzzleProgressEntry,
  DailyProgressEntry,
  ProgressState,
  BoardRotation,
  CachedPuzzleEntry,
  CacheState,
} from './storage';
export {
  STORAGE_KEYS,
  DEFAULT_PROGRESS_STATE,
  DEFAULT_CACHE_STATE,
  loadFromStorage,
  saveToStorage,
  removeFromStorage,
  isValidBoardRotation,
  isProgressState,
} from './storage';

// Unified Coordinate type (Spec 122 T4.1)
export type { Coordinate as UnifiedCoordinate } from './coordinate';
export {
  coordEqual,
  coord,
  coordToSgf as unifiedCoordToSgf,
  sgfToCoord as unifiedSgfToCoord,
  coordToDisplay,
  displayToCoord,
  isValidCoord,
  getAdjacentCoords as getAdjacentCoordinates,
  coordKey,
  keyToCoord,
} from './coordinate';
