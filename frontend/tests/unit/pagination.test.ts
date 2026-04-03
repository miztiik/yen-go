/**
 * Pagination Tests
 * @module tests/unit/pagination
 *
 * Tests for lib/puzzle/pagination module — index type detection,
 * page loading, cache management, and error handling.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  detectIndexType,
  loadPage,
  loadDirectoryIndex,
  PaginationError,
  createPaginationLoader,
} from '@lib/puzzle/pagination';

// Mock fetch
const mockFetch = vi.fn();

describe('pagination', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ============================================================================
  // PaginationError
  // ============================================================================

  describe('PaginationError', () => {
    it('should have correct properties', () => {
      const error = new PaginationError('test error', 'FETCH_FAILED', { url: '/test' });

      expect(error.message).toBe('test error');
      expect(error.code).toBe('FETCH_FAILED');
      expect(error.name).toBe('PaginationError');
      expect(error.details).toEqual({ url: '/test' });
    });
  });

  // ============================================================================
  // Generic v3.0 API: detectIndexType (Spec 131)
  // ============================================================================

  describe('detectIndexType (v3.0 generic)', () => {
    it('should detect single-file level (directory index 404, single file exists)', async () => {
      // First fetch: directory index → 404
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });
      // Second fetch: single file → entries
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            version: '3.0',
            type: 'level',
            name: 'beginner',
            entries: [
              { path: 'sgf/beginner/batch-0001/abc.sgf', tags: ['ko'] },
            ],
          }),
      });

      const result = await detectIndexType('https://cdn.example.com', 'level', 'beginner');
      expect(result).toEqual({
        name: 'beginner',
        count: 1,
        type: 'single',
      });
    });

    it('should detect paginated tag via directory index', async () => {
      // Directory index found → paginated
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            type: 'tag',
            name: 'ko',
            total_count: 30,
            page_size: 10,
            pages: 3,
          }),
      });

      const result = await detectIndexType('https://cdn.example.com', 'tag', 'ko');
      expect(result).toEqual({
        name: 'ko',
        count: 30,
        type: 'paginated',
        pages: 3,
      });
    });

    it('should detect paginated collection via legacy master format', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            totalPuzzles: 100,
            totalPages: 2,
            pageSize: 50,
          }),
      });

      const result = await detectIndexType('https://cdn.example.com', 'collection', 'test-coll');
      expect(result).toEqual({
        name: 'test-coll',
        count: 100,
        type: 'paginated',
        pages: 2,
      });
    });
  });

  // ============================================================================
  // Generic v3.0 API: loadPage (Spec 131)
  // ============================================================================

  describe('loadPage (v3.0 generic)', () => {
    it('should load v3.0 PageDocument format', async () => {
      const pageDoc = {
        type: 'level',
        name: 'beginner',
        page: 1,
        entries: [
          { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: ['life-and-death'] },
          { path: 'sgf/beginner/batch-0001/def456.sgf', tags: ['ko'] },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(pageDoc),
      });

      const result = await loadPage('https://cdn.example.com', 'level', 'beginner', 1);
      expect(result.type).toBe('level');
      expect(result.name).toBe('beginner');
      expect(result.page).toBe(1);
      expect(result.entries).toHaveLength(2);
    });

    it('should normalize legacy .puzzles to .entries', async () => {
      const legacyPage = {
        level: 'beginner',
        page: 2,
        total_pages: 3,
        puzzles: [
          { id: 'abc123', path: 'sgf/beginner/batch-0001/abc123.sgf' },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(legacyPage),
      });

      const result = await loadPage('https://cdn.example.com', 'level', 'beginner', 2);
      expect(result.entries).toHaveLength(1);
      expect(result.page).toBe(2);
    });

    it('should throw INVALID_PAGE on page < 1', async () => {
      await expect(
        loadPage('https://cdn.example.com', 'level', 'beginner', 0)
      ).rejects.toMatchObject({ code: 'INVALID_PAGE' });
    });

    it('should throw NOT_FOUND on 404', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await expect(
        loadPage('https://cdn.example.com', 'tag', 'ko', 99)
      ).rejects.toMatchObject({ code: 'NOT_FOUND' });
    });
  });

  // ============================================================================
  // Generic v3.0 API: loadDirectoryIndex (Spec 131)
  // ============================================================================

  describe('loadDirectoryIndex (v3.0 generic)', () => {
    it('should load v3.0 DirectoryIndex format', async () => {
      const dirIndex = {
        type: 'level',
        name: 'beginner',
        total_count: 500,
        page_size: 100,
        pages: 5,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(dirIndex),
      });

      const result = await loadDirectoryIndex('https://cdn.example.com', 'level', 'beginner');
      expect(result).toEqual(dirIndex);
    });

    it('should normalize legacy collection master format', async () => {
      const legacyMaster = {
        totalPuzzles: 200,
        totalPages: 4,
        pageSize: 50,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(legacyMaster),
      });

      const result = await loadDirectoryIndex('https://cdn.example.com', 'collection', 'test');
      expect(result.total_count).toBe(200);
      expect(result.pages).toBe(4);
      expect(result.page_size).toBe(50);
    });

    it('should throw NOT_FOUND on 404', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await expect(
        loadDirectoryIndex('https://cdn.example.com', 'level', 'nonexistent')
      ).rejects.toMatchObject({ code: 'NOT_FOUND' });
    });
  });

  // ============================================================================
  // Generic v3.0 API: createPaginationLoader (Spec 131)
  // ============================================================================

  describe('createPaginationLoader (v3.0 generic)', () => {
    it('should create loader with correct initial state', () => {
      const loader = createPaginationLoader('level', {
        baseUrl: 'https://cdn.example.com',
        name: 'beginner',
      });

      const state = loader.getState();
      expect(state.isLoading).toBe(false);
      expect(state.loadedPuzzles).toEqual([]);
      expect(state.hasMore).toBe(false);
      expect(state.currentPage).toBe(0);
    });

    it('should load single-file level via v3.0 envelope', async () => {
      const singleFileData = {
        version: '3.0',
        type: 'level',
        name: 'beginner',
        entries: [
          { path: 'sgf/beginner/batch-0001/abc.sgf', tags: ['ko'] },
          { path: 'sgf/beginner/batch-0001/def.sgf', tags: ['ladder'] },
        ],
      };

      // Fetch 1: directory index → 404 (detectIndexType first try)
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });
      // Fetch 2: single file (detectIndexType fallback)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(singleFileData),
      });
      // Fetch 3: single file again (loadInitial loads it)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(singleFileData),
      });

      const loader = createPaginationLoader('level', {
        baseUrl: 'https://cdn.example.com',
        name: 'beginner',
      });

      await loader.loadInitial();
      const state = loader.getState();
      expect(state.isLoading).toBe(false);
      expect(state.loadedPuzzles).toHaveLength(2);
      expect(state.hasMore).toBe(false);
    });

    it('should load paginated tag via v3.0 page format', async () => {
      const dirIndexData = {
        type: 'tag',
        name: 'ko',
        total_count: 200,
        page_size: 50,
        pages: 4,
      };

      // Fetch 1: directory index (detectIndexType) → paginated
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(dirIndexData),
      });

      // Fetch 2: directory index again (loadInitial calls loadDirectoryIndex)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(dirIndexData),
      });

      // Fetch 3: first page (v3.0 PageDocument)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            type: 'tag',
            name: 'ko',
            page: 1,
            entries: [
              { path: 'sgf/beginner/batch-0001/abc.sgf', level: 'beginner' },
            ],
          }),
      });

      const loader = createPaginationLoader('tag', {
        baseUrl: 'https://cdn.example.com',
        name: 'ko',
      });

      await loader.loadInitial();
      const state = loader.getState();
      expect(state.isLoading).toBe(false);
      expect(state.totalPages).toBe(4);
      expect(state.totalCount).toBe(200);
      expect(state.hasMore).toBe(true);
      expect(state.loadedPuzzles).toHaveLength(1);
    });

    it('should handle not-found view', async () => {
      // Fetch 1: directory index → 404
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });
      // Fetch 2: single file → also 404
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const loader = createPaginationLoader('level', {
        baseUrl: 'https://cdn.example.com',
        name: 'nonexistent',
      });

      await loader.loadInitial();
      const state = loader.getState();
      expect(state.error).toContain('not found');
    });

    it('should reset to initial state', () => {
      const loader = createPaginationLoader('level', {
        baseUrl: 'https://cdn.example.com',
        name: 'beginner',
      });

      loader.reset();
      const state = loader.getState();
      expect(state).toEqual({
        isLoading: false,
        currentPage: 0,
        totalPages: 0,
        totalCount: 0,
        loadedPuzzles: [],
        hasMore: false,
        error: null,
      });
    });

    it('should call onStateChange callback', async () => {
      const onStateChange = vi.fn();
      const singleFileData = {
        puzzles: [{ id: 'abc', path: 'sgf/beginner/batch-0001/abc.sgf' }],
      };

      // Fetch 1: directory index → 404
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });
      // Fetch 2: single file (detectIndexType)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(singleFileData),
      });
      // Fetch 3: single file (loadInitial)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(singleFileData),
      });

      const loader = createPaginationLoader('level', {
        baseUrl: 'https://cdn.example.com',
        name: 'beginner',
        onStateChange,
      });

      await loader.loadInitial();
      expect(onStateChange).toHaveBeenCalled();
    });
  });
});
