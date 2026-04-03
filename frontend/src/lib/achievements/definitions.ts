/**
 * Achievement definitions.
 * Defines all available achievements and their requirements.
 * @module lib/achievements/definitions
 */

/**
 * Achievement category.
 */
export type AchievementCategory =
  | 'puzzle'      // Puzzle completion achievements
  | 'streak'      // Daily streak achievements
  | 'rush'        // Rush mode achievements
  | 'mastery'     // Skill/mastery achievements
  | 'milestone';  // General milestones

/**
 * Achievement tier (rarity/difficulty).
 */
export type AchievementTier =
  | 'bronze'   // Easy to obtain
  | 'silver'   // Moderate effort
  | 'gold'     // Significant effort
  | 'platinum'; // Very difficult

/**
 * Achievement definition.
 */
export interface AchievementDefinition {
  /** Unique achievement ID */
  readonly id: string;
  /** Display name */
  readonly name: string;
  /** Description of how to earn */
  readonly description: string;
  /** Category */
  readonly category: AchievementCategory;
  /** Difficulty tier */
  readonly tier: AchievementTier;
  /** Icon identifier (emoji or icon name) */
  readonly icon: string;
  /** Required value to unlock (if progress-based) */
  readonly requirement: number;
  /** Progress type (count, streak, score, etc.) */
  readonly progressType: 'count' | 'streak' | 'score' | 'boolean';
  /** Whether achievement is hidden until unlocked */
  readonly hidden?: boolean;
}

/**
 * All achievement definitions.
 */
export const ACHIEVEMENTS: readonly AchievementDefinition[] = [
  // ========== PUZZLE COMPLETION ==========
  {
    id: 'first_solve',
    name: 'First Steps',
    description: 'Solve your first puzzle',
    category: 'puzzle',
    tier: 'bronze',
    icon: '🎯',
    requirement: 1,
    progressType: 'count',
  },
  {
    id: 'puzzles_10',
    name: 'Getting Started',
    description: 'Solve 10 puzzles',
    category: 'puzzle',
    tier: 'bronze',
    icon: '📚',
    requirement: 10,
    progressType: 'count',
  },
  {
    id: 'puzzles_50',
    name: 'Dedicated Student',
    description: 'Solve 50 puzzles',
    category: 'puzzle',
    tier: 'silver',
    icon: '📖',
    requirement: 50,
    progressType: 'count',
  },
  {
    id: 'puzzles_100',
    name: 'Century Club',
    description: 'Solve 100 puzzles',
    category: 'puzzle',
    tier: 'silver',
    icon: '💯',
    requirement: 100,
    progressType: 'count',
  },
  {
    id: 'puzzles_500',
    name: 'Puzzle Master',
    description: 'Solve 500 puzzles',
    category: 'puzzle',
    tier: 'gold',
    icon: '🏆',
    requirement: 500,
    progressType: 'count',
  },
  {
    id: 'puzzles_1000',
    name: 'Grand Master',
    description: 'Solve 1000 puzzles',
    category: 'puzzle',
    tier: 'platinum',
    icon: '👑',
    requirement: 1000,
    progressType: 'count',
  },

  // ========== NO HINTS ==========
  {
    id: 'no_hints_10',
    name: 'Independent Thinker',
    description: 'Solve 10 puzzles without hints',
    category: 'mastery',
    tier: 'bronze',
    icon: '🧠',
    requirement: 10,
    progressType: 'count',
  },
  {
    id: 'no_hints_50',
    name: 'Self-Reliant',
    description: 'Solve 50 puzzles without hints',
    category: 'mastery',
    tier: 'silver',
    icon: '💡',
    requirement: 50,
    progressType: 'count',
  },
  {
    id: 'no_hints_100',
    name: 'True Master',
    description: 'Solve 100 puzzles without hints',
    category: 'mastery',
    tier: 'gold',
    icon: '✨',
    requirement: 100,
    progressType: 'count',
  },

  // ========== DAILY STREAKS ==========
  {
    id: 'streak_3',
    name: 'Warming Up',
    description: 'Maintain a 3-day streak',
    category: 'streak',
    tier: 'bronze',
    icon: '🔥',
    requirement: 3,
    progressType: 'streak',
  },
  {
    id: 'streak_7',
    name: 'Week Warrior',
    description: 'Maintain a 7-day streak',
    category: 'streak',
    tier: 'bronze',
    icon: '📅',
    requirement: 7,
    progressType: 'streak',
  },
  {
    id: 'streak_30',
    name: 'Monthly Master',
    description: 'Maintain a 30-day streak',
    category: 'streak',
    tier: 'silver',
    icon: '📆',
    requirement: 30,
    progressType: 'streak',
  },
  {
    id: 'streak_100',
    name: 'Centurion',
    description: 'Maintain a 100-day streak',
    category: 'streak',
    tier: 'gold',
    icon: '🌟',
    requirement: 100,
    progressType: 'streak',
  },
  {
    id: 'streak_365',
    name: 'Year of Go',
    description: 'Maintain a 365-day streak',
    category: 'streak',
    tier: 'platinum',
    icon: '🎊',
    requirement: 365,
    progressType: 'streak',
  },

  // ========== RUSH MODE ==========
  {
    id: 'rush_first',
    name: 'Speed Demon',
    description: 'Complete your first rush session',
    category: 'rush',
    tier: 'bronze',
    icon: '⚡',
    requirement: 1,
    progressType: 'count',
  },
  {
    id: 'rush_score_500',
    name: 'Quick Thinker',
    description: 'Score 500+ points in a single rush',
    category: 'rush',
    tier: 'bronze',
    icon: '💨',
    requirement: 500,
    progressType: 'score',
  },
  {
    id: 'rush_score_1000',
    name: 'Lightning Fast',
    description: 'Score 1000+ points in a single rush',
    category: 'rush',
    tier: 'silver',
    icon: '⚡',
    requirement: 1000,
    progressType: 'score',
  },
  {
    id: 'rush_score_2000',
    name: 'Rush Master',
    description: 'Score 2000+ points in a single rush',
    category: 'rush',
    tier: 'gold',
    icon: '🏅',
    requirement: 2000,
    progressType: 'score',
  },
  {
    id: 'rush_perfect',
    name: 'Flawless',
    description: 'Complete a rush with no skips',
    category: 'rush',
    tier: 'silver',
    icon: '💎',
    requirement: 1,
    progressType: 'boolean',
  },
  {
    id: 'rush_streak_10',
    name: 'On Fire',
    description: 'Get a 10-puzzle streak in rush mode',
    category: 'rush',
    tier: 'silver',
    icon: '🔥',
    requirement: 10,
    progressType: 'streak',
  },

  // ========== CHALLENGE COMPLETION ==========
  {
    id: 'challenge_first',
    name: 'Challenge Accepted',
    description: 'Complete your first daily challenge',
    category: 'milestone',
    tier: 'bronze',
    icon: '🎯',
    requirement: 1,
    progressType: 'count',
  },
  {
    id: 'challenge_10',
    name: 'Daily Regular',
    description: 'Complete 10 daily challenges',
    category: 'milestone',
    tier: 'bronze',
    icon: '📋',
    requirement: 10,
    progressType: 'count',
  },
  {
    id: 'challenge_perfect',
    name: 'Perfectionist',
    description: 'Complete all puzzles in a daily challenge',
    category: 'milestone',
    tier: 'silver',
    icon: '⭐',
    requirement: 1,
    progressType: 'boolean',
  },

  // ========== DIFFICULTY MASTERY ==========
  {
    id: 'difficulty_easy_10',
    name: 'Beginner Complete',
    description: 'Complete 10 easy puzzles',
    category: 'mastery',
    tier: 'bronze',
    icon: '🌱',
    requirement: 10,
    progressType: 'count',
  },
  {
    id: 'difficulty_hard_10',
    name: 'Challenge Seeker',
    description: 'Complete 10 hard puzzles',
    category: 'mastery',
    tier: 'silver',
    icon: '🎯',
    requirement: 10,
    progressType: 'count',
  },
  {
    id: 'difficulty_expert_10',
    name: 'Expert Level',
    description: 'Complete 10 expert puzzles',
    category: 'mastery',
    tier: 'gold',
    icon: '🔮',
    requirement: 10,
    progressType: 'count',
  },
];

/**
 * Get achievement by ID.
 */
export function getAchievement(id: string): AchievementDefinition | undefined {
  return ACHIEVEMENTS.find(a => a.id === id);
}

/**
 * Get achievements by category.
 */
export function getAchievementsByCategory(
  category: AchievementCategory
): readonly AchievementDefinition[] {
  return ACHIEVEMENTS.filter(a => a.category === category);
}

/**
 * Get achievements by tier.
 */
export function getAchievementsByTier(
  tier: AchievementTier
): readonly AchievementDefinition[] {
  return ACHIEVEMENTS.filter(a => a.tier === tier);
}

/**
 * Achievement definition map for quick lookup.
 */
export const ACHIEVEMENT_MAP: ReadonlyMap<string, AchievementDefinition> = new Map(
  ACHIEVEMENTS.map(a => [a.id, a])
);

/**
 * Get tier color for display.
 */
export function getTierColor(tier: AchievementTier): string {
  switch (tier) {
    case 'bronze': return '#CD7F32';
    case 'silver': return '#C0C0C0';
    case 'gold': return '#FFD700';
    case 'platinum': return '#E5E4E2';
  }
}

/**
 * Get tier display name.
 */
export function getTierName(tier: AchievementTier): string {
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}
