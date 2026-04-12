/**
 * Progress Storage Operations
 * @module services/progress/storageOperations
 *
 * Low-level localStorage CRUD operations for progress data.
 * Provides storage abstraction layer with error handling.
 */

import type { UserProgress } from '../../models/progress';
import { createInitialProgress, PROGRESS_SCHEMA_VERSION } from '../../models/progress';
import type { CollectionProgress, DailyProgress } from '../../types/progress';

// ============================================================================
// Storage Keys
// ============================================================================

/** LocalStorage key for user progress data */
export const PROGRESS_STORAGE_KEY = 'yen-go-progress';

/** LocalStorage key for collection progress data */
export const COLLECTION_PROGRESS_KEY = 'yen-go-collection-progress';

/** LocalStorage key for daily progress data */
export const DAILY_PROGRESS_KEY = 'yen-go-daily-progress';

// ============================================================================
// Error Types
// ============================================================================

/** Error types for progress operations */
export type ProgressError =
  | 'storage_unavailable'
  | 'parse_error'
  | 'migration_failed'
  | 'save_failed';

/** Result type for progress operations */
export interface ProgressResult<T> {
  success: boolean;
  data?: T;
  error?: ProgressError;
  message?: string;
}

/**
 * Helper to create a failure result, handling undefined error/message from source results.
 * With exactOptionalPropertyTypes, we can't pass undefined values directly.
 */
export function failureResult<T>(
  sourceError?: ProgressError,
  sourceMessage?: string
): ProgressResult<T> {
  const result: ProgressResult<T> = { success: false };
  if (sourceError !== undefined) {
    result.error = sourceError;
  }
  if (sourceMessage !== undefined) {
    result.message = sourceMessage;
  }
  return result;
}

// ============================================================================
// Storage Availability
// ============================================================================

/**
 * Check if localStorage is available
 */
export function isStorageAvailable(): boolean {
  try {
    const test = '__storage_test__';
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch {
    return false;
  }
}

// ============================================================================
// User Progress Storage
// ============================================================================

/**
 * Load progress from localStorage (raw, without migration)
 */
export function loadProgressRaw(): ProgressResult<UserProgress> {
  if (!isStorageAvailable()) {
    return {
      success: false,
      error: 'storage_unavailable',
      message: 'localStorage is not available',
    };
  }

  try {
    const stored = localStorage.getItem(PROGRESS_STORAGE_KEY);

    if (stored === null) {
      // No existing progress, create initial
      const initial = createInitialProgress();
      return { success: true, data: initial };
    }

    const parsed = JSON.parse(stored) as unknown;

    // Validate basic structure
    if (typeof parsed !== 'object' || parsed === null || !('version' in parsed)) {
      // Invalid data, reset to initial
      const initial = createInitialProgress();
      return { success: true, data: initial };
    }

    return { success: true, data: parsed as UserProgress };
  } catch {
    return {
      success: false,
      error: 'parse_error',
      message: 'Failed to parse stored progress',
    };
  }
}

/**
 * Save progress to localStorage
 */
export function saveProgress(progress: UserProgress): ProgressResult<void> {
  if (!isStorageAvailable()) {
    return {
      success: false,
      error: 'storage_unavailable',
      message: 'localStorage is not available',
    };
  }

  try {
    const updated: UserProgress = {
      ...progress,
      lastUpdated: new Date().toISOString(),
    };
    localStorage.setItem(PROGRESS_STORAGE_KEY, JSON.stringify(updated));
    return { success: true };
  } catch {
    return {
      success: false,
      error: 'save_failed',
      message: 'Failed to save progress to localStorage',
    };
  }
}

/**
 * Reset all progress data
 */
export function resetProgress(): ProgressResult<UserProgress> {
  if (!isStorageAvailable()) {
    return {
      success: false,
      error: 'storage_unavailable',
      message: 'localStorage is not available',
    };
  }

  try {
    const initial = createInitialProgress();
    localStorage.setItem(PROGRESS_STORAGE_KEY, JSON.stringify(initial));
    return { success: true, data: initial };
  } catch {
    return {
      success: false,
      error: 'save_failed',
      message: 'Failed to reset progress',
    };
  }
}

// ============================================================================
// Collection Progress Storage
// ============================================================================

/**
 * Load all collection progress from localStorage
 */
export function loadCollectionProgress(): ProgressResult<Record<string, CollectionProgress>> {
  if (!isStorageAvailable()) {
    return {
      success: false,
      error: 'storage_unavailable',
      message: 'localStorage is not available',
    };
  }

  try {
    const stored = localStorage.getItem(COLLECTION_PROGRESS_KEY);
    if (stored === null) {
      return { success: true, data: {} };
    }
    const data = JSON.parse(stored) as Record<string, CollectionProgress>;
    return { success: true, data };
  } catch {
    return {
      success: false,
      error: 'parse_error',
      message: 'Failed to parse collection progress',
    };
  }
}

/**
 * Save collection progress to localStorage
 */
export function saveCollectionProgress(
  progress: Record<string, CollectionProgress>
): ProgressResult<void> {
  if (!isStorageAvailable()) {
    return {
      success: false,
      error: 'storage_unavailable',
      message: 'localStorage is not available',
    };
  }

  try {
    localStorage.setItem(COLLECTION_PROGRESS_KEY, JSON.stringify(progress));
    return { success: true };
  } catch {
    return {
      success: false,
      error: 'save_failed',
      message: 'Failed to save collection progress',
    };
  }
}

// ============================================================================
// Daily Progress Storage
// ============================================================================

/**
 * Load all daily progress from localStorage
 */
export function loadDailyProgress(): ProgressResult<Record<string, DailyProgress>> {
  if (!isStorageAvailable()) {
    return {
      success: false,
      error: 'storage_unavailable',
      message: 'localStorage is not available',
    };
  }

  try {
    const stored = localStorage.getItem(DAILY_PROGRESS_KEY);
    if (stored === null) {
      return { success: true, data: {} };
    }
    const data = JSON.parse(stored) as Record<string, DailyProgress>;
    return { success: true, data };
  } catch {
    return {
      success: false,
      error: 'parse_error',
      message: 'Failed to parse daily progress',
    };
  }
}

/**
 * Save daily progress to localStorage
 */
export function saveDailyProgress(progress: Record<string, DailyProgress>): ProgressResult<void> {
  if (!isStorageAvailable()) {
    return {
      success: false,
      error: 'storage_unavailable',
      message: 'localStorage is not available',
    };
  }

  try {
    localStorage.setItem(DAILY_PROGRESS_KEY, JSON.stringify(progress));
    return { success: true };
  } catch {
    return {
      success: false,
      error: 'save_failed',
      message: 'Failed to save daily progress',
    };
  }
}

/** Re-export schema version for convenience */
export { PROGRESS_SCHEMA_VERSION };
