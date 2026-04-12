/**
 * Progress storage service - localStorage wrapper for user progress.
 * @module lib/progress/storage
 */

import type { UserProgress } from '../../types/progress';
import { createDefaultProgress, PROGRESS_SCHEMA_VERSION } from '../../types/progress';

/**
 * localStorage key for progress data.
 */
export const STORAGE_KEY = 'yen-go-progress';

/**
 * Storage mode - determines where data is persisted.
 */
export type StorageMode = 'localStorage' | 'sessionStorage' | 'memory';

/**
 * Storage result indicating success or failure.
 */
export interface StorageResult<T> {
  readonly success: boolean;
  readonly data?: T;
  readonly error?: string;
}

/**
 * Progress storage interface for dependency injection.
 */
export interface ProgressStorage {
  /** Get current user progress */
  get(): StorageResult<UserProgress>;
  /** Save user progress */
  set(progress: UserProgress): StorageResult<void>;
  /** Clear all progress data */
  clear(): StorageResult<void>;
  /** Check if storage is available */
  isAvailable(): boolean;
  /** Get the current storage mode */
  getMode(): StorageMode;
}

/**
 * In-memory fallback storage for when localStorage is unavailable.
 */
class MemoryStorage implements Storage {
  private data: Map<string, string> = new Map();

  get length(): number {
    return this.data.size;
  }

  clear(): void {
    this.data.clear();
  }

  getItem(key: string): string | null {
    return this.data.get(key) ?? null;
  }

  key(index: number): string | null {
    const keys = Array.from(this.data.keys());
    return keys[index] ?? null;
  }

  removeItem(key: string): void {
    this.data.delete(key);
  }

  setItem(key: string, value: string): void {
    this.data.set(key, value);
  }
}

/**
 * Check if localStorage is available and writable.
 */
export function isLocalStorageAvailable(): boolean {
  try {
    const testKey = '__yen_go_test__';
    localStorage.setItem(testKey, 'test');
    localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if sessionStorage is available and writable.
 */
export function isSessionStorageAvailable(): boolean {
  try {
    const testKey = '__yen_go_test__';
    sessionStorage.setItem(testKey, 'test');
    sessionStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

/**
 * ProgressStorageService - main storage implementation.
 */
export class ProgressStorageService implements ProgressStorage {
  private storage: Storage;
  private mode: StorageMode;
  private key: string;

  constructor(key: string = STORAGE_KEY) {
    this.key = key;

    // Determine best available storage
    if (isLocalStorageAvailable()) {
      this.storage = localStorage;
      this.mode = 'localStorage';
    } else if (isSessionStorageAvailable()) {
      this.storage = sessionStorage;
      this.mode = 'sessionStorage';
    } else {
      this.storage = new MemoryStorage();
      this.mode = 'memory';
    }
  }

  /**
   * Get current storage mode.
   */
  getMode(): StorageMode {
    return this.mode;
  }

  /**
   * Check if persistent storage is available.
   */
  isAvailable(): boolean {
    return this.mode === 'localStorage';
  }

  /**
   * Get user progress from storage.
   */
  get(): StorageResult<UserProgress> {
    try {
      const raw = this.storage.getItem(this.key);

      if (!raw) {
        // No existing data - return default progress
        const defaultProgress = createDefaultProgress();
        return { success: true, data: defaultProgress };
      }

      const parsed = JSON.parse(raw) as unknown;

      // Validate it's an object with a version
      if (typeof parsed !== 'object' || parsed === null) {
        return {
          success: false,
          error: 'Invalid progress data: not an object',
        };
      }

      const progress = parsed as Record<string, unknown>;

      if (typeof progress.version !== 'number') {
        return {
          success: false,
          error: 'Invalid progress data: missing version',
        };
      }

      // Return as UserProgress (migration will be handled separately)
      return { success: true, data: progress as unknown as UserProgress };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return { success: false, error: `Failed to read progress: ${message}` };
    }
  }

  /**
   * Save user progress to storage.
   */
  set(progress: UserProgress): StorageResult<void> {
    try {
      // Ensure version is current
      const toSave: UserProgress = {
        ...progress,
        version: PROGRESS_SCHEMA_VERSION,
      };

      const serialized = JSON.stringify(toSave);
      this.storage.setItem(this.key, serialized);

      return { success: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';

      // Check for quota exceeded
      if (
        error instanceof DOMException &&
        (error.name === 'QuotaExceededError' || error.name === 'NS_ERROR_DOM_QUOTA_REACHED')
      ) {
        return {
          success: false,
          error: 'Storage quota exceeded. Please clear some browser data.',
        };
      }

      return { success: false, error: `Failed to save progress: ${message}` };
    }
  }

  /**
   * Clear all progress data.
   */
  clear(): StorageResult<void> {
    try {
      this.storage.removeItem(this.key);
      return { success: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return { success: false, error: `Failed to clear progress: ${message}` };
    }
  }

  /**
   * Get raw JSON string from storage (for debugging/export).
   */
  getRaw(): string | null {
    return this.storage.getItem(this.key);
  }

  /**
   * Set raw JSON string to storage (for import/restore).
   */
  setRaw(json: string): StorageResult<void> {
    try {
      // Validate it's valid JSON first
      JSON.parse(json);
      this.storage.setItem(this.key, json);
      return { success: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return { success: false, error: `Invalid JSON: ${message}` };
    }
  }
}

/**
 * Singleton instance for global access.
 */
let storageInstance: ProgressStorageService | null = null;

/**
 * Get the global storage service instance.
 */
export function getProgressStorage(): ProgressStorageService {
  if (!storageInstance) {
    storageInstance = new ProgressStorageService();
  }
  return storageInstance;
}

/**
 * Reset the global storage instance (for testing).
 */
export function resetProgressStorage(): void {
  storageInstance = null;
}
