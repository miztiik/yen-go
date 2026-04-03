/**
 * Puzzle Loaders Tests
 * @module tests/unit/puzzleLoaders
 *
 * Tests for services/puzzleLoaders — CollectionPuzzleLoader and DailyPuzzleLoader.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  CollectionPuzzleLoader,
  DailyPuzzleLoader,
} from '@services/puzzleLoaders';

// Mock the puzzleLoader service that CollectionPuzzleLoader depends on
vi.mock('@services/puzzleLoader', () => ({
  loadLevelIndex: vi.fn(),
  fetchSGFContent: vi.fn(),
}));

// Mock collectionService for prefixed collection IDs
vi.mock('@services/collectionService', () => ({
  loadCollection: vi.fn(),
  resolveCollectionDirId: vi.fn((id: string) => id),
  ensureCollectionIdsLoaded: vi.fn(() => Promise.resolve()),
}));

// Mock pagination module for paginated collections
vi.mock('@lib/puzzle/pagination', () => ({
  detectIndexType: vi.fn(),
  loadDirectoryIndex: vi.fn(),
  loadPage: vi.fn(),
}));

import { loadLevelIndex, fetchSGFContent } from '@services/puzzleLoader';
import { loadCollection, resolveCollectionDirId, ensureCollectionIdsLoaded } from '@services/collectionService';
import {
  detectIndexType,
  loadDirectoryIndex,
  loadPage,
} from '@lib/puzzle/pagination';

const mockLoadLevelIndex = vi.mocked(loadLevelIndex);
const mockFetchSGFContent = vi.mocked(fetchSGFContent);
const mockLoadCollection = vi.mocked(loadCollection);
const mockDetectIndexType = vi.mocked(detectIndexType);
const mockLoadDirectoryIndex = vi.mocked(loadDirectoryIndex);
const mockLoadPage = vi.mocked(loadPage);
const mockFetch = vi.fn();

describe('puzzleLoaders', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    mockLoadLevelIndex.mockReset();
    mockFetchSGFContent.mockReset();
    mockLoadCollection.mockReset();
    mockDetectIndexType.mockReset();
    mockLoadDirectoryIndex.mockReset();
    mockLoadPage.mockReset();
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ============================================================================
  // CollectionPuzzleLoader
  // ============================================================================

  describe('CollectionPuzzleLoader', () => {
    it('should start with idle status', () => {
      const loader = new CollectionPuzzleLoader('beginner');
      expect(loader.getStatus()).toBe('idle');
      expect(loader.getTotal()).toBe(0);
      expect(loader.getError()).toBeNull();
    });

    it('should load a collection successfully', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: true,
        data: {
          version: '3.0',
          level: 'beginner',
          count: 2,
          entries: [
            { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: ['life-and-death'] },
            { path: 'sgf/beginner/batch-0001/def456.sgf', tags: ['ko'] },
          ],
        },
      });

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(loader.getTotal()).toBe(2);
      expect(loader.getError()).toBeNull();
    });

    it('should report error on 404', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: false,
        error: 'not_found',
        message: 'Level not found',
      });

      // T040 fallback: bare slug also tries curated-{slug}
      mockLoadCollection.mockResolvedValueOnce({
        success: false,
        error: 'not_found',
        message: 'Collection not found',
      });

      const loader = new CollectionPuzzleLoader('nonexistent');
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('nonexistent');
      expect(loader.getError()).toContain('not found');
    });

    it('should report empty status for empty collection', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: true,
        data: {
          version: '3.0',
          level: 'beginner',
          count: 0,
          entries: [],
        },
      });

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      expect(loader.getStatus()).toBe('empty');
      expect(loader.getTotal()).toBe(0);
    });

    it('should handle network errors during load', async () => {
      mockLoadLevelIndex.mockRejectedValueOnce(new Error('Network failure'));

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('Network error');
    });

    it('should get entry metadata', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: true,
        data: {
          version: '3.0',
          level: 'beginner',
          count: 1,
          entries: [
            { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: ['life-and-death'] },
          ],
        },
      });

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      const entry = loader.getEntry(0);
      expect(entry).not.toBeNull();
      expect(entry!.id).toBe('abc123');
      expect(entry!.path).toBe('sgf/beginner/batch-0001/abc123.sgf');
      expect(entry!.level).toBe('beginner');
    });

    it('should return null for out-of-bounds entry', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: true,
        data: {
          version: '3.0',
          level: 'beginner',
          count: 1,
          entries: [
            { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: [] },
          ],
        },
      });

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      expect(loader.getEntry(5)).toBeNull();
    });

    it('should load SGF content for a puzzle', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: true,
        data: {
          version: '3.0',
          level: 'beginner',
          count: 1,
          entries: [
            { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: [] },
          ],
        },
      });

      const sgfContent = '(;FF[4]GM[1]SZ[19];B[dp])';
      mockFetchSGFContent.mockResolvedValueOnce({
        success: true,
        data: sgfContent,
      });

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      const result = await loader.getPuzzleSgf(0);
      expect(result.success).toBe(true);
      expect(result.data).toBe(sgfContent);
    });

    it('should cache SGF content', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: true,
        data: {
          version: '3.0',
          level: 'beginner',
          count: 1,
          entries: [
            { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: [] },
          ],
        },
      });

      mockFetchSGFContent.mockResolvedValueOnce({
        success: true,
        data: '(;FF[4])',
      });

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      // First call fetches
      await loader.getPuzzleSgf(0);
      // Second call uses cache
      await loader.getPuzzleSgf(0);

      expect(mockFetchSGFContent).toHaveBeenCalledTimes(1);
    });

    it('should return error for out-of-bounds SGF request', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: true,
        data: {
          version: '3.0',
          level: 'beginner',
          count: 1,
          entries: [
            { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: [] },
          ],
        },
      });

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      const result = await loader.getPuzzleSgf(99);
      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });

    it('should return error when SGF fetch fails', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: true,
        data: {
          version: '3.0',
          level: 'beginner',
          count: 1,
          entries: [
            { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: [] },
          ],
        },
      });

      mockFetchSGFContent.mockResolvedValueOnce({
        success: false,
        error: 'network_error',
        message: 'Failed to fetch SGF',
      });

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      const result = await loader.getPuzzleSgf(0);
      expect(result.success).toBe(false);
      expect(result.error).toBe('network_error');
    });

    // T051: Tests for prefixed collection IDs (T040 routing)
    it('should load level-prefixed collection via collectionService', async () => {
      mockDetectIndexType.mockResolvedValueOnce({
        name: 'level-beginner',
        count: 0,
        type: 'not-found',
      });
      mockLoadCollection.mockResolvedValueOnce({
        success: true,
        data: {
          id: 'level-beginner',
          name: 'Beginner Puzzles',
          description: '',
          version: '1.0',
          generatedAt: new Date().toISOString(),
          puzzles: [
            { id: 'abc123', path: 'sgf/beginner/batch-0001/abc123.sgf' },
            { id: 'def456', path: 'sgf/beginner/batch-0001/def456.sgf' },
          ],
        },
      });

      const loader = new CollectionPuzzleLoader('level-beginner');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(loader.getTotal()).toBe(2);
      expect(mockLoadCollection).toHaveBeenCalledWith('level-beginner');
    });

    it('should load tag-prefixed collection via collectionService', async () => {
      mockDetectIndexType.mockResolvedValueOnce({
        name: 'tag-life-and-death',
        count: 0,
        type: 'not-found',
      });
      mockLoadCollection.mockResolvedValueOnce({
        success: true,
        data: {
          id: 'tag-life-and-death',
          name: 'Life & Death',
          description: '',
          version: '1.0',
          generatedAt: new Date().toISOString(),
          puzzles: [
            { id: 'xyz789', path: 'sgf/intermediate/batch-0001/xyz789.sgf' },
          ],
        },
      });

      const loader = new CollectionPuzzleLoader('tag-life-and-death');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(loader.getTotal()).toBe(1);
    });

    it('should use legacy loadLevelIndex for bare slug', async () => {
      mockLoadLevelIndex.mockResolvedValueOnce({
        success: true,
        data: {
          version: '3.0',
          level: 'intermediate',
          count: 1,
          entries: [
            { path: 'sgf/intermediate/batch-0001/abc123.sgf', tags: [] },
          ],
        },
      });

      const loader = new CollectionPuzzleLoader('intermediate');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(mockLoadLevelIndex).toHaveBeenCalledWith('intermediate');
      expect(mockLoadCollection).not.toHaveBeenCalled();
    });

    // T051: Tests for paginated collections (T048)
    it('should load paginated collection and jump to target page', async () => {
      mockDetectIndexType.mockResolvedValueOnce({
        name: 'level-beginner',
        count: 150,
        type: 'paginated',
        pages: 3,
      });

      mockLoadDirectoryIndex.mockResolvedValueOnce({
        type: 'collection',
        name: 'level-beginner',
        total_count: 150,
        page_size: 50,
        pages: 3,
      });

      mockLoadPage.mockResolvedValueOnce({
        type: 'collection',
        name: 'level-beginner',
        page: 2,
        entries: [
          { path: 'sgf/beginner/batch-0001/p51.sgf' },
          { path: 'sgf/beginner/batch-0001/p52.sgf' },
        ],
      });

      // Adjacent page pre-fetches (fire-and-forget, may resolve later)
      mockLoadPage.mockResolvedValue({
        type: 'collection',
        name: 'level-beginner',
        page: 1,
        entries: [],
      });

      // startIndex=75 → page 2 (75/50 + 1 = 2)
      const loader = new CollectionPuzzleLoader('level-beginner', 75);
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(loader.getTotal()).toBe(150); // paginatedTotal, not entries.length
    });

    it('should show error for startIndex beyond totalPuzzles', async () => {
      mockDetectIndexType.mockResolvedValueOnce({
        name: 'level-beginner',
        count: 50,
        type: 'paginated',
        pages: 2,
      });

      mockLoadDirectoryIndex.mockResolvedValueOnce({
        type: 'collection',
        name: 'level-beginner',
        total_count: 50,
        page_size: 25,
        pages: 2,
      });

      const loader = new CollectionPuzzleLoader('level-beginner', 99999);
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('Puzzle not found');
      expect(loader.getError()).toContain('50');
    });
  });

  // ============================================================================
  // DailyPuzzleLoader
  // ============================================================================

  describe('DailyPuzzleLoader', () => {
    it('should start with idle status', () => {
      const loader = new DailyPuzzleLoader('2026-01-28');
      expect(loader.getStatus()).toBe('idle');
      expect(loader.getTotal()).toBe(0);
      expect(loader.getError()).toBeNull();
    });

    it('should load daily challenge successfully', async () => {
      const dailyData = {
        standard: {
          puzzles: [
            { path: 'sgf/beginner/batch-0001/abc123.sgf', level: 'beginner' },
            { path: 'sgf/intermediate/batch-0001/def456.sgf', level: 'intermediate' },
          ],
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(dailyData),
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(loader.getTotal()).toBe(2);
    });

    it('should try legacy path on 404', async () => {
      const dailyData = {
        standard: {
          puzzles: [
            { path: 'sgf/beginner/batch-0001/abc123.sgf', level: 'beginner' },
          ],
        },
      };

      // First fetch (nested path) returns 404
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });
      // Second fetch (legacy flat path) succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(dailyData),
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('should report error when both paths fail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('No daily challenge available');
    });

    it('should report empty status for empty daily', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ standard: { puzzles: [] } }),
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getStatus()).toBe('empty');
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network failure'));

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('Network error');
    });

    it('should get entry metadata', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            standard: {
              puzzles: [
                { path: 'sgf/beginner/batch-0001/abc123.sgf', level: 'beginner' },
              ],
            },
          }),
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      const entry = loader.getEntry(0);
      expect(entry).not.toBeNull();
      expect(entry!.id).toBe('abc123');
      expect(entry!.path).toBe('sgf/beginner/batch-0001/abc123.sgf');
      expect(entry!.level).toBe('beginner');
    });

    it('should return null for out-of-bounds entry', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            standard: { puzzles: [{ path: 'sgf/beginner/batch-0001/a.sgf', level: 'beginner' }] },
          }),
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getEntry(5)).toBeNull();
    });

    it('should load SGF content for a daily puzzle', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            standard: {
              puzzles: [
                { path: 'sgf/beginner/batch-0001/abc123.sgf', level: 'beginner' },
              ],
            },
          }),
      });

      const sgfContent = '(;FF[4]GM[1]SZ[19];B[dp])';
      mockFetchSGFContent.mockResolvedValueOnce({
        success: true,
        data: sgfContent,
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      const result = await loader.getPuzzleSgf(0);
      expect(result.success).toBe(true);
      expect(result.data).toBe(sgfContent);
    });

    it('should cache SGF content for daily puzzles', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            standard: {
              puzzles: [
                { path: 'sgf/beginner/batch-0001/abc123.sgf', level: 'beginner' },
              ],
            },
          }),
      });

      mockFetchSGFContent.mockResolvedValueOnce({
        success: true,
        data: '(;FF[4])',
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      await loader.getPuzzleSgf(0);
      await loader.getPuzzleSgf(0);

      expect(mockFetchSGFContent).toHaveBeenCalledTimes(1);
    });

    it('should return error for not-found puzzle index', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            standard: {
              puzzles: [
                { path: 'sgf/beginner/batch-0001/abc123.sgf', level: 'beginner' },
              ],
            },
          }),
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      const result = await loader.getPuzzleSgf(99);
      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });
  });
});
