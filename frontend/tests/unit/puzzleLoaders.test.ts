/**
 * Puzzle Loaders Tests
 * @module tests/unit/puzzleLoaders
 *
 * Tests for services/puzzleLoaders — CollectionPuzzleLoader and DailyPuzzleLoader.
 * Tests mock the SQLite-based query services that the loaders depend on.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  CollectionPuzzleLoader,
  DailyPuzzleLoader,
} from '@services/puzzleLoaders';
import type { PuzzleRow } from '@services/puzzleQueryService';

// ============================================================================
// Mocks — SQLite-based dependencies
// ============================================================================

vi.mock('@services/sqliteService', () => ({
  init: vi.fn(() => Promise.resolve()),
  query: vi.fn(() => []),
  isReady: vi.fn(() => true),
  getDb: vi.fn(() => null),
  checkForUpdates: vi.fn(() => Promise.resolve({ needsUpdate: false })),
}));

vi.mock('@services/puzzleQueryService', () => ({
  getPuzzlesByCollection: vi.fn(() => []),
  getPuzzlesByTag: vi.fn(() => []),
  getPuzzlesByLevel: vi.fn(() => []),
  getPuzzlesFiltered: vi.fn(() => []),
}));

vi.mock('@services/configService', () => ({
  levelIdToSlug: vi.fn((id: number) => {
    const map: Record<number, string> = { 120: 'beginner', 140: 'intermediate' };
    return map[id] ?? 'unknown';
  }),
  levelSlugToId: vi.fn((slug: string) => {
    const map: Record<string, number> = { beginner: 120, intermediate: 140 };
    return map[slug];
  }),
  tagSlugToId: vi.fn(() => undefined),
}));

vi.mock('@services/entryDecoder', () => ({
  expandPath: vi.fn((compact: string) => `sgf/${compact}.sgf`),
}));

vi.mock('@services/collectionService', () => ({
  resolveCollectionDirId: vi.fn(),
  ensureCollectionIdsLoaded: vi.fn(() => Promise.resolve()),
  getCollectionTypeBySlug: vi.fn(() => undefined),
}));

vi.mock('@services/puzzleLoader', () => ({
  fetchSGFContent: vi.fn(),
}));

vi.mock('@services/puzzleRushService', () => ({
  getNextRushPuzzle: vi.fn(),
  loadRushTagEntries: vi.fn(),
  loadLevelIndex: vi.fn(),
}));

vi.mock('@lib/puzzle/utils', () => ({
  extractPuzzleIdFromPath: vi.fn((path: string) => {
    const match = path.match(/([^/]+)\.sgf$/);
    return match?.[1] ?? path;
  }),
}));

vi.mock('@/constants/collectionConfig', () => ({
  SHUFFLE_POLICY: {},
  shuffleArray: vi.fn((arr: unknown[]) => arr),
}));

// DailyPuzzleLoader dynamically imports dailyQueryService
vi.mock('@services/dailyQueryService', () => ({
  getDailySchedule: vi.fn(),
  getDailyPuzzles: vi.fn(() => []),
}));

// ============================================================================
// Import mocked functions for per-test configuration
// ============================================================================

import {
  getPuzzlesByCollection,
  getPuzzlesByTag,
  getPuzzlesByLevel,
} from '@services/puzzleQueryService';
import { resolveCollectionDirId } from '@services/collectionService';
import { fetchSGFContent } from '@services/puzzleLoader';
import { getDailySchedule, getDailyPuzzles } from '@services/dailyQueryService';

const mockGetPuzzlesByCollection = vi.mocked(getPuzzlesByCollection);
const mockGetPuzzlesByTag = vi.mocked(getPuzzlesByTag);
const mockGetPuzzlesByLevel = vi.mocked(getPuzzlesByLevel);
const mockResolveCollectionDirId = vi.mocked(resolveCollectionDirId);
const mockFetchSGFContent = vi.mocked(fetchSGFContent);
const mockGetDailySchedule = vi.mocked(getDailySchedule);
const mockGetDailyPuzzles = vi.mocked(getDailyPuzzles);

// ============================================================================
// Helpers
// ============================================================================

/** Create a minimal PuzzleRow for testing. */
function makePuzzleRow(hash: string, batch = '0001', levelId = 120): PuzzleRow {
  return {
    content_hash: hash,
    batch,
    level_id: levelId,
    quality: 2,
    content_type: 1,
    cx_depth: 3,
    cx_refutations: 5,
    cx_solution_len: 3,
    cx_unique_resp: 2,
    ac: 1,
    attrs: '',
  };
}

describe('puzzleLoaders', () => {
  beforeEach(() => {
    mockGetPuzzlesByCollection.mockReset();
    mockGetPuzzlesByTag.mockReset();
    mockGetPuzzlesByLevel.mockReset();
    mockResolveCollectionDirId.mockReset();
    mockFetchSGFContent.mockReset();
    mockGetDailySchedule.mockReset();
    mockGetDailyPuzzles.mockReset().mockReturnValue([]);
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
      mockResolveCollectionDirId.mockReturnValue(1);
      mockGetPuzzlesByCollection.mockReturnValue([
        makePuzzleRow('abc123'),
        makePuzzleRow('def456'),
      ]);

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(loader.getTotal()).toBe(2);
      expect(loader.getError()).toBeNull();
    });

    it('should report error on 404', async () => {
      mockResolveCollectionDirId.mockReturnValue(undefined);

      const loader = new CollectionPuzzleLoader('nonexistent');
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('nonexistent');
    });

    it('should report empty status for empty collection', async () => {
      mockResolveCollectionDirId.mockReturnValue(1);
      mockGetPuzzlesByCollection.mockReturnValue([]);

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      expect(loader.getStatus()).toBe('empty');
      expect(loader.getTotal()).toBe(0);
    });

    it('should handle network errors during load', async () => {
      mockResolveCollectionDirId.mockImplementation(() => {
        throw new Error('Network failure');
      });

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('Network failure');
    });

    it('should get entry metadata', async () => {
      mockResolveCollectionDirId.mockReturnValue(1);
      mockGetPuzzlesByCollection.mockReturnValue([
        makePuzzleRow('abc123'),
      ]);

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      const entry = loader.getEntry(0);
      expect(entry).not.toBeNull();
      expect(entry!.id).toBe('abc123');
      expect(entry!.path).toBe('sgf/0001/abc123.sgf');
      expect(entry!.level).toBe('beginner');
    });

    it('should return null for out-of-bounds entry', async () => {
      mockResolveCollectionDirId.mockReturnValue(1);
      mockGetPuzzlesByCollection.mockReturnValue([
        makePuzzleRow('abc123'),
      ]);

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      expect(loader.getEntry(5)).toBeNull();
    });

    it('should load SGF content for a puzzle', async () => {
      mockResolveCollectionDirId.mockReturnValue(1);
      mockGetPuzzlesByCollection.mockReturnValue([
        makePuzzleRow('abc123'),
      ]);

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
      mockResolveCollectionDirId.mockReturnValue(1);
      mockGetPuzzlesByCollection.mockReturnValue([
        makePuzzleRow('abc123'),
      ]);

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
      mockResolveCollectionDirId.mockReturnValue(1);
      mockGetPuzzlesByCollection.mockReturnValue([
        makePuzzleRow('abc123'),
      ]);

      const loader = new CollectionPuzzleLoader('beginner');
      await loader.load();

      const result = await loader.getPuzzleSgf(99);
      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });

    it('should return error when SGF fetch fails', async () => {
      mockResolveCollectionDirId.mockReturnValue(1);
      mockGetPuzzlesByCollection.mockReturnValue([
        makePuzzleRow('abc123'),
      ]);

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

    it('should load level-prefixed collection via getPuzzlesByLevel', async () => {
      mockResolveCollectionDirId.mockReturnValue(120);
      mockGetPuzzlesByLevel.mockReturnValue([
        makePuzzleRow('abc123'),
        makePuzzleRow('def456'),
      ]);

      const loader = new CollectionPuzzleLoader('level-beginner');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(loader.getTotal()).toBe(2);
      expect(mockGetPuzzlesByLevel).toHaveBeenCalledWith(120);
    });

    it('should load tag-prefixed collection via getPuzzlesByTag', async () => {
      mockResolveCollectionDirId.mockReturnValue(5);
      mockGetPuzzlesByTag.mockReturnValue([
        makePuzzleRow('xyz789', '0001', 140),
      ]);

      const loader = new CollectionPuzzleLoader('tag-life-and-death');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(loader.getTotal()).toBe(1);
      expect(mockGetPuzzlesByTag).toHaveBeenCalledWith(5);
    });

    it('should use getPuzzlesByCollection for bare slug', async () => {
      mockResolveCollectionDirId.mockReturnValue(42);
      mockGetPuzzlesByCollection.mockReturnValue([
        makePuzzleRow('abc123', '0001', 140),
      ]);

      const loader = new CollectionPuzzleLoader('intermediate');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(mockGetPuzzlesByCollection).toHaveBeenCalledWith(42);
      expect(mockGetPuzzlesByLevel).not.toHaveBeenCalled();
    });

    it('should report error for unknown collection slug', async () => {
      mockResolveCollectionDirId.mockReturnValue(undefined);

      const loader = new CollectionPuzzleLoader('does-not-exist');
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('does-not-exist');
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
      mockGetDailySchedule.mockReturnValue({
        date: '2026-01-28',
        version: '1',
        generated_at: '2026-01-28T00:00:00Z',
        technique_of_day: 'life-and-death',
        attrs: '',
      });
      mockGetDailyPuzzles.mockReturnValue([
        { date: '2026-01-28', content_hash: 'abc123', section: 'standard', position: 0, batch: '0001', level_id: 120 },
        { date: '2026-01-28', content_hash: 'def456', section: 'standard', position: 1, batch: '0001', level_id: 140 },
      ]);

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getStatus()).toBe('ready');
      expect(loader.getTotal()).toBe(2);
    });

    it('should report error when no schedule exists', async () => {
      mockGetDailySchedule.mockReturnValue(null);

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('No daily challenge available');
    });

    it('should report empty status for empty daily', async () => {
      mockGetDailySchedule.mockReturnValue({
        date: '2026-01-28',
        version: '1',
        generated_at: '2026-01-28T00:00:00Z',
        technique_of_day: 'life-and-death',
        attrs: '',
      });
      mockGetDailyPuzzles.mockReturnValue([]);

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getStatus()).toBe('empty');
    });

    it('should handle errors during load', async () => {
      mockGetDailySchedule.mockImplementation(() => {
        throw new Error('DB not initialized');
      });

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getStatus()).toBe('error');
      expect(loader.getError()).toContain('DB not initialized');
    });

    it('should get entry metadata', async () => {
      mockGetDailySchedule.mockReturnValue({
        date: '2026-01-28',
        version: '1',
        generated_at: '2026-01-28T00:00:00Z',
        technique_of_day: 'life-and-death',
        attrs: '',
      });
      mockGetDailyPuzzles.mockReturnValue([
        { date: '2026-01-28', content_hash: 'abc123', section: 'standard', position: 0, batch: '0001', level_id: 120 },
      ]);

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      const entry = loader.getEntry(0);
      expect(entry).not.toBeNull();
      expect(entry!.id).toBe('abc123');
      expect(entry!.path).toBe('sgf/0001/abc123.sgf');
      expect(entry!.level).toBe('beginner');
    });

    it('should return null for out-of-bounds entry', async () => {
      mockGetDailySchedule.mockReturnValue({
        date: '2026-01-28',
        version: '1',
        generated_at: '2026-01-28T00:00:00Z',
        technique_of_day: 'life-and-death',
        attrs: '',
      });
      mockGetDailyPuzzles.mockReturnValue([
        { date: '2026-01-28', content_hash: 'abc123', section: 'standard', position: 0, batch: '0001', level_id: 120 },
      ]);

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      expect(loader.getEntry(5)).toBeNull();
    });

    it('should load SGF content for a daily puzzle', async () => {
      mockGetDailySchedule.mockReturnValue({
        date: '2026-01-28',
        version: '1',
        generated_at: '2026-01-28T00:00:00Z',
        technique_of_day: 'life-and-death',
        attrs: '',
      });
      mockGetDailyPuzzles.mockReturnValue([
        { date: '2026-01-28', content_hash: 'abc123', section: 'standard', position: 0, batch: '0001', level_id: 120 },
      ]);

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
      mockGetDailySchedule.mockReturnValue({
        date: '2026-01-28',
        version: '1',
        generated_at: '2026-01-28T00:00:00Z',
        technique_of_day: 'life-and-death',
        attrs: '',
      });
      mockGetDailyPuzzles.mockReturnValue([
        { date: '2026-01-28', content_hash: 'abc123', section: 'standard', position: 0, batch: '0001', level_id: 120 },
      ]);

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
      mockGetDailySchedule.mockReturnValue({
        date: '2026-01-28',
        version: '1',
        generated_at: '2026-01-28T00:00:00Z',
        technique_of_day: 'life-and-death',
        attrs: '',
      });
      mockGetDailyPuzzles.mockReturnValue([
        { date: '2026-01-28', content_hash: 'abc123', section: 'standard', position: 0, batch: '0001', level_id: 120 },
      ]);

      const loader = new DailyPuzzleLoader('2026-01-28');
      await loader.load();

      const result = await loader.getPuzzleSgf(99);
      expect(result.success).toBe(false);
      expect(result.error).toBe('not_found');
    });
  });
});
