/**
 * Collection Contract Tests (T052b)
 * @module tests/unit/collectionContract
 *
 * Verifies that TypeScript interfaces for collection indexes match
 * the actual backend pagination_writer.py output format.
 *
 * These tests ensure frontend types stay in sync with backend output.
 */

import { describe, it, expect } from 'vitest';
import {
  isViewEnvelope,
  isDirectoryIndex,
  isPageDocument,
  isCollectionMasterIndexV3,
} from '@/types/indexes';

// ============================================================================
// Backend output fixtures (matching pagination_writer.py format)
// ============================================================================

/**
 * Flat level index — bare JSON array format.
 * Backend generates: views/by-level/{level}.json
 * Format: array of puzzle entries (not wrapped in object)
 */
const FLAT_LEVEL_INDEX_ARRAY = [
  { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: ['life-and-death'] },
  { path: 'sgf/beginner/batch-0001/def456.sgf', tags: ['ko', 'ladder'] },
  { path: 'sgf/beginner/batch-0002/ghi789.sgf', tags: ['snapback'] },
];

/**
 * Flat level index — v3.0 ViewEnvelope format.
 * Backend generates: views/by-level/{level}.json
 */
const FLAT_LEVEL_INDEX_OBJECT = {
  version: '3.0',
  type: 'level',
  name: 'beginner',
  total: 2,
  entries: [
    { path: 'sgf/beginner/batch-0001/abc123.sgf', tags: ['life-and-death'] },
    { path: 'sgf/beginner/batch-0001/def456.sgf', tags: ['ko'] },
  ],
};

/**
 * Paginated level page (v3.0 PageDocument format).
 * Backend generates: views/by-level/{level}/page-001.json
 */
const PAGINATED_LEVEL_PAGE = {
  type: 'level',
  name: 'intermediate',
  page: 1,
  entries: [
    { id: 'abc123', path: 'sgf/intermediate/batch-0001/abc123.sgf' },
    { id: 'def456', path: 'sgf/intermediate/batch-0001/def456.sgf' },
  ],
};

/**
 * Level master index.
 * Backend generates: views/by-level/index.json
 * Note: Backend uses `levels[]` array with per-level metadata.
 * No dedicated v3.0 type guard — validated by structure.
 */
const LEVEL_MASTER_INDEX = {
  version: '1.0',
  generated_at: '2026-01-01T00:00:00Z',
  levels: [
    { name: 'beginner', slug: 'beginner', paginated: false, count: 42 },
    { name: 'intermediate', slug: 'intermediate', paginated: true, count: 1500, pages: 15 },
    { name: 'advanced', slug: 'advanced', paginated: false, count: 200 },
  ],
};

/**
 * Paginated level directory index (v3.0 DirectoryIndex format).
 * Backend generates: views/by-level/{level}/index.json
 */
const PAGINATED_LEVEL_INDEX = {
  type: 'level',
  name: 'intermediate',
  total_count: 1500,
  page_size: 100,
  pages: 15,
};

/**
 * Collection master index (v3.0 — uses `collections[]` root key).
 */
const COLLECTION_MASTER_INDEX = {
  version: '1.0',
  generated_at: '2026-01-01T00:00:00Z',
  collections: [
    { name: 'curated-classic', slug: 'curated-classic', paginated: true, count: 200 },
  ],
};

/**
 * Paginated collection page (v3.0 PageDocument format).
 */
const PAGINATED_COLLECTION_PAGE = {
  type: 'collection',
  name: 'curated-classic',
  page: 2,
  entries: [
    { path: 'sgf/intermediate/batch-0001/p51.sgf', level: 'intermediate' },
    { path: 'sgf/advanced/batch-0001/p52.sgf', level: 'advanced' },
  ],
};

// ============================================================================
// Contract Tests
// ============================================================================

describe('Collection Contract Tests (T052b)', () => {
  describe('ViewEnvelope (flat level index)', () => {
    it('object format should be recognized by isViewEnvelope', () => {
      expect(isViewEnvelope(FLAT_LEVEL_INDEX_OBJECT)).toBe(true);
    });

    it('array format should NOT be recognized by isViewEnvelope (needs wrapping)', () => {
      // Backend sometimes returns bare array — frontend code handles this explicitly
      expect(isViewEnvelope(FLAT_LEVEL_INDEX_ARRAY)).toBe(false);
    });
  });

  describe('DirectoryIndex (paginated level/tag)', () => {
    it('should be recognized by isDirectoryIndex', () => {
      expect(isDirectoryIndex(PAGINATED_LEVEL_INDEX)).toBe(true);
    });

    it('should NOT recognize ViewEnvelope as DirectoryIndex', () => {
      expect(isDirectoryIndex(FLAT_LEVEL_INDEX_OBJECT)).toBe(false);
    });
  });

  describe('PageDocument (paginated page)', () => {
    it('level page should be recognized by isPageDocument', () => {
      expect(isPageDocument(PAGINATED_LEVEL_PAGE)).toBe(true);
    });

    it('collection page should be recognized by isPageDocument', () => {
      expect(isPageDocument(PAGINATED_COLLECTION_PAGE)).toBe(true);
    });

    it('should NOT recognize ViewEnvelope as PageDocument (has total)', () => {
      expect(isPageDocument(FLAT_LEVEL_INDEX_OBJECT)).toBe(false);
    });
  });

  describe('Collection Master Index (v3.0)', () => {
    it('should be recognized by isCollectionMasterIndexV3', () => {
      expect(isCollectionMasterIndexV3(COLLECTION_MASTER_INDEX)).toBe(true);
    });

    it('level master should NOT be recognized as CollectionMasterIndexV3', () => {
      expect(isCollectionMasterIndexV3(LEVEL_MASTER_INDEX)).toBe(false);
    });
  });

  describe('Format discrimination', () => {
    it('should distinguish ViewEnvelope from DirectoryIndex', () => {
      expect(isViewEnvelope(FLAT_LEVEL_INDEX_OBJECT)).toBe(true);
      expect(isDirectoryIndex(FLAT_LEVEL_INDEX_OBJECT)).toBe(false);

      expect(isDirectoryIndex(PAGINATED_LEVEL_INDEX)).toBe(true);
      expect(isViewEnvelope(PAGINATED_LEVEL_INDEX)).toBe(false);
    });

    it('should distinguish level page from collection page by type field', () => {
      // Both are PageDocuments
      expect(isPageDocument(PAGINATED_LEVEL_PAGE)).toBe(true);
      expect(isPageDocument(PAGINATED_COLLECTION_PAGE)).toBe(true);
      // Discriminated by `type` field
      expect(PAGINATED_LEVEL_PAGE.type).toBe('level');
      expect(PAGINATED_COLLECTION_PAGE.type).toBe('collection');
    });

    it('should distinguish collection master from level master', () => {
      expect(isCollectionMasterIndexV3(COLLECTION_MASTER_INDEX)).toBe(true);
      expect(isCollectionMasterIndexV3(LEVEL_MASTER_INDEX)).toBe(false);
    });
  });

  describe('Backend format documentation', () => {
    /**
     * Known differences between TypeScript interfaces and backend output:
     *
     * 1. Level Master Index: Backend uses `levels[]` with per-level `slug` field.
     *    No dedicated type guard — validated structurally.
     *
     * 2. Flat Level Index: v3.0 uses ViewEnvelope with version, type, name, total, entries.
     *    Backend sometimes returns bare array — frontend handles both.
     *
     * 3. Collection Master Index: v3.0 uses `collections[]` root key.
     *    Level Master uses `levels[]` — structurally distinct.
     *
     * 4. Puzzle IDs: Backend may set `id` on entries or omit it.
     *    Frontend always falls back to `extractPuzzleIdFromPath()`.
     */
    it('should verify backend fixtures have expected fields', () => {
      // Level master: has version, generated_at, levels[]
      expect(LEVEL_MASTER_INDEX).toHaveProperty('version');
      expect(LEVEL_MASTER_INDEX).toHaveProperty('generated_at');
      expect(LEVEL_MASTER_INDEX).toHaveProperty('levels');
      expect(LEVEL_MASTER_INDEX.levels[0]).toHaveProperty('name');
      expect(LEVEL_MASTER_INDEX.levels[0]).toHaveProperty('slug');
      expect(LEVEL_MASTER_INDEX.levels[0]).toHaveProperty('paginated');
      expect(LEVEL_MASTER_INDEX.levels[0]).toHaveProperty('count');

      // Collection master: has version, generated_at, collections[]
      expect(COLLECTION_MASTER_INDEX).toHaveProperty('version');
      expect(COLLECTION_MASTER_INDEX).toHaveProperty('generated_at');
      expect(COLLECTION_MASTER_INDEX).toHaveProperty('collections');
    });
  });
});
