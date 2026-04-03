/**
 * Puzzle Set Loaders — class-based loaders for collection, training, daily, rush, and random puzzle sets.
 *
 * Uses SQLite search database for all loaders.
 * Each loader queries puzzleQueryService, maps PuzzleRow to EnrichedEntry, and loads SGF content.
 *
 * Spec 127: T045, FR-007
 * @module services/puzzleLoaders
 */

import { fetchSGFContent, type LoaderResult } from './puzzleLoader';
import { init as initDb } from './sqliteService';
import { getPuzzlesByCollection, getPuzzlesByTag, getPuzzlesByLevel, getPuzzlesFiltered, type PuzzleRow } from './puzzleQueryService';
import { expandPath } from './entryDecoder';
import { levelIdToSlug, levelSlugToId, tagSlugToId } from './configService';
import { getNextRushPuzzle } from './puzzleRushService';
import { resolveCollectionDirId, ensureCollectionIdsLoaded, getCollectionTypeBySlug } from './collectionService';
import type { CollectionType, SkillLevel } from '@/models/collection';
import { SHUFFLE_POLICY, shuffleArray } from '@/constants/collectionConfig';
import { extractPuzzleIdFromPath } from '../lib/puzzle/utils';
import type { DailyPuzzleEntry } from '../types/indexes';

// ============================================================================
// Types
// ============================================================================

/** A puzzle entry with its loaded SGF content. */
export interface LoadedPuzzleEntry {
  id: string;
  path: string;
  level: string;
  tags: readonly string[];
  sgf: string;
}

/** Status of the loader. */
export type LoaderStatus = 'idle' | 'loading' | 'ready' | 'error' | 'empty';

/** Interface for puzzle set loaders. */
export interface PuzzleSetLoader {
  /** Fetch the view JSON and prepare puzzle entries. */
  load(): Promise<void>;
  /** Get the current loader status. */
  getStatus(): LoaderStatus;
  /** Get total number of puzzles in the set. */
  getTotal(): number;
  /** Load and return SGF for puzzle at given index. */
  getPuzzleSgf(index: number): Promise<LoaderResult<string>>;
  /** Get entry metadata without loading SGF. */
  getEntry(index: number): PuzzleEntryMeta | null;
  /** Error message if status is 'error'. */
  getError(): string | null;
}

/**
 * StreamingPuzzleSetLoader — extends PuzzleSetLoader for infinite/on-demand puzzle sources.
 *
 * Used by Rush and Random modes where puzzles are fetched one at a time
 * rather than loaded from a finite collection.
 */
export interface StreamingPuzzleSetLoader extends PuzzleSetLoader {
  /** Whether more puzzles can be loaded. */
  hasMore(): boolean;
  /** Load the next batch of puzzles. Returns the number of new puzzles added. */
  loadMore(): Promise<number>;
}

export interface PuzzleEntryMeta {
  id: string;
  path: string;
  level: string;
}

/** Internal entry with enriched metadata for client-side filtering (C2). */
interface EnrichedEntry {
  id: string;
  path: string;
  level: string;
  tagIds?: number[];
  /** Content type numeric ID (1=curated, 2=practice, 3=training). */
  contentTypeId?: number;
  sequenceNumber?: number | undefined;
}

// ============================================================================
// PuzzleRow → EnrichedEntry / LoadedPuzzleEntry mapping
// ============================================================================

/**
 * Convert a PuzzleRow from SQL into an EnrichedEntry for internal loader use.
 * @param row - PuzzleRow from puzzleQueryService
 * @param levelSlugOverride - Optional level slug override (for training loader where slug is known)
 */
function puzzleRowToEnriched(row: PuzzleRow, levelSlugOverride?: string): EnrichedEntry {
  const compactPath = `${row.batch}/${row.content_hash}`;
  const path = expandPath(compactPath);
  return {
    id: extractPuzzleIdFromPath(path),
    path,
    level: levelSlugOverride ?? levelIdToSlug(row.level_id),
    contentTypeId: row.content_type,
    sequenceNumber: row.sequence_number ?? undefined,
  };
}

/**
 * Convert a PuzzleRow from SQL into a LoadedPuzzleEntry.
 * Exported for use in entryDecoder and tests.
 */
export function puzzleRowToEntry(row: PuzzleRow): LoadedPuzzleEntry {
  const compactPath = `${row.batch}/${row.content_hash}`;
  const path = expandPath(compactPath);
  return {
    id: extractPuzzleIdFromPath(path),
    path,
    level: levelIdToSlug(row.level_id),
    tags: [],
    sgf: '',
  };
}

// ============================================================================
// CollectionPuzzleLoader
// ============================================================================

/**
 * Loads puzzles from a collection via SQLite query.
 *
 * Uses getPuzzlesByCollection() / getPuzzlesFiltered() from puzzleQueryService.
 *
 * T045: Uses SQLite database for puzzle discovery.
 * T046: Returns clear error messages on query failure or SGF load failure.
 * T047: Reports 'empty' status when collection has 0 puzzles.
 * T048: Supports startIndex for deep-link.
 */
export class CollectionPuzzleLoader implements PuzzleSetLoader {
  private entries: EnrichedEntry[] = [];
  private status: LoaderStatus = 'idle';
  private errorMessage: string | null = null;
  private readonly sgfCache = new Map<number, string>();

  constructor(
    private readonly collectionId: string,
    _startIndex = 0,
    /** C2: Optional level IDs for client-side filtering (multi-select). */
    private readonly levelIds: readonly number[] = [],
    /** C2: Optional tag IDs for client-side filtering (multi-select). */
    private readonly tagIds: readonly number[] = [],
    /** Optional content-type filter (1=curated, 2=practice). 0 = no filter. */
    private readonly contentTypeId: number = 0,
    /** Optional collection type for shuffle policy. Resolved from config if not provided. */
    private readonly collectionType?: CollectionType,
    /** Optional chapter filter for chaptered collections. */
    private readonly chapter?: string,
  ) {}

  /**
   * Load collection puzzles from SQLite.
   *
   * 1. Ensure SQLite DB is initialized
   * 2. Resolve collectionId (slug or numeric) → numeric ID
   * 3. Query puzzles via getPuzzlesByCollection() or getPuzzlesFiltered()
   * 4. Convert PuzzleRow to EnrichedEntry
   * 5. Apply client-side filters if active
   */
  async load(): Promise<void> {
    this.status = 'loading';
    this.errorMessage = null;

    try {
      await initDb();

      // Resolve collection ID: numeric string or slug
      const numericId = await this.resolveNumericId();
      if (numericId === undefined) {
        this.status = 'error';
        this.errorMessage = `Unknown collection: "${this.collectionId}". Check the collection name and try again.`;
        return;
      }

      const hasFilters = this.levelIds.length > 0 || this.tagIds.length > 0 || this.contentTypeId > 0 || !!this.chapter;
      const isTagBased = this.collectionId.startsWith('tag-');
      const isLevelBased = this.collectionId.startsWith('level-');

      let rows: PuzzleRow[];
      if (hasFilters) {
        // Use filtered query for multi-dimension filtering
        const filters: import('./puzzleQueryService').QueryFilters = isTagBased
          ? { tagIds: [numericId] }
          : isLevelBased
            ? { levelId: numericId }
            : { collectionId: numericId };
        const firstLevelId = this.levelIds[0];
        if (this.levelIds.length === 1 && firstLevelId !== undefined) filters.levelId = firstLevelId;
        if (this.tagIds.length > 0) filters.tagIds = [...(filters.tagIds ?? []), ...this.tagIds];
        if (this.contentTypeId > 0) filters.contentType = this.contentTypeId;
        if (this.chapter) filters.chapter = this.chapter;
        rows = getPuzzlesFiltered(filters);
      } else if (isTagBased) {
        rows = getPuzzlesByTag(numericId);
      } else if (isLevelBased) {
        rows = getPuzzlesByLevel(numericId);
      } else {
        rows = getPuzzlesByCollection(numericId);
      }

      this.entries = rows.map(row => puzzleRowToEnriched(row));

      // For multi-level filter (more than one level), apply client-side
      if (this.levelIds.length > 1) {
        const targetSlugs = this.levelIds.map(id => levelIdToSlug(id)).filter(Boolean);
        this.entries = this.entries.filter(e => targetSlugs.includes(e.level));
      }

      // Apply shuffle policy based on collection type
      const resolvedType = this.collectionType ?? getCollectionTypeBySlug(this.collectionId);
      if (resolvedType && SHUFFLE_POLICY[resolvedType]) {
        this.entries = shuffleArray(this.entries);
      }

      this.status = this.entries.length === 0 ? 'empty' : 'ready';
    } catch (err) {
      this.status = 'error';
      this.errorMessage =
        err instanceof Error
          ? `Error loading collection: ${err.message}`
          : 'Unknown error loading collection';
    }
  }

  /**
   * Resolve collectionId to a numeric ID.
   * - If collectionId parses as a positive integer, use it directly.
   * - Otherwise, treat as a composite slug and resolve via collectionService.
   */
  private async resolveNumericId(): Promise<number | undefined> {
    const parsed = Number(this.collectionId);
    if (!Number.isNaN(parsed) && Number.isInteger(parsed) && parsed > 0) {
      return parsed;
    }

    // Slug-based resolution via collectionService
    await ensureCollectionIdsLoaded();
    return resolveCollectionDirId(this.collectionId);
  }

  getStatus(): LoaderStatus {
    return this.status;
  }

  getTotal(): number {
    return this.entries.length;
  }

  getError(): string | null {
    return this.errorMessage;
  }

  getEntry(index: number): PuzzleEntryMeta | null {
    const entry = this.entries[index];
    if (!entry) return null;
    return {
      id: entry.id ?? extractPuzzleIdFromPath(entry.path),
      path: entry.path,
      level: entry.level ?? this.collectionId,
    };
  }

  async getPuzzleSgf(index: number): Promise<LoaderResult<string>> {
    // Check cache
    const cached = this.sgfCache.get(index);
    if (cached) return { success: true, data: cached };

    const entry = this.entries[index];
    if (!entry) {
      return {
        success: false,
        error: 'not_found',
        message: `Puzzle at index ${index} not found in collection`,
      };
    }

    // T046: Load SGF with error handling
    const sgfResult = await fetchSGFContent(entry.path);
    if (!sgfResult.success || !sgfResult.data) {
      return {
        success: false,
        error: sgfResult.error ?? 'network_error',
        message: `Failed to load puzzle SGF: ${sgfResult.message ?? entry.path}. Try refreshing or skip this puzzle.`,
      };
    }

    this.sgfCache.set(index, sgfResult.data);
    return { success: true, data: sgfResult.data };
  }
}

// ============================================================================
// TrainingPuzzleLoader
// ============================================================================

/**
 * Loads puzzles for a training level from the SQLite database.
 *
 * Uses getPuzzlesByLevel() from puzzleQueryService.
 *
 * Wraps SQL queries to implement PuzzleSetLoader, allowing
 * TrainingViewPage to use the shared PuzzleSetPlayer component.
 */
export class TrainingPuzzleLoader implements PuzzleSetLoader {
  private entries: EnrichedEntry[] = [];
  private status: LoaderStatus = 'idle';
  private errorMessage: string | null = null;
  private readonly sgfCache = new Map<number, string>();

  constructor(
    private readonly levelSlug: string,
    /** Optional tag IDs for client-side filtering (multi-select). */
    private readonly tagIds: readonly number[] = [],
    /** Optional content-type filter (1=curated, 2=practice). 0 = no filter. */
    private readonly contentTypeId: number = 0,
  ) {}

  async load(): Promise<void> {
    this.status = 'loading';
    this.errorMessage = null;

    try {
      await initDb();

      // Resolve level slug to numeric ID
      const numericId = levelSlugToId(this.levelSlug);
      if (numericId === undefined) {
        this.status = 'error';
        this.errorMessage = `Unknown level: "${this.levelSlug}"`;
        return;
      }

      const hasFilters = this.tagIds.length > 0 || this.contentTypeId > 0;

      let rows: PuzzleRow[];
      if (hasFilters) {
        const filters: import('./puzzleQueryService').QueryFilters = { levelId: numericId };
        if (this.tagIds.length > 0) filters.tagIds = [...this.tagIds];
        if (this.contentTypeId > 0) filters.contentType = this.contentTypeId;
        rows = getPuzzlesFiltered(filters);
      } else {
        rows = getPuzzlesByLevel(numericId);
      }

      this.entries = rows.map(row => puzzleRowToEnriched(row, this.levelSlug));

      this.status = this.entries.length === 0 ? 'empty' : 'ready';
    } catch (err) {
      this.status = 'error';
      this.errorMessage =
        err instanceof Error
          ? `Error loading training level: ${err.message}`
          : 'Unknown error loading training level';
    }
  }

  getStatus(): LoaderStatus {
    return this.status;
  }

  getTotal(): number {
    return this.entries.length;
  }

  getError(): string | null {
    return this.errorMessage;
  }

  getEntry(index: number): PuzzleEntryMeta | null {
    const entry = this.entries[index];
    if (!entry) return null;
    return { id: entry.id, path: entry.path, level: entry.level };
  }

  async getPuzzleSgf(index: number): Promise<LoaderResult<string>> {
    const cached = this.sgfCache.get(index);
    if (cached) return { success: true, data: cached };

    const entry = this.entries[index];
    if (!entry) {
      return {
        success: false,
        error: 'not_found',
        message: `Training puzzle at index ${index} not found`,
      };
    }

    const sgfResult = await fetchSGFContent(entry.path);
    if (!sgfResult.success || !sgfResult.data) {
      return {
        success: false,
        error: sgfResult.error ?? 'network_error',
        message: `Failed to load training puzzle SGF: ${sgfResult.message ?? entry.path}`,
      };
    }

    this.sgfCache.set(index, sgfResult.data);
    return { success: true, data: sgfResult.data };
  }
}

// ============================================================================
// DailyPuzzleLoader
// ============================================================================

/**
 * Loads puzzles from the daily challenge SQLite tables.
 *
 * Uses dailyQueryService to query daily_schedule + daily_puzzles from
 * the in-memory yengo-search.db via sql.js.
 */
export class DailyPuzzleLoader implements PuzzleSetLoader {
  private entries: DailyPuzzleEntry[] = [];
  private status: LoaderStatus = 'idle';
  private errorMessage: string | null = null;
  private readonly sgfCache = new Map<number, string>();

  constructor(
    private readonly date: string,
    private readonly mode: string = 'standard',
  ) {}

  async load(): Promise<void> {
    this.status = 'loading';
    this.errorMessage = null;

    try {
      await initDb();

      const { getDailySchedule, getDailyPuzzles } = await import('./dailyQueryService');
      const schedule = getDailySchedule(this.date);
      if (!schedule) {
        this.status = 'error';
        this.errorMessage = `No daily challenge available for ${this.date}.`;
        return;
      }

      // Load the correct section based on mode.
      // Timed defaults to blitz (timed_blitz).
      const section = this.mode === 'timed' ? 'timed_blitz' : 'standard';
      const puzzleRows = getDailyPuzzles(this.date, section);
      this.entries = puzzleRows.map(row => ({
        level: levelIdToSlug(row.level_id) ?? 'beginner',
        path: `sgf/${row.batch}/${row.content_hash}.sgf`,
      }));

      this.status = this.entries.length === 0 ? 'empty' : 'ready';
    } catch (err) {
      this.status = 'error';
      this.errorMessage =
        err instanceof Error
          ? `Error loading daily challenge: ${err.message}`
          : 'Unknown error loading daily challenge';
    }
  }

  getStatus(): LoaderStatus {
    return this.status;
  }

  getTotal(): number {
    return this.entries.length;
  }

  getError(): string | null {
    return this.errorMessage;
  }

  getEntry(index: number): PuzzleEntryMeta | null {
    const entry = this.entries[index];
    if (!entry) return null;
    return {
      id: extractPuzzleIdFromPath(entry.path),
      path: entry.path,
      level: entry.level,
    };
  }

  async getPuzzleSgf(index: number): Promise<LoaderResult<string>> {
    const cached = this.sgfCache.get(index);
    if (cached) return { success: true, data: cached };

    const entry = this.entries[index];
    if (!entry) {
      return {
        success: false,
        error: 'not_found',
        message: `Daily puzzle at index ${index} not found`,
      };
    }

    const sgfResult = await fetchSGFContent(entry.path);
    if (!sgfResult.success || !sgfResult.data) {
      return {
        success: false,
        error: sgfResult.error ?? 'network_error',
        message: `Failed to load daily puzzle SGF: ${sgfResult.message ?? entry.path}`,
      };
    }

    this.sgfCache.set(index, sgfResult.data);
    return { success: true, data: sgfResult.data };
  }
}

// ============================================================================
// RushPuzzleLoader
// ============================================================================

export class RushPuzzleLoader implements StreamingPuzzleSetLoader {
  private status: LoaderStatus = 'idle';
  private errorMessage: string | null = null;
  private entries: PuzzleEntryMeta[] = [];
  private readonly sgfCache = new Map<number, string>();
  private usedPuzzleIds = new Set<string>();
  private prefetchPromise: Promise<void> | null = null;

  constructor(
    private readonly levelId: number | null,
    private readonly tagId: number | null,
  ) {}

  async load(): Promise<void> {
    this.status = 'loading';
    this.errorMessage = null;

    try {
      const count = await this.loadMore();
      if (count > 0) {
        // Prefetch SGF for the first puzzle and the next one
        this.prefetchSgf(0);
        this.status = 'ready';
      } else {
        this.status = 'empty';
      }
    } catch (err) {
      this.status = 'error';
      this.errorMessage = err instanceof Error ? err.message : 'Failed to load rush puzzle';
    }
  }

  getStatus(): LoaderStatus {
    return this.status;
  }

  getTotal(): number {
    return this.entries.length;
  }

  getError(): string | null {
    return this.errorMessage;
  }

  getEntry(index: number): PuzzleEntryMeta | null {
    return this.entries[index] ?? null;
  }

  async getPuzzleSgf(index: number): Promise<LoaderResult<string>> {
    // Wait for any prefetch in progress for this index
    if (this.prefetchPromise) {
      await this.prefetchPromise;
    }

    const cached = this.sgfCache.get(index);
    if (cached) return { success: true, data: cached };

    const entry = this.entries[index];
    if (!entry) return { success: false, message: `Index ${index} out of range` };

    const result = await fetchSGFContent(entry.path);
    if (result.success && result.data) {
      this.sgfCache.set(index, result.data);
      // Prefetch next puzzle SGF (RC-5: no skeleton flash)
      this.prefetchSgf(index + 1);
      return { success: true, data: result.data };
    }
    return { success: false, message: result.message ?? 'Failed to load SGF' };
  }

  hasMore(): boolean {
    return true; // Rush always has more puzzles
  }

  async loadMore(): Promise<number> {
    try {
      const setUsedIds = (updater: (prev: Set<string>) => Set<string>): void => {
        this.usedPuzzleIds = updater(this.usedPuzzleIds);
      };
      const puzzle = await getNextRushPuzzle(this.levelId, this.tagId, this.usedPuzzleIds, setUsedIds);
      if (!puzzle) return 0;

      this.entries.push({ id: puzzle.id, path: puzzle.path, level: puzzle.level });
      // Prefetch SGF for the newly added puzzle
      const newIndex = this.entries.length - 1;
      this.prefetchSgf(newIndex);
      return 1;
    } catch {
      return 0;
    }
  }

  /** Background prefetch of SGF content (RC-5: no skeleton flash between puzzles). */
  private prefetchSgf(index: number): void {
    const entry = this.entries[index];
    if (!entry || this.sgfCache.has(index)) return;

    this.prefetchPromise = fetchSGFContent(entry.path).then(result => {
      if (result.success && result.data) {
        this.sgfCache.set(index, result.data);
      }
      this.prefetchPromise = null;
    }).catch(() => {
      this.prefetchPromise = null;
    });
  }
}

// ============================================================================
// RandomPuzzleLoader
// ============================================================================

export class RandomPuzzleLoader implements StreamingPuzzleSetLoader {
  private status: LoaderStatus = 'idle';
  private errorMessage: string | null = null;
  private entries: PuzzleEntryMeta[] = [];
  private readonly sgfCache = new Map<number, string>();
  private usedIds = new Set<string>();

  constructor(
    private readonly level: SkillLevel,
    private readonly tagSlug?: string | null,
  ) {}

  async load(): Promise<void> {
    this.status = 'loading';
    this.errorMessage = null;

    try {
      await initDb();
      // Load first puzzle immediately
      const count = await this.loadMore();
      this.status = count > 0 ? 'ready' : 'empty';
    } catch (err) {
      this.status = 'error';
      this.errorMessage = err instanceof Error ? err.message : 'Failed to load random puzzle';
    }
  }

  getStatus(): LoaderStatus {
    return this.status;
  }

  getTotal(): number {
    return this.entries.length;
  }

  getError(): string | null {
    return this.errorMessage;
  }

  getEntry(index: number): PuzzleEntryMeta | null {
    return this.entries[index] ?? null;
  }

  async getPuzzleSgf(index: number): Promise<LoaderResult<string>> {
    const cached = this.sgfCache.get(index);
    if (cached) return { success: true, data: cached };

    const entry = this.entries[index];
    if (!entry) return { success: false, message: `Index ${index} out of range` };

    const result = await fetchSGFContent(entry.path);
    if (result.success && result.data) {
      this.sgfCache.set(index, result.data);
      return { success: true, data: result.data };
    }
    return { success: false, message: result.message ?? 'Failed to load SGF' };
  }

  hasMore(): boolean {
    return true; // Random always has more puzzles
  }

  async loadMore(): Promise<number> {
    try {
      const levelId = levelSlugToId(this.level);
      if (levelId === undefined) return 0;

      await initDb();

      let rows;
      if (this.tagSlug) {
        const tagId = tagSlugToId(this.tagSlug);
        rows = tagId !== undefined
          ? getPuzzlesFiltered({ levelId, tagIds: [tagId] })
          : getPuzzlesByLevel(levelId);
      } else {
        rows = getPuzzlesByLevel(levelId);
      }

      const allEntries = rows.map(puzzleRowToEntry);
      const available = allEntries.filter(e => !this.usedIds.has(e.id));
      if (available.length === 0) {
        // Reset pool when exhausted
        this.usedIds.clear();
        const pick = allEntries[Math.floor(Math.random() * allEntries.length)];
        if (!pick) return 0;
        this.usedIds.add(pick.id);
        this.entries.push({ id: pick.id, path: pick.path, level: pick.level });
        return 1;
      }

      const pick = available[Math.floor(Math.random() * available.length)]!;
      this.usedIds.add(pick.id);
      this.entries.push({ id: pick.id, path: pick.path, level: pick.level });
      return 1;
    } catch {
      return 0;
    }
  }
}
