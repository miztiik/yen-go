/**
 * Unit tests for Puzzle Rush Service
 * @module tests/unit/puzzleRushService
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  startRushSession,
  getCurrentSession,
  endRushSession,
  recordPuzzleResult,
  calculateLevel,
  canSkip,
  getSkipsRemaining,
  getBestScore,
  POINTS_PER_CORRECT,
  MAX_STRIKES,
  MAX_SKIPS,
  ADVANCE_EVERY,
  STARTING_LEVEL,
} from '../../src/services/puzzleRushService';

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

describe('puzzleRushService', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    // End any existing session
    if (getCurrentSession()) {
      endRushSession('quit');
    }
  });

  describe('constants', () => {
    it('should have correct default values', () => {
      expect(POINTS_PER_CORRECT).toBe(10);
      expect(MAX_STRIKES).toBe(3);
      expect(MAX_SKIPS).toBe(3);
      expect(ADVANCE_EVERY).toBe(5);
      expect(STARTING_LEVEL).toBe('elementary');
    });
  });

  describe('startRushSession', () => {
    it('should create a new session with correct initial values', () => {
      const session = startRushSession(5);

      expect(session.id).toMatch(/^rush-\d+$/);
      expect(session.durationMinutes).toBe(5);
      expect(session.startedAt).toBeDefined();
      expect(session.results).toEqual([]);
      expect(session.currentLevel).toBe(STARTING_LEVEL);
      expect(session.score).toBe(0);
      expect(session.strikes).toBe(0);
      expect(session.skipsUsed).toBe(0);
    });

    it('should make session retrievable via getCurrentSession', () => {
      const session = startRushSession(3);
      const current = getCurrentSession();

      expect(current).toEqual(session);
    });
  });

  describe('calculateLevel', () => {
    it('should return starting level for 0 correct answers', () => {
      expect(calculateLevel(0)).toBe(STARTING_LEVEL);
    });

    it('should remain at starting level for less than ADVANCE_EVERY correct', () => {
      expect(calculateLevel(ADVANCE_EVERY - 1)).toBe(STARTING_LEVEL);
    });

    it('should advance one level after ADVANCE_EVERY correct answers', () => {
      const level = calculateLevel(ADVANCE_EVERY);
      expect(level).toBe('intermediate'); // elementary -> intermediate
    });

    it('should advance multiple levels proportionally', () => {
      const level = calculateLevel(ADVANCE_EVERY * 2);
      expect(level).toBe('upper-intermediate');
    });

    it('should cap at expert level', () => {
      const level = calculateLevel(100); // Should cap at max level
      expect(level).toBe('expert');
    });
  });

  describe('recordPuzzleResult', () => {
    beforeEach(() => {
      startRushSession(5);
    });

    it('should record a correct answer and update score', () => {
      const { session, gameOver } = recordPuzzleResult(
        'puzzle-1',
        true,
        false,
        'elementary',
        ['life-and-death'],
        5000
      );

      expect(session.score).toBe(POINTS_PER_CORRECT);
      expect(session.results).toHaveLength(1);
      expect(session.results[0].success).toBe(true);
      expect(session.results[0].skipped).toBe(false);
      expect(gameOver).toBe(false);
    });

    it('should record a wrong answer and increment strikes', () => {
      const { session } = recordPuzzleResult(
        'puzzle-1',
        false,
        false,
        'elementary',
        ['life-and-death'],
        3000
      );

      expect(session.strikes).toBe(1);
      expect(session.score).toBe(0);
    });

    it('should record a skip without affecting score or strikes', () => {
      const { session } = recordPuzzleResult(
        'puzzle-1',
        false,
        true,
        'elementary',
        ['life-and-death'],
        1000
      );

      expect(session.skipsUsed).toBe(1);
      expect(session.strikes).toBe(0);
      expect(session.score).toBe(0);
    });

    it('should trigger game over at MAX_STRIKES', () => {
      recordPuzzleResult('p1', false, false, 'elementary', [], 1000);
      recordPuzzleResult('p2', false, false, 'elementary', [], 1000);
      const { gameOver } = recordPuzzleResult('p3', false, false, 'elementary', [], 1000);

      expect(gameOver).toBe(true);
    });

    it('should advance level after ADVANCE_EVERY correct answers', () => {
      for (let i = 0; i < ADVANCE_EVERY; i++) {
        recordPuzzleResult(`p${i}`, true, false, 'elementary', [], 1000);
      }

      const session = getCurrentSession();
      expect(session?.currentLevel).toBe('intermediate');
    });

    it('should throw if no active session', () => {
      endRushSession('quit');

      expect(() =>
        recordPuzzleResult('p1', true, false, 'elementary', [], 1000)
      ).toThrow('No active rush session');
    });
  });

  describe('canSkip and getSkipsRemaining', () => {
    it('should return MAX_SKIPS when no session', () => {
      expect(getSkipsRemaining()).toBe(MAX_SKIPS);
    });

    it('should return true for canSkip when skips available', () => {
      startRushSession(5);
      expect(canSkip()).toBe(true);
    });

    it('should decrement skips on use', () => {
      startRushSession(5);
      recordPuzzleResult('p1', false, true, 'elementary', [], 1000);

      expect(getSkipsRemaining()).toBe(MAX_SKIPS - 1);
    });

    it('should return false for canSkip when skips exhausted', () => {
      startRushSession(5);
      
      for (let i = 0; i < MAX_SKIPS; i++) {
        recordPuzzleResult(`p${i}`, false, true, 'elementary', [], 1000);
      }

      expect(canSkip()).toBe(false);
      expect(getSkipsRemaining()).toBe(0);
    });
  });

  describe('endRushSession', () => {
    it('should return null if no active session', () => {
      const result = endRushSession('timeout');
      expect(result).toBeNull();
    });

    it('should return session result with correct values', () => {
      startRushSession(5);
      recordPuzzleResult('p1', true, false, 'elementary', [], 1000);
      recordPuzzleResult('p2', true, false, 'elementary', [], 1000);
      recordPuzzleResult('p3', false, false, 'elementary', [], 1000);

      const result = endRushSession('timeout');

      expect(result).not.toBeNull();
      expect(result?.finalScore).toBe(POINTS_PER_CORRECT * 2);
      expect(result?.puzzlesSolved).toBe(2);
      expect(result?.accuracy).toBe(67); // 2/3 rounded
      expect(result?.endReason).toBe('timeout');
    });

    it('should save best score on new best', () => {
      startRushSession(5);
      recordPuzzleResult('p1', true, false, 'elementary', [], 1000);
      
      const result = endRushSession('quit');

      expect(result?.isNewBest).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it('should clear current session after ending', () => {
      startRushSession(5);
      endRushSession('quit');

      expect(getCurrentSession()).toBeNull();
    });
  });

  describe('getBestScore', () => {
    it('should return null when no best score saved', () => {
      expect(getBestScore()).toBeNull();
    });

    it('should return saved best score', () => {
      localStorageMock.setItem('yen-go-rush-best-score', '150');
      localStorageMock.getItem.mockReturnValueOnce('150');

      expect(getBestScore()).toBe(150);
    });
  });
});
