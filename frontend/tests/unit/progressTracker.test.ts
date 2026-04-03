/**
 * Tests for Progress Tracker Service
 * @module tests/unit/progressTracker.test
 *
 * Covers: FR-015 to FR-022, US3
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  loadProgress,
  saveProgress,
  resetProgress,
  migrateProgress,
  recordPuzzleCompletion,
  isPuzzleCompleted,
  getPuzzleCompletion,
  unlockLevel,
  isLevelUnlocked,
  getStatistics,
  getStreakData,
  updateStreakData,
  getAchievements,
  addAchievement,
  updateRushHighScore,
  getRushHighScore,
  getPreferences,
  updatePreferences,
  getLevelCompletionCount,
  exportProgress,
  importProgress,
  PROGRESS_STORAGE_KEY,
  PROGRESS_SCHEMA_VERSION,
} from '../../src/services/progressTracker';
import { createInitialProgress } from '../../src/models/progress';

describe('progressTracker', () => {
  let mockStore: Record<string, string>;

  beforeEach(() => {
    // Create fresh mock store
    mockStore = {};

    // Create mock localStorage
    const mockLocalStorage = {
      getItem: vi.fn((key: string) => mockStore[key] ?? null),
      setItem: vi.fn((key: string, value: string) => {
        mockStore[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete mockStore[key];
      }),
      clear: vi.fn(() => {
        mockStore = {};
      }),
      get length() {
        return Object.keys(mockStore).length;
      },
      key: vi.fn((i: number) => Object.keys(mockStore)[i] ?? null),
    };

    Object.defineProperty(global, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('loadProgress', () => {
    it('should return initial progress when no data stored', () => {
      const result = loadProgress();

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.data!.version).toBe(PROGRESS_SCHEMA_VERSION);
      expect(result.data!.completedPuzzles).toEqual({});
    });

    it('should load existing progress from localStorage', () => {
      const existing = createInitialProgress();
      const completedPuzzles = {
        ...existing.completedPuzzles,
        'test-puzzle': {
          puzzleId: 'test-puzzle',
          completedAt: '2026-01-20T10:00:00Z',
          timeSpentMs: 30000,
          attempts: 1,
          hintsUsed: 0,
          perfectSolve: true,
        },
      };
      const withPuzzle = { ...existing, completedPuzzles };
      mockStore[PROGRESS_STORAGE_KEY] = JSON.stringify(withPuzzle);

      const result = loadProgress();

      expect(result.success).toBe(true);
      expect(result.data!.completedPuzzles['test-puzzle']).toBeDefined();
    });

    it('should reset to initial when data is invalid', () => {
      mockStore[PROGRESS_STORAGE_KEY] = 'invalid json';

      const result = loadProgress();

      expect(result.success).toBe(false);
      expect(result.error).toBe('parse_error');
    });
  });

  describe('saveProgress', () => {
    it('should save progress to localStorage', () => {
      const progress = createInitialProgress();

      const result = saveProgress(progress);

      expect(result.success).toBe(true);
      expect(mockStore[PROGRESS_STORAGE_KEY]).toBeDefined();
    });
  });

  describe('resetProgress', () => {
    it('should reset to initial state', () => {
      const existing = createInitialProgress();
      mockStore[PROGRESS_STORAGE_KEY] = JSON.stringify(existing);

      const result = resetProgress();

      expect(result.success).toBe(true);
      expect(result.data!.completedPuzzles).toEqual({});
    });
  });

  describe('migrateProgress', () => {
    it('should migrate from version 0 to current', () => {
      const oldProgress = {
        version: 0,
      } as any;

      const result = migrateProgress(oldProgress);

      expect(result.success).toBe(true);
      expect(result.data!.version).toBe(PROGRESS_SCHEMA_VERSION);
    });
  });

  describe('recordPuzzleCompletion', () => {
    it('should record a puzzle completion', () => {
      const result = recordPuzzleCompletion('level1/puzzle1', {
        timeSpentMs: 45000,
        attempts: 2,
        hintsUsed: 1,
        perfectSolve: false,
        difficulty: 'intermediate',
      });

      expect(result.success).toBe(true);
      expect(result.data!.completedPuzzles['level1/puzzle1']).toBeDefined();
      expect(
        result.data!.completedPuzzles['level1/puzzle1']!.attempts
      ).toBe(2);
    });

    it('should update statistics', () => {
      recordPuzzleCompletion('puzzle1', {
        timeSpentMs: 30000,
        attempts: 1,
        hintsUsed: 0,
        perfectSolve: true,
        difficulty: 'beginner',
      });

      const stats = getStatistics();

      expect(stats.totalSolved).toBe(1);
      expect(stats.totalTimeMs).toBe(30000);
    });
  });

  describe('isPuzzleCompleted', () => {
    it('should return true for completed puzzle', () => {
      recordPuzzleCompletion('puzzle1', {
        timeSpentMs: 30000,
        attempts: 1,
        hintsUsed: 0,
        perfectSolve: true,
        difficulty: 'beginner',
      });

      expect(isPuzzleCompleted('puzzle1')).toBe(true);
    });

    it('should return false for uncompleted puzzle', () => {
      expect(isPuzzleCompleted('nonexistent')).toBe(false);
    });
  });

  describe('getPuzzleCompletion', () => {
    it('should return completion data', () => {
      recordPuzzleCompletion('puzzle1', {
        timeSpentMs: 60000,
        attempts: 3,
        hintsUsed: 2,
        perfectSolve: false,
        difficulty: 'advanced',
      });

      const completion = getPuzzleCompletion('puzzle1');

      expect(completion).toBeDefined();
      expect(completion!.attempts).toBe(3);
      expect(completion!.hintsUsed).toBe(2);
    });
  });

  describe('unlockLevel', () => {
    it('should unlock a level', () => {
      const result = unlockLevel('2026-01-20');

      expect(result.success).toBe(true);
      expect(result.data!.unlockedLevels).toContain('2026-01-20');
    });

    it('should not duplicate unlocked levels', () => {
      unlockLevel('2026-01-20');
      unlockLevel('2026-01-20');

      const result = loadProgress();
      const count = result.data!.unlockedLevels.filter(
        (l) => l === '2026-01-20'
      ).length;

      expect(count).toBe(1);
    });
  });

  describe('isLevelUnlocked', () => {
    it('should return true for unlocked level', () => {
      unlockLevel('level1');

      expect(isLevelUnlocked('level1')).toBe(true);
    });

    it('should return false for locked level', () => {
      expect(isLevelUnlocked('locked')).toBe(false);
    });
  });

  describe('streak management', () => {
    it('should update streak data', () => {
      const streakData = {
        currentStreak: 5,
        longestStreak: 10,
        lastPlayedDate: '2026-01-20',
        streakStartDate: '2026-01-15',
      };

      updateStreakData(streakData);

      const result = getStreakData();
      expect(result.currentStreak).toBe(5);
      expect(result.longestStreak).toBe(10);
    });
  });

  describe('achievements', () => {
    it('should add an achievement', () => {
      const result = addAchievement({
        id: 'first_solve',
        name: 'First Solve',
        description: 'Solved your first puzzle',
        target: 1,
        progress: 1,
      });

      expect(result.success).toBe(true);
      expect(result.data!.achievements).toHaveLength(1);
    });

    it('should not duplicate achievements', () => {
      addAchievement({
        id: 'first_solve',
        name: 'First Solve',
        description: 'Solved your first puzzle',
        target: 1,
        progress: 1,
      });
      addAchievement({
        id: 'first_solve',
        name: 'First Solve',
        description: 'Solved your first puzzle',
        target: 1,
        progress: 1,
      });

      const achievements = getAchievements();
      expect(achievements).toHaveLength(1);
    });
  });

  describe('rush high scores', () => {
    it('should update high score when higher', () => {
      updateRushHighScore(10, 180);
      updateRushHighScore(15, 180);

      expect(getRushHighScore()).toBe(15);
    });

    it('should not update high score when lower', () => {
      updateRushHighScore(15, 180);
      updateRushHighScore(10, 180);

      expect(getRushHighScore()).toBe(15);
    });
  });

  describe('preferences', () => {
    it('should update preferences', () => {
      updatePreferences({ soundEnabled: false });

      const prefs = getPreferences();
      expect(prefs.soundEnabled).toBe(false);
    });

    it('should merge with existing preferences', () => {
      updatePreferences({ soundEnabled: false });
      updatePreferences({ theme: 'dark' });

      const prefs = getPreferences();
      expect(prefs.soundEnabled).toBe(false);
      expect(prefs.theme).toBe('dark');
    });
  });

  describe('getLevelCompletionCount', () => {
    it('should count completed puzzles in a level', () => {
      recordPuzzleCompletion('level1/puzzle1', {
        timeSpentMs: 30000,
        attempts: 1,
        hintsUsed: 0,
        perfectSolve: true,
        difficulty: 'beginner',
      });
      recordPuzzleCompletion('level1/puzzle2', {
        timeSpentMs: 30000,
        attempts: 1,
        hintsUsed: 0,
        perfectSolve: true,
        difficulty: 'beginner',
      });
      recordPuzzleCompletion('level2/puzzle1', {
        timeSpentMs: 30000,
        attempts: 1,
        hintsUsed: 0,
        perfectSolve: true,
        difficulty: 'beginner',
      });

      expect(getLevelCompletionCount('level1')).toBe(2);
      expect(getLevelCompletionCount('level2')).toBe(1);
    });
  });

  describe('export/import', () => {
    it('should export progress as JSON', () => {
      recordPuzzleCompletion('puzzle1', {
        timeSpentMs: 30000,
        attempts: 1,
        hintsUsed: 0,
        perfectSolve: true,
        difficulty: 'beginner',
      });

      const exported = exportProgress();

      expect(exported).not.toBeNull();
      const parsed = JSON.parse(exported!);
      expect(parsed.completedPuzzles['puzzle1']).toBeDefined();
    });

    it('should import progress from JSON', () => {
      const data = createInitialProgress();
      const completedPuzzles = {
        ...data.completedPuzzles,
        'imported-puzzle': {
          puzzleId: 'imported-puzzle',
          completedAt: '2026-01-20T10:00:00Z',
          timeSpentMs: 30000,
          attempts: 1,
          hintsUsed: 0,
          perfectSolve: true,
        },
      };

      const result = importProgress(JSON.stringify({ ...data, completedPuzzles }));

      expect(result.success).toBe(true);
      expect(isPuzzleCompleted('imported-puzzle')).toBe(true);
    });

    it('should reject invalid import data', () => {
      const result = importProgress('{ "invalid": true }');

      expect(result.success).toBe(false);
      expect(result.error).toBe('parse_error');
    });
  });
});
