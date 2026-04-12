/**
 * Collection Service
 * @module services/collectionService
 *
 * Responsible for loading puzzle collections from static JSON files.
 * Collections are derived from:
 * - Level indexes (views/by-level/)
 * - Tag-based collections (views/by-tag/)
 * - Curated collections (views/by-collection/, config/collections.json)
 *
 * Covers: FR-001 to FR-016 (Collection Browsing + Curated Collections)
 */

import type {
  Collection,
  CollectionSummary,
  CollectionIndex,
  CollectionPuzzleEntry,
  CollectionFilter,
  SkillLevel,
  CuratedCollection,
  CollectionCatalog,
  CollectionType,
  CollectionTier,
} from '@/models/collection';
import { compareSkillLevels, SKILL_LEVELS } from '@/models/collection';
import type { LoaderResult, LoaderError } from '@/types/common';
import { APP_CONSTANTS } from '@/config/constants';
import { extractPuzzleIdFromPath } from '@/lib/puzzle/utils';
import { safeFetchJson } from '@/utils/safeFetchJson';
import { expandPath } from '@/services/entryDecoder';
import { levelSlugToId, levelIdToSlug, tagSlugToId, getTagMeta } from '@/services/configService';
import { init as initDb } from '@/services/sqliteService';
import { getPuzzlesByCollection, getPuzzlesByLevel, getPuzzlesByTag, getTagCounts, getCollectionCounts, getFilterCounts, getCollectionChapters, getCollectionChapterCounts, getAllCollectionChapterCounts } from '@/services/puzzleQueryService';
import { TAG_SLUGS } from '@/lib/tags/config';
import { DEFAULT_LEVEL, FIRST_LEVEL, LAST_LEVEL } from '@/lib/levels/level-defaults';

// Default level for new users
const DEFAULT_USER_LEVEL: SkillLevel = DEFAULT_LEVEL;

// ============================================================================
// Configuration
// ============================================================================

/** Estimated time per puzzle in seconds */
const SECONDS_PER_PUZZLE = 45;

// ============================================================================
// Curated Collection Types (config/collections.json)
// ============================================================================

/** Entry from config/collections.json */
interface CuratedCollectionConfig {
  slug: string;
  name: string;
  description: string;
  curator: string;
  source: string;
  type: 'author' | 'reference' | 'graded' | 'technique' | 'system';
  ordering: 'source' | 'difficulty' | 'manual';
  tier?: 'editorial' | 'premier' | 'curated';
  aliases?: string[];
  id?: number;
  level_hint?: string;
}

/** Config file format for config/collections.json */
interface CollectionsConfigFile {
  version: string;
  collections: CuratedCollectionConfig[];
}

/** Entry from views/by-collection/{slug}.json */
interface CollectionViewEntry {
  path: string;
  level: string;
  sequence_number: number;
  chapter?: string;
}

/** View file format for views/by-collection/{slug}.json */
interface CollectionViewFile {
  version: string;
  collection: string;
  total: number;
  entries: CollectionViewEntry[];
}

// ============================================================================
// Cache
// ============================================================================

/** Cache for loaded collection data */
const collectionCache = {
  index: null as CollectionIndex | null,
  collections: new Map<string, Collection>(),
  curatedConfig: null as CollectionsConfigFile | null,
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Convert level slug to collection ID
 */
function levelToCollectionId(level: SkillLevel): string {
  return `level-${level}`;
}

/**
 * Convert tag slug to collection ID
 */
function tagToCollectionId(tag: string): string {
  return `tag-${tag}`;
}

/**
 * Extract level from collection ID (if it's a level-based collection)
 */
function collectionIdToLevel(collectionId: string): SkillLevel | null {
  if (collectionId.startsWith('level-')) {
    const level = collectionId.slice(6);
    return SKILL_LEVELS.some(l => l.slug === level) ? level : null;
  }
  return null;
}

/**
 * Extract tag from collection ID (if it's a tag-based collection)
 */
function collectionIdToTag(collectionId: string): string | null {
  if (collectionId.startsWith('tag-')) {
    return collectionId.slice(4);
  }
  return null;
}

/**
 * Calculate estimated time for collection
 */
function calculateEstimatedMinutes(puzzleCount: number): number {
  return Math.ceil((puzzleCount * SECONDS_PER_PUZZLE) / 60);
}

/**
 * Create a success result
 */
function success<T>(data: T): LoaderResult<T> {
  return { success: true, data };
}

/**
 * Create an error result
 */
function error<T>(errorType: LoaderError, message: string): LoaderResult<T> {
  return { success: false, error: errorType, message };
}

// ============================================================================
// Curated Collection Loaders (config/collections.json + views/by-collection/)
// ============================================================================

/**
 * Load curated collection definitions from config/collections.json.
 * Returns cached result after first successful load.
 * Populates collectionSlugToIdMap for D23 numeric dir resolution.
 */
async function loadCollectionsConfig(): Promise<CollectionsConfigFile | null> {
  if (collectionCache.curatedConfig !== null) {
    return collectionCache.curatedConfig;
  }

  try {
    const url = `${APP_CONSTANTS.paths.configBase}/collections.json`;
    const data = await safeFetchJson<CollectionsConfigFile>(url);
    if (!data.collections || !Array.isArray(data.collections)) return null;

    // D23: Build slug → numeric ID lookup for collection URL resolution
    // Also capture slug → display name for use in master index / headers
    for (const c of data.collections) {
      if (typeof c.id === 'number') {
        collectionSlugToIdMap.set(c.slug, c.id);
      }
      if (typeof c.name === 'string') {
        collectionSlugToNameMap.set(c.slug, c.name);
      }
    }

    collectionCache.curatedConfig = data;
    return data;
  } catch {
    return null;
  }
}

/**
 * Load collection view index from the SQLite search database.
 * Returns entries sorted by sequence_number.
 */
async function loadCollectionViewIndex(slug: string): Promise<CollectionViewFile | null> {
  try {
    await ensureCollectionIdsLoaded();
    const collectionId = collectionSlugToId(slug);
    if (collectionId === undefined) return null;

    await initDb();
    const rows = getPuzzlesByCollection(collectionId);
    if (rows.length === 0) return null;

    const entries: CollectionViewEntry[] = rows.map(row => ({
      path: expandPath(`${row.batch}/${row.content_hash}`),
      level: levelIdToSlug(row.level_id),
      sequence_number: row.sequence_number ?? 0,
      chapter: row.chapter ?? '',
    }));

    return {
      version: '4.0',
      collection: slug,
      total: entries.length,
      entries,
    };
  } catch {
    return null;
  }
}

/**
 * Get distinct chapter strings for a collection, with puzzle counts.
 * Returns empty object for chapterless collections.
 */
export async function getChaptersForCollection(slug: string): Promise<{
  chapters: string[];
  chapterCounts: Record<string, number>;
}> {
  try {
    await ensureCollectionIdsLoaded();
    const colId = collectionSlugToId(slug);
    if (colId === undefined) return { chapters: [], chapterCounts: {} };
    await initDb();
    const chapters = getCollectionChapters(colId);
    if (chapters.length === 0) return { chapters: [], chapterCounts: {} };
    const chapterCounts = getCollectionChapterCounts(colId);
    return { chapters, chapterCounts };
  } catch {
    return { chapters: [], chapterCounts: {} };
  }
}

// ============================================================================
// ============================================================================

/** 
 * Puzzle entry from views/by-level/*.json or views/by-tag/*.json
 * Spec 119: Simplified schema - id extractable from path, level from filename
 * by-level entries: {path, tags}
 * by-tag entries: {path, level}
 */
interface ViewPuzzleEntry {
  path: string;
  // Optional fields (may be present in legacy data, extracted from context otherwise)
  id?: string;
  level?: string;
  board_size?: number;
  tags?: string[];
}

/**
 * Load level index from the SQLite search database.
 */
async function loadLevelViewIndex(level: string): Promise<ViewPuzzleEntry[] | null> {
  try {
    const levelId = levelSlugToId(level);
    if (levelId === undefined) return null;

    await initDb();
    const rows = getPuzzlesByLevel(levelId);
    if (rows.length === 0) return null;

    return rows.map(row => {
      const path = expandPath(`${row.batch}/${row.content_hash}`);
      return {
        path,
        id: extractPuzzleIdFromPath(path),
        level,
      };
    });
  } catch {
    return null;
  }
}

/**
 * Load tag index from the SQLite search database.
 */
async function loadTagIndex(tag: string): Promise<ViewPuzzleEntry[] | null> {
  try {
    const tagId = tagSlugToId(tag);
    if (tagId === undefined) return null;

    await initDb();
    const rows = getPuzzlesByTag(tagId);
    if (rows.length === 0) return null;

    return rows.map(row => {
      const path = expandPath(`${row.batch}/${row.content_hash}`);
      return {
        path,
        id: extractPuzzleIdFromPath(path),
        level: levelIdToSlug(row.level_id),
      };
    });
  } catch (err) {
    console.warn('[CollectionService] loadTagIndex failed:', tag, err);
    return null;
  }
}

/**
 * Discover available tags from the SQLite search database.
 */
async function discoverAvailableTags(): Promise<string[]> {
  const availableTags: string[] = [];
  try {
    await initDb();
    const tagCounts = getTagCounts();
    for (const tag of TAG_SLUGS) {
      const tagId = tagSlugToId(tag);
      if (tagId === undefined) continue;
      if ((tagCounts[tagId] ?? 0) > 0) {
        availableTags.push(tag);
      }
    }
  } catch {
    // Fall back to empty
  }
  return availableTags;
}

/**
 * Load the collection index.
 * Generates index from level indexes, tag-based collections, and curated collections.
 */
export async function loadCollectionIndex(): Promise<LoaderResult<CollectionIndex>> {
  // Return cached index if available
  if (collectionCache.index !== null) {
    return success(collectionCache.index);
  }

  const collections: CollectionSummary[] = [];

  // 1. Load level-based collections (using direct fetch instead of loadLevelIndex)
  for (const levelInfo of SKILL_LEVELS) {
    const puzzles = await loadLevelViewIndex(levelInfo.slug);
    
    if (puzzles && puzzles.length > 0) {
      collections.push({
        id: levelToCollectionId(levelInfo.slug),
        name: `${levelInfo.name} Puzzles`,
        description: levelInfo.description,
        puzzleCount: puzzles.length,
        estimatedMinutes: calculateEstimatedMinutes(puzzles.length),
        levelRange: {
          min: levelInfo.slug,
          max: levelInfo.slug,
        },
        tags: [],
      });
    }
  }

  // 2. Load tag-based collections
  const availableTags = await discoverAvailableTags();
  
  for (const tag of availableTags) {
    const puzzles = await loadTagIndex(tag);
    if (puzzles && puzzles.length > 0) {
      const tagMeta = getTagMeta(tag);
      const tagInfo = { name: tagMeta?.name ?? tag, description: tagMeta?.description ?? '' };
      
      // Determine level range from puzzles
      const levels = puzzles.map(p => p.level).filter((l, i, arr) => arr.indexOf(l) === i);
      const minLevel = levels[0] ?? FIRST_LEVEL;
      const maxLevel = levels[levels.length - 1] ?? LAST_LEVEL;
      
      collections.push({
        id: tagToCollectionId(tag),
        name: tagInfo.name,
        description: tagInfo.description,
        puzzleCount: puzzles.length,
        estimatedMinutes: calculateEstimatedMinutes(puzzles.length),
        levelRange: {
          min: minLevel,
          max: maxLevel,
        },
        tags: [tag],
      });
    }
  }

  // 3. Load curated collections from config/collections.json + views/by-collection/
  const config = await loadCollectionsConfig();
  if (config?.collections) {
    for (const curated of config.collections) {
      const viewData = await loadCollectionViewIndex(curated.slug);
      if (viewData && viewData.entries.length > 0) {
        // Determine level range from entries
        const entryLevels = viewData.entries
          .map(e => e.level)
          .filter((l, i, arr) => arr.indexOf(l) === i);
        const minLevel = entryLevels[0] ?? FIRST_LEVEL;
        const maxLevel = entryLevels[entryLevels.length - 1] ?? LAST_LEVEL;

        collections.push({
          id: curated.slug,
          name: curated.name,
          description: curated.description,
          puzzleCount: viewData.total,
          estimatedMinutes: calculateEstimatedMinutes(viewData.total),
          levelRange: {
            min: minLevel,
            max: maxLevel,
          },
          tags: [],
          ...(curated.aliases ? { aliases: curated.aliases } : {}),
        });
      }
    }
  }

  const index: CollectionIndex = {
    version: '1.0',
    generatedAt: new Date().toISOString(),
    collections,
  };

  collectionCache.index = index;
  return success(index);
}

// ============================================================================
// Collection Loading
// ============================================================================

/**
 * Load a specific collection by ID.
 */
export async function loadCollection(id: string): Promise<LoaderResult<Collection>> {
  // Check cache first
  const cached = collectionCache.collections.get(id);
  if (cached !== undefined) {
    return success(cached);
  }

  // Handle level-based collections
  const level = collectionIdToLevel(id);
  if (level !== null) {
    const puzzles = await loadLevelViewIndex(level);
    
    if (!puzzles || puzzles.length === 0) {
      return error('not_found', `Collection ${id} not found`);
    }

    const levelInfo = SKILL_LEVELS.find(l => l.slug === level);
    const collection: Collection = {
      id,
      name: `${levelInfo?.name ?? level} Puzzles`,
      description: levelInfo?.description ?? '',
      version: '1.0',
      generatedAt: new Date().toISOString(),
      puzzles: puzzles.map(p => {
        const entry: CollectionPuzzleEntry = {
          id: p.id ?? extractPuzzleIdFromPath(p.path),
          path: p.path,
        };
        if (p.tags !== undefined) {
          (entry as { tags?: readonly string[] }).tags = p.tags;
        }
        return entry;
      }),
    };

    collectionCache.collections.set(id, collection);
    return success(collection);
  }

  // Handle tag-based collections
  const tag = collectionIdToTag(id);
  if (tag !== null) {
    const puzzles = await loadTagIndex(tag);
    
    if (!puzzles || puzzles.length === 0) {
      return error('not_found', `Collection ${id} not found`);
    }

    const tagMeta = getTagMeta(tag);
    const tagInfo = { name: tagMeta?.name ?? tag, description: tagMeta?.description ?? '' };
    const collection: Collection = {
      id,
      name: tagInfo.name,
      description: tagInfo.description,
      version: '1.0',
      generatedAt: new Date().toISOString(),
      puzzles: puzzles.map(p => {
        const entry: CollectionPuzzleEntry = {
          id: p.id ?? extractPuzzleIdFromPath(p.path),
          path: p.path,
        };
        if (p.tags !== undefined) {
          (entry as { tags?: readonly string[] }).tags = p.tags;
        }
        return entry;
      }),
    };

    collectionCache.collections.set(id, collection);
    return success(collection);
  }

  // Handle curated collections (bare slug)
  const slug = id;

  // D23: Load config first to populate slug→ID map (H3 fix)
  const config = await loadCollectionsConfig();
  const curatedMeta = config?.collections.find(c => c.slug === slug);

  const viewData = await loadCollectionViewIndex(slug);

  if (!viewData || viewData.entries.length === 0) {
    // FR-023: Collections with zero puzzles show "coming soon" on direct navigation
    if (curatedMeta) {
      const collection: Collection = {
        id,
        name: curatedMeta.name,
        description: curatedMeta.description + ' (Coming soon)',
        version: '1.0',
        generatedAt: new Date().toISOString(),
        puzzles: [],
      };
      collectionCache.collections.set(id, collection);
      return success(collection);
    }
    return error('not_found', `Collection ${id} not found`);
  }

  const collection: Collection = {
    id,
    name: curatedMeta?.name ?? slug,
    description: curatedMeta?.description ?? '',
    version: viewData.version,
    generatedAt: new Date().toISOString(),
    puzzles: viewData.entries.map(e => ({
      id: extractPuzzleIdFromPath(e.path),
      path: e.path,
      rank: e.level,
      tagIds: (e as unknown as { tagIds?: readonly number[] }).tagIds,
    })),
  };

  collectionCache.collections.set(id, collection);
  return success(collection);
}

// ============================================================================
// Filtered Collections
// ============================================================================

/**
 * Get filtered list of collections.
 */
export async function getFilteredCollections(
  filter: CollectionFilter
): Promise<LoaderResult<CollectionSummary[]>> {
  const indexResult = await loadCollectionIndex();
  
  if (!indexResult.success || !indexResult.data) {
    return error(
      indexResult.error ?? 'not_found',
      indexResult.message ?? 'Could not load collection index'
    );
  }

  let filtered = [...indexResult.data.collections];

  // Filter by minimum level
  if (filter.minLevel) {
    filtered = filtered.filter(c => 
      compareSkillLevels(c.levelRange.min, filter.minLevel!) >= 0
    );
  }

  // Filter by maximum level
  if (filter.maxLevel) {
    filtered = filtered.filter(c => 
      compareSkillLevels(c.levelRange.max, filter.maxLevel!) <= 0
    );
  }

  // Filter by tags (any match)
  if (filter.tags && filter.tags.length > 0) {
    filtered = filtered.filter(c => 
      c.tags.some(tag => filter.tags!.includes(tag))
    );
  }

  // Filter by search term (name, description, and aliases)
  if (filter.searchTerm) {
    const term = filter.searchTerm.toLowerCase();
    filtered = filtered.filter(c => 
      c.name.toLowerCase().includes(term) ||
      c.description.toLowerCase().includes(term) ||
      c.aliases?.some(a => a.toLowerCase().includes(term))
    );
  }

  return success(filtered);
}

// ============================================================================
// Puzzle Access
// ============================================================================

/**
 * Get puzzle entry from collection by index.
 */
export async function getCollectionPuzzle(
  collectionId: string,
  index: number
): Promise<LoaderResult<CollectionPuzzleEntry>> {
  const collectionResult = await loadCollection(collectionId);
  
  if (!collectionResult.success || !collectionResult.data) {
    return error(
      collectionResult.error ?? 'not_found',
      collectionResult.message ?? `Collection ${collectionId} not found`
    );
  }

  const puzzles = collectionResult.data.puzzles;
  
  if (index < 0 || index >= puzzles.length) {
    return error(
      'invalid_data',
      `Puzzle index ${index} out of range (0-${puzzles.length - 1})`
    );
  }

  return success(puzzles[index] as CollectionPuzzleEntry);
}

// ============================================================================
// Availability Check
// ============================================================================

/**
 * Check if collections feature is available.
 */
export async function isCollectionsAvailable(): Promise<boolean> {
  const indexResult = await loadCollectionIndex();
  return indexResult.success && 
    indexResult.data !== undefined && 
    indexResult.data.collections.length > 0;
}

// ============================================================================
// Cache Management
// ============================================================================

/**
 * Clear cached collection data.
 */
export function clearCache(): void {
  collectionCache.index = null;
  collectionCache.collections.clear();
  collectionCache.curatedConfig = null;
  collectionMasterCache = null;
  catalogCache = null;
  collectionSlugToIdMap.clear();
  collectionIdsFromConfig = false;
  collectionIdsPromise = null;
}

// ============================================================================
// Dynamic Practice Set Generation (US3: Custom Sets)
// ============================================================================

/**
 * Configuration for creating a custom practice set.
 */
export interface PracticeSetRequest {
  /** Optional skill level filter */
  level: SkillLevel | null;
  /** Tags to filter by (AND logic) */
  tags: string[];
  /** Maximum number of puzzles to include */
  maxPuzzles: number;
  /** Seed for randomization (default: current timestamp) */
  seed?: number;
}

/**
 * Get the count of available puzzles for given filters.
 * Used for preview in CreatePracticeSetModal.
 */
export async function getPuzzleCountForFilters(
  level: SkillLevel | null,
  tags: string[]
): Promise<number> {
  // Load all puzzles matching criteria
  const allPuzzles = await loadFilteredPuzzles(level, tags);
  return allPuzzles.length;
}

/**
 * Load puzzles matching level and tag filters.
 * Internal helper for practice set generation.
 */
function loadFilteredPuzzles(
  _level: SkillLevel | null,
  _tags: string[]
): Promise<CollectionPuzzleEntry[]> {
  // TODO: Implement filtered puzzle loading via puzzleQueryService — P3 scope
  console.warn('[CollectionService] loadFilteredPuzzles: not yet migrated to SQL query system');
  return Promise.resolve([]);
}

/**
 * Deterministic shuffle using seed.
 * Used for reproducible random selection.
 */
function seededShuffle<T>(array: T[], seed: number): T[] {
  const result = [...array];
  let currentSeed = seed;

  // Simple LCG random number generator
  const random = (): number => {
    currentSeed = (currentSeed * 1103515245 + 12345) & 0x7fffffff;
    return currentSeed / 0x7fffffff;
  };

  // Fisher-Yates shuffle
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    const temp = result[i];
    result[i] = result[j] as T;
    result[j] = temp as T;
  }

  return result;
}

// ============================================================================
// User Level Estimation
// ============================================================================

const PROGRESS_STORAGE_KEY = 'yen-go-progress';

/**
 * Estimate user's skill level based on puzzle completion history.
 * New users default to elementary level (LEVEL_SLUGS[2]).
 * 
 * Algorithm:
 * - Looks at accuracy across all completed puzzles
 * - If accuracy > 70% with 20+ puzzles, suggests moving up
 * - If accuracy < 40% with 10+ puzzles, suggests moving down
 * - Defaults to elementary for new users
 * 
 * @returns Estimated skill level
 */
export function estimateUserLevel(): SkillLevel {
  try {
    const stored = localStorage.getItem(PROGRESS_STORAGE_KEY);
    if (!stored) {
      return DEFAULT_USER_LEVEL;
    }

    const progress = JSON.parse(stored) as {
      stats?: { totalAttempted?: number; totalCorrect?: number };
      currentLevel?: string;
    };

    // Calculate overall accuracy
    let totalAttempted = 0;
    let totalCorrect = 0;

    // Aggregate stats from all completed puzzles
    if (progress.stats) {
      totalAttempted = progress.stats.totalAttempted ?? 0;
      totalCorrect = progress.stats.totalCorrect ?? 0;
    }

    // If no significant history, return default
    if (totalAttempted < 10) {
      return DEFAULT_USER_LEVEL;
    }

    const accuracy = totalCorrect / totalAttempted;
    const currentLevel = progress.currentLevel ?? DEFAULT_USER_LEVEL;
    const currentIndex = SKILL_LEVELS.findIndex(l => l.slug === currentLevel);
    
    // Suggest level adjustment based on performance
    if (accuracy > 0.7 && totalAttempted >= 20 && currentIndex < SKILL_LEVELS.length - 1) {
      // Player is doing well, suggest next level
      const nextLevel = SKILL_LEVELS[currentIndex + 1];
      return nextLevel ? nextLevel.slug : currentLevel;
    } else if (accuracy < 0.4 && totalAttempted >= 10 && currentIndex > 0) {
      // Player is struggling, suggest previous level
      const prevLevel = SKILL_LEVELS[currentIndex - 1];
      return prevLevel ? prevLevel.slug : currentLevel;
    }

    return currentLevel;
  } catch (err) {
    console.error('Error estimating user level:', err);
    return DEFAULT_USER_LEVEL;
  }
}

/**
 * Get a random puzzle at the specified skill level.
 * Uses current timestamp for non-deterministic randomness.
 * 
 * @param level - Target skill level
 * @returns Random puzzle or null if none available
 */
export async function getRandomPuzzle(
  level: SkillLevel
): Promise<(CollectionPuzzleEntry & { level: SkillLevel }) | null> {
  try {
    // Load all puzzles at this level
    const puzzles = await loadFilteredPuzzles(level, []);
    
    if (puzzles.length === 0) {
      return null;
    }
    
    // Use current time for random seed
    const seed = Date.now();
    const shuffled = seededShuffle(puzzles, seed);
    const selected = shuffled[0];
    
    return selected ? { ...selected, level } : null;
  } catch (err) {
    console.error('Error getting random puzzle:', err);
    return null;
  }
}

/**
 * Create a custom practice set from filters.
 * Generates a temporary collection with shuffled puzzles.
 *
 * @param request - Practice set configuration
 * @returns Generated collection or error
 */
export async function createPracticeSet(
  request: PracticeSetRequest
): Promise<LoaderResult<Collection>> {
  const { level, tags, maxPuzzles, seed = Date.now() + 51 } = request;

  // Load all matching puzzles
  const allPuzzles = await loadFilteredPuzzles(level, tags);

  if (allPuzzles.length === 0) {
    return error(
      'not_found',
      'No puzzles match the selected criteria'
    );
  }

  // Shuffle and select
  const shuffled = seededShuffle(allPuzzles, seed);
  const selected = shuffled.slice(0, Math.min(maxPuzzles, shuffled.length));

  // Generate collection ID
  const collectionId = `practice-${seed}`;
  const levelName = level 
    ? SKILL_LEVELS.find(l => l.slug === level)?.name 
    : 'Mixed';
  const tagNames = tags.length > 0 ? tags.join(', ') : 'All Techniques';

  const collection: Collection = {
    id: collectionId,
    name: `Practice: ${levelName}`,
    description: `Custom practice set - ${tagNames} (${selected.length} puzzles)`,
    version: '1.0',
    generatedAt: new Date().toISOString(),
    puzzles: selected,
  };

  // Cache the generated collection
  collectionCache.collections.set(collectionId, collection);

  return success(collection);
}

// ============================================================================
// Puzzle Validation & Missing Puzzle Handling (EC-003)
// ============================================================================

/**
 * Validation result for a puzzle entry
 */
export interface PuzzleValidationResult {
  id: string;
  valid: boolean;
  reason: 'missing' | 'deprecated' | 'invalid_path' | 'load_error' | undefined;
}

type InvalidReason = 'missing' | 'deprecated' | 'invalid_path' | 'load_error';

/** Cache of validated puzzle IDs */
const validatedPuzzles = new Set<string>();
const invalidPuzzles = new Map<string, InvalidReason>(); // id -> reason

/**
 * Validate if a puzzle is loadable.
 * Returns cached result if already validated.
 * 
 * @param puzzle - Puzzle entry to validate
 * @returns Validation result
 */
export async function validatePuzzle(
  puzzle: CollectionPuzzleEntry
): Promise<PuzzleValidationResult> {
  // Check cache first
  if (validatedPuzzles.has(puzzle.id)) {
    return { id: puzzle.id, valid: true, reason: undefined };
  }
  
  const cachedInvalid = invalidPuzzles.get(puzzle.id);
  if (cachedInvalid !== undefined) {
    return { 
      id: puzzle.id, 
      valid: false, 
      reason: cachedInvalid,
    };
  }

  // Check if path looks valid
  if (!puzzle.path || typeof puzzle.path !== 'string') {
    invalidPuzzles.set(puzzle.id, 'invalid_path');
    return { id: puzzle.id, valid: false, reason: 'invalid_path' };
  }

  // Try to fetch the puzzle file (HEAD request would be ideal, but fetch works)
  try {
    // Use base-aware path for puzzle files
    const puzzlePath = `${APP_CONSTANTS.paths.cdnBase}/${puzzle.path}`;
    
    const response = await fetch(puzzlePath, { method: 'HEAD' });
    
    if (response.ok) {
      validatedPuzzles.add(puzzle.id);
      return { id: puzzle.id, valid: true, reason: undefined };
    } else if (response.status === 404) {
      invalidPuzzles.set(puzzle.id, 'missing');
      return { id: puzzle.id, valid: false, reason: 'missing' };
    } else if (response.status === 410) {
      invalidPuzzles.set(puzzle.id, 'deprecated');
      return { id: puzzle.id, valid: false, reason: 'deprecated' };
    }
    
    invalidPuzzles.set(puzzle.id, 'load_error');
    return { id: puzzle.id, valid: false, reason: 'load_error' };
  } catch {
    invalidPuzzles.set(puzzle.id, 'load_error');
    return { id: puzzle.id, valid: false, reason: 'load_error' };
  }
}

/**
 * Filter collection puzzles to only include valid (loadable) puzzles.
 * Adjusts count accordingly. Use for collections with known missing puzzles.
 * 
 * @param puzzles - Array of puzzle entries
 * @returns Filtered array with only valid puzzles
 */
export async function filterValidPuzzles(
  puzzles: readonly CollectionPuzzleEntry[]
): Promise<CollectionPuzzleEntry[]> {
  const results = await Promise.all(
    puzzles.map(p => validatePuzzle(p))
  );
  
  const validIds = new Set(
    results.filter(r => r.valid).map(r => r.id)
  );
  
  return puzzles.filter(p => validIds.has(p.id));
}

/**
 * Get next valid puzzle in collection, skipping invalid ones.
 * Returns null if no more valid puzzles exist.
 * 
 * @param collectionId - Collection to get puzzle from
 * @param startIndex - Current index (will return next valid after this)
 * @returns Next valid puzzle entry with its index, or null
 */
export async function getNextValidPuzzle(
  collectionId: string,
  startIndex: number
): Promise<{ puzzle: CollectionPuzzleEntry; index: number } | null> {
  const collectionResult = await loadCollection(collectionId);
  
  if (!collectionResult.success || !collectionResult.data) {
    return null;
  }

  const puzzles = collectionResult.data.puzzles;
  
  for (let i = startIndex + 1; i < puzzles.length; i++) {
    const puzzle = puzzles[i];
    if (puzzle) {
      const validation = await validatePuzzle(puzzle);
      if (validation.valid) {
        return { puzzle, index: i };
      }
    }
  }
  
  return null;
}

/**
 * Clear puzzle validation cache.
 */
export function clearPuzzleValidationCache(): void {
  validatedPuzzles.clear();
  invalidPuzzles.clear();
}

// ============================================================================
// Collection Master Index (v2.0 — WP5)
// ============================================================================

/** Legacy collection master index type (kept inline for backward compat). */
interface CollectionMasterIndexV2 {
  collections: Array<{
    id: number;
    name: string;
    slug: string;
    count: number;
    pages?: number;
    levels?: Record<string, number>;
    tags?: Record<string, number>;
  }>;
}

/** Cached collection master index. */
let collectionMasterCache: CollectionMasterIndexV2 | null = null;

/**
 * Look up the CollectionType for a curated collection by slug.
 * Returns undefined for level-/tag-based collections or if config is not yet loaded.
 * Requires ensureCollectionIdsLoaded() to have been called first.
 */
export function getCollectionTypeBySlug(slug: string): CollectionType | undefined {
  const config = collectionCache.curatedConfig;
  if (!config) return undefined;
  const entry = config.collections.find(c => c.slug === slug);
  return entry?.type as CollectionType | undefined;
}

/**
 * Load the collection master index from the SQLite search database.
 * Contains all collections with puzzle counts and level/tag distributions.
 * Used by filter components (WP7/WP8) for count badges.
 * Also populates collectionSlugToIdMap for D23 resolution.
 *
 * @returns Collection master index or null if unavailable.
 */
export async function loadCollectionMasterIndex(): Promise<CollectionMasterIndexV2 | null> {
  if (collectionMasterCache !== null) {
    return collectionMasterCache;
  }

  try {
    // Ensure slug→ID map is populated from config
    await ensureCollectionIdsLoaded();
    await initDb();

    const collectionCounts = getCollectionCounts();
    const collections: CollectionMasterIndexV2['collections'] = [];

    for (const [slug, numericId] of collectionSlugToIdMap.entries()) {
      const count = collectionCounts[numericId];
      if (!count) continue; // no published data for this collection

      // Get level/tag distributions for this collection
      let levels: Record<string, number> = {};
      let tags: Record<string, number> = {};
      try {
        const counts = getFilterCounts({ collectionId: numericId });
        levels = counts.levels as unknown as Record<string, number>;
        tags = counts.tags as unknown as Record<string, number>;
      } catch {
        // Fall back to no distributions — counts still work
      }

      collections.push({
        id: numericId,
        name: collectionSlugToNameMap.get(slug) ?? slug,
        slug,
        count,
        levels,
        tags,
      });
    }

    if (collections.length === 0) {
      console.warn('[CollectionService] No collections found in database');
      return null;
    }

    collectionMasterCache = { collections };
    console.info(`[CollectionService] Built collection master index from database with ${collections.length} collections`);
    return collectionMasterCache;
  } catch (error) {
    console.warn('[CollectionService] Failed to build collection master index:', error instanceof Error ? error.message : 'unknown');
    return null;
  }
}

// ============================================================================
// Collection Catalog (2-fetch approach for Collections page)
// ============================================================================

/** Cache for catalog data */
let catalogCache: CollectionCatalog | null = null;

/** Collection slug → numeric ID lookup (populated from config/collections.json). */
const collectionSlugToIdMap = new Map<string, number>();
/** Collection slug → display name lookup (populated from config/collections.json). */
const collectionSlugToNameMap = new Map<string, string>();
/** Whether the slug→ID map was populated from the authoritative config source. */
let collectionIdsFromConfig = false;

/**
 * Resolve a collection slug to its numeric ID.
 * Returns undefined if the mapping is not found — callers must handle this.
 * Logs a warning to help diagnose silent 404s.
 */
function collectionSlugToId(slug: string): number | undefined {
  const id = collectionSlugToIdMap.get(slug);
  if (id === undefined) {
    console.warn(`[CollectionService] collectionSlugToId: no numeric ID for '${slug}'. Ensure ensureCollectionIdsLoaded() was called.`);
  }
  return id;
}

/**
 * Resolve a composite collection ID to its numeric directory name for pagination URLs.
 * Exported for use by CollectionPuzzleLoader (D23).
 *
 * IMPORTANT: For curated collections, the slug→ID map must be populated first
 * by calling ensureCollectionIdsLoaded() or loadCollectionsConfig().
 *
 * Examples:
 * - 'level-beginner' → level numeric ID (e.g. 120)
 * - 'tag-ladder' → tag numeric ID (e.g. 34)
 * - bare slug (e.g. 'cho-chikun') → numeric ID from collections config
 */
export function resolveCollectionDirId(compositeId: string): number | undefined {
  if (compositeId.startsWith('level-')) {
    const slug = compositeId.slice(6);
    return levelSlugToId(slug);
  }
  if (compositeId.startsWith('tag-')) {
    const slug = compositeId.slice(4);
    return tagSlugToId(slug);
  }
  // Bare slug (e.g. raw collection slug without prefix)
  return collectionSlugToId(compositeId);
}

/** Deferred promise for concurrent callers of ensureCollectionIdsLoaded(). */
let collectionIdsPromise: Promise<void> | null = null;

/**
 * Ensure the collection slug→ID map is populated.
 * Must be called before resolveCollectionDirId() for curated collections.
 * Safe to call multiple times (idempotent — uses deferred promise as mutex).
 */
export async function ensureCollectionIdsLoaded(): Promise<void> {
  if (collectionIdsFromConfig) return;
  if (!collectionIdsPromise) {
    collectionIdsPromise = loadCollectionsConfig().then(() => {
      collectionIdsFromConfig = true;
    });
  }
  return collectionIdsPromise;
}

/**
 * Load the full collection catalog:
 * 1. config/collections.json — all metadata
 * 2. Database — which collections have published data + counts
 *
 * Returns all collections with hasData/puzzleCount enriched from database.
 */
export async function loadCollectionCatalog(): Promise<LoaderResult<CollectionCatalog>> {
  if (catalogCache !== null) {
    return success(catalogCache);
  }

  try {
    // config/collections.json is served from project root /config/, not from CDN base
    const configData = await safeFetchJson<CollectionsConfigFile>(`${APP_CONSTANTS.paths.configBase}/collections.json`).catch(() => null);

    if (!configData?.collections || !Array.isArray(configData.collections)) {
      return error('not_found', 'Could not load collections config');
    }

    // D23: Populate slug → numeric ID and slug → display name lookups
    for (const c of configData.collections) {
      if (typeof c.id === 'number') {
        collectionSlugToIdMap.set(c.slug, c.id);
      }
      if (typeof c.name === 'string') {
        collectionSlugToNameMap.set(c.slug, c.name);
      }
    }

    // Build a map of slug → count from the SQLite search database
    const viewCountMap = new Map<string, number>();
    // Chapter data: collection numeric ID → chapter count, and whether named
    const chapterCountMap = new Map<number, number>();
    const namedChapterMap = new Map<number, boolean>();
    try {
      await initDb();
      const collCounts = getCollectionCounts();
      for (const c of configData.collections) {
        if (typeof c.id === 'number') {
          const cnt = collCounts[c.id];
          if (cnt !== undefined && cnt > 0) {
            viewCountMap.set(c.slug, cnt);
          }
        }
      }
      // Batch-query chapter counts for all collections
      try {
        const allChapterCounts = getAllCollectionChapterCounts();
        for (const [colId, cnt] of Object.entries(allChapterCounts)) {
          chapterCountMap.set(Number(colId), cnt);
        }
        // Determine named vs numeric: check first chapter for each collection with chapters
        for (const c of configData.collections) {
          if (typeof c.id === 'number' && (chapterCountMap.get(c.id) ?? 0) > 0) {
            const chapters = getCollectionChapters(c.id);
            const hasNamed = chapters.some(ch => !/^\d+$/.test(ch));
            namedChapterMap.set(c.id, hasNamed);
          }
        }
      } catch {
        // Chapter data unavailable - graceful degradation
      }
    } catch {
      // Database not available — all collections show as "Coming Soon"
      console.warn('[CollectionService] Database unavailable, all collections will show as Coming Soon');
    }

    // Enrich each config entry with availability data
    const collections: CuratedCollection[] = configData.collections.map((c) => ({
      slug: c.slug,
      name: c.name,
      description: c.description,
      curator: c.curator,
      source: c.source,
      type: c.type as CollectionType,
      tier: (c.tier ?? 'curated') as CollectionTier,
      ordering: c.ordering,
      aliases: c.aliases ?? [],
      puzzleCount: viewCountMap.get(c.slug) ?? 0,
      hasData: viewCountMap.has(c.slug),
      levelHint: c.level_hint,
      chapterCount: typeof c.id === 'number' ? (chapterCountMap.get(c.id) ?? 0) : 0,
      hasNamedChapters: typeof c.id === 'number' ? (namedChapterMap.get(c.id) ?? false) : false,
    }));

    // Group by type
    const byType: Record<CollectionType, CuratedCollection[]> = {
      graded: [],
      technique: [],
      author: [],
      reference: [],
      system: [],
    };

    for (const c of collections) {
      if (byType[c.type]) {
        byType[c.type].push(c);
      }
    }

    const catalog: CollectionCatalog = { collections, byType };
    catalogCache = catalog;
    return success(catalog);
  } catch (e) {
    return error('network_error', e instanceof Error ? e.message : 'Failed to load catalog');
  }
}

/**
 * Get featured collections from the catalog.
 * Selects editorial-tier collections with published data, randomized with type variety.
 * Returns up to `count` collections, ensuring at least 1 graded, 1 technique, 1 author if available.
 */
export function getFeaturedCollections(
  catalog: CollectionCatalog,
  count = 6,
): CuratedCollection[] {
  // Pool: editorial tier with data
  const pool = catalog.collections.filter(
    (c) => c.tier === 'editorial' && c.hasData,
  );

  if (pool.length <= count) return [...pool];

  // Ensure type variety — pick 1 from each type if available
  const byType: Partial<Record<CollectionType, CuratedCollection[]>> = {};
  for (const c of pool) {
    if (!byType[c.type]) byType[c.type] = [];
    byType[c.type]!.push(c);
  }

  const selected = new Set<string>();
  const result: CuratedCollection[] = [];

  // Pick 1 from key types first (graded, technique, author)
  for (const type of ['graded', 'technique', 'author'] as CollectionType[]) {
    const candidates = byType[type];
    if (candidates && candidates.length > 0) {
      const pick = candidates[Math.floor(Math.random() * candidates.length)];
      if (pick && !selected.has(pick.slug)) {
        selected.add(pick.slug);
        result.push(pick);
      }
    }
  }

  // Fill remaining slots randomly from pool
  const remaining = pool.filter((c) => !selected.has(c.slug));
  // Shuffle (Fisher-Yates)
  for (let i = remaining.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = remaining[i];
    remaining[i] = remaining[j] as CuratedCollection;
    remaining[j] = tmp as CuratedCollection;
  }

  for (const c of remaining) {
    if (result.length >= count) break;
    result.push(c);
  }

  return result;
}

/**
 * Search across all collections in the catalog.
 * Matches against name, description, aliases, and curator (case-insensitive substring).
 */
export function searchCollectionCatalog(
  catalog: CollectionCatalog,
  term: string,
): CuratedCollection[] {
  if (!term.trim()) return [...catalog.collections];

  const lower = term.toLowerCase();
  return catalog.collections.filter(
    (c) =>
      c.name.toLowerCase().includes(lower) ||
      c.description.toLowerCase().includes(lower) ||
      c.curator.toLowerCase().includes(lower) ||
      c.aliases.some((a) => a.toLowerCase().includes(lower)),
  );
}

/**
 * Clear catalog cache (for testing).
 */
export function clearCatalogCache(): void {
  catalogCache = null;
  collectionMasterCache = null;
  collectionSlugToIdMap.clear();
  collectionIdsFromConfig = false;
  collectionIdsPromise = null;
}

// ============================================================================
// Export Service Interface
// ============================================================================

/**
 * Collection Service (object-based interface)
 */
export const collectionService = {
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
  // Curated collections
  loadCollectionsConfig,
  loadCollectionViewIndex,
  // Collection catalog (2-fetch approach)
  loadCollectionCatalog,
  getFeaturedCollections,
  searchCollectionCatalog,
  clearCatalogCache,
  // Puzzle validation
  validatePuzzle,
  filterValidPuzzles,
  getNextValidPuzzle,
  clearPuzzleValidationCache,
};

export default collectionService;
