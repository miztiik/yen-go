/**
 * Rush mode module exports.
 * @module lib/rush
 */

export {
  RushTimer,
  createRushTimer,
  TIMER_DURATIONS,
  formatTime,
  formatDetailedTime,
  type TimerState,
  type TimerConfig,
  type TimerDuration,
} from './timer';

export {
  VisibilityHandler,
  createVisibilityHandler,
  createVisibilityState,
  getVisibilityInfo,
  DEFAULT_FORFEIT_THRESHOLD,
  type VisibilityState,
  type VisibilityConfig,
} from './visibility';

export {
  RushQueue,
  createRushQueue,
  createRushQueueFromPuzzles,
  createQueueState,
  type QueueItem,
  type QueueState,
  type QueueConfig,
} from './queue';

export {
  RushScoring,
  createRushScoring,
  calculateTimeBonus,
  calculateStreakBonus,
  calculateRank,
  createScoringState,
  DEFAULT_SCORING_CONFIG,
  type PuzzleScore,
  type ScoringState,
  type ScoringConfig,
} from './scoring';

export {
  SkipManager,
  createSkipManager,
  createSkipState,
  formatSkipPenalty,
  getSkipStatusInfo,
  DEFAULT_SKIP_CONFIG,
  type SkipResult,
  type SkipConfig,
  type SkipState,
} from './skip';
