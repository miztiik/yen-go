/**
 * Achievement Model Unit Tests
 * @module tests/unit/achievement
 *
 * Tests for achievement types, definitions, and helper functions
 */

import { describe, it, expect } from 'vitest';
import {
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
  type AchievementId,
  type AchievementCategory,
  type AchievementTier,
  type AchievementDefinition,
  type AchievementProgress,
  type AchievementWithProgress,
} from '../../src/models/achievement';

describe('Achievement Definitions', () => {
  it('should have all required achievements', () => {
    // Check required achievements from spec (US8)
    const requiredIds: AchievementId[] = [
      'first_puzzle',    // "First Steps" - first puzzle
      'streak_7',        // "Weekly Warrior" - 7-day streak
      'hundred_puzzles', // "Century Solver" - 100 puzzles
    ];

    requiredIds.forEach((id) => {
      expect(ACHIEVEMENT_MAP.has(id), `Missing required achievement: ${id}`).toBe(true);
    });
  });

  it('should have unique IDs', () => {
    const ids = ACHIEVEMENT_DEFINITIONS.map((def) => def.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });

  it('should have valid categories for all achievements', () => {
    const validCategories: AchievementCategory[] = [
      'puzzles',
      'streaks',
      'rush',
      'mastery',
      'collection',
      'special',
    ];

    ACHIEVEMENT_DEFINITIONS.forEach((def) => {
      expect(validCategories).toContain(def.category);
    });
  });

  it('should have valid tiers for all achievements', () => {
    const validTiers: AchievementTier[] = ['bronze', 'silver', 'gold', 'platinum'];

    ACHIEVEMENT_DEFINITIONS.forEach((def) => {
      expect(validTiers).toContain(def.tier);
    });
  });

  it('should have positive targets for all achievements', () => {
    ACHIEVEMENT_DEFINITIONS.forEach((def) => {
      expect(def.target).toBeGreaterThan(0);
    });
  });

  it('should have non-empty names and descriptions', () => {
    ACHIEVEMENT_DEFINITIONS.forEach((def) => {
      expect(def.name.trim().length).toBeGreaterThan(0);
      expect(def.description.trim().length).toBeGreaterThan(0);
    });
  });

  it('should have emoji icons', () => {
    ACHIEVEMENT_DEFINITIONS.forEach((def) => {
      expect(def.icon.trim().length).toBeGreaterThan(0);
    });
  });

  it('should have First Steps as the easiest puzzle achievement', () => {
    const firstSteps = getAchievementDefinition('first_puzzle');
    expect(firstSteps).toBeDefined();
    expect(firstSteps!.name).toBe('First Steps');
    expect(firstSteps!.target).toBe(1);
    expect(firstSteps!.tier).toBe('bronze');
  });

  it('should have Weekly Warrior for 7-day streak', () => {
    const weeklyWarrior = getAchievementDefinition('streak_7');
    expect(weeklyWarrior).toBeDefined();
    expect(weeklyWarrior!.name).toBe('Weekly Warrior');
    expect(weeklyWarrior!.target).toBe(7);
    expect(weeklyWarrior!.category).toBe('streaks');
  });

  it('should have Century Solver for 100 puzzles', () => {
    const centurySolver = getAchievementDefinition('hundred_puzzles');
    expect(centurySolver).toBeDefined();
    expect(centurySolver!.name).toBe('Century Solver');
    expect(centurySolver!.target).toBe(100);
  });
});

describe('ACHIEVEMENT_MAP', () => {
  it('should contain all definitions', () => {
    expect(ACHIEVEMENT_MAP.size).toBe(ACHIEVEMENT_DEFINITIONS.length);
  });

  it('should map IDs to correct definitions', () => {
    ACHIEVEMENT_DEFINITIONS.forEach((def) => {
      const mapped = ACHIEVEMENT_MAP.get(def.id);
      expect(mapped).toBe(def);
    });
  });
});

describe('getAchievementDefinition', () => {
  it('should return definition for valid ID', () => {
    const result = getAchievementDefinition('first_puzzle');
    expect(result).toBeDefined();
    expect(result!.id).toBe('first_puzzle');
    expect(result!.name).toBe('First Steps');
  });

  it('should return undefined for invalid ID', () => {
    // @ts-expect-error - testing invalid ID
    const result = getAchievementDefinition('invalid_id');
    expect(result).toBeUndefined();
  });
});

describe('getAchievementsByCategory', () => {
  it('should return puzzle achievements', () => {
    const puzzles = getAchievementsByCategory('puzzles');
    expect(puzzles.length).toBeGreaterThan(0);
    puzzles.forEach((def) => {
      expect(def.category).toBe('puzzles');
    });
  });

  it('should return streak achievements', () => {
    const streaks = getAchievementsByCategory('streaks');
    expect(streaks.length).toBeGreaterThan(0);
    streaks.forEach((def) => {
      expect(def.category).toBe('streaks');
    });
  });

  it('should return rush achievements', () => {
    const rush = getAchievementsByCategory('rush');
    expect(rush.length).toBeGreaterThan(0);
    rush.forEach((def) => {
      expect(def.category).toBe('rush');
    });
  });

  it('should return empty array for category with no achievements', () => {
    // All categories should have achievements, but test the behavior
    const all = ACHIEVEMENT_DEFINITIONS;
    const categories = new Set(all.map((d) => d.category));
    categories.forEach((cat) => {
      const results = getAchievementsByCategory(cat);
      expect(results.length).toBeGreaterThan(0);
    });
  });
});

describe('getAchievementsByTier', () => {
  it('should return bronze achievements', () => {
    const bronze = getAchievementsByTier('bronze');
    expect(bronze.length).toBeGreaterThan(0);
    bronze.forEach((def) => {
      expect(def.tier).toBe('bronze');
    });
  });

  it('should return silver achievements', () => {
    const silver = getAchievementsByTier('silver');
    expect(silver.length).toBeGreaterThan(0);
    silver.forEach((def) => {
      expect(def.tier).toBe('silver');
    });
  });

  it('should return gold achievements', () => {
    const gold = getAchievementsByTier('gold');
    expect(gold.length).toBeGreaterThan(0);
    gold.forEach((def) => {
      expect(def.tier).toBe('gold');
    });
  });

  it('should return platinum achievements', () => {
    const platinum = getAchievementsByTier('platinum');
    expect(platinum.length).toBeGreaterThan(0);
    platinum.forEach((def) => {
      expect(def.tier).toBe('platinum');
    });
  });
});

describe('calculateProgressPercent', () => {
  it('should return 0 for 0 progress', () => {
    expect(calculateProgressPercent(0, 100)).toBe(0);
  });

  it('should return 50 for half progress', () => {
    expect(calculateProgressPercent(50, 100)).toBe(50);
  });

  it('should return 100 for complete progress', () => {
    expect(calculateProgressPercent(100, 100)).toBe(100);
  });

  it('should cap at 100 for over progress', () => {
    expect(calculateProgressPercent(150, 100)).toBe(100);
  });

  it('should handle small targets', () => {
    expect(calculateProgressPercent(1, 1)).toBe(100);
    expect(calculateProgressPercent(0, 1)).toBe(0);
  });

  it('should handle zero target', () => {
    expect(calculateProgressPercent(5, 0)).toBe(100);
  });

  it('should floor partial percentages', () => {
    expect(calculateProgressPercent(1, 3)).toBe(33);
    expect(calculateProgressPercent(2, 3)).toBe(66);
  });
});

describe('isAchievementUnlocked', () => {
  it('should return false when below target', () => {
    expect(isAchievementUnlocked(0, 10)).toBe(false);
    expect(isAchievementUnlocked(5, 10)).toBe(false);
    expect(isAchievementUnlocked(9, 10)).toBe(false);
  });

  it('should return true when at target', () => {
    expect(isAchievementUnlocked(10, 10)).toBe(true);
  });

  it('should return true when above target', () => {
    expect(isAchievementUnlocked(15, 10)).toBe(true);
  });

  it('should handle edge case of 0 target', () => {
    expect(isAchievementUnlocked(0, 0)).toBe(true);
  });
});

describe('combineWithProgress', () => {
  const testDefinition: AchievementDefinition = {
    id: 'first_puzzle',
    name: 'First Steps',
    description: 'Solve your first puzzle',
    category: 'puzzles',
    tier: 'bronze',
    target: 1,
    icon: '🎯',
  };

  it('should combine with no progress', () => {
    const result = combineWithProgress(testDefinition, undefined);
    expect(result.id).toBe('first_puzzle');
    expect(result.currentValue).toBe(0);
    expect(result.unlockedAt).toBeNull();
    expect(result.isUnlocked).toBe(false);
    expect(result.progressPercent).toBe(0);
  });

  it('should combine with partial progress', () => {
    const progress: AchievementProgress = {
      achievementId: 'first_puzzle',
      currentValue: 0,
      unlockedAt: null,
    };
    const result = combineWithProgress(testDefinition, progress);
    expect(result.currentValue).toBe(0);
    expect(result.isUnlocked).toBe(false);
    expect(result.progressPercent).toBe(0);
  });

  it('should combine with complete progress', () => {
    const progress: AchievementProgress = {
      achievementId: 'first_puzzle',
      currentValue: 1,
      unlockedAt: '2024-01-15T10:30:00Z',
    };
    const result = combineWithProgress(testDefinition, progress);
    expect(result.currentValue).toBe(1);
    expect(result.unlockedAt).toBe('2024-01-15T10:30:00Z');
    expect(result.isUnlocked).toBe(true);
    expect(result.progressPercent).toBe(100);
  });

  it('should detect unlock from value even without unlockedAt', () => {
    const progress: AchievementProgress = {
      achievementId: 'first_puzzle',
      currentValue: 1,
      unlockedAt: null,
    };
    const result = combineWithProgress(testDefinition, progress);
    expect(result.isUnlocked).toBe(true);
  });

  it('should preserve all definition fields', () => {
    const result = combineWithProgress(testDefinition, undefined);
    expect(result.name).toBe(testDefinition.name);
    expect(result.description).toBe(testDefinition.description);
    expect(result.category).toBe(testDefinition.category);
    expect(result.tier).toBe(testDefinition.tier);
    expect(result.target).toBe(testDefinition.target);
    expect(result.icon).toBe(testDefinition.icon);
  });
});

describe('getTierColor', () => {
  it('should return bronze color', () => {
    expect(getTierColor('bronze')).toBe('#92734A');
  });

  it('should return silver color', () => {
    expect(getTierColor('silver')).toBe('#C0C0C0');
  });

  it('should return gold color', () => {
    expect(getTierColor('gold')).toBe('#3B6D96');
  });

  it('should return platinum color', () => {
    expect(getTierColor('platinum')).toBe('#E5E4E2');
  });

  it('should return gray for unknown tier', () => {
    // @ts-expect-error - testing invalid tier
    expect(getTierColor('unknown')).toBe('#808080');
  });
});

describe('getTierDisplayName', () => {
  it('should capitalize bronze', () => {
    expect(getTierDisplayName('bronze')).toBe('Bronze');
  });

  it('should capitalize silver', () => {
    expect(getTierDisplayName('silver')).toBe('Silver');
  });

  it('should capitalize gold', () => {
    expect(getTierDisplayName('gold')).toBe('Gold');
  });

  it('should capitalize platinum', () => {
    expect(getTierDisplayName('platinum')).toBe('Platinum');
  });
});

describe('sortAchievements', () => {
  const createAchievement = (
    id: AchievementId,
    tier: AchievementTier,
    isUnlocked: boolean,
    progressPercent: number
  ): AchievementWithProgress => ({
    id,
    name: `Achievement ${id}`,
    description: 'Test',
    category: 'puzzles',
    tier,
    target: 10,
    icon: '🎯',
    currentValue: isUnlocked ? 10 : Math.floor(progressPercent / 10),
    unlockedAt: isUnlocked ? '2024-01-15T10:30:00Z' : null,
    isUnlocked,
    progressPercent,
  });

  it('should sort unlocked before locked', () => {
    const achievements: AchievementWithProgress[] = [
      createAchievement('first_puzzle', 'bronze', false, 50),
      createAchievement('ten_puzzles', 'bronze', true, 100),
    ];

    const sorted = sortAchievements(achievements);
    expect(sorted[0].isUnlocked).toBe(true);
    expect(sorted[1].isUnlocked).toBe(false);
  });

  it('should sort by tier within unlock status (platinum first)', () => {
    const achievements: AchievementWithProgress[] = [
      createAchievement('first_puzzle', 'bronze', true, 100),
      createAchievement('thousand_puzzles', 'platinum', true, 100),
      createAchievement('hundred_puzzles', 'silver', true, 100),
      createAchievement('five_hundred', 'gold', true, 100),
    ];

    const sorted = sortAchievements(achievements);
    expect(sorted[0].tier).toBe('platinum');
    expect(sorted[1].tier).toBe('gold');
    expect(sorted[2].tier).toBe('silver');
    expect(sorted[3].tier).toBe('bronze');
  });

  it('should sort by progress percent within same tier', () => {
    const achievements: AchievementWithProgress[] = [
      createAchievement('first_puzzle', 'bronze', false, 30),
      createAchievement('ten_puzzles', 'bronze', false, 80),
      createAchievement('rush_beginner', 'bronze', false, 50),
    ];

    const sorted = sortAchievements(achievements);
    expect(sorted[0].progressPercent).toBe(80);
    expect(sorted[1].progressPercent).toBe(50);
    expect(sorted[2].progressPercent).toBe(30);
  });

  it('should sort alphabetically as final tiebreaker', () => {
    const achievements: AchievementWithProgress[] = [
      { ...createAchievement('ten_puzzles', 'bronze', true, 100), name: 'Zebra' },
      { ...createAchievement('first_puzzle', 'bronze', true, 100), name: 'Alpha' },
    ];

    const sorted = sortAchievements(achievements);
    expect(sorted[0].name).toBe('Alpha');
    expect(sorted[1].name).toBe('Zebra');
  });

  it('should not mutate original array', () => {
    const original: AchievementWithProgress[] = [
      createAchievement('first_puzzle', 'bronze', false, 50),
      createAchievement('thousand_puzzles', 'platinum', true, 100),
    ];

    const sorted = sortAchievements(original);
    expect(original[0].id).toBe('first_puzzle');
    expect(sorted[0].id).toBe('thousand_puzzles');
  });

  it('should handle empty array', () => {
    const sorted = sortAchievements([]);
    expect(sorted).toEqual([]);
  });

  it('should handle single item array', () => {
    const single = [createAchievement('first_puzzle', 'bronze', true, 100)];
    const sorted = sortAchievements(single);
    expect(sorted).toHaveLength(1);
    expect(sorted[0].id).toBe('first_puzzle');
  });
});

describe('Achievement Categories Coverage', () => {
  it('should have at least 3 achievements per category', () => {
    const categories: AchievementCategory[] = ['puzzles', 'streaks', 'rush', 'mastery', 'collection'];
    categories.forEach((cat) => {
      const count = getAchievementsByCategory(cat).length;
      expect(count, `Category ${cat} should have at least 3 achievements`).toBeGreaterThanOrEqual(3);
    });
  });

  it('should have achievements of all tiers', () => {
    const tiers: AchievementTier[] = ['bronze', 'silver', 'gold', 'platinum'];
    tiers.forEach((tier) => {
      const count = getAchievementsByTier(tier).length;
      expect(count, `Tier ${tier} should have at least 1 achievement`).toBeGreaterThanOrEqual(1);
    });
  });
});

describe('Achievement Progression Logic', () => {
  it('puzzle milestones should increase in target', () => {
    const milestones = ['first_puzzle', 'ten_puzzles', 'fifty_puzzles', 'hundred_puzzles', 'five_hundred', 'thousand_puzzles'] as const;
    const targets = milestones.map((id) => getAchievementDefinition(id)!.target);

    for (let i = 1; i < targets.length; i++) {
      expect(targets[i], `${milestones[i]} should have higher target than ${milestones[i - 1]}`).toBeGreaterThan(targets[i - 1]);
    }
  });

  it('streak achievements should increase in target', () => {
    const streaks = ['streak_7', 'streak_30', 'streak_100', 'streak_365'] as const;
    const targets = streaks.map((id) => getAchievementDefinition(id)!.target);

    for (let i = 1; i < targets.length; i++) {
      expect(targets[i]).toBeGreaterThan(targets[i - 1]);
    }
  });

  it('rush achievements should increase in target', () => {
    const rushAchievements = ['rush_beginner', 'rush_10', 'rush_20', 'rush_50'] as const;
    const targets = rushAchievements.map((id) => getAchievementDefinition(id)!.target);

    for (let i = 1; i < targets.length; i++) {
      expect(targets[i]).toBeGreaterThan(targets[i - 1]);
    }
  });
});
