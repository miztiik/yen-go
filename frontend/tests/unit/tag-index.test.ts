/**
 * Tag Index Contract Tests
 * @module tests/unit/tag-index.test
 *
 * Tests the tag index structure and tag loader functionality.
 *
 * Covers: T035
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch before importing modules
const mockFetch = vi.fn();

// Mock CDN base path - should match what tag-loader imports
vi.mock('@/config/cdn', () => ({
  CDN_BASE_PATH: '/yengo-puzzle-collections',
}));

describe('Tag Index Contract', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubGlobal('fetch', mockFetch);
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  describe('TagIndex structure', () => {
    const validTagIndex = {
      version: '3.0',
      tag: 'snapback',
      displayName: 'Snapback',
      description: 'Sacrifice to immediately recapture',
      category: 'technique',
      totalCount: 3, // Matches the entries array length
      entries: [
        { p: '0001/abc123', l: 120, t: [34], c: [], x: [1, 1, 3, 1] },
        { p: '0001/def456', l: 130, t: [34], c: [], x: [1, 1, 5, 1] },
        { p: '0002/ghi789', l: 140, t: [34], c: [], x: [2, 1, 7, 2] },
      ],
    };

    it('should have required version field', () => {
      expect(validTagIndex.version).toBeDefined();
      expect(validTagIndex.version).toMatch(/^\d+\.\d+$/);
    });

    it('should have tag identifier', () => {
      expect(validTagIndex.tag).toBeDefined();
      expect(typeof validTagIndex.tag).toBe('string');
      expect(validTagIndex.tag.length).toBeGreaterThan(0);
    });

    it('should have display name for UI', () => {
      expect(validTagIndex.displayName).toBeDefined();
      expect(typeof validTagIndex.displayName).toBe('string');
    });

    it('should have description', () => {
      expect(validTagIndex.description).toBeDefined();
      expect(typeof validTagIndex.description).toBe('string');
    });

    it('should have category (technique, position, goal, etc)', () => {
      expect(validTagIndex.category).toBeDefined();
      expect(['technique', 'position', 'goal', 'pattern', 'other']).toContain(validTagIndex.category);
    });

    it('should have totalCount matching puzzles length', () => {
      expect(validTagIndex.totalCount).toBeDefined();
      expect(validTagIndex.totalCount).toBe(validTagIndex.entries.length);
    });

    it('should have entries array with puzzle entries', () => {
      expect(Array.isArray(validTagIndex.entries)).toBe(true);
      expect(validTagIndex.entries.length).toBeGreaterThan(0);
    });
  });

  describe('Compact entry structure', () => {
    const validEntry = {
      p: '0001/abc123',
      l: 120,
      t: [34],
      c: [],
      x: [1, 1, 3, 1],
    };

    it('should have compact path', () => {
      expect(validEntry.p).toBeDefined();
      expect(validEntry.p).toMatch(/^\d{4}\//);
    });

    it('should have numeric level ID', () => {
      expect(validEntry.l).toBeDefined();
      expect(typeof validEntry.l).toBe('number');
    });

    it('should have numeric tag IDs array', () => {
      expect(validEntry.t).toBeDefined();
      expect(Array.isArray(validEntry.t)).toBe(true);
    });
  });

  describe('Tag listing (tags.json)', () => {
    const validTagListing = {
      version: '3.0',
      tags: [
        { id: 'snapback', displayName: 'Snapback', count: 42, category: 'technique' },
        { id: 'ladder', displayName: 'Ladder', count: 38, category: 'technique' },
        { id: 'net', displayName: 'Net (Geta)', count: 25, category: 'technique' },
        { id: 'ko', displayName: 'Ko', count: 18, category: 'position' },
      ],
    };

    it('should have version field', () => {
      expect(validTagListing.version).toBeDefined();
    });

    it('should have tags array', () => {
      expect(Array.isArray(validTagListing.tags)).toBe(true);
      expect(validTagListing.tags.length).toBeGreaterThan(0);
    });

    it('each tag should have id, displayName, count, and category', () => {
      for (const tag of validTagListing.tags) {
        expect(tag.id).toBeDefined();
        expect(tag.displayName).toBeDefined();
        expect(tag.count).toBeDefined();
        expect(tag.category).toBeDefined();
      }
    });
  });
});

describe('Tag Loader', () => {
  beforeEach(async () => {
    // Reset module cache to get fresh imports
    vi.resetModules();
    // Stub global fetch BEFORE any imports
    vi.stubGlobal('fetch', mockFetch);
    mockFetch.mockReset();
    // Clear tag loader cache
    const { clearTagCache } = await import('@/lib/puzzle/tag-loader');
    clearTagCache();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('loadTagList', () => {
    it('should fetch from views/by-tag/index.json', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          version: '3.0',
          tags: [
            { id: 'snapback', displayName: 'Snapback', count: 42, category: 'technique' },
          ],
        }),
      });

      const { loadTagList } = await import('@/lib/puzzle/tag-loader');
      const result = await loadTagList();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/views/by-tag/index.json')
      );
      expect(result).toBeDefined();
      expect(result?.tags.length).toBe(1);
    });

    it('should return null on fetch error', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

      const { loadTagList } = await import('@/lib/puzzle/tag-loader');
      const result = await loadTagList();

      expect(result).toBeNull();
    });

    it('should cache successful results', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          version: '3.0',
          tags: [{ id: 'snapback', displayName: 'Snapback', count: 42, category: 'technique' }],
        }),
      });

      const { loadTagList, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();

      await loadTagList();
      await loadTagList();

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('loadTagIndex', () => {
    it('should fetch from views/by-tag/{tag}/page-001.json', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          type: 'tag',
          name: 'snapback',
          page: 1,
          entries: [
            { path: 'sgf/beginner/2026/01/batch-001/puzzle-001.sgf', rank: '30k-25k', level: 'beginner' },
          ],
        }),
      });

      const { loadTagIndex, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();
      const result = await loadTagIndex('snapback');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/views/by-tag/30/page-001.json')
      );
      expect(result).toBeDefined();
      expect(result?.tag).toBe('snapback');
    });

    it('should return null for non-existent tag', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

      const { loadTagIndex, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();
      const result = await loadTagIndex('non-existent');

      expect(result).toBeNull();
    });

    it('should cache tag indexes by tag name', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          type: 'tag',
          name: 'ladder',
          page: 1,
          entries: [],
        }),
      });

      const { loadTagIndex, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();

      await loadTagIndex('ladder');
      await loadTagIndex('ladder');

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('getTagPuzzles', () => {
    it('should return puzzles for a tag', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          type: 'tag',
          name: 'ko',
          page: 1,
          entries: [
            { path: 'sgf/beginner/2026/01/batch-001/p1.sgf', rank: '30k-25k', level: 'beginner' },
            { path: 'sgf/basic/2026/01/batch-001/p2.sgf', rank: '25k-20k', level: 'basic' },
            { path: 'sgf/intermediate/2026/01/batch-001/p3.sgf', rank: '15k-10k', level: 'intermediate' },
          ],
        }),
      });

      const { getTagPuzzles, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();
      const puzzles = await getTagPuzzles('ko');

      expect(puzzles.length).toBe(3);
      expect(puzzles[0]?.path).toBeDefined();
    });

    it('should return empty array for non-existent tag', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

      const { getTagPuzzles, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();
      const puzzles = await getTagPuzzles('fake-tag');

      expect(puzzles).toEqual([]);
    });
  });

  describe('loadTagPuzzle', () => {
    it('should load a puzzle from tag index', async () => {
      // First mock for tag index
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          type: 'tag',
          name: 'snapback',
          page: 1,
          entries: [
            { path: 'sgf/beginner/2026/01/batch-001/puzzle-001.sgf', rank: '30k-25k', level: 'beginner' },
          ],
        }),
      });

      // Second mock for SGF file
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => `(;FF[4]GM[1]SZ[9]
YV[3.0]YG[beginner]YT[snapback]
AB[cc][dc][ec]
AW[cd][dd][ed]
;B[ce]
)`,
      });

      const { loadTagPuzzle, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();
      const puzzle = await loadTagPuzzle('snapback', 0);

      expect(puzzle).toBeDefined();
      expect(puzzle?.tags).toContain('snapback');
    });

    it('should return null for invalid index', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          version: '3.0',
          tag: 'snapback',
          puzzles: [],
          totalCount: 0,
        }),
      });

      const { loadTagPuzzle, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();
      const puzzle = await loadTagPuzzle('snapback', 0);

      expect(puzzle).toBeNull();
    });
  });

  describe('getTagCount', () => {
    it('should return total puzzle count for a tag', async () => {
      const entries = Array.from({ length: 15 }, (_, i) => ({
        path: `sgf/0001/puzzle${i}.sgf`,
        level: 'beginner',
      }));
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          type: 'tag',
          name: 'seki',
          page: 1,
          entries,
        }),
      });

      const { getTagCount, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();
      const count = await getTagCount('seki');

      expect(count).toBe(15);
    });

    it('should return 0 for non-existent tag', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

      const { getTagCount, clearTagCache } = await import('@/lib/puzzle/tag-loader');
      clearTagCache();
      const count = await getTagCount('fake');

      expect(count).toBe(0);
    });
  });
});
