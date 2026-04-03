/**
 * Timed Challenge Integration Tests
 * Tests: T031 - Integration test for timed mode
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  loadTimedQueue,
  loadTimedPuzzle,
  preloadTimedPuzzles,
  getTimedChallengeInfo,
  isTimedAvailable,
  getTimedQueueSize,
  createTimedChallenge,
  clearTimedCache,
  type TimedChallengeConfig,
} from '@/lib/puzzle/timed-loader';
import { clearDailyCache } from '@/lib/puzzle/daily-loader';
import type { DailyIndex } from '@/types/indexes';

// Mock fetch
const mockFetch = vi.fn();

// Sample daily index with timed challenge
const sampleDailyIndex: DailyIndex = {
  indexVersion: '3.0',
  date: '2026-01-25',
  generatedAt: '2026-01-25T00:00:00Z',
  timed: {
    queue: [
      'sgf/beginner/2026/01/batch-001/puzzle-001.sgf',
      'sgf/beginner/2026/01/batch-001/puzzle-002.sgf',
      'sgf/basic/2026/01/batch-001/puzzle-001.sgf',
      'sgf/basic/2026/01/batch-001/puzzle-002.sgf',
      'sgf/intermediate/2026/01/batch-001/puzzle-001.sgf',
    ],
  },
};

// Sample SGF content
const sampleSGF = `(;FF[4]GM[1]SZ[9]
PL[B]AB[cc][dc]AW[dd][ed]
YV[3.0]YG[beginner]YT[capture]
(;B[ce]C[CORRECT]))`;

describe('Timed Challenge', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    clearTimedCache();
    clearDailyCache();
    mockFetch.mockReset();
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'info').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('loadTimedQueue', () => {
    it('should load timed queue from daily index', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });

      const queue = await loadTimedQueue('2026-01-25');

      expect(queue.length).toBe(5);
      expect(queue[0]).toBe('sgf/beginner/2026/01/batch-001/puzzle-001.sgf');
    });

    it('should return empty array if no timed challenge', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ indexVersion: '3.0', date: '2026-01-25' }),
      });

      const queue = await loadTimedQueue('2026-01-25');

      expect(queue).toEqual([]);
    });

    it('should cache queue paths', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });

      await loadTimedQueue('2026-01-25');
      await loadTimedQueue('2026-01-25');

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('loadTimedPuzzle', () => {
    it('should load puzzle at specific index', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sampleSGF),
      });

      const puzzle = await loadTimedPuzzle(0, '2026-01-25');

      expect(puzzle).not.toBeNull();
      expect(puzzle?.boardSize).toBe(9);
    });

    it('should return null for out of range index', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });

      const puzzle = await loadTimedPuzzle(999, '2026-01-25');

      expect(puzzle).toBeNull();
    });
  });

  describe('preloadTimedPuzzles', () => {
    it('should preload multiple puzzles', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });
      // Mock 3 SGF fetches
      for (let i = 0; i < 3; i++) {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(sampleSGF),
        });
      }

      const preloaded = await preloadTimedPuzzles(0, 3, '2026-01-25');

      expect(preloaded.size).toBe(3);
      expect(preloaded.has(0)).toBe(true);
      expect(preloaded.has(1)).toBe(true);
      expect(preloaded.has(2)).toBe(true);
    });

    it('should handle partial failures', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });
      // First succeeds, second fails
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sampleSGF),
      });
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sampleSGF),
      });

      const preloaded = await preloadTimedPuzzles(0, 3, '2026-01-25');

      expect(preloaded.size).toBe(2);
    });
  });

  describe('isTimedAvailable', () => {
    it('should return true when timed queue has puzzles', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });

      const available = await isTimedAvailable('2026-01-25');

      expect(available).toBe(true);
    });

    it('should return false when no timed queue', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ indexVersion: '3.0', date: '2026-01-25' }),
      });

      const available = await isTimedAvailable('2026-01-25');

      expect(available).toBe(false);
    });
  });

  describe('getTimedQueueSize', () => {
    it('should return correct queue size', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });

      const size = await getTimedQueueSize('2026-01-25');

      expect(size).toBe(5);
    });
  });

  describe('getTimedChallengeInfo', () => {
    it('should return timed challenge info', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });

      const info = await getTimedChallengeInfo('2026-01-25');

      expect(info).not.toBeNull();
      expect(info?.queue.length).toBe(5);
    });

    it('should return null if no timed challenge', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ indexVersion: '3.0', date: '2026-01-25' }),
      });

      const info = await getTimedChallengeInfo('2026-01-25');

      expect(info).toBeNull();
    });
  });

  describe('TimedChallengeManager', () => {
    it('should initialize with queue', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });
      // First puzzle
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sampleSGF),
      });
      // Preload 3 more
      for (let i = 0; i < 3; i++) {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(sampleSGF),
        });
      }

      const config: TimedChallengeConfig = { duration: 5, date: '2026-01-25' };
      const manager = createTimedChallenge(config);
      const initialized = await manager.initialize();

      expect(initialized).toBe(true);
      const state = manager.getState();
      expect(state.totalPuzzles).toBe(5);
      expect(state.currentPuzzle).not.toBeNull();
    });

    it('should track time remaining', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sampleSGF),
      });
      // Preload
      for (let i = 0; i < 3; i++) {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(sampleSGF),
        });
      }

      const config: TimedChallengeConfig = { duration: 3, date: '2026-01-25' };
      const manager = createTimedChallenge(config);
      await manager.initialize();
      
      // Before start
      expect(manager.getTimeRemaining()).toBe(180); // 3 minutes

      manager.start();
      
      // After start, time should be decreasing
      expect(manager.getTimeRemaining()).toBeLessThanOrEqual(180);
    });

    it('should move to next puzzle on solve', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sampleSGF),
      });
      // Preload
      for (let i = 0; i < 4; i++) {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(sampleSGF),
        });
      }

      const config: TimedChallengeConfig = { duration: 5, date: '2026-01-25' };
      const manager = createTimedChallenge(config);
      await manager.initialize();
      manager.start();

      expect(manager.getState().currentIndex).toBe(0);
      
      await manager.markSolvedAndNext();
      
      expect(manager.getState().currentIndex).toBe(1);
      expect(manager.getState().solvedCount).toBe(1);
    });

    it('should handle queue exhaustion', async () => {
      // Small queue
      const smallDailyIndex = {
        ...sampleDailyIndex,
        timed: {
          queue: ['sgf/beginner/puzzle-001.sgf'],
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(smallDailyIndex),
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sampleSGF),
      });

      const config: TimedChallengeConfig = { duration: 5, date: '2026-01-25' };
      const manager = createTimedChallenge(config);
      await manager.initialize();
      manager.start();

      // Solve the only puzzle
      const next = await manager.markSolvedAndNext();
      
      expect(next).toBeNull();
      expect(manager.getState().currentPuzzle).toBeNull();
    });

    it('should return results on stop', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(sampleDailyIndex),
      });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(sampleSGF),
      });
      // Preload
      for (let i = 0; i < 3; i++) {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(sampleSGF),
        });
      }

      const config: TimedChallengeConfig = { duration: 5, date: '2026-01-25' };
      const manager = createTimedChallenge(config);
      await manager.initialize();
      manager.start();

      // Solve one puzzle
      await manager.markSolvedAndNext();

      manager.stop();
      const results = manager.getResults();

      expect(results.solved).toBe(1);
      expect(results.total).toBe(5);
      expect(results.duration).toBe(5);
    });
  });
});
