import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Mock } from 'vitest';

const mockQuery = vi.fn();

vi.mock('@services/sqliteService', () => ({
  query: (...args: unknown[]) => mockQuery(...args) as unknown,
  isReady: vi.fn().mockReturnValue(true),
}));

import {
  getEditionCollections,
  getAllCollections,
  searchCollections,
  searchCollectionsByTypes,
} from '@services/puzzleQueryService';

function lastCallSql(): string {
  return (mockQuery as Mock).mock.calls.at(-1)?.[0] as string;
}

function lastCallParams(): unknown[] {
  return ((mockQuery as Mock).mock.calls.at(-1)?.[1] as unknown[]) ?? [];
}

describe('edition queries', () => {
  beforeEach(() => {
    mockQuery.mockReset();
    mockQuery.mockReturnValue([]);
  });

  it('getEditionCollections queries by parent_id', () => {
    getEditionCollections(42);
    const sql = lastCallSql();
    expect(sql).toContain("json_extract(attrs, '$.parent_id') = ?");
    expect(sql).toContain('ORDER BY puzzle_count DESC');
    expect(lastCallParams()).toEqual([42]);
  });

  it('getAllCollections filters out editions (parent_id IS NULL)', () => {
    getAllCollections();
    const sql = lastCallSql();
    expect(sql).toContain("json_extract(attrs, '$.parent_id') IS NULL");
  });

  it('searchCollections excludes editions', () => {
    searchCollections('cho');
    const sql = lastCallSql();
    expect(sql).toContain("json_extract(c.attrs, '$.parent_id') IS NULL");
  });

  it('searchCollectionsByTypes excludes editions', () => {
    searchCollectionsByTypes('cho', ['author']);
    const sql = lastCallSql();
    expect(sql).toContain("json_extract(c.attrs, '$.parent_id') IS NULL");
  });
});
