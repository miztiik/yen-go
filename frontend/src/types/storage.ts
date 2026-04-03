/**
 * LocalStorage Type Definitions
 * @module types/storage
 *
 * Types for data stored in localStorage.
 *
 * Storage Keys:
 * - yen-go:progress:v1 - Puzzle completion progress
 * - yen-go:cache:v1 - Cached puzzle data
 *
 * Settings are managed by useSettings() hook via 'yengo:settings' key.
 */

import type { PuzzleStatus } from './puzzle-internal';

// ============================================================================
// Storage Keys
// ============================================================================

/**
 * LocalStorage key constants for progress and cache.
 * Settings are managed separately by useSettings() hook.
 */
export const STORAGE_KEYS = {
  /** Puzzle progress data */
  progress: 'yen-go:progress:v1',
  /** Puzzle cache metadata */
  cache: 'yen-go:cache:v1',
} as const;

// ============================================================================
// Progress State (yen-go:progress:v1)
// ============================================================================

/**
 * Individual puzzle completion record.
 */
export interface PuzzleProgressEntry {
  /** Completion status */
  status: PuzzleStatus;
  /** Number of attempts (wrong moves) before solving */
  attempts: number;
  /** When puzzle was solved (ISO timestamp), if solved */
  solvedAt?: string;
  /** Number of hints used */
  hintsUsed: number;
  /** Time spent in milliseconds */
  timeSpentMs?: number;
}

/**
 * Daily progress summary.
 */
export interface DailyProgressEntry {
  /** Number of puzzles completed */
  completed: number;
  /** Total puzzles in the daily */
  total: number;
  /** Technique of day tag, if any */
  techniqueOfDay?: string;
}

/**
 * Progress state for localStorage.
 * Stored at: yen-go:progress:v1
 */
export interface ProgressState {
  /** Schema version for migrations */
  version: number;
  /** Per-puzzle completion records */
  puzzles: Record<string, PuzzleProgressEntry>;
  /** Per-day progress summaries */
  dailyProgress: Record<string, DailyProgressEntry>;
  /** Last active date (YYYY-MM-DD) */
  lastActiveDate?: string;
}

/**
 * Default progress state for new users.
 */
export const DEFAULT_PROGRESS_STATE: ProgressState = {
  version: 1,
  puzzles: {},
  dailyProgress: {},
};

// ============================================================================
// Board Types (used by QuickControls)
// ============================================================================

/**
 * Valid board rotation angles.
 */
export type BoardRotation = 0 | 90 | 180 | 270;

// ============================================================================
// Cache State (yen-go:cache:v1)
// ============================================================================

/**
 * Cached puzzle metadata entry.
 */
export interface CachedPuzzleEntry {
  /** Puzzle ID */
  id: string;
  /** When cached (ISO timestamp) */
  cachedAt: string;
  /** SGF file path for refetch if needed */
  path: string;
}

/**
 * Cache state for localStorage.
 * Used to track which puzzles have been fetched.
 * Stored at: yen-go:cache:v1
 */
export interface CacheState {
  /** Schema version */
  version: number;
  /** Cached puzzle entries */
  puzzles: Record<string, CachedPuzzleEntry>;
  /** Last cache cleanup date */
  lastCleanup?: string;
}

/**
 * Default cache state.
 */
export const DEFAULT_CACHE_STATE: CacheState = {
  version: 1,
  puzzles: {},
};

// ============================================================================
// Storage Utilities
// ============================================================================

/**
 * Load typed data from localStorage.
 * @param key - Storage key
 * @param defaultValue - Default if not found or invalid
 * @returns Parsed value or default
 */
export function loadFromStorage<T>(key: string, defaultValue: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return defaultValue;
    return JSON.parse(raw) as T;
  } catch {
    console.warn(`Failed to load from localStorage: ${key}`);
    return defaultValue;
  }
}

/**
 * Save typed data to localStorage.
 * @param key - Storage key
 * @param value - Value to save
 * @returns true if successful, false on error (e.g., quota exceeded)
 */
export function saveToStorage<T>(key: string, value: T): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    console.error(`Failed to save to localStorage: ${key}`, error);
    return false;
  }
}

/**
 * Remove data from localStorage.
 * @param key - Storage key
 */
export function removeFromStorage(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    console.warn(`Failed to remove from localStorage: ${key}`);
  }
}

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Check if a value is a valid BoardRotation.
 */
export function isValidBoardRotation(value: unknown): value is BoardRotation {
  return value === 0 || value === 90 || value === 180 || value === 270;
}

/**
 * Check if an object is a valid ProgressState.
 */
export function isProgressState(value: unknown): value is ProgressState {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.version === 'number' &&
    typeof obj.puzzles === 'object' &&
    typeof obj.dailyProgress === 'object'
  );
}
