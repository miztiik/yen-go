/**
 * Tests for Daily Loader
 * Covers: T014, T016 - DailyIndex parsing and daily-loader functionality
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  formatDateKey,
  getTodayKey,
  loadDailyIndex,
  loadTodayIndex,
  extractPuzzlePaths,
  getStandardPuzzlePaths,
  getTimedPuzzlePaths,
  getTagPuzzlePaths,
  loadSGFContent,
  loadPuzzle,
  loadTodayStandardPuzzles,
  loadTimedPuzzles,
  loadTagPuzzles,
  loadPuzzleBatch,
  getStandardChallengeInfo,
  getTimedChallengeInfo,
  getTagChallengeInfo,
  isDailyAvailable,
  clearDailyCache,
} from '@/lib/puzzle/daily-loader';
import type { DailyIndex, DailyPuzzleEntry } from '@/types/indexes';

// Mock fetch
const mockFetch = vi.fn();

describe('Daily Loader', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    vi.clearAllMocks();
    clearDailyCache();
  });

  afterEach(() => {
    clearDailyCache();
  });

  describe('formatDateKey', () => {
    it('formats date to YYYY-MM-DD', () => {
      const date = new Date('2026-01-25T12:00:00Z');
      expect(formatDateKey(date)).toBe('2026-01-25');
    });

    it('pads single digit months and days', () => {
      const date = new Date('2026-03-05T00:00:00Z');
      expect(formatDateKey(date)).toBe('2026-03-05');
    });
  });

  describe('getTodayKey', () => {
    it('returns today in YYYY-MM-DD format', () => {
      const result = getTodayKey();
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
  });

  describe('extractPuzzlePaths', () => {
    it('handles string array format', () => {
      const paths = ['sgf/beginner/puzzle-001.sgf', 'sgf/beginner/puzzle-002.sgf'];
      expect(extractPuzzlePaths(paths)).toEqual(paths);
    });

    it('handles DailyPuzzleEntry array format', () => {
      const entries: DailyPuzzleEntry[] = [
        { path: 'sgf/beginner/puzzle-001.sgf', level: 'beginner' },
        { path: 'sgf/basic/puzzle-002.sgf', level: 'basic' },
      ];
      expect(extractPuzzlePaths(entries)).toEqual([
        'sgf/beginner/puzzle-001.sgf',
        'sgf/basic/puzzle-002.sgf',
      ]);
    });

    it('handles empty array', () => {
      expect(extractPuzzlePaths([])).toEqual([]);
    });
  });

  describe('loadDailyIndex', () => {
    it('loads daily index from date string', async () => {
      const mockDaily: DailyIndex = {
        date: '2026-01-25',
        generated_at: '2026-01-25T00:00:00Z',
        standard: {
          puzzles: ['sgf/beginner/puzzle-001.sgf'],
          total: 1,
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDaily),
      });

      const result = await loadDailyIndex('2026-01-25');

      expect(result).toEqual(mockDaily);
      // Spec 112: Uses nested path pattern
      expect(mockFetch).toHaveBeenCalledWith(
        '/yengo-puzzle-collections/views/daily/2026/01/2026-01-25-001.json'
      );
    });

    it('loads daily index from Date object', async () => {
      const mockDaily: DailyIndex = {
        date: '2026-03-15',
        standard: { puzzles: [], total: 0 },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDaily),
      });

      const date = new Date('2026-03-15T12:00:00Z');
      const result = await loadDailyIndex(date);

      expect(result).toEqual(mockDaily);
    });

    it('returns null on 404', async () => {
      // Spec 112: loader tries nested path first, then legacy path
      // Both must return 404 for the date to be considered not found
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
        });

      const result = await loadDailyIndex('2099-01-01');

      expect(result).toBeNull();
    });

    it('returns null on network error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await loadDailyIndex('2026-01-25');

      expect(result).toBeNull();
    });

    it('caches successful loads', async () => {
      const mockDaily: DailyIndex = {
        date: '2026-01-25',
        standard: { puzzles: [], total: 0 },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDaily),
      });

      // First call
      const result1 = await loadDailyIndex('2026-01-25');
      // Second call (should use cache)
      const result2 = await loadDailyIndex('2026-01-25');

      expect(result1).toEqual(result2);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('getStandardPuzzlePaths', () => {
    it('returns paths from standard challenge', () => {
      const daily: DailyIndex = {
        date: '2026-01-25',
        standard: {
          puzzles: ['sgf/a.sgf', 'sgf/b.sgf'],
          total: 2,
        },
      };

      expect(getStandardPuzzlePaths(daily)).toEqual(['sgf/a.sgf', 'sgf/b.sgf']);
    });

    it('returns empty array when no standard challenge', () => {
      const daily: DailyIndex = {
        date: '2026-01-25',
      };

      expect(getStandardPuzzlePaths(daily)).toEqual([]);
    });
  });

  describe('getTimedPuzzlePaths', () => {
    it('returns paths from timed queue', () => {
      const daily: DailyIndex = {
        date: '2026-01-25',
        timed: {
          queue: ['sgf/t1.sgf', 'sgf/t2.sgf', 'sgf/t3.sgf'],
          queue_size: 3,
          suggested_durations: [180, 300, 600],
        },
      };

      expect(getTimedPuzzlePaths(daily)).toEqual(['sgf/t1.sgf', 'sgf/t2.sgf', 'sgf/t3.sgf']);
    });
  });

  describe('getTagPuzzlePaths', () => {
    it('returns paths from tag challenge', () => {
      const daily: DailyIndex = {
        date: '2026-01-25',
        tag: {
          tag: 'ladder',
          technique_of_day: 'ladder',
          puzzles: ['sgf/ladder1.sgf'],
          total: 1,
        },
      };

      expect(getTagPuzzlePaths(daily)).toEqual(['sgf/ladder1.sgf']);
    });
  });

  describe('loadSGFContent', () => {
    it('loads SGF content from path', async () => {
      const mockSGF = '(;FF[4]GM[1]SZ[9]AB[aa])';

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(mockSGF),
      });

      const result = await loadSGFContent('sgf/beginner/test.sgf');

      expect(result).toBe(mockSGF);
      expect(mockFetch).toHaveBeenCalledWith(
        '/yengo-puzzle-collections/sgf/beginner/test.sgf'
      );
    });

    it('returns null on error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const result = await loadSGFContent('sgf/nonexistent.sgf');

      expect(result).toBeNull();
    });

    it('caches SGF content', async () => {
      const mockSGF = '(;FF[4]GM[1]SZ[9])';

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(mockSGF),
      });

      await loadSGFContent('sgf/cached.sgf');
      await loadSGFContent('sgf/cached.sgf');

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('loadPuzzle', () => {
    it('loads and parses puzzle from SGF path', async () => {
      const mockSGF = `(;FF[4]GM[1]SZ[9]
AB[aa][ba]AW[ca]
PL[B]
YG[beginner]YT[capture]
;B[da])`;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(mockSGF),
      });

      const result = await loadPuzzle('sgf/beginner/2026/01/batch-001/puzzle-001.sgf');

      expect(result).not.toBeNull();
      expect(result?.id).toBe('puzzle-001');
      expect(result?.boardSize).toBe(9);
      expect(result?.sideToMove).toBe('B');
      expect(result?.level).toBe('beginner');
      expect(result?.tags).toContain('capture');
    });

    it('returns null for invalid SGF', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve('not valid sgf'),
      });

      const result = await loadPuzzle('sgf/invalid.sgf');

      expect(result).toBeNull();
    });
  });

  describe('loadPuzzleBatch', () => {
    it('loads multiple puzzles in parallel', async () => {
      const mockSGF1 = '(;FF[4]GM[1]SZ[9]AB[aa]PL[B];B[ba])';
      const mockSGF2 = '(;FF[4]GM[1]SZ[9]AB[bb]PL[B];B[cb])';

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(mockSGF1),
        })
        .mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(mockSGF2),
        });

      const result = await loadPuzzleBatch(['sgf/p1.sgf', 'sgf/p2.sgf']);

      expect(result).toHaveLength(2);
    });

    it('filters out failed loads', async () => {
      const mockSGF = '(;FF[4]GM[1]SZ[9]AB[aa]PL[B];B[ba])';

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(mockSGF),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
        });

      const result = await loadPuzzleBatch(['sgf/good.sgf', 'sgf/bad.sgf']);

      expect(result).toHaveLength(1);
    });
  });

  describe('Challenge Info Functions', () => {
    const mockDaily: DailyIndex = {
      date: '2026-01-25',
      standard: {
        puzzles: ['sgf/p1.sgf'],
        total: 1,
      },
      timed: {
        queue: ['sgf/t1.sgf'],
        queue_size: 1,
        suggested_durations: [180],
      },
      tag: {
        tag: 'ladder',
        technique_of_day: 'ladder',
        puzzles: ['sgf/l1.sgf'],
        total: 1,
      },
    };

    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockDaily),
      });
    });

    it('getStandardChallengeInfo returns standard data', async () => {
      const result = await getStandardChallengeInfo('2026-01-25');
      expect(result).toEqual(mockDaily.standard);
    });

    it('getTimedChallengeInfo returns timed data', async () => {
      const result = await getTimedChallengeInfo('2026-01-25');
      expect(result).toEqual(mockDaily.timed);
    });

    it('getTagChallengeInfo returns tag data', async () => {
      const result = await getTagChallengeInfo('2026-01-25');
      expect(result).toEqual(mockDaily.tag);
    });
  });

  describe('isDailyAvailable', () => {
    it('returns true when daily exists', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ date: '2026-01-25' }),
      });

      expect(await isDailyAvailable('2026-01-25')).toBe(true);
    });

    it('returns false when daily not found', async () => {
      // Spec 112: loader tries nested path first, then legacy path
      // Both must return 404 for the date to be considered unavailable
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
        });

      expect(await isDailyAvailable('2099-01-01')).toBe(false);
    });
  });

  describe('clearDailyCache', () => {
    it('clears all caches', async () => {
      // Load something to cache
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ date: '2026-01-25' }),
      });
      await loadDailyIndex('2026-01-25');

      // Clear and try again
      clearDailyCache();
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ date: '2026-01-25' }),
      });
      await loadDailyIndex('2026-01-25');

      // Should have made 2 fetch calls (cache was cleared)
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });
});

describe('DailyIndex Contract Tests', () => {
  describe('Required fields', () => {
    it('validates minimal daily index', () => {
      const minimal: DailyIndex = {
        date: '2026-01-25',
      };

      expect(minimal.date).toBe('2026-01-25');
      expect(minimal.standard).toBeUndefined();
      expect(minimal.timed).toBeUndefined();
      expect(minimal.tag).toBeUndefined();
    });

    it('validates full daily index', () => {
      const full: DailyIndex = {
        date: '2026-01-25',
        generated_at: '2026-01-25T00:00:00Z',
        standard: {
          puzzles: ['p1.sgf', 'p2.sgf'],
          total: 2,
        },
        timed: {
          queue: ['t1.sgf'],
          queue_size: 1,
          suggested_durations: [180, 300],
        },
        tag: {
          tag: 'snapback',
          technique_of_day: 'snapback',
          puzzles: ['s1.sgf'],
          total: 1,
        },
        gauntlet: {
          puzzles: ['g1.sgf'],
          total: 1,
        },
        source_spotlight: {
          source: 'Cho Chikun',
          puzzles: ['cho1.sgf'],
          total: 1,
        },
      };

      expect(full.standard?.total).toBe(2);
      expect(full.timed?.queue_size).toBe(1);
      expect(full.tag?.technique_of_day).toBe('snapback');
      expect(full.gauntlet?.total).toBe(1);
      expect(full.source_spotlight?.source).toBe('Cho Chikun');
    });
  });

  describe('DailyPuzzleEntry format', () => {
    it('supports object entries with metadata', () => {
      const daily: DailyIndex = {
        date: '2026-01-25',
        standard: {
          puzzles: [
            { path: 'sgf/p1.sgf', level: 'beginner', rank: '25k' },
            { path: 'sgf/p2.sgf', level: 'basic' },
          ],
          total: 2,
        },
      };

      const paths = extractPuzzlePaths(daily.standard!.puzzles);
      expect(paths).toEqual(['sgf/p1.sgf', 'sgf/p2.sgf']);
    });
  });
});
