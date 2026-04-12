/**
 * PuzzleLoader Service Tests
 * @module tests/unit/puzzleLoader.test
 *
 * Tests for T026: PuzzleLoader service
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  loadManifest,
  loadLevel,
  loadPuzzle,
  getLevels,
  clearCache,
} from '@services/puzzleLoader';
import type { LevelManifest, LevelData } from '@models/level';
import type { Puzzle } from '@models/puzzle';

// Mock fetch via vi.stubGlobal so setup.ts afterEach can restore it
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('PuzzleLoader Service', () => {
  const mockManifest: LevelManifest = {
    version: '1.0',
    generatedAt: '2026-01-20T00:00:00Z',
    levels: [
      {
        id: '2026-01-20',
        date: '2026-01-20',
        name: 'Daily Challenge - January 20',
        puzzleCount: 3,
        byDifficulty: { beginner: 1, intermediate: 1, advanced: 1 },
      },
    ],
  };

  const mockPuzzle: Puzzle = {
    version: '1.0',
    id: '2026-01-20/001',
    boardSize: 9,
    initialState: [
      ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
      ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
      ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
      ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
      ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
      ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
      ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
      ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
      ['empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty', 'empty'],
    ],
    sideToMove: 'black',
    solutionTree: { move: { x: 4, y: 4 } },
    hints: ['Place in center'],
    explanations: [],
    metadata: {
      difficulty: '20kyu',
      difficultyScore: 1,
      tags: ['beginner'],
      level: '2026-01-20',
      createdAt: '2026-01-20T00:00:00Z',
    },
  };

  const mockLevelData: LevelData = {
    levelId: '2026-01-20',
    puzzles: [mockPuzzle],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    clearCache(); // Clear internal cache before each test
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('loadManifest', () => {
    it('should load manifest successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockManifest),
      });

      const result = await loadManifest();

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockManifest);
      expect(mockFetch).toHaveBeenCalledWith('/puzzles/manifest.json');
    });

    it('should cache manifest after first load', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockManifest),
      });

      // First load
      await loadManifest();
      
      // Second load should use cache
      const result = await loadManifest();

      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should return not_found error when manifest is missing', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      const result = await loadManifest();

      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });

    it('should return network_error on fetch failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network failed'));

      const result = await loadManifest();

      expect(result.success).toBe(false);
      expect(result.error).toBe('network_error');
    });
  });

  describe('loadLevel', () => {
    it('should load level data successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockLevelData),
      });

      const result = await loadLevel('2026-01-20');

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockLevelData);
      expect(mockFetch).toHaveBeenCalledWith('/puzzles/levels/2026-01-20.json');
    });

    it('should cache level data after first load', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockLevelData),
      });

      // First load
      await loadLevel('2026-01-20');
      
      // Second load should use cache
      const result = await loadLevel('2026-01-20');

      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should return not_found error when level is missing', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      const result = await loadLevel('nonexistent');

      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });
  });

  describe('loadPuzzle', () => {
    it('should load puzzle from level', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockLevelData),
      });

      const result = await loadPuzzle('2026-01-20/001');

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockPuzzle);
    });

    it('should return error for invalid puzzle ID format', async () => {
      const result = await loadPuzzle('invalid-id');

      expect(result.success).toBe(false);
      expect(result.error).toBe('invalid_data');
    });

    it('should return not_found when puzzle not in level', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockLevelData),
      });

      const result = await loadPuzzle('2026-01-20/999');

      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });
  });

  describe('getLevels', () => {
    it('should return levels from manifest', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockManifest),
      });

      const result = await getLevels();

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockManifest.levels);
    });

    it('should propagate manifest load error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      const result = await getLevels();

      expect(result.success).toBe(false);
    });
  });

  describe('Cache behavior', () => {
    it('should cache puzzles individually when loading a level', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockLevelData),
      });

      // Load level first
      await loadLevel('2026-01-20');

      // Loading puzzle should use cached data
      const result = await loadPuzzle('2026-01-20/001');

      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });
});
