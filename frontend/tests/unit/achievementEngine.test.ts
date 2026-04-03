/**
 * Achievement Engine Unit Tests
 * @module tests/unit/achievementEngine
 *
 * Tests for achievement detection, progress tracking, and awarding
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  extractMetrics,
  getProgressValue,
  shouldUnlock,
  getUnlockedIds,
  checkAchievements,
  detectNewAchievements,
  processAchievements,
  getAchievementProgress,
  isAchievementUnlocked,
  getAchievementProgressPercent,
  type ProgressMetrics,
  type AchievementCheckResult,
} from '../../src/services/achievementEngine';
import {
  ACHIEVEMENT_DEFINITIONS,
  getAchievementDefinition,
  type AchievementId,
} from '../../src/models/achievement';
import type { UserProgress, Achievement } from '../../src/models/progress';
import * as progressTracker from '../../src/services/progressTracker';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
    get length() { return Object.keys(store).length; },
    key: (index: number) => Object.keys(store)[index] || null,
  };
})();

Object.defineProperty(global, 'localStorage', { value: localStorageMock });

// Helper to create mock progress
const createMockProgress = (overrides: Partial<UserProgress> & { currentStreak?: number; longestStreak?: number } = {}): UserProgress => {
  const { currentStreak, longestStreak, ...rest } = overrides;
  return {
    version: 1,
    completedPuzzles: {},
    unlockedLevels: ['level-1'],
    statistics: {
      totalSolved: 0,
      totalAttempts: 0,
      totalTimeMs: 0,
      totalHintsUsed: 0,
      perfectSolves: 0,
      byDifficulty: {
        beginner: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 },
        intermediate: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 },
        advanced: { solved: 0, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 },
      },
      rushHighScores: [],
    },
    streakData: {
      currentStreak: currentStreak ?? 0,
      longestStreak: longestStreak ?? 0,
      lastPlayedDate: null,
      streakStartDate: null,
    },
    achievements: [],
    preferences: {
      hintsEnabled: true,
      soundEnabled: true,
      theme: 'system',
      boardStyle: 'classic',
    },
    lastUpdated: new Date().toISOString(),
    ...rest,
  };
};

describe('extractMetrics', () => {
  it('should extract total solved from statistics', () => {
    const progress = createMockProgress({
      statistics: {
        ...createMockProgress().statistics,
        totalSolved: 42,
      },
    });

    const metrics = extractMetrics(progress);
    expect(metrics.totalSolved).toBe(42);
  });

  it('should extract streak data', () => {
    const progress = createMockProgress({
      currentStreak: 7,
      longestStreak: 14,
    });

    const metrics = extractMetrics(progress);
    expect(metrics.currentStreak).toBe(7);
    expect(metrics.longestStreak).toBe(14);
  });

  it('should extract perfect solves', () => {
    const progress = createMockProgress({
      statistics: {
        ...createMockProgress().statistics,
        perfectSolves: 10,
      },
    });

    const metrics = extractMetrics(progress);
    expect(metrics.perfectSolves).toBe(10);
  });

  it('should count puzzles without hints', () => {
    const progress = createMockProgress({
      completedPuzzles: {
        'p1': { puzzleId: 'p1', completedAt: '2024-01-01', timeSpentMs: 5000, attempts: 1, hintsUsed: 0, perfectSolve: true },
        'p2': { puzzleId: 'p2', completedAt: '2024-01-02', timeSpentMs: 5000, attempts: 1, hintsUsed: 1, perfectSolve: false },
        'p3': { puzzleId: 'p3', completedAt: '2024-01-03', timeSpentMs: 5000, attempts: 1, hintsUsed: 0, perfectSolve: true },
      },
    });

    const metrics = extractMetrics(progress);
    expect(metrics.puzzlesWithoutHints).toBe(2);
  });

  it('should count fast solves under 10 seconds', () => {
    const progress = createMockProgress({
      completedPuzzles: {
        'p1': { puzzleId: 'p1', completedAt: '2024-01-01', timeSpentMs: 5000, attempts: 1, hintsUsed: 0, perfectSolve: true },
        'p2': { puzzleId: 'p2', completedAt: '2024-01-02', timeSpentMs: 15000, attempts: 1, hintsUsed: 0, perfectSolve: true },
        'p3': { puzzleId: 'p3', completedAt: '2024-01-03', timeSpentMs: 8000, attempts: 1, hintsUsed: 0, perfectSolve: true },
      },
    });

    const metrics = extractMetrics(progress);
    expect(metrics.fastSolves).toBe(2);
  });

  it('should count quick solves under 30 seconds', () => {
    const progress = createMockProgress({
      completedPuzzles: {
        'p1': { puzzleId: 'p1', completedAt: '2024-01-01', timeSpentMs: 5000, attempts: 1, hintsUsed: 0, perfectSolve: true },
        'p2': { puzzleId: 'p2', completedAt: '2024-01-02', timeSpentMs: 25000, attempts: 1, hintsUsed: 0, perfectSolve: true },
        'p3': { puzzleId: 'p3', completedAt: '2024-01-03', timeSpentMs: 45000, attempts: 1, hintsUsed: 0, perfectSolve: true },
      },
    });

    const metrics = extractMetrics(progress);
    expect(metrics.quickSolves).toBe(2);
  });

  it('should extract rush high score', () => {
    const progress = createMockProgress({
      statistics: {
        ...createMockProgress().statistics,
        rushHighScores: [
          { score: 25, achievedAt: '2024-01-01T00:00:00Z', duration: 180 },
        ],
      },
    });

    const metrics = extractMetrics(progress);
    expect(metrics.rushHighScore).toBe(25);
    expect(metrics.rushSessionsCompleted).toBe(1);
  });

  it('should extract difficulty-specific stats', () => {
    const progress = createMockProgress({
      statistics: {
        ...createMockProgress().statistics,
        byDifficulty: {
          beginner: { solved: 50, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 },
          intermediate: { solved: 30, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 },
          advanced: { solved: 20, totalTimeMs: 0, avgTimeMs: 0, perfectSolves: 0 },
        },
      },
    });

    const metrics = extractMetrics(progress);
    expect(metrics.beginnerSolved).toBe(50);
    expect(metrics.intermediateSolved).toBe(30);
    expect(metrics.advancedSolved).toBe(20);
  });

  it('should detect comeback after streak break', () => {
    const progress = createMockProgress({
      currentStreak: 3,
      longestStreak: 10, // Had a longer streak before
    });

    const metrics = extractMetrics(progress);
    expect(metrics.hasReturnedAfterBreak).toBe(true);
  });

  it('should not detect comeback if no previous streak', () => {
    const progress = createMockProgress({
      currentStreak: 5,
      longestStreak: 5,
    });

    const metrics = extractMetrics(progress);
    expect(metrics.hasReturnedAfterBreak).toBe(false);
  });
});

describe('getProgressValue', () => {
  const metrics: ProgressMetrics = {
    totalSolved: 75,
    currentStreak: 10,
    longestStreak: 15,
    perfectSolves: 8,
    hintsUsed: 5,
    puzzlesWithoutHints: 60,
    fastSolves: 3,
    quickSolves: 12,
    rushHighScore: 18,
    rushSessionsCompleted: 5,
    beginnerSolved: 100,
    intermediateSolved: 40,
    advancedSolved: 25,
    levelsCompleted: 2,
    hasReturnedAfterBreak: true,
  };

  it('should return totalSolved for puzzle milestones', () => {
    expect(getProgressValue('first_puzzle', metrics)).toBe(75);
    expect(getProgressValue('ten_puzzles', metrics)).toBe(75);
    expect(getProgressValue('fifty_puzzles', metrics)).toBe(75);
    expect(getProgressValue('hundred_puzzles', metrics)).toBe(75);
  });

  it('should return currentStreak for streak achievements', () => {
    expect(getProgressValue('streak_7', metrics)).toBe(10);
    expect(getProgressValue('streak_30', metrics)).toBe(10);
  });

  it('should return perfectSolves for perfect_ten', () => {
    expect(getProgressValue('perfect_ten', metrics)).toBe(8);
  });

  it('should return puzzlesWithoutHints for no_hints_master', () => {
    expect(getProgressValue('no_hints_master', metrics)).toBe(60);
  });

  it('should return fastSolves for speed_demon', () => {
    expect(getProgressValue('speed_demon', metrics)).toBe(3);
  });

  it('should return rushHighScore for rush score achievements', () => {
    expect(getProgressValue('rush_10', metrics)).toBe(18);
    expect(getProgressValue('rush_20', metrics)).toBe(18);
  });

  it('should return rushSessionsCompleted for rush_beginner', () => {
    expect(getProgressValue('rush_beginner', metrics)).toBe(5);
  });

  it('should return advancedSolved for difficulty_master', () => {
    expect(getProgressValue('difficulty_master', metrics)).toBe(25);
  });

  it('should return beginnerSolved for beginner_graduate', () => {
    expect(getProgressValue('beginner_graduate', metrics)).toBe(100);
  });

  it('should return 1 for comeback_kid when returned after break', () => {
    expect(getProgressValue('comeback_kid', metrics)).toBe(1);
  });
});

describe('shouldUnlock', () => {
  it('should return true when target is met', () => {
    const definition = getAchievementDefinition('first_puzzle')!;
    const metrics: ProgressMetrics = {
      totalSolved: 1,
      currentStreak: 0,
      longestStreak: 0,
      perfectSolves: 0,
      hintsUsed: 0,
      puzzlesWithoutHints: 0,
      fastSolves: 0,
      quickSolves: 0,
      rushHighScore: 0,
      rushSessionsCompleted: 0,
      beginnerSolved: 0,
      intermediateSolved: 0,
      advancedSolved: 0,
      levelsCompleted: 0,
      hasReturnedAfterBreak: false,
    };

    expect(shouldUnlock(definition, metrics)).toBe(true);
  });

  it('should return true when target is exceeded', () => {
    const definition = getAchievementDefinition('ten_puzzles')!;
    const metrics: ProgressMetrics = {
      totalSolved: 15,
      currentStreak: 0,
      longestStreak: 0,
      perfectSolves: 0,
      hintsUsed: 0,
      puzzlesWithoutHints: 0,
      fastSolves: 0,
      quickSolves: 0,
      rushHighScore: 0,
      rushSessionsCompleted: 0,
      beginnerSolved: 0,
      intermediateSolved: 0,
      advancedSolved: 0,
      levelsCompleted: 0,
      hasReturnedAfterBreak: false,
    };

    expect(shouldUnlock(definition, metrics)).toBe(true);
  });

  it('should return false when below target', () => {
    const definition = getAchievementDefinition('hundred_puzzles')!;
    const metrics: ProgressMetrics = {
      totalSolved: 50,
      currentStreak: 0,
      longestStreak: 0,
      perfectSolves: 0,
      hintsUsed: 0,
      puzzlesWithoutHints: 0,
      fastSolves: 0,
      quickSolves: 0,
      rushHighScore: 0,
      rushSessionsCompleted: 0,
      beginnerSolved: 0,
      intermediateSolved: 0,
      advancedSolved: 0,
      levelsCompleted: 0,
      hasReturnedAfterBreak: false,
    };

    expect(shouldUnlock(definition, metrics)).toBe(false);
  });
});

describe('getUnlockedIds', () => {
  it('should return set of unlocked achievement IDs', () => {
    const achievements: Achievement[] = [
      { id: 'first_puzzle', name: 'First Steps', description: '', unlockedAt: '2024-01-01', progress: 1, target: 1 },
      { id: 'streak_7', name: 'Weekly Warrior', description: '', unlockedAt: '2024-01-07', progress: 7, target: 7 },
    ];

    const unlocked = getUnlockedIds(achievements);
    expect(unlocked.has('first_puzzle' as AchievementId)).toBe(true);
    expect(unlocked.has('streak_7' as AchievementId)).toBe(true);
    expect(unlocked.has('hundred_puzzles' as AchievementId)).toBe(false);
  });

  it('should exclude achievements without unlockedAt', () => {
    const achievements: Achievement[] = [
      { id: 'first_puzzle', name: 'First Steps', description: '', unlockedAt: '2024-01-01', progress: 1, target: 1 },
      { id: 'hundred_puzzles', name: 'Century', description: '', progress: 50, target: 100 }, // No unlockedAt
    ];

    const unlocked = getUnlockedIds(achievements);
    expect(unlocked.has('first_puzzle' as AchievementId)).toBe(true);
    expect(unlocked.has('hundred_puzzles' as AchievementId)).toBe(false);
  });

  it('should return empty set for empty achievements', () => {
    const unlocked = getUnlockedIds([]);
    expect(unlocked.size).toBe(0);
  });
});

describe('checkAchievements', () => {
  it('should detect newly unlocked achievements', () => {
    const progress = createMockProgress({
      statistics: {
        ...createMockProgress().statistics,
        totalSolved: 1,
      },
      achievements: [],
    });

    const result = checkAchievements(progress);
    expect(result.newlyUnlocked.length).toBeGreaterThan(0);
    
    const firstPuzzle = result.newlyUnlocked.find(
      (n) => n.achievement.id === 'first_puzzle'
    );
    expect(firstPuzzle).toBeDefined();
  });

  it('should not re-unlock already unlocked achievements', () => {
    const progress = createMockProgress({
      statistics: {
        ...createMockProgress().statistics,
        totalSolved: 5,
      },
      achievements: [
        { id: 'first_puzzle', name: 'First Steps', description: '', unlockedAt: '2024-01-01', progress: 1, target: 1 },
      ],
    });

    const result = checkAchievements(progress);
    const firstPuzzle = result.newlyUnlocked.find(
      (n) => n.achievement.id === 'first_puzzle'
    );
    expect(firstPuzzle).toBeUndefined();
  });

  it('should detect multiple achievements at once', () => {
    const progress = createMockProgress({
      statistics: {
        ...createMockProgress().statistics,
        totalSolved: 10,
      },
      currentStreak: 7,
      achievements: [],
    });

    const result = checkAchievements(progress);
    
    // Should unlock first_puzzle, ten_puzzles, and streak_7
    const ids = result.newlyUnlocked.map((n) => n.achievement.id);
    expect(ids).toContain('first_puzzle');
    expect(ids).toContain('ten_puzzles');
    expect(ids).toContain('streak_7');
  });

  it('should include progress updates', () => {
    const progress = createMockProgress({
      statistics: {
        ...createMockProgress().statistics,
        totalSolved: 50,
      },
      achievements: [
        { id: 'hundred_puzzles', name: 'Century', description: '', progress: 40, target: 100 },
      ],
    });

    const result = checkAchievements(progress);
    
    const centuryUpdate = result.progressUpdates.find(
      (u) => u.achievementId === 'hundred_puzzles'
    );
    expect(centuryUpdate).toBeDefined();
    expect(centuryUpdate!.previousValue).toBe(40);
    expect(centuryUpdate!.currentValue).toBe(50);
    expect(centuryUpdate!.isComplete).toBe(false);
  });

  it('should mark progress update as complete when target reached', () => {
    const progress = createMockProgress({
      statistics: {
        ...createMockProgress().statistics,
        totalSolved: 100,
      },
      achievements: [
        { id: 'hundred_puzzles', name: 'Century', description: '', progress: 90, target: 100 },
      ],
    });

    const result = checkAchievements(progress);
    
    const centuryUpdate = result.progressUpdates.find(
      (u) => u.achievementId === 'hundred_puzzles'
    );
    expect(centuryUpdate).toBeDefined();
    expect(centuryUpdate!.isComplete).toBe(true);
  });
});

describe('Achievement Integration', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('should detect no achievements for empty progress', () => {
    vi.spyOn(progressTracker, 'loadProgress').mockReturnValue({
      success: true,
      data: createMockProgress(),
    });

    const result = detectNewAchievements();
    expect(result.newlyUnlocked.length).toBe(0);
  });

  it('should detect first puzzle achievement', () => {
    vi.spyOn(progressTracker, 'loadProgress').mockReturnValue({
      success: true,
      data: createMockProgress({
        statistics: {
          ...createMockProgress().statistics,
          totalSolved: 1,
        },
      }),
    });

    const result = detectNewAchievements();
    const firstPuzzle = result.newlyUnlocked.find(
      (n) => n.achievement.id === 'first_puzzle'
    );
    expect(firstPuzzle).toBeDefined();
    expect(firstPuzzle!.achievement.name).toBe('First Steps');
  });

  it('should return empty result on load failure', () => {
    vi.spyOn(progressTracker, 'loadProgress').mockReturnValue({
      success: false,
      error: 'load_failed',
    });

    const result = detectNewAchievements();
    expect(result.newlyUnlocked).toHaveLength(0);
    expect(result.progressUpdates).toHaveLength(0);
  });
});

describe('getAchievementProgress', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('should return progress map for all achievements', () => {
    vi.spyOn(progressTracker, 'loadProgress').mockReturnValue({
      success: true,
      data: createMockProgress({
        statistics: {
          ...createMockProgress().statistics,
          totalSolved: 25,
        },
        currentStreak: 3,
      }),
    });

    const progressMap = getAchievementProgress();
    
    expect(progressMap.get('first_puzzle')).toBe(25);
    expect(progressMap.get('streak_7')).toBe(3);
    expect(progressMap.size).toBe(ACHIEVEMENT_DEFINITIONS.length);
  });

  it('should return empty map on load failure', () => {
    vi.spyOn(progressTracker, 'loadProgress').mockReturnValue({
      success: false,
      error: 'load_failed',
    });

    const progressMap = getAchievementProgress();
    expect(progressMap.size).toBe(0);
  });
});

describe('isAchievementUnlocked', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should return true for unlocked achievement', () => {
    vi.spyOn(progressTracker, 'getAchievements').mockReturnValue([
      { id: 'first_puzzle', name: 'First Steps', description: '', unlockedAt: '2024-01-01', progress: 1, target: 1 },
    ]);

    expect(isAchievementUnlocked('first_puzzle')).toBe(true);
  });

  it('should return false for locked achievement', () => {
    vi.spyOn(progressTracker, 'getAchievements').mockReturnValue([
      { id: 'first_puzzle', name: 'First Steps', description: '', unlockedAt: '2024-01-01', progress: 1, target: 1 },
    ]);

    expect(isAchievementUnlocked('hundred_puzzles')).toBe(false);
  });

  it('should return false for achievement without unlockedAt', () => {
    vi.spyOn(progressTracker, 'getAchievements').mockReturnValue([
      { id: 'hundred_puzzles', name: 'Century', description: '', progress: 50, target: 100 },
    ]);

    expect(isAchievementUnlocked('hundred_puzzles')).toBe(false);
  });
});

describe('getAchievementProgressPercent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should return correct percentage', () => {
    vi.spyOn(progressTracker, 'loadProgress').mockReturnValue({
      success: true,
      data: createMockProgress({
        statistics: {
          ...createMockProgress().statistics,
          totalSolved: 50,
        },
      }),
    });

    expect(getAchievementProgressPercent('hundred_puzzles')).toBe(50);
  });

  it('should cap at 100%', () => {
    vi.spyOn(progressTracker, 'loadProgress').mockReturnValue({
      success: true,
      data: createMockProgress({
        statistics: {
          ...createMockProgress().statistics,
          totalSolved: 150,
        },
      }),
    });

    expect(getAchievementProgressPercent('hundred_puzzles')).toBe(100);
  });

  it('should return 0 for unknown achievement', () => {
    vi.spyOn(progressTracker, 'loadProgress').mockReturnValue({
      success: true,
      data: createMockProgress(),
    });

    // @ts-expect-error - testing invalid ID
    expect(getAchievementProgressPercent('invalid_achievement')).toBe(0);
  });

  it('should return 0 on load failure', () => {
    vi.spyOn(progressTracker, 'loadProgress').mockReturnValue({
      success: false,
      error: 'load_failed',
    });

    expect(getAchievementProgressPercent('first_puzzle')).toBe(0);
  });
});

describe('Required Achievements (US8)', () => {
  it('should have First Steps for first puzzle', () => {
    const progress = createMockProgress({
      statistics: { ...createMockProgress().statistics, totalSolved: 1 },
    });

    const result = checkAchievements(progress);
    const firstSteps = result.newlyUnlocked.find(n => n.achievement.name === 'First Steps');
    expect(firstSteps).toBeDefined();
  });

  it('should have Weekly Warrior for 7-day streak', () => {
    const progress = createMockProgress({ currentStreak: 7 });

    const result = checkAchievements(progress);
    const weeklyWarrior = result.newlyUnlocked.find(n => n.achievement.name === 'Weekly Warrior');
    expect(weeklyWarrior).toBeDefined();
  });

  it('should have Century Solver for 100 puzzles', () => {
    const progress = createMockProgress({
      statistics: { ...createMockProgress().statistics, totalSolved: 100 },
    });

    const result = checkAchievements(progress);
    const centurySolver = result.newlyUnlocked.find(n => n.achievement.name === 'Century Solver');
    expect(centurySolver).toBeDefined();
  });
});
