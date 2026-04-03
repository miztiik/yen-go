/**
 * Daily Challenge Service Unit Tests
 * @module tests/unit/dailyChallengeService.test
 *
 * Tests for daily challenge loading and streak tracking.
 * Covers: US2 (Daily Challenge), FR-015 to FR-024
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  loadDailyChallenge,
  getDailyProgress,
  saveDailyProgress,
  getDailyStreak,
  updateDailyStreak,
  isDailyChallengeCompleted,
  DAILY_CHALLENGE_MODES,
  type DailyChallengeMode,
} from '../../src/services/dailyChallengeService';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
});

describe('dailyChallengeService', () => {
  const today = new Date().toISOString().split('T')[0] as string;
  const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0] as string;

  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('DAILY_CHALLENGE_MODES', () => {
    it('should have quick mode', () => {
      expect(DAILY_CHALLENGE_MODES).toContainEqual(
        expect.objectContaining({ id: 'quick' })
      );
    });

    it('should have practice mode', () => {
      expect(DAILY_CHALLENGE_MODES).toContainEqual(
        expect.objectContaining({ id: 'practice' })
      );
    });

    it('should have time attack mode', () => {
      expect(DAILY_CHALLENGE_MODES).toContainEqual(
        expect.objectContaining({ id: 'time-attack' })
      );
    });

    it('should have descriptions for all modes', () => {
      DAILY_CHALLENGE_MODES.forEach(mode => {
        expect(mode.description).toBeDefined();
        expect(mode.description.length).toBeGreaterThan(0);
      });
    });
  });

  describe('loadDailyChallenge', () => {
    const mockDailyData = {
      date: today,
      level: 'intermediate',
      puzzles: [
        { id: 'daily-1', path: 'path/to/daily-1.sgf' },
        { id: 'daily-2', path: 'path/to/daily-2.sgf' },
      ],
    };

    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockDailyData,
      });
    });

    it('should load daily challenge for today', async () => {
      const result = await loadDailyChallenge();

      expect(result.success).toBe(true);
      expect(result.data?.date).toBe(today);
      expect(result.data?.puzzles.length).toBeGreaterThan(0);
    });

    it('should load daily challenge for specific date', async () => {
      const result = await loadDailyChallenge(yesterday);

      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(yesterday)
      );
    });

    it('should return error for missing challenge', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const result = await loadDailyChallenge();

      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });

    it('should cache loaded challenge', async () => {
      await loadDailyChallenge();
      await loadDailyChallenge();

      // Should only fetch once (cached)
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('getDailyProgress', () => {
    it('should return null for new date', () => {
      const progress = getDailyProgress(today);
      expect(progress).toBeNull();
    });

    it('should return saved progress', () => {
      const savedProgress = {
        date: today,
        completedPuzzles: ['p1', 'p2'],
        attempts: 5,
        correctAttempts: 4,
        startedAt: new Date().toISOString(),
      };
      
      localStorageMock.setItem(
        `yen-go-daily-${today}`,
        JSON.stringify(savedProgress)
      );

      const progress = getDailyProgress(today);
      
      expect(progress).not.toBeNull();
      expect(progress?.completedPuzzles).toEqual(['p1', 'p2']);
    });
  });

  describe('saveDailyProgress', () => {
    it('should save progress to localStorage', () => {
      const progress = {
        date: today,
        completedPuzzles: ['p1'],
        attempts: 2,
        correctAttempts: 1,
        startedAt: new Date().toISOString(),
      };

      saveDailyProgress(today, progress);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        `yen-go-daily-${today}`,
        expect.any(String)
      );
    });

    it('should update existing progress', () => {
      const initialProgress = {
        date: today,
        completedPuzzles: ['p1'],
        attempts: 1,
        correctAttempts: 1,
        startedAt: new Date().toISOString(),
      };
      
      saveDailyProgress(today, initialProgress);
      
      const updatedProgress = {
        ...initialProgress,
        completedPuzzles: ['p1', 'p2'],
        attempts: 3,
        correctAttempts: 2,
      };
      
      saveDailyProgress(today, updatedProgress);

      const saved = getDailyProgress(today);
      expect(saved?.completedPuzzles).toEqual(['p1', 'p2']);
    });
  });

  describe('getDailyStreak', () => {
    it('should return 0 for new users', () => {
      const streak = getDailyStreak();
      
      expect(streak.current).toBe(0);
      expect(streak.best).toBe(0);
    });

    it('should return saved streak', () => {
      localStorageMock.setItem('yen-go-daily-streak', JSON.stringify({
        current: 5,
        best: 10,
        lastCompletedDate: yesterday,
      }));

      const streak = getDailyStreak();
      
      expect(streak.current).toBe(5);
      expect(streak.best).toBe(10);
    });

    it('should reset streak if gap in dates', () => {
      const twoDaysAgo = new Date(Date.now() - 2 * 86400000)
        .toISOString().split('T')[0];
      
      localStorageMock.setItem('yen-go-daily-streak', JSON.stringify({
        current: 5,
        best: 10,
        lastCompletedDate: twoDaysAgo, // Gap of 1 day
      }));

      const streak = getDailyStreak();
      
      // Streak should be reset due to gap
      expect(streak.current).toBe(0);
      expect(streak.best).toBe(10); // Best preserved
    });
  });

  describe('updateDailyStreak', () => {
    it('should increment streak on consecutive completion', () => {
      localStorageMock.setItem('yen-go-daily-streak', JSON.stringify({
        current: 5,
        best: 5,
        lastCompletedDate: yesterday,
      }));

      updateDailyStreak();

      const streak = getDailyStreak();
      expect(streak.current).toBe(6);
      expect(streak.best).toBe(6);
    });

    it('should start new streak if previous was broken', () => {
      const threeDaysAgo = new Date(Date.now() - 3 * 86400000)
        .toISOString().split('T')[0];
      
      localStorageMock.setItem('yen-go-daily-streak', JSON.stringify({
        current: 10,
        best: 15,
        lastCompletedDate: threeDaysAgo,
      }));

      updateDailyStreak();

      const streak = getDailyStreak();
      expect(streak.current).toBe(1);
      expect(streak.best).toBe(15); // Best preserved
    });

    it('should not double-count same day completion', () => {
      localStorageMock.setItem('yen-go-daily-streak', JSON.stringify({
        current: 5,
        best: 5,
        lastCompletedDate: today, // Already completed today
      }));

      updateDailyStreak();

      const streak = getDailyStreak();
      expect(streak.current).toBe(5); // Not incremented
    });

    it('should update best when current exceeds', () => {
      localStorageMock.setItem('yen-go-daily-streak', JSON.stringify({
        current: 5,
        best: 5,
        lastCompletedDate: yesterday,
      }));

      updateDailyStreak();

      const streak = getDailyStreak();
      expect(streak.best).toBe(6);
    });
  });

  describe('isDailyChallengeCompleted', () => {
    it('should return false for uncompleted challenge', () => {
      const completed = isDailyChallengeCompleted(today);
      expect(completed).toBe(false);
    });

    it('should return true for completed challenge', () => {
      localStorageMock.setItem(`yen-go-daily-${today}`, JSON.stringify({
        date: today,
        completed: true,
        completedPuzzles: ['p1', 'p2', 'p3'],
        attempts: 5,
        correctAttempts: 5,
      }));

      const completed = isDailyChallengeCompleted(today);
      expect(completed).toBe(true);
    });

    it('should return false for partially completed', () => {
      localStorageMock.setItem(`yen-go-daily-${today}`, JSON.stringify({
        date: today,
        completed: false,
        completedPuzzles: ['p1'],
        attempts: 3,
        correctAttempts: 1,
      }));

      const completed = isDailyChallengeCompleted(today);
      expect(completed).toBe(false);
    });
  });
});

describe('Daily Challenge Modes', () => {
  describe('Quick Play mode', () => {
    it('should have no time limit', () => {
      const quickMode = DAILY_CHALLENGE_MODES.find(m => m.id === 'quick');
      expect(quickMode?.timeLimit).toBeUndefined();
    });

    it('should not allow hints', () => {
      const quickMode = DAILY_CHALLENGE_MODES.find(m => m.id === 'quick');
      expect(quickMode?.hintsEnabled).toBe(false);
    });
  });

  describe('Practice mode', () => {
    it('should allow hints', () => {
      const practiceMode = DAILY_CHALLENGE_MODES.find(m => m.id === 'practice');
      expect(practiceMode?.hintsEnabled).toBe(true);
    });

    it('should have no time limit', () => {
      const practiceMode = DAILY_CHALLENGE_MODES.find(m => m.id === 'practice');
      expect(practiceMode?.timeLimit).toBeUndefined();
    });
  });

  describe('Time Attack mode', () => {
    it('should have time limit', () => {
      const timeMode = DAILY_CHALLENGE_MODES.find(m => m.id === 'time-attack');
      expect(timeMode?.timeLimit).toBeGreaterThan(0);
    });

    it('should not allow hints in time attack', () => {
      const timeMode = DAILY_CHALLENGE_MODES.find(m => m.id === 'time-attack');
      expect(timeMode?.hintsEnabled).toBe(false);
    });
  });
});
