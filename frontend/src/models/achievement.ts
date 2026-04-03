/**
 * Achievement Types and Definitions
 * @module models/achievement
 *
 * Defines achievement system for US8 (FR-042 to FR-044)
 *
 * Constitution Compliance:
 * - IV. Local-First Persistence: All achievements stored in localStorage
 * - VI. Type Safety: Full TypeScript types for achievement system
 */

/** Achievement category for grouping */
export type AchievementCategory =
  | 'puzzles'    // Puzzle-solving milestones
  | 'streaks'    // Daily streak achievements
  | 'rush'       // Puzzle rush mode achievements
  | 'mastery'    // Skill-based achievements
  | 'collection' // Collection/completion achievements
  | 'special';   // Special/hidden achievements

/** Achievement tier for rarity/difficulty */
export type AchievementTier = 'bronze' | 'silver' | 'gold' | 'platinum';

/** Unique achievement identifier */
export type AchievementId =
  // Puzzle milestones
  | 'first_puzzle'      // Solve first puzzle
  | 'ten_puzzles'       // Solve 10 puzzles
  | 'fifty_puzzles'     // Solve 50 puzzles
  | 'hundred_puzzles'   // Solve 100 puzzles
  | 'five_hundred'      // Solve 500 puzzles
  | 'thousand_puzzles'  // Solve 1000 puzzles
  // Streak achievements
  | 'streak_7'          // 7-day streak
  | 'streak_30'         // 30-day streak
  | 'streak_100'        // 100-day streak
  | 'streak_365'        // 365-day streak (year!)
  // Skill achievements
  | 'perfect_ten'       // 10 perfect solves (no hints, first attempt)
  | 'no_hints_master'   // 50 puzzles without hints
  | 'speed_demon'       // Solve puzzle in under 10 seconds
  | 'quick_thinker'     // Solve 5 puzzles in under 30 seconds each
  // Rush mode achievements
  | 'rush_beginner'     // Complete first rush session
  | 'rush_10'           // Score 10+ in rush mode
  | 'rush_20'           // Score 20+ in rush mode
  | 'rush_50'           // Score 50+ in rush mode
  // Collection achievements
  | 'level_complete'    // Complete all puzzles in a level
  | 'difficulty_master' // Complete 50 advanced puzzles
  | 'beginner_graduate' // Complete 100 beginner puzzles
  // Special achievements
  | 'comeback_kid'      // Break and restart a streak
  | 'dedicated';        // Play 7 days in a row without missing

/** Static definition of an achievement (immutable) */
export interface AchievementDefinition {
  readonly id: AchievementId;
  readonly name: string;
  readonly description: string;
  readonly category: AchievementCategory;
  readonly tier: AchievementTier;
  readonly target: number;
  readonly icon: string; // Emoji for display
  readonly hidden?: boolean; // Hidden until unlocked
}

/** User's progress toward an achievement */
export interface AchievementProgress {
  readonly achievementId: AchievementId;
  readonly currentValue: number;
  readonly unlockedAt: string | null; // ISO 8601 or null if locked
}

/** Combined view of definition + user progress */
export interface AchievementWithProgress extends AchievementDefinition {
  readonly currentValue: number;
  readonly unlockedAt: string | null;
  readonly isUnlocked: boolean;
  readonly progressPercent: number;
}

/** Achievement notification data */
export interface AchievementNotification {
  readonly achievement: AchievementDefinition;
  readonly unlockedAt: string;
  readonly isNew: boolean;
}

// ============================================================================
// Achievement Definitions Registry
// ============================================================================

/** All achievement definitions */
export const ACHIEVEMENT_DEFINITIONS: readonly AchievementDefinition[] = [
  // Puzzle milestones
  {
    id: 'first_puzzle',
    name: 'First Steps',
    description: 'Solve your first puzzle',
    category: 'puzzles',
    tier: 'bronze',
    target: 1,
    icon: '🎯',
  },
  {
    id: 'ten_puzzles',
    name: 'Getting Started',
    description: 'Solve 10 puzzles',
    category: 'puzzles',
    tier: 'bronze',
    target: 10,
    icon: '📚',
  },
  {
    id: 'fifty_puzzles',
    name: 'Puzzle Enthusiast',
    description: 'Solve 50 puzzles',
    category: 'puzzles',
    tier: 'silver',
    target: 50,
    icon: '⭐',
  },
  {
    id: 'hundred_puzzles',
    name: 'Century Solver',
    description: 'Solve 100 puzzles',
    category: 'puzzles',
    tier: 'silver',
    target: 100,
    icon: '💯',
  },
  {
    id: 'five_hundred',
    name: 'Puzzle Master',
    description: 'Solve 500 puzzles',
    category: 'puzzles',
    tier: 'gold',
    target: 500,
    icon: '🏆',
  },
  {
    id: 'thousand_puzzles',
    name: 'Grandmaster',
    description: 'Solve 1000 puzzles',
    category: 'puzzles',
    tier: 'platinum',
    target: 1000,
    icon: '👑',
  },

  // Streak achievements
  {
    id: 'streak_7',
    name: 'Weekly Warrior',
    description: 'Maintain a 7-day streak',
    category: 'streaks',
    tier: 'bronze',
    target: 7,
    icon: '🔥',
  },
  {
    id: 'streak_30',
    name: 'Monthly Master',
    description: 'Maintain a 30-day streak',
    category: 'streaks',
    tier: 'silver',
    target: 30,
    icon: '🌟',
  },
  {
    id: 'streak_100',
    name: 'Hundred Days',
    description: 'Maintain a 100-day streak',
    category: 'streaks',
    tier: 'gold',
    target: 100,
    icon: '💪',
  },
  {
    id: 'streak_365',
    name: 'Year of Go',
    description: 'Maintain a 365-day streak',
    category: 'streaks',
    tier: 'platinum',
    target: 365,
    icon: '🎊',
  },

  // Skill achievements
  {
    id: 'perfect_ten',
    name: 'Perfect Ten',
    description: 'Get 10 perfect solves (no hints, first attempt)',
    category: 'mastery',
    tier: 'silver',
    target: 10,
    icon: '✨',
  },
  {
    id: 'no_hints_master',
    name: 'Pure Skill',
    description: 'Solve 50 puzzles without using hints',
    category: 'mastery',
    tier: 'gold',
    target: 50,
    icon: '🧠',
  },
  {
    id: 'speed_demon',
    name: 'Speed Demon',
    description: 'Solve a puzzle in under 10 seconds',
    category: 'mastery',
    tier: 'silver',
    target: 1,
    icon: '⚡',
  },
  {
    id: 'quick_thinker',
    name: 'Quick Thinker',
    description: 'Solve 5 puzzles in under 30 seconds each',
    category: 'mastery',
    tier: 'gold',
    target: 5,
    icon: '🚀',
  },

  // Rush mode achievements
  {
    id: 'rush_beginner',
    name: 'Rush Hour',
    description: 'Complete your first puzzle rush session',
    category: 'rush',
    tier: 'bronze',
    target: 1,
    icon: '⏱️',
  },
  {
    id: 'rush_10',
    name: 'Rush Runner',
    description: 'Score 10 or more in puzzle rush',
    category: 'rush',
    tier: 'silver',
    target: 10,
    icon: '🏃',
  },
  {
    id: 'rush_20',
    name: 'Rush Champion',
    description: 'Score 20 or more in puzzle rush',
    category: 'rush',
    tier: 'gold',
    target: 20,
    icon: '🎖️',
  },
  {
    id: 'rush_50',
    name: 'Rush Legend',
    description: 'Score 50 or more in puzzle rush',
    category: 'rush',
    tier: 'platinum',
    target: 50,
    icon: '🌠',
  },

  // Collection achievements
  {
    id: 'level_complete',
    name: 'Level Complete',
    description: 'Complete all puzzles in a single level',
    category: 'collection',
    tier: 'silver',
    target: 1,
    icon: '📋',
  },
  {
    id: 'difficulty_master',
    name: 'Difficulty Master',
    description: 'Complete 50 advanced puzzles',
    category: 'collection',
    tier: 'gold',
    target: 50,
    icon: '🎓',
  },
  {
    id: 'beginner_graduate',
    name: 'Beginner Graduate',
    description: 'Complete 100 beginner puzzles',
    category: 'collection',
    tier: 'silver',
    target: 100,
    icon: '🎒',
  },

  // Special achievements
  {
    id: 'comeback_kid',
    name: 'Comeback Kid',
    description: 'Return after breaking a streak and start a new one',
    category: 'special',
    tier: 'bronze',
    target: 1,
    icon: '🔄',
    hidden: true,
  },
  {
    id: 'dedicated',
    name: 'Dedicated',
    description: 'Play every day for a week without skipping',
    category: 'special',
    tier: 'silver',
    target: 7,
    icon: '💎',
  },
];

/** Map of achievement ID to definition for quick lookup */
export const ACHIEVEMENT_MAP: ReadonlyMap<AchievementId, AchievementDefinition> = new Map(
  ACHIEVEMENT_DEFINITIONS.map((def) => [def.id, def])
);

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get achievement definition by ID
 */
export function getAchievementDefinition(id: AchievementId): AchievementDefinition | undefined {
  return ACHIEVEMENT_MAP.get(id);
}

/**
 * Get all achievements in a category
 */
export function getAchievementsByCategory(category: AchievementCategory): readonly AchievementDefinition[] {
  return ACHIEVEMENT_DEFINITIONS.filter((def) => def.category === category);
}

/**
 * Get all achievements of a tier
 */
export function getAchievementsByTier(tier: AchievementTier): readonly AchievementDefinition[] {
  return ACHIEVEMENT_DEFINITIONS.filter((def) => def.tier === tier);
}

/**
 * Calculate progress percentage (0-100)
 */
export function calculateProgressPercent(current: number, target: number): number {
  if (target <= 0) return 100;
  return Math.min(100, Math.floor((current / target) * 100));
}

/**
 * Check if achievement is unlocked
 */
export function isAchievementUnlocked(current: number, target: number): boolean {
  return current >= target;
}

/**
 * Combine definition with user progress
 */
export function combineWithProgress(
  definition: AchievementDefinition,
  progress: AchievementProgress | undefined
): AchievementWithProgress {
  const currentValue = progress?.currentValue ?? 0;
  const unlockedAt = progress?.unlockedAt ?? null;
  const isUnlocked = unlockedAt !== null || currentValue >= definition.target;
  
  return {
    ...definition,
    currentValue,
    unlockedAt,
    isUnlocked,
    progressPercent: calculateProgressPercent(currentValue, definition.target),
  };
}

/**
 * Get tier color for display
 */
export function getTierColor(tier: AchievementTier): string {
  switch (tier) {
    case 'bronze':
      return '#92734A';
    case 'silver':
      return '#C0C0C0';
    case 'gold':
      return '#3B6D96';
    case 'platinum':
      return '#E5E4E2';
    default:
      return '#808080';
  }
}

/**
 * Get tier display name
 */
export function getTierDisplayName(tier: AchievementTier): string {
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}

/**
 * Sort achievements by unlock status, then tier, then name
 */
export function sortAchievements(achievements: readonly AchievementWithProgress[]): AchievementWithProgress[] {
  const tierOrder: Record<AchievementTier, number> = {
    platinum: 0,
    gold: 1,
    silver: 2,
    bronze: 3,
  };

  return [...achievements].sort((a, b) => {
    // Unlocked first
    if (a.isUnlocked !== b.isUnlocked) {
      return a.isUnlocked ? -1 : 1;
    }
    // Then by tier (platinum > gold > silver > bronze)
    if (a.tier !== b.tier) {
      return tierOrder[a.tier] - tierOrder[b.tier];
    }
    // Then by progress percent (descending)
    if (a.progressPercent !== b.progressPercent) {
      return b.progressPercent - a.progressPercent;
    }
    // Finally alphabetically
    return a.name.localeCompare(b.name);
  });
}

export default {
  ACHIEVEMENT_DEFINITIONS,
  ACHIEVEMENT_MAP,
  getAchievementDefinition,
  getAchievementsByCategory,
  getAchievementsByTier,
  calculateProgressPercent,
  isAchievementUnlocked,
  combineWithProgress,
  getTierColor,
  getTierDisplayName,
  sortAchievements,
};
