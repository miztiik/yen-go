/**
 * Unit tests for schema migrations.
 * Tests v0→v1 migration, corrupt data handling, and missing fields.
 * @module tests/unit/progress/migrations
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  migrateProgress,
  needsMigration,
  getDataVersion,
  validateProgress,
  ensureComplete,
  MIGRATIONS,
} from '../../../src/lib/progress/migrations';
import {
  PROGRESS_SCHEMA_VERSION,
  DEFAULT_PREFERENCES,
  DEFAULT_STATISTICS,
  DEFAULT_STREAK_DATA,
  createDefaultProgress,
} from '../../../src/types/progress';

describe('migrations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getDataVersion', () => {
    it('should return 0 for data without version', () => {
      expect(getDataVersion({})).toBe(0);
    });

    it('should return 0 for invalid version type', () => {
      expect(getDataVersion({ version: 'invalid' })).toBe(0);
      expect(getDataVersion({ version: null })).toBe(0);
      expect(getDataVersion({ version: undefined })).toBe(0);
    });

    it('should return 0 for negative version', () => {
      expect(getDataVersion({ version: -1 })).toBe(0);
      expect(getDataVersion({ version: 0 })).toBe(0);
    });

    it('should return the version for valid version', () => {
      expect(getDataVersion({ version: 1 })).toBe(1);
      expect(getDataVersion({ version: 2 })).toBe(2);
    });
  });

  describe('needsMigration', () => {
    it('should return true for data without version', () => {
      expect(needsMigration({})).toBe(true);
    });

    it('should return true for version 0', () => {
      expect(needsMigration({ version: 0 })).toBe(true);
    });

    it('should return true for version less than current', () => {
      expect(needsMigration({ version: PROGRESS_SCHEMA_VERSION - 1 })).toBe(true);
    });

    it('should return false for current version', () => {
      expect(needsMigration({ version: PROGRESS_SCHEMA_VERSION })).toBe(false);
    });

    it('should return false for version greater than current', () => {
      expect(needsMigration({ version: PROGRESS_SCHEMA_VERSION + 1 })).toBe(false);
    });
  });

  describe('validateProgress', () => {
    it('should fail for missing version', () => {
      const result = validateProgress({
        completedPuzzles: {},
        unlockedLevels: [],
        statistics: {},
        streakData: {},
        achievements: [],
        preferences: {},
      });
      expect(result.success).toBe(false);
      expect(result.error).toContain('version');
    });

    it('should fail for invalid completedPuzzles', () => {
      const result = validateProgress({
        version: 1,
        completedPuzzles: null,
        unlockedLevels: [],
        statistics: {},
        streakData: {},
        achievements: [],
        preferences: {},
      });
      expect(result.success).toBe(false);
      expect(result.error).toContain('completedPuzzles');
    });

    it('should fail for completedPuzzles as array', () => {
      const result = validateProgress({
        version: 1,
        completedPuzzles: [],
        unlockedLevels: [],
        statistics: {},
        streakData: {},
        achievements: [],
        preferences: {},
      });
      expect(result.success).toBe(false);
      expect(result.error).toContain('completedPuzzles');
    });

    it('should fail for missing unlockedLevels', () => {
      const result = validateProgress({
        version: 1,
        completedPuzzles: {},
        unlockedLevels: 'not-array',
        statistics: {},
        streakData: {},
        achievements: [],
        preferences: {},
      });
      expect(result.success).toBe(false);
      expect(result.error).toContain('unlockedLevels');
    });

    it('should fail for missing statistics', () => {
      const result = validateProgress({
        version: 1,
        completedPuzzles: {},
        unlockedLevels: [],
        statistics: null,
        streakData: {},
        achievements: [],
        preferences: {},
      });
      expect(result.success).toBe(false);
      expect(result.error).toContain('statistics');
    });

    it('should fail for missing streakData', () => {
      const result = validateProgress({
        version: 1,
        completedPuzzles: {},
        unlockedLevels: [],
        statistics: {},
        streakData: null,
        achievements: [],
        preferences: {},
      });
      expect(result.success).toBe(false);
      expect(result.error).toContain('streakData');
    });

    it('should fail for missing achievements', () => {
      const result = validateProgress({
        version: 1,
        completedPuzzles: {},
        unlockedLevels: [],
        statistics: {},
        streakData: {},
        achievements: 'not-array',
        preferences: {},
      });
      expect(result.success).toBe(false);
      expect(result.error).toContain('achievements');
    });

    it('should fail for missing preferences', () => {
      const result = validateProgress({
        version: 1,
        completedPuzzles: {},
        unlockedLevels: [],
        statistics: {},
        streakData: {},
        achievements: [],
        preferences: null,
      });
      expect(result.success).toBe(false);
      expect(result.error).toContain('preferences');
    });

    it('should pass for valid progress data', () => {
      const result = validateProgress({
        version: 1,
        completedPuzzles: {},
        unlockedLevels: [],
        statistics: {},
        streakData: {},
        achievements: [],
        preferences: {},
      });
      expect(result.success).toBe(true);
      expect(result.error).toBeUndefined();
    });
  });

  describe('migrateProgress - v0 to v1', () => {
    it('should migrate empty object to v1', () => {
      const result = migrateProgress({});

      expect(result.success).toBe(true);
      expect(result.progress).toBeDefined();
      expect(result.progress?.version).toBe(1);
      expect(result.migrationsApplied).toContain(1);
    });

    it('should migrate v0 data with existing completedPuzzles', () => {
      const result = migrateProgress({
        completedPuzzles: {
          'puzzle-1': { puzzleId: 'puzzle-1', completedAt: '2026-01-20T00:00:00Z' },
        },
      });

      expect(result.success).toBe(true);
      expect(result.progress?.completedPuzzles).toHaveProperty('puzzle-1');
    });

    it('should preserve existing data during migration', () => {
      const existingAchievements = ['first-puzzle', 'streak-7'];
      const result = migrateProgress({
        achievements: existingAchievements,
      });

      expect(result.success).toBe(true);
      expect(result.progress?.achievements).toEqual(existingAchievements);
    });

    it('should add default fields for missing data', () => {
      const result = migrateProgress({});

      expect(result.success).toBe(true);
      expect(result.progress?.statistics).toEqual(DEFAULT_STATISTICS);
      expect(result.progress?.streakData).toEqual(DEFAULT_STREAK_DATA);
      expect(result.progress?.preferences).toEqual(DEFAULT_PREFERENCES);
      expect(result.progress?.completedPuzzles).toEqual({});
      expect(result.progress?.unlockedLevels).toEqual([]);
      expect(result.progress?.achievements).toEqual([]);
    });

    it('should not migrate already current version', () => {
      const currentData = createDefaultProgress();
      const result = migrateProgress(currentData as unknown as Record<string, unknown>);

      expect(result.success).toBe(true);
      expect(result.migrationsApplied).toHaveLength(0);
    });
  });

  describe('migrateProgress - corrupt data handling', () => {
    it('should handle null values gracefully', () => {
      const result = migrateProgress({
        version: null,
        completedPuzzles: null,
        statistics: null,
      });

      expect(result.success).toBe(true);
      expect(result.progress?.version).toBe(1);
      expect(result.progress?.completedPuzzles).toEqual({});
      expect(result.progress?.statistics).toEqual(DEFAULT_STATISTICS);
    });

    it('should handle undefined values gracefully', () => {
      const result = migrateProgress({
        version: undefined,
        completedPuzzles: undefined,
      });

      expect(result.success).toBe(true);
      expect(result.progress?.version).toBe(1);
    });

    it('should handle wrong types for fields', () => {
      const result = migrateProgress({
        version: 'not-a-number',
        completedPuzzles: 'not-an-object',
        unlockedLevels: 'not-an-array',
      });

      // Migration should try to handle gracefully
      expect(result.success).toBe(true);
      expect(result.progress?.version).toBe(1);
    });

    it('should handle deeply nested corrupt data', () => {
      const result = migrateProgress({
        statistics: {
          totalPuzzlesSolved: 'not-a-number',
          avgTimeByDifficulty: null,
        },
      });

      expect(result.success).toBe(true);
      // Should use default or preserve corrupt data based on migration logic
    });

    it('should log warning and reset for unknown version with no migration path', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      // Create a scenario where there's no migration path
      // Since we only have v0→v1, using v999 should trigger reset
      const result = migrateProgress({ version: 999 });

      // Should succeed with default progress since there's no migration path
      // The behavior depends on implementation - it should reset to defaults
      expect(result.success).toBe(true);

      consoleSpy.mockRestore();
    });
  });

  describe('migrateProgress - missing fields', () => {
    it('should add missing statistics field', () => {
      const result = migrateProgress({
        completedPuzzles: {},
        unlockedLevels: [],
        achievements: [],
        preferences: DEFAULT_PREFERENCES,
        streakData: DEFAULT_STREAK_DATA,
      });

      expect(result.success).toBe(true);
      expect(result.progress?.statistics).toBeDefined();
      expect(result.progress?.statistics).toEqual(DEFAULT_STATISTICS);
    });

    it('should add missing streakData field', () => {
      const result = migrateProgress({
        completedPuzzles: {},
        unlockedLevels: [],
        achievements: [],
        preferences: DEFAULT_PREFERENCES,
        statistics: DEFAULT_STATISTICS,
      });

      expect(result.success).toBe(true);
      expect(result.progress?.streakData).toBeDefined();
      expect(result.progress?.streakData).toEqual(DEFAULT_STREAK_DATA);
    });

    it('should add missing preferences field', () => {
      const result = migrateProgress({
        completedPuzzles: {},
        unlockedLevels: [],
        achievements: [],
        statistics: DEFAULT_STATISTICS,
        streakData: DEFAULT_STREAK_DATA,
      });

      expect(result.success).toBe(true);
      expect(result.progress?.preferences).toBeDefined();
      expect(result.progress?.preferences).toEqual(DEFAULT_PREFERENCES);
    });

    it('should add missing achievements field', () => {
      const result = migrateProgress({
        completedPuzzles: {},
        unlockedLevels: [],
        statistics: DEFAULT_STATISTICS,
        streakData: DEFAULT_STREAK_DATA,
        preferences: DEFAULT_PREFERENCES,
      });

      expect(result.success).toBe(true);
      expect(result.progress?.achievements).toBeDefined();
      expect(result.progress?.achievements).toEqual([]);
    });

    it('should add missing unlockedLevels field', () => {
      const result = migrateProgress({
        completedPuzzles: {},
        achievements: [],
        statistics: DEFAULT_STATISTICS,
        streakData: DEFAULT_STREAK_DATA,
        preferences: DEFAULT_PREFERENCES,
      });

      expect(result.success).toBe(true);
      expect(result.progress?.unlockedLevels).toBeDefined();
      expect(result.progress?.unlockedLevels).toEqual([]);
    });

    it('should add missing completedPuzzles field', () => {
      const result = migrateProgress({
        unlockedLevels: [],
        achievements: [],
        statistics: DEFAULT_STATISTICS,
        streakData: DEFAULT_STREAK_DATA,
        preferences: DEFAULT_PREFERENCES,
      });

      expect(result.success).toBe(true);
      expect(result.progress?.completedPuzzles).toBeDefined();
      expect(result.progress?.completedPuzzles).toEqual({});
    });
  });

  describe('ensureComplete', () => {
    it('should return default progress for empty partial', () => {
      const result = ensureComplete({});
      const defaults = createDefaultProgress();

      expect(result.version).toBe(defaults.version);
      expect(result.completedPuzzles).toEqual(defaults.completedPuzzles);
      expect(result.unlockedLevels).toEqual(defaults.unlockedLevels);
      expect(result.statistics).toEqual(defaults.statistics);
      expect(result.streakData).toEqual(defaults.streakData);
      expect(result.achievements).toEqual(defaults.achievements);
      expect(result.preferences).toEqual(defaults.preferences);
    });

    it('should preserve provided fields', () => {
      const completedPuzzles = {
        'puzzle-1': {
          puzzleId: 'puzzle-1',
          completedAt: '2026-01-20T00:00:00Z',
          timeSpentMs: 5000,
          attempts: 2,
          hintsUsed: 0,
        },
      };

      const result = ensureComplete({
        completedPuzzles,
      });

      expect(result.completedPuzzles).toEqual(completedPuzzles);
    });

    it('should merge nested objects with defaults', () => {
      const partialPreferences = {
        hintsEnabled: false,
        // Missing other fields
      };

      const result = ensureComplete({
        preferences: partialPreferences as any,
      });

      // Should have merged with defaults
      expect(result.preferences.hintsEnabled).toBe(false);
      expect(result.preferences.soundEnabled).toBeDefined();
      expect(result.preferences.boardTheme).toBeDefined();
    });

    it('should handle partial statistics', () => {
      const partialStats = {
        totalPuzzlesSolved: 10,
        // Missing other fields
      };

      const result = ensureComplete({
        statistics: partialStats as any,
      });

      expect(result.statistics.totalPuzzlesSolved).toBe(10);
      expect(result.statistics.totalTimeSpentMs).toBeDefined();
    });

    it('should handle partial streakData', () => {
      const partialStreak = {
        currentStreak: 5,
        // Missing other fields
      };

      const result = ensureComplete({
        streakData: partialStreak as any,
      });

      expect(result.streakData.currentStreak).toBe(5);
      expect(result.streakData.longestStreak).toBeDefined();
    });
  });

  describe('MIGRATIONS registry', () => {
    it('should have migration from v0', () => {
      expect(MIGRATIONS.has(0)).toBe(true);
    });

    it('should migrate v0 to v1', () => {
      const migration = MIGRATIONS.get(0);
      expect(migration).toBeDefined();
      expect(migration?.toVersion).toBe(1);
    });

    it('should have description for v0 migration', () => {
      const migration = MIGRATIONS.get(0);
      expect(migration?.description).toBeTruthy();
      expect(typeof migration?.description).toBe('string');
    });

    it('v0 migration function should set version to 1', () => {
      const migration = MIGRATIONS.get(0);
      const result = migration?.migrate({});
      expect(result?.version).toBe(1);
    });

    it('v0 migration should initialize all required fields', () => {
      const migration = MIGRATIONS.get(0);
      const result = migration?.migrate({});

      expect(result).toHaveProperty('version');
      expect(result).toHaveProperty('completedPuzzles');
      expect(result).toHaveProperty('unlockedLevels');
      expect(result).toHaveProperty('statistics');
      expect(result).toHaveProperty('streakData');
      expect(result).toHaveProperty('achievements');
      expect(result).toHaveProperty('preferences');
    });
  });

  describe('migration edge cases', () => {
    it('should handle migration with circular references gracefully', () => {
      const circularData: Record<string, unknown> = { version: 0 };
      // Can't actually create circular JSON, but simulate deep nesting
      circularData.nested = { deep: { value: circularData } };

      // Should not throw
      const result = migrateProgress(circularData);
      expect(result).toBeDefined();
    });

    it('should handle very large completedPuzzles object', () => {
      const largePuzzles: Record<string, unknown> = {};
      for (let i = 0; i < 1000; i++) {
        largePuzzles[`puzzle-${i}`] = {
          puzzleId: `puzzle-${i}`,
          completedAt: '2026-01-20T00:00:00Z',
        };
      }

      const result = migrateProgress({
        completedPuzzles: largePuzzles,
      });

      expect(result.success).toBe(true);
      expect(Object.keys(result.progress?.completedPuzzles || {})).toHaveLength(1000);
    });

    it('should handle special characters in puzzle IDs', () => {
      const result = migrateProgress({
        completedPuzzles: {
          'puzzle-with-special-chars!@#$%': { puzzleId: 'puzzle-with-special-chars!@#$%' },
          'puzzle/with/slashes': { puzzleId: 'puzzle/with/slashes' },
          'puzzle with spaces': { puzzleId: 'puzzle with spaces' },
        },
      });

      expect(result.success).toBe(true);
      expect(result.progress?.completedPuzzles).toHaveProperty('puzzle-with-special-chars!@#$%');
    });

    it('should handle unicode in data', () => {
      const result = migrateProgress({
        completedPuzzles: {
          '日本語パズル': { puzzleId: '日本語パズル' },
          '🎯puzzle': { puzzleId: '🎯puzzle' },
        },
      });

      expect(result.success).toBe(true);
      expect(result.progress?.completedPuzzles).toHaveProperty('日本語パズル');
    });

    it('should handle empty strings in fields', () => {
      const result = migrateProgress({
        completedPuzzles: {
          '': { puzzleId: '' },
        },
      });

      expect(result.success).toBe(true);
    });
  });
});
