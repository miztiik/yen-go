import { query } from './sqliteService';

// --- Types ---

export interface PuzzleRow {
  content_hash: string;
  batch: string;
  level_id: number;
  quality: number;
  content_type: number;
  cx_depth: number;
  cx_refutations: number;
  cx_solution_len: number;
  cx_unique_resp: number;
  ac: number;
  attrs: string; // JSON string
  sequence_number?: number | null;
  chapter?: string | null;
}

export interface CollectionRow {
  collection_id: number;
  slug: string;
  name: string;
  category: string | null;
  puzzle_count: number;
  attrs: string; // JSON string
}

export interface QueryFilters {
  levelId?: number;
  tagIds?: number[];
  collectionId?: number;
  quality?: number;
  contentType?: number;
  minDepth?: number;
  maxDepth?: number;
  chapter?: string;
}

export interface FilterCounts {
  levels: Record<number, number>;
  tags: Record<number, number>;
  collections: Record<number, number>;
  quality: Record<number, number>;
  contentTypes: Record<number, number>;
  depthPresets: Record<string, number>;
}

// --- Internals ---

const BASE_SELECT = `SELECT p.content_hash, p.batch, p.level_id, p.quality, p.content_type,
  p.cx_depth, p.cx_refutations, p.cx_solution_len, p.cx_unique_resp, p.ac, p.attrs`;

function buildJoinClause(filters: QueryFilters): string {
  const joins: string[] = [];
  if (filters.collectionId !== undefined || filters.chapter !== undefined) {
    joins.push('JOIN puzzle_collections pc ON p.content_hash = pc.content_hash');
  }
  return joins.join(' ');
}

function buildWhereClause(filters: QueryFilters): string {
  const conditions: string[] = [];
  if (filters.levelId !== undefined) conditions.push('p.level_id = ?');
  if (filters.tagIds?.length) {
    const placeholders = filters.tagIds.map(() => '?').join(',');
    conditions.push(
      `p.content_hash IN (SELECT content_hash FROM puzzle_tags WHERE tag_id IN (${placeholders}) GROUP BY content_hash HAVING COUNT(DISTINCT tag_id) = ?)`
    );
  }
  if (filters.collectionId !== undefined) conditions.push('pc.collection_id = ?');
  if (filters.chapter !== undefined) conditions.push('pc.chapter = ?');
  if (filters.quality !== undefined) conditions.push('p.quality >= ?');
  if (filters.contentType !== undefined) conditions.push('p.content_type = ?');
  if (filters.minDepth !== undefined) conditions.push('p.cx_depth >= ?');
  if (filters.maxDepth !== undefined) conditions.push('p.cx_depth <= ?');
  return conditions.length ? 'WHERE ' + conditions.join(' AND ') : '';
}

function buildParams(filters: QueryFilters): (string | number)[] {
  const params: (string | number)[] = [];
  if (filters.levelId !== undefined) params.push(filters.levelId);
  if (filters.tagIds?.length) {
    params.push(...filters.tagIds);
    params.push(filters.tagIds.length);
  }
  if (filters.collectionId !== undefined) params.push(filters.collectionId);
  if (filters.chapter !== undefined) params.push(filters.chapter);
  if (filters.quality !== undefined) params.push(filters.quality);
  if (filters.contentType !== undefined) params.push(filters.contentType);
  if (filters.minDepth !== undefined) params.push(filters.minDepth);
  if (filters.maxDepth !== undefined) params.push(filters.maxDepth);
  return params;
}

// --- Query Functions ---

export function getPuzzlesByLevel(levelId: number): PuzzleRow[] {
  return query<PuzzleRow>(`${BASE_SELECT} FROM puzzles p WHERE p.level_id = ?`, [levelId]);
}

export function getPuzzlesByTag(tagId: number): PuzzleRow[] {
  return query<PuzzleRow>(
    `${BASE_SELECT} FROM puzzles p
     JOIN puzzle_tags pt ON p.content_hash = pt.content_hash
     WHERE pt.tag_id = ?`,
    [tagId]
  );
}

export function getPuzzlesByCollection(colId: number): PuzzleRow[] {
  try {
    return query<PuzzleRow>(
      `${BASE_SELECT}, pc.sequence_number, pc.chapter FROM puzzles p
       JOIN puzzle_collections pc ON p.content_hash = pc.content_hash
       WHERE pc.collection_id = ?
       ORDER BY pc.sequence_number`,
      [colId]
    );
  } catch {
    // Fallback for older DB versions without the chapter column
    return query<PuzzleRow>(
      `${BASE_SELECT}, pc.sequence_number FROM puzzles p
       JOIN puzzle_collections pc ON p.content_hash = pc.content_hash
       WHERE pc.collection_id = ?
       ORDER BY pc.sequence_number`,
      [colId]
    );
  }
}

/** Get distinct non-empty chapter strings for a collection. */
export function getCollectionChapters(colId: number): string[] {
  try {
    const rows = query<{ chapter: string }>(
      `SELECT DISTINCT chapter FROM puzzle_collections
       WHERE collection_id = ? AND chapter != '' AND chapter != '0'
       ORDER BY chapter`,
      [colId]
    );
    return rows.map((r) => r.chapter);
  } catch {
    return [];
  }
}

/** Get puzzle count per chapter for a collection. */
export function getCollectionChapterCounts(colId: number): Record<string, number> {
  try {
    const rows = query<{ chapter: string; cnt: number }>(
      `SELECT chapter, COUNT(*) as cnt FROM puzzle_collections
       WHERE collection_id = ? AND chapter != '' AND chapter != '0'
       GROUP BY chapter
       ORDER BY chapter`,
      [colId]
    );
    return Object.fromEntries(rows.map((r) => [r.chapter, r.cnt]));
  } catch {
    return {};
  }
}

/** Get distinct chapter count per collection. 0 for chapterless collections. */
export function getAllCollectionChapterCounts(): Record<number, number> {
  try {
    const rows = query<{ collection_id: number; cnt: number }>(
      `SELECT collection_id, COUNT(DISTINCT chapter) as cnt
       FROM puzzle_collections
       WHERE chapter != '' AND chapter != '0'
       GROUP BY collection_id`
    );
    return Object.fromEntries(rows.map((r) => [r.collection_id, r.cnt]));
  } catch {
    return {};
  }
}

export function searchCollections(searchQuery: string): CollectionRow[] {
  const escaped = searchQuery.replace(/["\-*()^~]/g, ' ').trim();
  if (!escaped) return [];
  return query<CollectionRow>(
    `SELECT c.collection_id, c.name, c.slug, c.category, c.puzzle_count, c.attrs
     FROM collections_fts fts
     JOIN collections c ON fts.rowid = c.collection_id
     WHERE fts MATCH ?
     AND json_extract(c.attrs, '$.parent_id') IS NULL
     ORDER BY rank`,
    [escaped + '*']
  );
}

/**
 * Search collections by FTS query, filtered to specific collection types.
 * Types are matched against json_extract(attrs, '$.type').
 */
export function searchCollectionsByTypes(searchQuery: string, types: string[]): CollectionRow[] {
  const escaped = searchQuery.replace(/["\-*()^~]/g, ' ').trim();
  if (!escaped || types.length === 0) return [];
  const placeholders = types.map(() => '?').join(',');
  return query<CollectionRow>(
    `SELECT c.collection_id, c.name, c.slug, c.category, c.puzzle_count, c.attrs
     FROM collections_fts fts
     JOIN collections c ON fts.rowid = c.collection_id
     WHERE fts MATCH ?
     AND json_extract(c.attrs, '$.type') IN (${placeholders})
     AND json_extract(c.attrs, '$.parent_id') IS NULL
     ORDER BY rank`,
    [escaped + '*', ...types]
  );
}

export function getAllCollections(): CollectionRow[] {
  return query<CollectionRow>(
    `SELECT collection_id, slug, name, category, puzzle_count, attrs
     FROM collections
     WHERE json_extract(attrs, '$.parent_id') IS NULL
     ORDER BY name`
  );
}

export function getEditionCollections(parentId: number): CollectionRow[] {
  return query<CollectionRow>(
    `SELECT collection_id, slug, name, category, puzzle_count, attrs
     FROM collections
     WHERE json_extract(attrs, '$.parent_id') = ?
     ORDER BY puzzle_count DESC`,
    [parentId]
  );
}

export function getLevelCounts(): Record<number, number> {
  const rows = query<{ level_id: number; cnt: number }>(
    'SELECT level_id, COUNT(*) as cnt FROM puzzles GROUP BY level_id'
  );
  return Object.fromEntries(rows.map((r) => [r.level_id, r.cnt]));
}

export function getTagCounts(): Record<number, number> {
  const rows = query<{ tag_id: number; cnt: number }>(
    'SELECT tag_id, COUNT(*) as cnt FROM puzzle_tags GROUP BY tag_id'
  );
  return Object.fromEntries(rows.map((r) => [r.tag_id, r.cnt]));
}

export function getCollectionCounts(): Record<number, number> {
  const rows = query<{ collection_id: number; cnt: number }>(
    'SELECT collection_id, COUNT(*) as cnt FROM puzzle_collections GROUP BY collection_id'
  );
  return Object.fromEntries(rows.map((r) => [r.collection_id, r.cnt]));
}

export function getQualityCounts(): Record<number, number> {
  const rows = query<{ quality: number; cnt: number }>(
    'SELECT quality, COUNT(*) as cnt FROM puzzles GROUP BY quality'
  );
  return Object.fromEntries(rows.map((r) => [r.quality, r.cnt]));
}

export function getContentTypeCounts(): Record<number, number> {
  const rows = query<{ content_type: number; cnt: number }>(
    'SELECT content_type, COUNT(*) as cnt FROM puzzles GROUP BY content_type'
  );
  return Object.fromEntries(rows.map((r) => [r.content_type, r.cnt]));
}

export function getDepthPresetCounts(filters: QueryFilters): Record<string, number> {
  const whereClause = buildWhereClause(filters);
  const params = buildParams(filters);
  const rows = query<{ preset: string; cnt: number }>(
    `SELECT
       CASE
         WHEN p.cx_depth >= 1 AND p.cx_depth <= 2 THEN 'quick'
         WHEN p.cx_depth >= 3 AND p.cx_depth <= 5 THEN 'medium'
         WHEN p.cx_depth >= 6 THEN 'deep'
       END AS preset,
       COUNT(DISTINCT p.content_hash) AS cnt
     FROM puzzles p ${buildJoinClause(filters)}
     ${whereClause}
     GROUP BY preset
     HAVING preset IS NOT NULL`,
    params
  );
  return Object.fromEntries(rows.map((r) => [r.preset, r.cnt]));
}

export function getFilterCounts(filters: QueryFilters): FilterCounts {
  if (
    !filters.levelId &&
    !filters.tagIds?.length &&
    !filters.collectionId &&
    filters.quality === undefined &&
    filters.contentType === undefined &&
    filters.minDepth === undefined &&
    filters.maxDepth === undefined
  ) {
    return {
      levels: getLevelCounts(),
      tags: getTagCounts(),
      collections: getCollectionCounts(),
      quality: getQualityCounts(),
      contentTypes: getContentTypeCounts(),
      depthPresets: getDepthPresetCounts({}),
    };
  }

  const whereClause = buildWhereClause(filters);
  const params = buildParams(filters);

  const levels = query<{ level_id: number; cnt: number }>(
    `SELECT p.level_id, COUNT(DISTINCT p.content_hash) as cnt
     FROM puzzles p ${buildJoinClause(filters)}
     ${whereClause} GROUP BY p.level_id`,
    params
  );

  const tags = query<{ tag_id: number; cnt: number }>(
    `SELECT pt2.tag_id, COUNT(DISTINCT p.content_hash) as cnt
     FROM puzzles p ${buildJoinClause(filters)}
     JOIN puzzle_tags pt2 ON p.content_hash = pt2.content_hash
     ${whereClause} GROUP BY pt2.tag_id`,
    params
  );

  const qualityRows = query<{ quality: number; cnt: number }>(
    `SELECT p.quality, COUNT(DISTINCT p.content_hash) as cnt
     FROM puzzles p ${buildJoinClause(filters)}
     ${whereClause} GROUP BY p.quality`,
    params
  );

  const contentTypeRows = query<{ content_type: number; cnt: number }>(
    `SELECT p.content_type, COUNT(DISTINCT p.content_hash) as cnt
     FROM puzzles p ${buildJoinClause(filters)}
     ${whereClause} GROUP BY p.content_type`,
    params
  );

  return {
    levels: Object.fromEntries(levels.map((r) => [r.level_id, r.cnt])),
    tags: Object.fromEntries(tags.map((r) => [r.tag_id, r.cnt])),
    collections: getCollectionCounts(),
    quality: Object.fromEntries(qualityRows.map((r) => [r.quality, r.cnt])),
    contentTypes: Object.fromEntries(contentTypeRows.map((r) => [r.content_type, r.cnt])),
    depthPresets: getDepthPresetCounts(filters),
  };
}

export function getPuzzlesFiltered(filters: QueryFilters, limit = 500, offset = 0): PuzzleRow[] {
  const whereClause = buildWhereClause(filters);
  const params = buildParams(filters);

  return query<PuzzleRow>(
    `${BASE_SELECT} FROM puzzles p ${buildJoinClause(filters)}
     ${whereClause} LIMIT ? OFFSET ?`,
    [...params, limit, offset]
  );
}

export function getPuzzleByHash(contentHash: string): PuzzleRow | undefined {
  const rows = query<PuzzleRow>(`${BASE_SELECT} FROM puzzles p WHERE p.content_hash = ?`, [
    contentHash,
  ]);
  return rows[0];
}

export function getTotalPuzzleCount(): number {
  const rows = query<{ cnt: number }>('SELECT COUNT(*) as cnt FROM puzzles');
  return rows[0]?.cnt ?? 0;
}

/** Cross-tab: for each level, map of tagId → count. */
export function getTagDistributionByLevel(): Record<number, Record<string, number>> {
  const rows = query<{ level_id: number; tag_id: number; cnt: number }>(
    `SELECT p.level_id, pt.tag_id, COUNT(*) as cnt
     FROM puzzles p
     JOIN puzzle_tags pt ON p.content_hash = pt.content_hash
     GROUP BY p.level_id, pt.tag_id`
  );
  const result: Record<number, Record<string, number>> = {};
  for (const r of rows) {
    if (!result[r.level_id]) result[r.level_id] = {};
    result[r.level_id]![String(r.tag_id)] = r.cnt;
  }
  return result;
}

/** Cross-tab: for each tag, map of levelId → count. */
export function getLevelDistributionByTag(): Record<number, Record<string, number>> {
  const rows = query<{ tag_id: number; level_id: number; cnt: number }>(
    `SELECT pt.tag_id, p.level_id, COUNT(*) as cnt
     FROM puzzles p
     JOIN puzzle_tags pt ON p.content_hash = pt.content_hash
     GROUP BY pt.tag_id, p.level_id`
  );
  const result: Record<number, Record<string, number>> = {};
  for (const r of rows) {
    if (!result[r.tag_id]) result[r.tag_id] = {};
    result[r.tag_id]![String(r.level_id)] = r.cnt;
  }
  return result;
}
