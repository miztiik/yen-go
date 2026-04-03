import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Mock } from 'vitest';

const mockQuery = vi.fn();

vi.mock('@services/sqliteService', () => ({
  query: (...args: unknown[]) => mockQuery(...args) as unknown,
  isReady: vi.fn().mockReturnValue(true),
}));

import {
  getPuzzlesByLevel,
  getPuzzlesByTag,
  getPuzzlesByCollection,
  searchCollections,
  getAllCollections,
  getLevelCounts,
  getTagCounts,
  getCollectionCounts,
  getFilterCounts,
  getDepthPresetCounts,
  getPuzzlesFiltered,
  getPuzzleByHash,
  getTotalPuzzleCount,
} from '@services/puzzleQueryService';

function lastCallSql(): string {
  return (mockQuery as Mock).mock.calls.at(-1)?.[0] as string;
}

function lastCallParams(): unknown[] {
  return ((mockQuery as Mock).mock.calls.at(-1)?.[1] as unknown[]) ?? [];
}

describe('puzzleQueryService', () => {
  beforeEach(() => {
    mockQuery.mockReset();
    mockQuery.mockReturnValue([]);
  });

  // --- getPuzzlesByLevel ---

  it('getPuzzlesByLevel passes correct SQL and params', () => {
    getPuzzlesByLevel(120);
    expect(lastCallSql()).toContain('FROM puzzles p WHERE p.level_id = ?');
    expect(lastCallParams()).toEqual([120]);
  });

  // --- getPuzzlesByTag ---

  it('getPuzzlesByTag joins puzzle_tags', () => {
    getPuzzlesByTag(36);
    const sql = lastCallSql();
    expect(sql).toContain('JOIN puzzle_tags pt ON p.content_hash = pt.content_hash');
    expect(sql).toContain('WHERE pt.tag_id = ?');
    expect(lastCallParams()).toEqual([36]);
  });

  // --- getPuzzlesByCollection ---

  it('getPuzzlesByCollection orders by sequence_number', () => {
    getPuzzlesByCollection(5);
    const sql = lastCallSql();
    expect(sql).toContain('JOIN puzzle_collections pc ON p.content_hash = pc.content_hash');
    expect(sql).toContain('WHERE pc.collection_id = ?');
    expect(sql).toContain('ORDER BY pc.sequence_number');
    expect(sql).toContain('pc.sequence_number');
    expect(lastCallParams()).toEqual([5]);
  });

  // --- searchCollections ---

  it('searchCollections uses FTS5 MATCH with wildcard', () => {
    searchCollections('life');
    const sql = lastCallSql();
    expect(sql).toContain('collections_fts');
    expect(sql).toContain('MATCH ?');
    expect(sql).toContain('ORDER BY rank');
    expect(lastCallParams()).toEqual(['life*']);
  });

  // --- getAllCollections ---

  it('getAllCollections returns all ordered by name', () => {
    getAllCollections();
    const sql = lastCallSql();
    expect(sql).toContain('FROM collections');
    expect(sql).toContain('ORDER BY name');
    expect(sql).toContain("json_extract(attrs, '$.parent_id') IS NULL");
  });

  // --- count functions ---

  it('getLevelCounts returns record from GROUP BY', () => {
    mockQuery.mockReturnValueOnce([
      { level_id: 100, cnt: 50 },
      { level_id: 120, cnt: 30 },
    ]);
    const result = getLevelCounts();
    expect(result).toEqual({ 100: 50, 120: 30 });
    expect(lastCallSql()).toContain('GROUP BY level_id');
  });

  it('getTagCounts groups by tag_id', () => {
    mockQuery.mockReturnValueOnce([{ tag_id: 10, cnt: 7 }]);
    const result = getTagCounts();
    expect(result).toEqual({ 10: 7 });
    expect(lastCallSql()).toContain('GROUP BY tag_id');
  });

  it('getCollectionCounts groups by collection_id', () => {
    mockQuery.mockReturnValueOnce([{ collection_id: 2, cnt: 15 }]);
    const result = getCollectionCounts();
    expect(result).toEqual({ 2: 15 });
    expect(lastCallSql()).toContain('GROUP BY collection_id');
  });

  // --- getPuzzlesFiltered ---

  it('getPuzzlesFiltered with level + tag combines WHERE conditions', () => {
    getPuzzlesFiltered({ levelId: 120, tagIds: [36, 60] });
    const sql = lastCallSql();
    expect(sql).toContain('p.level_id = ?');
    expect(sql).toContain('tag_id IN (?,?)');
    expect(sql).toContain('HAVING COUNT(DISTINCT tag_id) = ?');
    expect(sql).toContain('LIMIT ? OFFSET ?');
    // params: levelId + 2 tag ids + tag count + limit + offset
    expect(lastCallParams()).toEqual([120, 36, 60, 2, 500, 0]);
  });

  it('getPuzzlesFiltered with limit and offset', () => {
    getPuzzlesFiltered({ levelId: 100 }, 20, 40);
    expect(lastCallParams()).toEqual([100, 20, 40]);
    expect(lastCallSql()).toContain('LIMIT ? OFFSET ?');
  });

  it('getPuzzlesFiltered with empty filters returns all puzzles', () => {
    getPuzzlesFiltered({});
    const sql = lastCallSql();
    // No WHERE clause when no filters
    expect(sql).not.toContain('WHERE');
    expect(sql).toContain('LIMIT ? OFFSET ?');
    expect(lastCallParams()).toEqual([500, 0]);
  });

  it('getPuzzlesFiltered with collection joins puzzle_collections', () => {
    getPuzzlesFiltered({ collectionId: 3 });
    const sql = lastCallSql();
    expect(sql).toContain('JOIN puzzle_collections pc');
    expect(sql).toContain('pc.collection_id = ?');
    expect(lastCallParams()).toEqual([3, 500, 0]);
  });

  it('getPuzzlesFiltered with quality and depth filters', () => {
    getPuzzlesFiltered({ quality: 2, minDepth: 3, maxDepth: 8 });
    const sql = lastCallSql();
    expect(sql).toContain('p.quality >= ?');
    expect(sql).toContain('p.cx_depth >= ?');
    expect(sql).toContain('p.cx_depth <= ?');
    expect(lastCallParams()).toEqual([2, 3, 8, 500, 0]);
  });

  // --- getPuzzleByHash ---

  it('getPuzzleByHash returns single result', () => {
    const row = {
      content_hash: 'abc123',
      batch: '0001',
      level_id: 120,
      quality: 3,
      content_type: 1,
      cx_depth: 2,
      cx_refutations: 1,
      cx_solution_len: 5,
      cx_unique_resp: 1,
      attrs: '{}',
    };
    mockQuery.mockReturnValueOnce([row]);
    const result = getPuzzleByHash('abc123');
    expect(result).toEqual(row);
    expect(lastCallSql()).toContain('WHERE p.content_hash = ?');
    expect(lastCallParams()).toEqual(['abc123']);
  });

  it('getPuzzleByHash returns undefined when not found', () => {
    mockQuery.mockReturnValueOnce([]);
    expect(getPuzzleByHash('nonexistent')).toBeUndefined();
  });

  // --- getTotalPuzzleCount ---

  it('getTotalPuzzleCount returns count', () => {
    mockQuery.mockReturnValueOnce([{ cnt: 1250 }]);
    expect(getTotalPuzzleCount()).toBe(1250);
  });

  it('getTotalPuzzleCount returns 0 when empty', () => {
    mockQuery.mockReturnValueOnce([]);
    expect(getTotalPuzzleCount()).toBe(0);
  });

  // --- getFilterCounts ---

  it('getFilterCounts with no filters returns global counts', () => {
    // getLevelCounts, getTagCounts, getCollectionCounts, getQualityCounts, getContentTypeCounts, getDepthPresetCounts each call query once
    mockQuery
      .mockReturnValueOnce([{ level_id: 100, cnt: 10 }])
      .mockReturnValueOnce([{ tag_id: 5, cnt: 20 }])
      .mockReturnValueOnce([{ collection_id: 1, cnt: 30 }])
      .mockReturnValueOnce([{ quality: 3, cnt: 15 }])
      .mockReturnValueOnce([{ content_type: 1, cnt: 25 }])
      .mockReturnValueOnce([{ preset: 'quick', cnt: 10 }]);

    const result = getFilterCounts({});
    expect(result).toEqual({
      levels: { 100: 10 },
      tags: { 5: 20 },
      collections: { 1: 30 },
      quality: { 3: 15 },
      contentTypes: { 1: 25 },
      depthPresets: { quick: 10 },
    });
    expect(mockQuery).toHaveBeenCalledTimes(6);
  });

  it('getFilterCounts with levelId uses filtered queries', () => {
    // Filtered: levels query, tags query, quality query, contentType query, getCollectionCounts, getDepthPresetCounts
    mockQuery
      .mockReturnValueOnce([{ level_id: 120, cnt: 5 }])
      .mockReturnValueOnce([{ tag_id: 10, cnt: 3 }])
      .mockReturnValueOnce([{ quality: 2, cnt: 4 }])
      .mockReturnValueOnce([{ content_type: 1, cnt: 5 }])
      .mockReturnValueOnce([{ collection_id: 1, cnt: 30 }])
      .mockReturnValueOnce([{ preset: 'quick', cnt: 2 }]);

    const result = getFilterCounts({ levelId: 120 });
    expect(result.levels).toEqual({ 120: 5 });
    expect(result.tags).toEqual({ 10: 3 });

    // First call: level counts with WHERE
    const firstSql = (mockQuery as Mock).mock.calls[0]?.[0] as string;
    expect(firstSql).toContain('COUNT(DISTINCT p.content_hash)');
    expect(firstSql).toContain('GROUP BY p.level_id');
  });

  // --- Parameterized query safety ---

  it('all queries use parameterized placeholders, never interpolated values', () => {
    // Run a variety of queries and verify no raw values in SQL
    getPuzzlesByLevel(999);
    const sql1 = lastCallSql();
    expect(sql1).not.toContain('999');
    expect(sql1).toContain('?');

    getPuzzlesFiltered({ levelId: 120, tagIds: [36] });
    const sql2 = lastCallSql();
    expect(sql2).not.toContain('120');
    expect(sql2).not.toContain('36');
  });

  // --- GAP-1: AND semantics for multi-tag filter ---

  it('getPuzzlesFiltered with multiple tags uses subquery for AND semantics', () => {
    getPuzzlesFiltered({ tagIds: [10, 36, 60] });
    const sql = lastCallSql();
    expect(sql).toContain('p.content_hash IN (SELECT content_hash FROM puzzle_tags');
    expect(sql).toContain('tag_id IN (?,?,?)');
    expect(sql).toContain('HAVING COUNT(DISTINCT tag_id) = ?');
    // params: 3 tag ids + tag count + limit + offset
    expect(lastCallParams()).toEqual([10, 36, 60, 3, 500, 0]);
  });

  it('getPuzzlesFiltered with single tag uses subquery for AND semantics', () => {
    getPuzzlesFiltered({ tagIds: [36] });
    const sql = lastCallSql();
    expect(sql).toContain('p.content_hash IN (SELECT content_hash FROM puzzle_tags');
    expect(sql).toContain('HAVING COUNT(DISTINCT tag_id) = ?');
    expect(lastCallParams()).toEqual([36, 1, 500, 0]);
  });

  it('getPuzzlesFiltered without tags has no GROUP BY', () => {
    getPuzzlesFiltered({ levelId: 120 });
    const sql = lastCallSql();
    expect(sql).not.toContain('GROUP BY');
    expect(sql).not.toContain('HAVING');
  });

  // --- Bug fix: getFilterCounts fast-path bypass ---

  it('getFilterCounts with quality-only filter uses filtered path', () => {
    mockQuery
      .mockReturnValueOnce([{ level_id: 120, cnt: 3 }])
      .mockReturnValueOnce([{ tag_id: 10, cnt: 2 }])
      .mockReturnValueOnce([{ quality: 3, cnt: 3 }])
      .mockReturnValueOnce([{ content_type: 1, cnt: 3 }])
      .mockReturnValueOnce([{ collection_id: 1, cnt: 30 }])
      .mockReturnValueOnce([{ preset: 'medium', cnt: 3 }]);

    const result = getFilterCounts({ quality: 3 });
    // Should use filtered queries (not the fast-path global counts)
    const firstSql = (mockQuery as Mock).mock.calls[0]?.[0] as string;
    expect(firstSql).toContain('p.quality >= ?');
    expect(result.levels).toEqual({ 120: 3 });
  });

  it('getFilterCounts with multi-tag uses AND-semantics subquery', () => {
    mockQuery
      .mockReturnValueOnce([{ level_id: 120, cnt: 2 }])
      .mockReturnValueOnce([{ tag_id: 10, cnt: 2 }, { tag_id: 36, cnt: 2 }])
      .mockReturnValueOnce([{ quality: 3, cnt: 2 }])
      .mockReturnValueOnce([{ content_type: 1, cnt: 2 }])
      .mockReturnValueOnce([{ collection_id: 1, cnt: 30 }])
      .mockReturnValueOnce([{ preset: 'quick', cnt: 1 }]);

    getFilterCounts({ tagIds: [10, 36] });
    // Level count query should use subquery for AND semantics
    const levelSql = (mockQuery as Mock).mock.calls[0]?.[0] as string;
    expect(levelSql).toContain('p.content_hash IN (SELECT content_hash FROM puzzle_tags');
    expect(levelSql).toContain('HAVING COUNT(DISTINCT tag_id) = ?');
    // params: 2 tag ids + tag count
    const levelParams = (mockQuery as Mock).mock.calls[0]?.[1] as unknown[];
    expect(levelParams).toEqual([10, 36, 2]);
  });

  // --- GAP-10: FTS5 metacharacter sanitization ---

  it('searchCollections strips FTS5 metacharacters', () => {
    searchCollections('cho "chikun"');
    const params = lastCallParams();
    // Double quotes should be stripped
    expect(params[0]).toBe('cho  chikun*');
  });

  it('searchCollections strips special chars: -*()', () => {
    searchCollections('life-and-death (advanced)');
    const params = lastCallParams();
    // Hyphens and parens stripped, trailing wildcard added
    expect(params[0]).toBe('life and death  advanced*');
  });

  it('searchCollections returns empty for all-special-char input', () => {
    const result = searchCollections('"*-()^~');
    expect(result).toEqual([]);
    expect(mockQuery).not.toHaveBeenCalled();
  });

  // --- getDepthPresetCounts ---

  it('getDepthPresetCounts uses CASE expression for bucket counting', () => {
    mockQuery.mockReturnValueOnce([
      { preset: 'quick', cnt: 50 },
      { preset: 'medium', cnt: 30 },
      { preset: 'deep', cnt: 20 },
    ]);
    const result = getDepthPresetCounts({});
    expect(result).toEqual({ quick: 50, medium: 30, deep: 20 });
    const sql = lastCallSql();
    expect(sql).toContain('CASE');
    expect(sql).toContain("THEN 'quick'");
    expect(sql).toContain("THEN 'medium'");
    expect(sql).toContain("THEN 'deep'");
    expect(sql).toContain('GROUP BY preset');
  });

  it('getDepthPresetCounts respects active filters', () => {
    mockQuery.mockReturnValueOnce([{ preset: 'quick', cnt: 5 }]);
    getDepthPresetCounts({ levelId: 120 });
    const sql = lastCallSql();
    expect(sql).toContain('p.level_id = ?');
    expect(sql).toContain('CASE');
    expect(lastCallParams()).toEqual([120]);
  });

  it('getDepthPresetCounts returns empty record when no puzzles match', () => {
    mockQuery.mockReturnValueOnce([]);
    const result = getDepthPresetCounts({ levelId: 999 });
    expect(result).toEqual({});
  });

  // --- getFilterCounts includes depthPresets ---

  it('getFilterCounts with no filters includes depthPresets', () => {
    mockQuery
      .mockReturnValueOnce([{ level_id: 100, cnt: 10 }])
      .mockReturnValueOnce([{ tag_id: 5, cnt: 20 }])
      .mockReturnValueOnce([{ collection_id: 1, cnt: 30 }])
      .mockReturnValueOnce([{ quality: 3, cnt: 15 }])
      .mockReturnValueOnce([{ content_type: 1, cnt: 25 }])
      .mockReturnValueOnce([{ preset: 'quick', cnt: 40 }]);

    const result = getFilterCounts({});
    expect(result.depthPresets).toEqual({ quick: 40 });
    expect(mockQuery).toHaveBeenCalledTimes(6);
  });

  it('getFilterCounts with filters includes depthPresets', () => {
    // 4 filtered queries + getCollectionCounts + getDepthPresetCounts
    mockQuery
      .mockReturnValueOnce([{ level_id: 120, cnt: 5 }])
      .mockReturnValueOnce([{ tag_id: 10, cnt: 3 }])
      .mockReturnValueOnce([{ quality: 2, cnt: 4 }])
      .mockReturnValueOnce([{ content_type: 1, cnt: 5 }])
      .mockReturnValueOnce([{ collection_id: 1, cnt: 30 }])
      .mockReturnValueOnce([{ preset: 'medium', cnt: 3 }]);

    const result = getFilterCounts({ levelId: 120 });
    expect(result.depthPresets).toEqual({ medium: 3 });
  });
});
