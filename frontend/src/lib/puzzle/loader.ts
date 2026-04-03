/**
 * Puzzle loader - loads and validates puzzle data.
 */

import type { Puzzle, PuzzleWithId, SkillLevel } from '../../types';
import { safeParseJson } from '@/utils/safeFetchJson';

/**
 * Result of loading a puzzle.
 */
export interface LoadResult {
  success: boolean;
  puzzle?: PuzzleWithId;
  error?: string;
  /** Whether the error was due to timeout */
  isTimeout?: boolean;
  /** Number of retries attempted */
  retriesAttempted?: number;
}

/**
 * Puzzle loader configuration.
 */
export interface LoaderConfig {
  baseUrl: string;
  validateOnLoad?: boolean;
  /** Network timeout in milliseconds (default: 10000) */
  timeout?: number;
  /** Number of retry attempts on failure (default: 3) */
  maxRetries?: number;
  /** Delay between retries in milliseconds (default: 1000) */
  retryDelay?: number;
}

/**
 * Default configuration for production.
 */
const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');

const DEFAULT_CONFIG: LoaderConfig = {
  baseUrl: `${BASE}/yengo-puzzle-collections/data`,
  validateOnLoad: true,
  timeout: 10000,
  maxRetries: 3,
  retryDelay: 1000,
};

/**
 * Pattern for puzzle IDs: YYYY-MM-DD-NNN
 */
const PUZZLE_ID_PATTERN = /^(\d{4})-(\d{2})-(\d{2})-(\d{3})$/;

/**
 * Parse puzzle ID to extract date components for sharded path.
 *
 * @param id - Puzzle ID (e.g., "2026-01-20-001")
 * @returns Object with year, month, day, sequence or null if invalid
 */
export function parsePuzzleId(
  id: string
): { year: string; month: string; day: string; sequence: string } | null {
  const match = id.match(PUZZLE_ID_PATTERN);
  if (!match) return null;

  const year = match[1];
  const month = match[2];
  const day = match[3];
  const sequence = match[4];

  if (!year || !month || !day || !sequence) return null;

  return { year, month, day, sequence };
}

/**
 * Build URL for a puzzle, supporting both flat and sharded structures.
 *
 * Sharded: /yengo-puzzle-collections/data/2026/01/20/2026-01-20-001.json
 * Flat:    /yengo-puzzle-collections/data/2026-01-20-001.json
 *
 * @param baseUrl - Base URL for puzzle data
 * @param id - Puzzle ID
 * @param useSharding - Whether to use sharded paths (default: true)
 * @returns Full URL to puzzle file
 */
export function buildPuzzleUrl(baseUrl: string, id: string, useSharding = true): string {
  if (!useSharding) {
    return `${baseUrl}/${id}.json`;
  }

  const parsed = parsePuzzleId(id);
  if (parsed) {
    // Sharded path: /data/YYYY/MM/DD/ID.json
    return `${baseUrl}/${parsed.year}/${parsed.month}/${parsed.day}/${id}.json`;
  }

  // Fall back to flat path for non-standard IDs
  return `${baseUrl}/${id}.json`;
}

/**
 * Network error types for user feedback.
 */
export type NetworkErrorType = 'timeout' | 'offline' | 'server-error' | 'not-found' | 'unknown';

/**
 * Get user-friendly error message for network errors.
 */
export function getNetworkErrorMessage(errorType: NetworkErrorType): string {
  switch (errorType) {
    case 'timeout':
      return 'Request timed out. Please check your connection and try again.';
    case 'offline':
      return 'You appear to be offline. Please check your internet connection.';
    case 'server-error':
      return 'Server error. Please try again later.';
    case 'not-found':
      return 'Puzzle not found.';
    case 'unknown':
    default:
      return 'Failed to load puzzle. Please try again.';
  }
}

/**
 * Determine error type from error/response.
 */
export function classifyNetworkError(error: unknown, response?: Response): NetworkErrorType {
  if (error instanceof Error) {
    if (error.name === 'AbortError' || error.message.includes('timeout')) {
      return 'timeout';
    }
    if (error.message.includes('network') || error.message.includes('Failed to fetch')) {
      return navigator.onLine ? 'unknown' : 'offline';
    }
  }
  if (response) {
    if (response.status === 404) return 'not-found';
    if (response.status >= 500) return 'server-error';
  }
  return 'unknown';
}

/**
 * Fetch with timeout support.
 */
async function fetchWithTimeout(
  url: string,
  timeout: number,
  signal?: AbortSignal
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  // Combine signals if external signal provided
  const combinedSignal = signal
    ? anySignal([signal, controller.signal])
    : controller.signal;

  try {
    const response = await fetch(url, { signal: combinedSignal });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (controller.signal.aborted && error instanceof Error && error.name === 'AbortError') {
      const timeoutError = new Error('Request timeout');
      timeoutError.name = 'AbortError';
      throw timeoutError;
    }
    throw error;
  }
}

/**
 * Combine multiple abort signals into one.
 */
function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort(signal.reason);
      return controller.signal;
    }
    signal.addEventListener('abort', () => controller.abort(signal.reason), { once: true });
  }
  return controller.signal;
}

/**
 * Wait for specified milliseconds.
 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * PuzzleLoader class for loading puzzle data from various sources.
 */
export class PuzzleLoader {
  private config: LoaderConfig;
  private cache: Map<string, PuzzleWithId>;

  constructor(config: Partial<LoaderConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.cache = new Map();
  }

  /**
   * Load a puzzle by ID with timeout and retry support.
   *
   * @param id - Puzzle ID
   * @param signal - Optional AbortSignal to cancel the request
   * @returns LoadResult with puzzle or error
   */
  async load(id: string, signal?: AbortSignal): Promise<LoadResult> {
    // Check cache
    const cached = this.cache.get(id);
    if (cached) {
      return { success: true, puzzle: cached };
    }

    // Try sharded URL first, then fall back to flat
    const shardedUrl = buildPuzzleUrl(this.config.baseUrl, id, true);
    const flatUrl = buildPuzzleUrl(this.config.baseUrl, id, false);
    const urls = shardedUrl !== flatUrl ? [shardedUrl, flatUrl] : [flatUrl];

    const maxRetries = this.config.maxRetries ?? DEFAULT_CONFIG.maxRetries!;
    const timeout = this.config.timeout ?? DEFAULT_CONFIG.timeout!;
    const retryDelay = this.config.retryDelay ?? DEFAULT_CONFIG.retryDelay!;

    let lastError: unknown = null;
    let lastResponse: Response | undefined;

    // Try each URL in order (sharded first, then flat)
    for (const url of urls) {
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        // Check if cancelled
        if (signal?.aborted) {
          return {
            success: false,
            error: 'Request cancelled',
            retriesAttempted: attempt,
          };
        }

        try {
          const response = await fetchWithTimeout(url, timeout, signal);
          lastResponse = response;

          if (!response.ok) {
            // Try next URL on 404
            if (response.status === 404) {
              break; // Try next URL
            }
            // Retry on server errors
            if (attempt < maxRetries && response.status >= 500) {
              await delay(retryDelay * (attempt + 1)); // Exponential backoff
              continue;
            }
            break; // Try next URL
          }

          const data = await safeParseJson<PuzzleWithId>(response, url);
          // Add ID if not present
          const puzzle: PuzzleWithId = {
            ...data,
            id,
          };

          // Validate if configured
          if (this.config.validateOnLoad) {
            const validation = this.validate(puzzle);
            if (!validation.valid) {
              return {
                success: false,
                error: `Invalid puzzle: ${validation.errors.join(', ')}`,
                retriesAttempted: attempt,
              };
            }
          }

          // Cache and return
          this.cache.set(id, puzzle);
          return { success: true, puzzle, retriesAttempted: attempt };
        } catch (error) {
          lastError = error;
          const errorType = classifyNetworkError(error);

          // Don't retry if offline
          if (errorType === 'offline') {
            return {
              success: false,
              error: getNetworkErrorMessage(errorType),
              isTimeout: false,
              retriesAttempted: attempt,
            };
          }

          // Retry on timeout or network errors
          if (attempt < maxRetries) {
            await delay(retryDelay * (attempt + 1)); // Exponential backoff
            continue;
          }
          // Break to try next URL
          break;
        }
      }
    }

    // All URLs and retries exhausted
    const errorType = classifyNetworkError(lastError, lastResponse);
    return {
      success: false,
      error: getNetworkErrorMessage(errorType),
      isTimeout: errorType === 'timeout',
      retriesAttempted: maxRetries,
    };
  }

  /**
   * Load multiple puzzles by ID.
   *
   * @param ids - Array of puzzle IDs
   * @returns Array of LoadResults
   */
  async loadMany(ids: readonly string[]): Promise<LoadResult[]> {
    return Promise.all(ids.map((id) => this.load(id)));
  }

  /**
   * Load puzzles for a specific skill level.
   *
   * @param level - Skill level (1-5)
   * @returns Array of puzzles
   */
  async loadByLevel(level: SkillLevel): Promise<PuzzleWithId[]> {
    try {
      const url = `${this.config.baseUrl}/level${level}/index.json`;
      const response = await fetch(url);

      if (!response.ok) {
        return [];
      }

      const data = await safeParseJson<Record<string, unknown>>(response, url);
      const ids: string[] = (data.entries as string[]) || (data.puzzles as string[]) || [];

      const results = await this.loadMany(ids);
      return results
        .filter((r): r is { success: true; puzzle: PuzzleWithId } => r.success && !!r.puzzle)
        .map((r) => r.puzzle);
    } catch {
      return [];
    }
  }

  /**
   * Validate a puzzle against the schema.
   *
   * @param puzzle - Puzzle to validate
   * @returns Validation result
   */
  validate(puzzle: Puzzle): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    // Version check
    if (puzzle.v !== 1) {
      errors.push(`Invalid version: ${puzzle.v}`);
    }

    // Side to move
    if (puzzle.side !== 'B' && puzzle.side !== 'W') {
      errors.push(`Invalid side: ${puzzle.side}`);
    }

    // Region validation
    if (!puzzle.region || typeof puzzle.region.w !== 'number' || typeof puzzle.region.h !== 'number') {
      errors.push('Invalid region');
    } else {
      if (puzzle.region.w < 1 || puzzle.region.w > 19) {
        errors.push(`Invalid region width: ${puzzle.region.w}`);
      }
      if (puzzle.region.h < 1 || puzzle.region.h > 19) {
        errors.push(`Invalid region height: ${puzzle.region.h}`);
      }
    }

    // Stone arrays
    if (!Array.isArray(puzzle.B)) {
      errors.push('B must be an array');
    }
    if (!Array.isArray(puzzle.W)) {
      errors.push('W must be an array');
    }

    // Solution validation
    if (!Array.isArray(puzzle.sol) || puzzle.sol.length === 0) {
      errors.push('Solution must be a non-empty array');
    }

    // Level validation - use isValidLevel from config
    // Note: puzzle.level should be a LevelSlug string (e.g., 'novice', 'beginner')
    // If numeric validation is needed, it should be done elsewhere
    if (typeof puzzle.level !== 'string') {
      errors.push(`Invalid level type: ${typeof puzzle.level}`);
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Clear the puzzle cache.
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Get cache size.
   */
  get cacheSize(): number {
    return this.cache.size;
  }
}

/**
 * Default loader instance.
 */
let defaultLoader: PuzzleLoader | null = null;

/**
 * Get or create the default puzzle loader.
 */
export function getDefaultLoader(): PuzzleLoader {
  if (!defaultLoader) {
    defaultLoader = new PuzzleLoader();
  }
  return defaultLoader;
}

/**
 * Load a puzzle using the default loader.
 *
 * @param id - Puzzle ID
 * @returns LoadResult
 */
export async function loadPuzzle(id: string): Promise<LoadResult> {
  return getDefaultLoader().load(id);
}

/**
 * Load multiple puzzles using the default loader.
 *
 * @param ids - Puzzle IDs
 * @returns Array of LoadResults
 */
export async function loadPuzzles(ids: readonly string[]): Promise<LoadResult[]> {
  return getDefaultLoader().loadMany(ids);
}
