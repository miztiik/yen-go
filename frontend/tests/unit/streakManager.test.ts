/**
 * Tests for Streak Manager Service
 * @module tests/unit/streakManager.test
 *
 * Covers: FR-023 to FR-026, US4
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  getUTCDateString,
  getLocalDateString,
  parseDateString,
  daysDifference,
  isYesterday,
  isToday,
  checkMilestones,
  recordPlay,
  isStreakAtRisk,
  isStreakActive,
  daysUntilMilestone,
  getNextMilestone,
  getStreakStats,
  STREAK_MILESTONES,
} from '../../src/services/streakManager';
import { PROGRESS_STORAGE_KEY } from '../../src/services/progressTracker';
import { createInitialProgress } from '../../src/models/progress';

describe('streakManager', () => {
  let mockStore: Record<string, string>;

  beforeEach(() => {
    mockStore = {};

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

  describe('getUTCDateString', () => {
    it('should return date in YYYY-MM-DD format using UTC', () => {
      // Use Date.UTC to create a specific UTC time
      const date = new Date(Date.UTC(2026, 0, 20, 12, 0, 0)); // January 20, 2026 12:00 UTC
      const result = getUTCDateString(date);
      expect(result).toBe('2026-01-20');
    });

    it('should pad single digit months and days', () => {
      const date = new Date(Date.UTC(2026, 0, 5, 0, 0, 0)); // January 5, 2026 UTC
      const result = getUTCDateString(date);
      expect(result).toBe('2026-01-05');
    });

    it('should handle day boundaries correctly in UTC', () => {
      // 23:00 UTC on Jan 19 should still be Jan 19
      const lateNight = new Date(Date.UTC(2026, 0, 19, 23, 0, 0));
      expect(getUTCDateString(lateNight)).toBe('2026-01-19');

      // 01:00 UTC on Jan 20 should be Jan 20
      const earlyMorning = new Date(Date.UTC(2026, 0, 20, 1, 0, 0));
      expect(getUTCDateString(earlyMorning)).toBe('2026-01-20');
    });
  });

  describe('getLocalDateString (deprecated alias)', () => {
    it('should be an alias for getUTCDateString', () => {
      const date = new Date(Date.UTC(2026, 0, 20, 12, 0, 0));
      expect(getLocalDateString(date)).toBe(getUTCDateString(date));
    });
  });

  describe('parseDateString', () => {
    it('should parse a date string correctly to UTC midnight', () => {
      const date = parseDateString('2026-01-20');
      expect(date.getUTCFullYear()).toBe(2026);
      expect(date.getUTCMonth()).toBe(0); // January
      expect(date.getUTCDate()).toBe(20);
      expect(date.getUTCHours()).toBe(0);
      expect(date.getUTCMinutes()).toBe(0);
    });
  });

  describe('daysDifference', () => {
    it('should return 0 for same day', () => {
      expect(daysDifference('2026-01-20', '2026-01-20')).toBe(0);
    });

    it('should return 1 for consecutive days', () => {
      expect(daysDifference('2026-01-21', '2026-01-20')).toBe(1);
    });

    it('should return -1 when date1 is before date2', () => {
      expect(daysDifference('2026-01-19', '2026-01-20')).toBe(-1);
    });

    it('should handle month boundaries', () => {
      expect(daysDifference('2026-02-01', '2026-01-31')).toBe(1);
    });

    it('should handle year boundaries', () => {
      expect(daysDifference('2027-01-01', '2026-12-31')).toBe(1);
    });
  });

  describe('isYesterday', () => {
    it('should return true for yesterday', () => {
      expect(isYesterday('2026-01-19', '2026-01-20')).toBe(true);
    });

    it('should return false for today', () => {
      expect(isYesterday('2026-01-20', '2026-01-20')).toBe(false);
    });

    it('should return false for two days ago', () => {
      expect(isYesterday('2026-01-18', '2026-01-20')).toBe(false);
    });
  });

  describe('isToday', () => {
    it('should return true for same date', () => {
      expect(isToday('2026-01-20', '2026-01-20')).toBe(true);
    });

    it('should return false for different dates', () => {
      expect(isToday('2026-01-19', '2026-01-20')).toBe(false);
    });
  });

  describe('checkMilestones', () => {
    it('should return empty array when no milestones reached', () => {
      expect(checkMilestones(2, 1)).toEqual([]);
    });

    it('should return milestone when reached', () => {
      expect(checkMilestones(3, 2)).toContain(3);
    });

    it('should return multiple milestones if skipped', () => {
      const result = checkMilestones(10, 2);
      expect(result).toContain(3);
      expect(result).toContain(7);
    });

    it('should not return already achieved milestones', () => {
      expect(checkMilestones(8, 5)).not.toContain(3);
    });
  });

  describe('recordPlay', () => {
    it('should start a new streak on first play', () => {
      const result = recordPlay('2026-01-20');

      expect(result.success).toBe(true);
      expect(result.data?.streakData.currentStreak).toBe(1);
      expect(result.data?.streakData.lastPlayedDate).toBe('2026-01-20');
      expect(result.data?.streakContinued).toBe(true);
      expect(result.data?.streakBroken).toBe(false);
    });

    it('should continue streak when played yesterday', () => {
      // First play
      recordPlay('2026-01-19');
      // Second play (next day)
      const result = recordPlay('2026-01-20');

      expect(result.success).toBe(true);
      expect(result.data?.streakData.currentStreak).toBe(2);
      expect(result.data?.streakContinued).toBe(true);
      expect(result.data?.streakBroken).toBe(false);
    });

    it('should not change streak when played same day', () => {
      // First play
      recordPlay('2026-01-20');
      // Second play (same day)
      const result = recordPlay('2026-01-20');

      expect(result.success).toBe(true);
      expect(result.data?.streakData.currentStreak).toBe(1);
      expect(result.data?.streakContinued).toBe(false);
      expect(result.data?.streakBroken).toBe(false);
    });

    it('should break streak when more than 1 day gap', () => {
      // First play
      recordPlay('2026-01-18');
      // Second play (2 days later)
      const result = recordPlay('2026-01-20');

      expect(result.success).toBe(true);
      expect(result.data?.streakData.currentStreak).toBe(1);
      expect(result.data?.streakContinued).toBe(false);
      expect(result.data?.streakBroken).toBe(true);
    });

    it('should preserve longest streak when breaking', () => {
      // Build up a 3-day streak
      recordPlay('2026-01-17');
      recordPlay('2026-01-18');
      recordPlay('2026-01-19');
      // Break streak
      const result = recordPlay('2026-01-25');

      expect(result.data?.streakData.currentStreak).toBe(1);
      expect(result.data?.streakData.longestStreak).toBe(3);
    });

    it('should detect milestone reached', () => {
      recordPlay('2026-01-17');
      recordPlay('2026-01-18');
      const result = recordPlay('2026-01-19'); // 3rd day

      expect(result.data?.milestonesReached).toContain(3);
    });
  });

  describe('isStreakAtRisk', () => {
    it('should return false when never played', () => {
      expect(isStreakAtRisk('2026-01-20')).toBe(false);
    });

    it('should return true when played yesterday but not today', () => {
      recordPlay('2026-01-19');
      expect(isStreakAtRisk('2026-01-20')).toBe(true);
    });

    it('should return false when already played today', () => {
      recordPlay('2026-01-20');
      expect(isStreakAtRisk('2026-01-20')).toBe(false);
    });

    it('should return false when streak already broken', () => {
      recordPlay('2026-01-17');
      expect(isStreakAtRisk('2026-01-20')).toBe(false);
    });
  });

  describe('isStreakActive', () => {
    it('should return false when never played', () => {
      expect(isStreakActive('2026-01-20')).toBe(false);
    });

    it('should return true when played today', () => {
      recordPlay('2026-01-20');
      expect(isStreakActive('2026-01-20')).toBe(true);
    });

    it('should return true when played yesterday', () => {
      recordPlay('2026-01-19');
      expect(isStreakActive('2026-01-20')).toBe(true);
    });

    it('should return false when streak broken', () => {
      recordPlay('2026-01-17');
      expect(isStreakActive('2026-01-20')).toBe(false);
    });
  });

  describe('daysUntilMilestone', () => {
    it('should return days until 3-day milestone', () => {
      expect(daysUntilMilestone(1)).toBe(2);
    });

    it('should return days until 7-day milestone', () => {
      expect(daysUntilMilestone(4)).toBe(3);
    });

    it('should return null when all milestones achieved', () => {
      expect(daysUntilMilestone(400)).toBe(null);
    });
  });

  describe('getNextMilestone', () => {
    it('should return 3 for streak of 0', () => {
      expect(getNextMilestone(0)).toBe(3);
    });

    it('should return 7 for streak of 5', () => {
      expect(getNextMilestone(5)).toBe(7);
    });

    it('should return null when all milestones achieved', () => {
      expect(getNextMilestone(400)).toBe(null);
    });
  });

  describe('getStreakStats', () => {
    it('should return zeros for new user', () => {
      const stats = getStreakStats('2026-01-20');

      expect(stats.currentStreak).toBe(0);
      expect(stats.longestStreak).toBe(0);
      expect(stats.isActive).toBe(false);
      expect(stats.isAtRisk).toBe(false);
    });

    it('should return correct stats after playing', () => {
      recordPlay('2026-01-20');
      const stats = getStreakStats('2026-01-20');

      expect(stats.currentStreak).toBe(1);
      expect(stats.isActive).toBe(true);
      expect(stats.isAtRisk).toBe(false);
      expect(stats.nextMilestone).toBe(3);
      expect(stats.daysUntilNextMilestone).toBe(2);
    });

    it('should show streak at risk correctly', () => {
      recordPlay('2026-01-19');
      const stats = getStreakStats('2026-01-20');

      expect(stats.isAtRisk).toBe(true);
      expect(stats.currentStreak).toBe(1); // Still shows current, user can save it
    });

    it('should show broken streak as 0', () => {
      recordPlay('2026-01-17');
      const stats = getStreakStats('2026-01-20');

      expect(stats.currentStreak).toBe(0);
      expect(stats.isActive).toBe(false);
      expect(stats.isAtRisk).toBe(false);
    });
  });

  describe('STREAK_MILESTONES', () => {
    it('should contain expected milestones', () => {
      expect(STREAK_MILESTONES).toContain(3);
      expect(STREAK_MILESTONES).toContain(7);
      expect(STREAK_MILESTONES).toContain(14);
      expect(STREAK_MILESTONES).toContain(30);
      expect(STREAK_MILESTONES).toContain(100);
      expect(STREAK_MILESTONES).toContain(365);
    });

    it('should be in ascending order', () => {
      for (let i = 1; i < STREAK_MILESTONES.length; i++) {
        expect(STREAK_MILESTONES[i]).toBeGreaterThan(STREAK_MILESTONES[i - 1]!);
      }
    });
  });
});
