/**
 * Achievement type definitions
 * @module types/achievement
 */

/**
 * Achievement trigger types
 */
export type AchievementTrigger =
  | { type: 'puzzles_solved'; count: number }
  | { type: 'streak_days'; count: number }
  | { type: 'skill_level_completed'; level: number; count: number }
  | { type: 'rush_score'; score: number }
  | { type: 'puzzles_without_hints'; count: number }
  | { type: 'perfect_solves'; count: number }
  | { type: 'first_puzzle' }
  | { type: 'first_level_completed' };

/**
 * Achievement definition
 */
export interface AchievementDefinition {
  /** Unique achievement ID */
  readonly id: string;
  /** Display name */
  readonly name: string;
  /** Description of how to unlock */
  readonly description: string;
  /** Icon identifier */
  readonly icon: string;
  /** Trigger condition */
  readonly trigger: AchievementTrigger;
}

/**
 * Achievement progress state
 */
export interface AchievementProgress {
  /** Achievement ID */
  readonly id: string;
  /** Current progress value */
  readonly current: number;
  /** Target value to unlock */
  readonly target: number;
  /** Whether unlocked */
  readonly unlocked: boolean;
  /** ISO 8601 timestamp when unlocked */
  readonly unlockedAt?: string;
}

/**
 * Achievement with full definition and progress
 */
export interface AchievementWithProgress extends AchievementDefinition {
  /** Current progress */
  readonly progress: AchievementProgress;
}

/**
 * Built-in achievement definitions
 */
export const ACHIEVEMENTS: readonly AchievementDefinition[] = [
  {
    id: 'first-steps',
    name: 'First Steps',
    description: 'Complete your first puzzle',
    icon: '🎯',
    trigger: { type: 'first_puzzle' },
  },
  {
    id: 'weekly-warrior',
    name: 'Weekly Warrior',
    description: 'Maintain a 7-day streak',
    icon: '🔥',
    trigger: { type: 'streak_days', count: 7 },
  },
  {
    id: 'monthly-master',
    name: 'Monthly Master',
    description: 'Maintain a 30-day streak',
    icon: '🏆',
    trigger: { type: 'streak_days', count: 30 },
  },
  {
    id: 'century-solver',
    name: 'Century Solver',
    description: 'Complete 100 puzzles',
    icon: '💯',
    trigger: { type: 'puzzles_solved', count: 100 },
  },
  {
    id: 'five-hundred',
    name: 'Five Hundred Club',
    description: 'Complete 500 puzzles',
    icon: '🎖️',
    trigger: { type: 'puzzles_solved', count: 500 },
  },
  {
    id: 'thousand-solver',
    name: 'Thousand Solver',
    description: 'Complete 1000 puzzles',
    icon: '👑',
    trigger: { type: 'puzzles_solved', count: 1000 },
  },
  {
    id: 'pure-skill',
    name: 'Pure Skill',
    description: 'Complete 50 puzzles without using hints',
    icon: '🧠',
    trigger: { type: 'puzzles_without_hints', count: 50 },
  },
  {
    id: 'rush-rookie',
    name: 'Rush Rookie',
    description: 'Score 10+ in Puzzle Rush',
    icon: '⚡',
    trigger: { type: 'rush_score', score: 10 },
  },
  {
    id: 'rush-master',
    name: 'Rush Master',
    description: 'Score 25+ in Puzzle Rush',
    icon: '🚀',
    trigger: { type: 'rush_score', score: 25 },
  },
  {
    id: 'level-up',
    name: 'Level Up',
    description: 'Complete your first Daily Challenge',
    icon: '📈',
    trigger: { type: 'first_level_completed' },
  },
] as const;

/**
 * Get achievement definition by ID
 */
export function getAchievementById(id: string): AchievementDefinition | undefined {
  return ACHIEVEMENTS.find((a) => a.id === id);
}
