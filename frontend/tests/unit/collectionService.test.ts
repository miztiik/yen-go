/**
 * Collection Service Unit Tests
 * @module tests/unit/collectionService.test
 *
 * Tests for collection loading, filtering, and progress tracking.
 * Covers: FR-001 to FR-014 (Collection Browsing)
 * 
 * KNOWN ISSUES (pre-existing, not from Phase 14):
 * - Some tests have mock isolation issues due to shared cache state
 * - createPracticeSet tag filtering test has wrong mock setup
 * - getRandomPuzzle level filtering needs level-specific mock
 * - getNextValidPuzzle needs mock refactoring
 * TODO: Refactor mocks to properly isolate cache state between tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  loadCollectionIndex,
  loadCollection,
  getFilteredCollections,
  getCollectionPuzzle,
  isCollectionsAvailable,
  clearCache,
  getPuzzleCountForFilters,
  createPracticeSet,
  estimateUserLevel,
  getRandomPuzzle,
  validatePuzzle,
  filterValidPuzzles,
  getNextValidPuzzle,
  clearPuzzleValidationCache,
  loadCollectionMasterIndex,
  clearCatalogCache,
  resolveCollectionDirId,
  ensureCollectionIdsLoaded,
} from '../../src/services/collectionService';
import { clearCache as clearPuzzleLoaderCache } from '../../src/services/puzzleLoader';
import type { CollectionPuzzleEntry, CollectionSummary } from '../../src/models/collection';

/**
 * Helper to clear all caches - both collectionService and puzzleLoader caches
 */
function clearAllCaches(): void {
  clearCache();
  clearPuzzleLoaderCache();
  clearPuzzleValidationCache();
}

// Mock fetch
const mockFetch = vi.fn();

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

describe('collectionService', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    // Clear ALL caches: collectionService, puzzleLoader, and validation
    clearAllCaches();
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('loadCollectionIndex', () => {
    it('should return cached index on subsequent calls', async () => {
      // Setup mock for all level indexes (service fetches all 9 levels)
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: [{ id: 'p1', path: 'path/to/p1.sgf' }],
        }),
      });

      const result1 = await loadCollectionIndex();
      const initialFetchCount = mockFetch.mock.calls.length;
      
      const result2 = await loadCollectionIndex();
      
      // Should not fetch again (cached)
      expect(mockFetch).toHaveBeenCalledTimes(initialFetchCount);
      expect(result1.success).toBe(result2.success);
    });
  });

  describe('getFilteredCollections', () => {
    beforeEach(() => {
      // Setup mock for multiple levels
      const levels = ['elementary', 'intermediate', 'advanced'];
      let callCount = 0;
      
      mockFetch.mockImplementation(async () => {
        const level = levels[callCount % levels.length] ?? 'elementary';
        callCount++;
        return {
          ok: true,
          json: async () => ({
            level,
            generatedAt: '2024-01-01',
            entries: Array.from({ length: 10 }, (_, i) => ({
              id: `${level}-p${i}`,
              path: `path/to/${level}-p${i}.sgf`,
            })),
          }),
        };
      });
    });

    it('should filter by search term', async () => {
      const result = await getFilteredCollections({ searchTerm: 'elementary' });

      expect(result.success).toBe(true);
      if (result.success && result.data) {
        const hasElementary = result.data.some((c: CollectionSummary) => 
          c.name.toLowerCase().includes('elementary')
        );
        expect(hasElementary).toBe(true);
      }
    });
  });

  describe('getCollectionPuzzle', () => {
    beforeEach(() => {
      // Clear cache and mocks before each test
      clearCache();
      vi.clearAllMocks();
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: [
            { id: 'p0', path: 'path/to/p0.sgf' },
            { id: 'p1', path: 'path/to/p1.sgf' },
            { id: 'p2', path: 'path/to/p2.sgf' },
          ],
        }),
      });
    });

    it('should return puzzle at valid index', async () => {
      // Setup fresh mock with proper puzzle data
      clearCache();
      vi.clearAllMocks();
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: [
            { id: 'p0', path: 'path/to/p0.sgf' },
            { id: 'p1', path: 'path/to/p1.sgf' },
            { id: 'p2', path: 'path/to/p2.sgf' },
          ],
        }),
      });

      const result = await getCollectionPuzzle('level-elementary', 1);

      expect(result.success).toBe(true);
      expect(result.data?.id).toBe('p1');
    });

    it('should return error for invalid index', async () => {
      const result = await getCollectionPuzzle('level-elementary', 100);

      expect(result.success).toBe(false);
      expect(result.error).toBe('invalid_data');
    });

    it('should return error for negative index', async () => {
      const result = await getCollectionPuzzle('level-elementary', -1);

      expect(result.success).toBe(false);
    });
  });

  describe('loadCollection - curated with zero puzzles (FR-023)', () => {
    it('should append "(Coming soon)" to description for curated collection with no view data', async () => {
      clearAllCaches();
      vi.clearAllMocks();

      mockFetch.mockImplementation(async (url: string) => {
        // config/collections.json — return a curated collection
        if (url.includes('config/collections.json')) {
          return {
            ok: true,
            json: async () => ({
              version: '2.0',
              collections: [
                {
                  slug: 'gokyo-shumyo',
                  name: 'Gokyo Shumyo',
                  description: 'Classical life-and-death collection',
                  curator: 'Hayashi Genbi',
                  source: 'mixed',
                  type: 'author',
                  ordering: 'source',
                  aliases: ['碁経衆妙', 'shumyo'],
                },
              ],
            }),
          };
        }
        // views/by-collection/{slug}.json — 404 (no puzzles yet)
        if (url.includes('by-collection')) {
          return { ok: false, status: 404 };
        }
        // All other requests (level indexes etc.) — empty
        return { ok: false, status: 404 };
      });

      const result = await loadCollection('curated-gokyo-shumyo');

      expect(result.success).toBe(true);
      expect(result.data?.name).toBe('Gokyo Shumyo');
      expect(result.data?.description).toContain('(Coming soon)');
      expect(result.data?.puzzles).toEqual([]);
    });

    it('should NOT append "(Coming soon)" for curated collection with puzzles', async () => {
      clearAllCaches();
      vi.clearAllMocks();

      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes('config/collections.json')) {
          return {
            ok: true,
            json: async () => ({
              version: '2.0',
              collections: [
                {
                  id: 42,
                  slug: 'ladder-problems',
                  name: 'Ladder Problems',
                  description: 'Techniques involving ladders',
                  curator: 'Curated',
                  source: 'mixed',
                  type: 'technique',
                  ordering: 'difficulty',
                  aliases: ['シチョウ', 'ladder'],
                },
              ],
            }),
          };
        }
        // D23: View fetched by numeric ID (42), not slug
        if (url.includes('by-collection/42')) {
          return {
            ok: true,
            json: async () => ({
              version: '1.0',
              collection: 'ladder-problems',
              total: 2,
              entries: [
                { path: 'sgf/beginner/batch-0001/abc.sgf', level: 'beginner', sequence_number: 1 },
                { path: 'sgf/beginner/batch-0001/def.sgf', level: 'beginner', sequence_number: 2 },
              ],
            }),
          };
        }
        return { ok: false, status: 404 };
      });

      const result = await loadCollection('curated-ladder-problems');

      expect(result.success).toBe(true);
      expect(result.data?.name).toBe('Ladder Problems');
      expect(result.data?.description).not.toContain('(Coming soon)');
      expect(result.data?.puzzles.length).toBe(2);
    });
  });

  describe('isCollectionsAvailable', () => {
    it('should return true when collections exist', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: [{ id: 'p1', path: 'path/to/p1.sgf' }],
        }),
      });

      const available = await isCollectionsAvailable();
      expect(available).toBe(true);
    });
  });

  describe('getPuzzleCountForFilters', () => {
    beforeEach(() => {
      // Clear cache to ensure fresh state
      clearCache();
      vi.clearAllMocks();
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: [
            { id: 'p1', path: 'path/to/p1.sgf', tags: ['snapback'] },
            { id: 'p2', path: 'path/to/p2.sgf', tags: ['ladder'] },
            { id: 'p3', path: 'path/to/p3.sgf', tags: ['snapback', 'capture'] },
          ],
        }),
      });
    });

    it('should count puzzles matching level filter', async () => {
      const count = await getPuzzleCountForFilters('elementary', []);
      expect(count).toBeGreaterThan(0);
    });

    it('should count puzzles matching tag filter', async () => {
      // Setup mock with puzzles that have tags
      clearCache();
      vi.clearAllMocks();
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: [
            { id: 'p1', path: 'path/to/p1.sgf', tags: ['snapback'] },
            { id: 'p2', path: 'path/to/p2.sgf', tags: ['ladder'] },
            { id: 'p3', path: 'path/to/p3.sgf', tags: ['snapback', 'capture'] },
            { id: 'p4', path: 'path/to/p4.sgf', tags: ['ko'] },
          ],
        }),
      });

      const count = await getPuzzleCountForFilters('elementary', ['snapback']);
      expect(count).toBe(2);
    });
  });

  describe('createPracticeSet', () => {
    beforeEach(() => {
      // Clear cache to ensure fresh state
      clearCache();
      vi.clearAllMocks();
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: Array.from({ length: 20 }, (_, i) => ({
            id: `p${i}`,
            path: `path/to/p${i}.sgf`,
            tags: i % 2 === 0 ? ['snapback'] : ['ladder'],
          })),
        }),
      });
    });

    it('should create practice set with max puzzles', async () => {
      // Clear cache and setup fresh mock
      clearCache();
      vi.clearAllMocks();
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: Array.from({ length: 20 }, (_, i) => ({
            id: `p${i}`,
            path: `path/to/p${i}.sgf`,
            tags: i % 2 === 0 ? ['snapback'] : ['ladder'],
          })),
        }),
      });

      const result = await createPracticeSet({
        level: 'elementary',
        tags: [],
        maxPuzzles: 5,
      });

      expect(result.success).toBe(true);
      expect(result.data?.puzzles.length).toBe(5);
    });

    it('should filter by tags', async () => {
      // Clear cache and setup fresh mock with tagged puzzles
      clearCache();
      vi.clearAllMocks();
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: Array.from({ length: 20 }, (_, i) => ({
            id: `p${i}`,
            path: `path/to/p${i}.sgf`,
            tags: i % 2 === 0 ? ['snapback'] : ['ladder'],
          })),
        }),
      });

      const result = await createPracticeSet({
        level: 'elementary',
        tags: ['snapback'],
        maxPuzzles: 100,
      });

      expect(result.success).toBe(true);
      expect(result.data?.puzzles.length).toBe(10); // Half have snapback tag
    });

    it('should use seed for reproducible shuffling', async () => {
      const result1 = await createPracticeSet({
        level: 'elementary',
        tags: [],
        maxPuzzles: 5,
        seed: 12345,
      });
      
      clearCache();
      
      const result2 = await createPracticeSet({
        level: 'elementary',
        tags: [],
        maxPuzzles: 5,
        seed: 12345,
      });

      expect(result1.data?.puzzles.map((p: CollectionPuzzleEntry) => p.id)).toEqual(
        result2.data?.puzzles.map((p: CollectionPuzzleEntry) => p.id)
      );
    });
  });

  describe('estimateUserLevel', () => {
    it('should return elementary for new users', () => {
      const level = estimateUserLevel();
      expect(level).toBe('elementary');
    });

    it('should return current level when enough data with moderate accuracy', () => {
      // Need >= 10 attempts to avoid defaulting to elementary
      localStorageMock.setItem('yen-go-progress', JSON.stringify({
        currentLevel: 'intermediate',
        stats: { totalAttempted: 15, totalCorrect: 8 }, // 53% accuracy - stays at current
      }));

      const level = estimateUserLevel();
      expect(level).toBe('intermediate');
    });

    it('should suggest higher level for high accuracy', () => {
      localStorageMock.setItem('yen-go-progress', JSON.stringify({
        currentLevel: 'elementary',
        stats: { totalAttempted: 25, totalCorrect: 20 }, // 80% accuracy
      }));

      const level = estimateUserLevel();
      expect(level).toBe('intermediate');
    });

    it('should suggest lower level for low accuracy', () => {
      localStorageMock.setItem('yen-go-progress', JSON.stringify({
        currentLevel: 'intermediate',
        stats: { totalAttempted: 15, totalCorrect: 4 }, // ~27% accuracy
      }));

      const level = estimateUserLevel();
      expect(level).toBe('elementary');
    });
  });

  describe('getRandomPuzzle', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          level: 'elementary',
          generatedAt: '2024-01-01',
          entries: [
            { id: 'p1', path: 'path/to/p1.sgf' },
            { id: 'p2', path: 'path/to/p2.sgf' },
          ],
        }),
      });
    });

    it('should return a puzzle at the specified level', async () => {
      const puzzle = await getRandomPuzzle('elementary');
      
      expect(puzzle).not.toBeNull();
      expect(puzzle?.level).toBe('elementary');
    });

    it('should return null if no puzzles at level', async () => {
      // Setup level-aware mock that returns empty array for expert
      clearCache();
      vi.clearAllMocks();
      
      mockFetch.mockImplementation(async (url: string) => {
        // Return empty entries for expert level (numeric ID 230)
        if (url.includes('/230/')) {
          return {
            ok: true,
            json: async () => ({
              level: 'expert',
              generatedAt: '2024-01-01',
              entries: [], // Empty entries array
            }),
          };
        }
        // Return some puzzles for other levels
        return {
          ok: true,
          json: async () => ({
            level: 'elementary',
            generatedAt: '2024-01-01',
            entries: [{ id: 'p1', path: 'path/to/p1.sgf' }],
          }),
        };
      });

      const puzzle = await getRandomPuzzle('expert');
      
      expect(puzzle).toBeNull();
    });
  });

  describe('validatePuzzle', () => {
    it('should return valid for accessible puzzle', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      const puzzle: CollectionPuzzleEntry = {
        id: 'valid-puzzle',
        path: 'path/to/valid.sgf',
      };

      const result = await validatePuzzle(puzzle);
      
      expect(result.valid).toBe(true);
      expect(result.reason).toBeUndefined();
    });

    it('should return missing for 404 response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

      const puzzle: CollectionPuzzleEntry = {
        id: 'missing-puzzle',
        path: 'path/to/missing.sgf',
      };

      const result = await validatePuzzle(puzzle);
      
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('missing');
    });

    it('should return deprecated for 410 response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 410 });

      const puzzle: CollectionPuzzleEntry = {
        id: 'old-puzzle',
        path: 'path/to/old.sgf',
      };

      const result = await validatePuzzle(puzzle);
      
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('deprecated');
    });

    it('should cache validation results', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      const puzzle: CollectionPuzzleEntry = {
        id: 'cached-puzzle',
        path: 'path/to/cached.sgf',
      };

      await validatePuzzle(puzzle);
      await validatePuzzle(puzzle);
      
      // Should only fetch once
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('filterValidPuzzles', () => {
    it('should filter out invalid puzzles', async () => {
      mockFetch
        .mockResolvedValueOnce({ ok: true }) // p1 valid
        .mockResolvedValueOnce({ ok: false, status: 404 }) // p2 missing
        .mockResolvedValueOnce({ ok: true }); // p3 valid

      const puzzles: CollectionPuzzleEntry[] = [
        { id: 'p1', path: 'path/to/p1.sgf' },
        { id: 'p2', path: 'path/to/p2.sgf' },
        { id: 'p3', path: 'path/to/p3.sgf' },
      ];

      const valid = await filterValidPuzzles(puzzles);
      
      expect(valid.length).toBe(2);
      expect(valid.map(p => p.id)).toEqual(['p1', 'p3']);
    });
  });

  describe('getNextValidPuzzle', () => {
    beforeEach(() => {
      // Clear cache to ensure fresh state
      clearCache();
      clearPuzzleValidationCache();
      vi.clearAllMocks();
      
      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes('level')) {
          return {
            ok: true,
            json: async () => ({
              level: 'elementary',
              generatedAt: '2024-01-01',
              entries: [
                { id: 'p0', path: 'path/to/p0.sgf' },
                { id: 'p1', path: 'path/to/p1.sgf' },
                { id: 'p2', path: 'path/to/p2.sgf' },
              ],
            }),
          };
        }
        // HEAD requests for validation
        if (url.includes('p1')) {
          return { ok: false, status: 404 }; // p1 is missing
        }
        return { ok: true };
      });
    });

    it('should skip invalid puzzles and return next valid', async () => {
      // Clear all caches and setup fresh mocks
      clearCache();
      clearPuzzleValidationCache();
      vi.clearAllMocks();
      
      mockFetch.mockImplementation(async (url: string) => {
        // Level index requests
        if (url.includes('by-level')) {
          return {
            ok: true,
            json: async () => ({
              level: 'elementary',
              generatedAt: '2024-01-01',
              entries: [
                { id: 'p0', path: 'path/to/p0.sgf' },
                { id: 'p1', path: 'path/to/p1.sgf' },
                { id: 'p2', path: 'path/to/p2.sgf' },
              ],
            }),
          };
        }
        // HEAD requests for validation - p1 is missing
        if (url.includes('p1')) {
          return { ok: false, status: 404 };
        }
        return { ok: true };
      });

      const result = await getNextValidPuzzle('level-elementary', 0);
      
      // Should skip p1 (invalid at index 1) and return p2 (valid at index 2)
      expect(result).not.toBeNull();
      expect(result?.puzzle.id).toBe('p2');
      expect(result?.index).toBe(2);
    });

    it('should return null when no more valid puzzles', async () => {
      const result = await getNextValidPuzzle('level-elementary', 2);
      
      expect(result).toBeNull();
    });
  });

  describe('loadCollectionMasterIndex', () => {
    beforeEach(() => {
      clearAllCaches();
      clearCatalogCache();
      vi.clearAllMocks();
    });

    it('should load and cache collection master index', async () => {
      const mockMasterIndex = {
        version: '2.0',
        generated_at: '2026-02-19T00:00:00Z',
        collections: [
          { id: 1, name: 'Beginner Essentials', slug: 'beginner-essentials', paginated: true, count: 50, pages: 1, levels: { '120': 20 }, tags: { '10': 15 } },
          { id: 2, name: 'Ladder Drills', slug: 'ladder-drills', paginated: true, count: 30, pages: 1, levels: { '130': 10 }, tags: { '34': 30 } },
        ],
      };
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockMasterIndex,
      });

      const result = await loadCollectionMasterIndex();
      expect(result).not.toBeNull();
      expect(result?.collections).toHaveLength(2);
      expect(result?.collections[0].id).toBe(1);

      // Should cache — no second fetch for master index URL
      const result2 = await loadCollectionMasterIndex();
      expect(result2).toBe(result);
    });

    it('should return null on invalid structure', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ version: '2.0' }), // Missing collections array
      });

      const result = await loadCollectionMasterIndex();
      expect(result).toBeNull();
    });

    it('should return null on network error', async () => {
      mockFetch.mockRejectedValue(new Error('network'));

      const result = await loadCollectionMasterIndex();
      expect(result).toBeNull();
    });
  });

  // SE-06: Unit tests for resolveCollectionDirId slug→numeric ID resolution
  describe('resolveCollectionDirId', () => {
    beforeEach(() => {
      clearAllCaches();
      vi.clearAllMocks();
    });

    it('should resolve level-prefixed ID to numeric level ID', () => {
      // 'beginner' → 120 (from generated-types)
      const result = resolveCollectionDirId('level-beginner');
      expect(result).toBe(120);
    });

    it('should resolve tag-prefixed ID to numeric tag ID', () => {
      // 'ladder' → 34 (from generated-types)
      const result = resolveCollectionDirId('tag-ladder');
      expect(result).toBe(34);
    });

    it('should return undefined for unknown level slug', () => {
      const result = resolveCollectionDirId('level-nonexistent');
      expect(result).toBeUndefined();
    });

    it('should return undefined for unknown tag slug', () => {
      const result = resolveCollectionDirId('tag-nonexistent');
      expect(result).toBeUndefined();
    });

    it('should resolve curated-prefixed ID after ensureCollectionIdsLoaded', async () => {
      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes('config/collections.json')) {
          return {
            ok: true,
            json: async () => ({
              version: '2.0',
              collections: [{ id: 7, slug: 'cho-chikun', name: 'Cho Chikun', description: '', curator: '', source: '', type: 'author', ordering: 'source' }],
            }),
          };
        }
        return { ok: false, status: 404 };
      });

      await ensureCollectionIdsLoaded();
      const result = resolveCollectionDirId('curated-cho-chikun');
      expect(result).toBe(7);
    });

    it('should return undefined for unknown curated slug', async () => {
      mockFetch.mockImplementation(async (url: string) => {
        if (url.includes('config/collections.json')) {
          return {
            ok: true,
            json: async () => ({ version: '2.0', collections: [] }),
          };
        }
        return { ok: false, status: 404 };
      });

      await ensureCollectionIdsLoaded();
      const result = resolveCollectionDirId('curated-nonexistent');
      expect(result).toBeUndefined();
    });
  });
});
