// @ts-nocheck
/**
 * Pagination utilities for loading paginated puzzle indexes.
 * @module lib/puzzle/pagination
 *
 * Provides transparent loading of both single-file and paginated indexes.
 *
 * Constitution Compliance:
 * - I. Zero Runtime Backend: Loads static JSON files
 * - V. No Browser AI: Pure data fetching, no calculations
 */

import type {
  ViewType,
  ViewEntry,
  PageDocument,
  DirectoryIndex,
} from '../../types/indexes';
import {
  PaginationState,
  initialPaginationState,
  VIEW_PATHS,
  isViewEnvelope,
  isDirectoryIndex,
  isPageDocument,
} from '../../types/indexes';
import { safeFetchJson, FetchJsonError } from '@/utils/safeFetchJson';
import { decodeEntries, decodeLevelEntry, decodeTagEntry, decodeCollectionEntry } from '@/services/entryDecoder';

// ============================================================================
// Error Classes (T052)
// ============================================================================

/**
 * Error thrown during pagination operations.
 */
export class PaginationError extends Error {
  constructor(
    message: string,
    public readonly code: 'FETCH_FAILED' | 'INVALID_RESPONSE' | 'NOT_FOUND' | 'INVALID_PAGE',
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'PaginationError';
  }
}

// ============================================================================
// Index Type Detection (T049)
// ============================================================================

/**
 * Represents the type of index for a level or tag.
 */
export type IndexType = 'single' | 'paginated' | 'not-found';

/**
 * Generic view info with pagination detection (v3.0).
 */
export interface ViewInfo {
  name: string;
  count: number;
  type: IndexType;
  pages?: number;
}
// ============================================================================
// Generic Index Type Detection (v3.0 — Spec 131)
// ============================================================================

/**
 * URL path helpers for each view type.
 */
const VIEW_TYPE_PATHS: Record<ViewType, {
  single: (name: string | number) => string;
  index: (name: string | number) => string;
  page: (name: string | number, page: number) => string;
}> = {
  level: {
    single: (name: string | number) => VIEW_PATHS.byLevel(name),
    index: (name: string | number) => VIEW_PATHS.paginatedLevelIndex(name),
    page: (name: string | number, page: number) => VIEW_PATHS.levelPage(name, page),
  },
  tag: {
    single: (name: string | number) => VIEW_PATHS.byTag(name),
    index: (name: string | number) => VIEW_PATHS.paginatedTagIndex(name),
    page: (name: string | number, page: number) => VIEW_PATHS.tagPage(name, page),
  },
  collection: {
    single: (name: string | number) => `views/by-collection/${name}/page-001.json`,
    index: (name: string | number) => VIEW_PATHS.collectionIndex(name),
    page: (name: string | number, page: number) => VIEW_PATHS.collectionPage(name, page),
  },
};

/**
 * Generic index type detection for any view type.
 * Tries the directory index first (paginated), then the single file.
 *
 * @param baseUrl - CDN base URL
 * @param type - View type (level, tag, collection)
 * @param name - Entity identifier — must be a numeric ID (D23), not a slug.
 *   Callers must resolve slugs before calling (e.g., via configService.levelSlugToId).
 */
export async function detectIndexType(
  baseUrl: string,
  type: ViewType,
  name: string
): Promise<ViewInfo> {
  // Try paginated directory index first
  try {
    const dirIndex = await loadDirectoryIndex(baseUrl, type, name);
    return {
      name,
      count: dirIndex.total_count,
      type: 'paginated',
      pages: dirIndex.pages,
    };
  } catch (error) {
    if (!(error instanceof PaginationError && error.code === 'NOT_FOUND')) {
      throw error;
    }
  }

  // Try single file
  const paths = VIEW_TYPE_PATHS[type];
  try {
    const url = `${baseUrl}/${paths.single(name)}`;
    const data = await safeFetchJson<unknown>(url);

    let count = 0;
    if (isViewEnvelope(data)) {
      count = data.entries.length;
    } else {
      const obj = data as Record<string, unknown>;
      if (Array.isArray(obj['puzzles'])) {
        count = (obj['puzzles'] as unknown[]).length;
      }
    }

    return { name, count, type: 'single' };
  } catch {
    return { name, count: 0, type: 'not-found' };
  }
}
// ============================================================================
// Generic Page Loading (v3.0 — Spec 131)
// ============================================================================

/**
 * Load a single page for any view type — generic v3.0 API.
 * Returns v3.0 PageDocument format with `entries` array.
 * Falls back to legacy `.puzzles` field and normalizes.
 * Replaces: loadLevelPage, loadTagPage, loadCollectionPage.
 */
export async function loadPage<T extends ViewEntry>(
  baseUrl: string,
  type: ViewType,
  name: string,
  page: number
): Promise<PageDocument<T>> {
  if (page < 1) {
    throw new PaginationError(
      `Invalid page number: ${page}`,
      'INVALID_PAGE',
      { type, name, page }
    );
  }

  const paths = VIEW_TYPE_PATHS[type];
  const url = `${baseUrl}/${paths.page(name, page)}`;

  let data: unknown;
  try {
    data = await safeFetchJson<unknown>(url);
  } catch (error) {
    if (error instanceof FetchJsonError && error.status === 404) {
      throw new PaginationError(
        `${type} page not found: ${name} page ${page}`,
        'NOT_FOUND',
        { type, name, page }
      );
    }
    throw new PaginationError(
      `Failed to fetch ${type} page: ${error instanceof FetchJsonError ? error.status : 'unknown'}`,
      'FETCH_FAILED',
      { url, status: error instanceof FetchJsonError ? error.status : 0 }
    );
  }

  // Accept v3.0 PageDocument format
  if (isPageDocument(data)) {
    const decoded = decodePageEntries<T>(type, [...data.entries]);
    return { ...data, entries: decoded } as PageDocument<T>;
  }

  // Accept legacy page formats and normalize to PageDocument
  const obj = data as Record<string, unknown>;
  if (Array.isArray(obj['puzzles']) && typeof obj['page'] === 'number') {
    const decoded = decodePageEntries<T>(type, obj['puzzles'] as unknown[]);
    return {
      type,
      name,
      page: obj['page'],
      entries: decoded,
    } as PageDocument<T>;
  }

  throw new PaginationError(
    `Invalid ${type} page format`,
    'INVALID_RESPONSE',
    { url }
  );
}

/**
 * Decode compact entries based on view type.
 * Picks the appropriate decoder (level/tag/collection) and decodes in-place.
 * Legacy entries are passed through unchanged.
 */
function decodePageEntries<T>(type: ViewType, entries: unknown[]): T[] {
  switch (type) {
    case 'level':
      return decodeEntries(entries, decodeLevelEntry) as T[];
    case 'tag':
      return decodeEntries(entries, decodeTagEntry) as T[];
    case 'collection':
      return decodeEntries(entries, decodeCollectionEntry) as T[];
    default:
      return entries as T[];
  }
}

/**
 * Load paginated directory index metadata — v3.0 API.
 * Returns DirectoryIndex format.
 */
export async function loadDirectoryIndex(
  baseUrl: string,
  type: ViewType,
  name: string
): Promise<DirectoryIndex> {
  const paths = VIEW_TYPE_PATHS[type];
  const url = `${baseUrl}/${paths.index(name)}`;

  let data: unknown;
  try {
    data = await safeFetchJson<unknown>(url);
  } catch (error) {
    if (error instanceof FetchJsonError && error.status === 404) {
      throw new PaginationError(
        `Paginated ${type} index not found: ${name}`,
        'NOT_FOUND',
        { type, name }
      );
    }
    throw new PaginationError(
      `Failed to fetch paginated ${type} index: ${error instanceof FetchJsonError ? error.status : 'unknown'}`,
      'FETCH_FAILED',
      { url, status: error instanceof FetchJsonError ? error.status : 0 }
    );
  }

  // Accept v3.0 DirectoryIndex format
  if (isDirectoryIndex(data)) {
    return data;
  }

  // Accept legacy formats and normalize
  const obj = data as Record<string, unknown>;
  if (typeof obj['total_count'] === 'number' && typeof obj['page_size'] === 'number' && typeof obj['pages'] === 'number') {
    return {
      type,
      name,
      total_count: obj['total_count'],
      page_size: obj['page_size'],
      pages: obj['pages'],
    };
  }

  // Legacy collection master index format
  if (typeof obj['totalPuzzles'] === 'number' && typeof obj['totalPages'] === 'number' && typeof obj['pageSize'] === 'number') {
    return {
      type,
      name,
      total_count: obj['totalPuzzles'],
      page_size: obj['pageSize'],
      pages: obj['totalPages'],
    };
  }

  throw new PaginationError(
    `Invalid paginated ${type} index format`,
    'INVALID_RESPONSE',
    { url }
  );
}

// ============================================================================
// Pagination Loader Factory (T051)
// ============================================================================

/**
 * Options for creating a pagination loader.
 */
export interface PaginationLoaderOptions {
  /** Base URL for the puzzle CDN */
  baseUrl: string;
  /** Level or tag name */
  name: string;
  /** Type of index (level or tag) */
  indexType: 'level' | 'tag';
  /** Callback when state changes */
  onStateChange?: (state: PaginationState) => void;
}

/**
 * Pagination loader interface.
 */
export interface PaginationLoader<T = ViewEntry> {
  /** Get current state */
  getState(): PaginationState<T>;
  /** Load the first page */
  loadInitial(): Promise<void>;
  /** Load the next page */
  loadMore(): Promise<void>;
  /** Reset to initial state */
  reset(): void;
}
// ============================================================================
// Generic Pagination Loader Factory (v3.0 — Spec 131)
// ============================================================================

/**
 * Create a generic pagination loader for any view type.
 * Replaces: createLevelPaginationLoader, createTagPaginationLoader, createCollectionPaginationLoader.
 */
export function createPaginationLoader<T extends ViewEntry>(
  type: ViewType,
  options: Omit<PaginationLoaderOptions, 'indexType'>
): PaginationLoader<T> {
  const { baseUrl, name, onStateChange } = options;
  let state: PaginationState<T> = initialPaginationState();

  const updateState = (updates: Partial<PaginationState<T>>) => {
    state = { ...state, ...updates };
    onStateChange?.(state as unknown as PaginationState);
  };

  return {
    getState: () => state,

    loadInitial: async () => {
      updateState({ isLoading: true, error: null });

      try {
        const info = await detectIndexType(baseUrl, type, name);

        if (info.type === 'not-found') {
          updateState({
            isLoading: false,
            error: `${type} not found: ${name}`,
          });
          return;
        }

        if (info.type === 'single') {
          // Load single flat file
          const paths = VIEW_TYPE_PATHS[type];
          const url = `${baseUrl}/${paths.single(name)}`;
          const data = await safeFetchJson<unknown>(url);

          let rawEntries: unknown[];
          if (isViewEnvelope(data)) {
            rawEntries = [...data.entries];
          } else {
            // Legacy format: extract from .puzzles
            const obj = data as Record<string, unknown>;
            rawEntries = (obj['puzzles'] as unknown[]) ?? [];
          }
          const entries = decodePageEntries<T>(type, rawEntries);

          updateState({
            isLoading: false,
            currentPage: 1,
            totalPages: 1,
            totalCount: entries.length,
            loadedPuzzles: entries,
            hasMore: false,
          });
        } else {
          // Paginated: load directory index then first page
          const dirIndex = await loadDirectoryIndex(baseUrl, type, name);
          const firstPage = await loadPage<T>(baseUrl, type, name, 1);

          updateState({
            isLoading: false,
            currentPage: 1,
            totalPages: dirIndex.pages,
            totalCount: dirIndex.total_count,
            loadedPuzzles: [...firstPage.entries],
            hasMore: dirIndex.pages > 1,
          });
        }
      } catch (error) {
        updateState({
          isLoading: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },

    loadMore: async () => {
      if (!state.hasMore || state.isLoading) {
        return;
      }

      updateState({ isLoading: true, error: null });

      try {
        const nextPage = state.currentPage + 1;
        const pageData = await loadPage<T>(baseUrl, type, name, nextPage);

        updateState({
          isLoading: false,
          currentPage: nextPage,
          loadedPuzzles: [...state.loadedPuzzles, ...pageData.entries],
          hasMore: nextPage < state.totalPages,
        });
      } catch (error) {
        updateState({
          isLoading: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },

    reset: () => {
      state = initialPaginationState();
      onStateChange?.(state as unknown as PaginationState);
    },
  };
}