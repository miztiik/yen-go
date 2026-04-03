/**
 * Puzzle Loader Tests
 * @module tests/unit/puzzle-loader
 *
 * Tests for the SGF-based puzzle loader service.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  loadManifest,
  loadLevelIndex,
  loadDailyIndex,
  loadPuzzleFromPath,
  loadPuzzle,
  loadDailyChallengePuzzles,
  clearCache,
  getCachedPuzzleCount,
  SKILL_LEVELS,
  loadLevelMasterIndex,
} from '@services/puzzleLoader';

// Mock fetch
const mockFetch = vi.fn();

describe('puzzleLoader', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    clearCache();
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('loadManifest', () => {
    it('should load and cache manifest', async () => {
      const mockManifest = {
        version: '3.1',
        generated_at: '2026-01-24T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockManifest,
      });

      const result = await loadManifest();

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockManifest);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Should use cache on second call
      const result2 = await loadManifest();
      expect(result2.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(1); // No additional fetch
    });

    it('should return error when manifest not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const result = await loadManifest();

      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });

    it('should return error on network failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await loadManifest();

      expect(result.success).toBe(false);
      expect(result.error).toBe('network_error');
      expect(result.message).toContain('Network error');
    });
  });

  describe('loadLevelIndex', () => {
    it('should load level index', async () => {
      const mockLevelIndex = {
        level: 'beginner',
        count: 12,
        entries: [
          { id: 'puzzle1', path: 'sgf/beginner/puzzle1.sgf', tags: [] },
          { id: 'puzzle2', path: 'sgf/beginner/puzzle2.sgf', tags: ['ladder'] },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockLevelIndex,
      });

      const result = await loadLevelIndex('beginner');

      expect(result.success).toBe(true);
      expect(result.data?.name).toBe('beginner');
      expect(result.data?.entries).toHaveLength(2);
      expect(mockFetch).toHaveBeenCalledWith('/yengo-puzzle-collections/views/by-level/120/page-001.json');
    });

    it('should cache level index', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ level: 'beginner', entries: [] }),
      });

      await loadLevelIndex('beginner');
      await loadLevelIndex('beginner');

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should return error for invalid level', async () => {
      const result = await loadLevelIndex('nonexistent');

      expect(result.success).toBe(false);
      expect(result.error).toBe('invalid_data');
      expect(result.message).toContain('Unknown level slug');
    });
  });

  describe('loadDailyIndex', () => {
    it('should load daily index', async () => {
      const mockDaily = {
        date: '2026-01-25',
        generated_at: '2026-01-24T00:00:00Z',
        standard: {
          puzzles: [
            { id: 'p1', level: 'beginner', path: 'sgf/beginner/p1.sgf' },
          ],
        },
        timed: {
          queue: [
            { id: 'p2', level: 'beginner', path: 'sgf/beginner/p2.sgf' },
          ],
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDaily,
      });

      const result = await loadDailyIndex('2026-01-25');

      expect(result.success).toBe(true);
      expect(result.data?.date).toBe('2026-01-25');
      expect(result.data?.standard.puzzles).toHaveLength(1);
    });

    it('should return error for missing date', async () => {
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

      const result = await loadDailyIndex('1999-01-01');

      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });
  });

  describe('loadPuzzleFromPath', () => {
    it('should load and parse SGF puzzle', async () => {
      const sgfContent = `(;FF[4]GM[1]SZ[9]
AB[cc][dc][ec][cd][dd][ce]
AW[cb][db][eb][fc][bc][bd][be]
PL[B]
YG[beginner]
YT[capturing]
YH1[dc]
;B[fb];W[ed])`;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => sgfContent,
      });

      const result = await loadPuzzleFromPath('test-puzzle', 'sgf/beginner/test.sgf');

      expect(result.success).toBe(true);
      expect(result.data?.id).toBe('test-puzzle');
      expect(result.data?.boardSize).toBe(9);
      expect(result.data?.sideToMove).toBe('B');
      expect(result.data?.level).toBe('beginner');
      expect(result.data?.tags).toContain('capturing');
    });

    it('should cache loaded puzzles', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => '(;FF[4]GM[1]SZ[9]AB[aa]PL[B];B[bb])',
      });

      await loadPuzzleFromPath('puzzle-1', 'sgf/test.sgf');
      
      expect(getCachedPuzzleCount()).toBe(1);

      // Second call should use cache
      const result = await loadPuzzleFromPath('puzzle-1', 'sgf/test.sgf');
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should return error for invalid SGF', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => 'not valid sgf',
      });

      const result = await loadPuzzleFromPath('bad-puzzle', 'sgf/bad.sgf');

      expect(result.success).toBe(false);
      expect(result.error).toBe('parse_error');
    });

    it('should use level hint when YG not in SGF', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => '(;FF[4]GM[1]SZ[9]AB[aa]PL[B];B[bb])',
      });

      const result = await loadPuzzleFromPath('puzzle', 'sgf/test.sgf', 'intermediate');

      expect(result.success).toBe(true);
      expect(result.data?.level).toBe('intermediate');
    });
  });

  describe('loadPuzzle', () => {
    it('should find puzzle by searching levels', async () => {
      // Mock level index with the puzzle
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            level: 'beginner',
            entries: [
              { id: 'target-puzzle', path: 'sgf/beginner/target-puzzle.sgf', tags: [] },
            ],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          text: async () => '(;FF[4]GM[1]SZ[9]AB[aa]PL[B];B[bb])',
        });

      const result = await loadPuzzle('target-puzzle', 'beginner');

      expect(result.success).toBe(true);
      expect(result.data?.id).toBe('target-puzzle');
    });

    it('should return cached puzzle', async () => {
      // First load
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            level: 'beginner',
            entries: [{ id: 'cached-puzzle', path: 'sgf/beginner/cached-puzzle.sgf', tags: [] }],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          text: async () => '(;FF[4]GM[1]SZ[9]AB[aa]PL[B];B[bb])',
        });

      await loadPuzzle('cached-puzzle', 'beginner');

      // Second load should use cache
      mockFetch.mockClear();
      const result = await loadPuzzle('cached-puzzle');
      
      expect(result.success).toBe(true);
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('loadDailyChallengePuzzles', () => {
    it('should load all puzzles for daily challenge', async () => {
      // Mock daily index
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            date: '2026-01-25',
            standard: {
              puzzles: [
                { id: 'p1', level: 'beginner', path: 'sgf/beginner/p1.sgf' },
                { id: 'p2', level: 'beginner', path: 'sgf/beginner/p2.sgf' },
              ],
            },
            timed: { queue: [] },
          }),
        })
        // Mock SGF fetches
        .mockResolvedValueOnce({
          ok: true,
          text: async () => '(;FF[4]GM[1]SZ[9]AB[aa]PL[B];B[bb])',
        })
        .mockResolvedValueOnce({
          ok: true,
          text: async () => '(;FF[4]GM[1]SZ[9]AB[ab]PL[W];W[cc])',
        });

      const result = await loadDailyChallengePuzzles('2026-01-25');

      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(2);
    });

    it('should handle old string format for puzzle IDs', async () => {
      // This tests backward compatibility with old format
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            date: '2026-01-25',
            standard: {
              puzzles: ['puzzle1', 'puzzle2'], // Old format: string array
            },
            timed: { queue: [] },
          }),
        })
        // For string IDs, paths are empty so loadPuzzleFromPath will need to search
        .mockResolvedValueOnce({ ok: false, status: 404 }) // Empty path fails
        .mockResolvedValueOnce({ ok: false, status: 404 });

      const result = await loadDailyChallengePuzzles('2026-01-25');

      // Should fail because string IDs have no paths
      expect(result.success).toBe(false);
    });
  });

  describe('clearCache', () => {
    it('should clear all caches', async () => {
      // Load some data
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ version: '1.0', generated_at: '2026-01-01' }),
        text: async () => '(;FF[4])',
      });

      await loadManifest();
      
      expect(getCachedPuzzleCount()).toBe(0);
      
      clearCache();
      
      // Manifest should need to be reloaded
      await loadManifest();
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('SKILL_LEVELS', () => {
    it('should export correct skill levels', () => {
      // 9-level system per spec-010-level-system-refactor
      expect(SKILL_LEVELS).toEqual([
        'novice',
        'beginner',
        'elementary',
        'intermediate',
        'upper-intermediate',
        'advanced',
        'low-dan',
        'high-dan',
        'expert',
      ]);
    });
  });

  describe('loadLevelMasterIndex', () => {
    it('should load and cache level master index', async () => {
      const mockMasterIndex = {
        version: '2.0',
        generated_at: '2026-02-19T00:00:00Z',
        levels: [
          { id: 120, name: 'Beginner', slug: 'beginner', paginated: true, count: 42, pages: 1, tags: { '10': 5, '34': 3 } },
          { id: 130, name: 'Elementary', slug: 'elementary', paginated: true, count: 30, pages: 1, tags: { '10': 10 } },
        ],
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockMasterIndex,
      });

      const result = await loadLevelMasterIndex();
      expect(result).not.toBeNull();
      expect(result?.levels).toHaveLength(2);
      expect(result?.levels[0].id).toBe(120);

      // Should be cached — no second fetch
      const result2 = await loadLevelMasterIndex();
      expect(result2).toBe(result);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should return null on invalid structure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ version: '2.0' }), // Missing levels array
      });

      const result = await loadLevelMasterIndex();
      expect(result).toBeNull();
    });

    it('should return null on network error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('network'));

      const result = await loadLevelMasterIndex();
      expect(result).toBeNull();
    });

    it('should clear cache via clearCache()', async () => {
      const mockMasterIndex = {
        version: '2.0',
        generated_at: '2026-02-19T00:00:00Z',
        levels: [{ id: 120, name: 'Beginner', slug: 'beginner', paginated: true, count: 10, pages: 1, tags: {} }],
      };
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockMasterIndex,
      });

      await loadLevelMasterIndex();
      clearCache();
      await loadLevelMasterIndex();

      // Should have been called twice (once before clear, once after)
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });
});
