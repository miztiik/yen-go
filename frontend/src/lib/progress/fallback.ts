/**
 * Fallback storage handling for when localStorage is unavailable.
 * @module lib/progress/fallback
 */

import type { UserProgress } from '../../types/progress';
import { createDefaultProgress } from '../../types/progress';
import type { ProgressStorage, StorageMode, StorageResult } from './storage';
import { ProgressStorageService } from './storage';

/**
 * Warning message when operating in session-only mode.
 */
export const SESSION_ONLY_WARNING =
  'Your progress will only be saved for this browser session. ' +
  'LocalStorage is unavailable (private browsing mode or storage disabled).';

/**
 * Warning message when operating in memory-only mode.
 */
export const MEMORY_ONLY_WARNING =
  'Your progress will NOT be saved. ' +
  'Storage is completely unavailable. Your progress will be lost when you close this tab.';

/**
 * Get appropriate warning message for storage mode.
 *
 * @param mode - Current storage mode
 * @returns Warning message or null if no warning needed
 */
export function getStorageWarning(mode: StorageMode): string | null {
  switch (mode) {
    case 'localStorage':
      return null;
    case 'sessionStorage':
      return SESSION_ONLY_WARNING;
    case 'memory':
      return MEMORY_ONLY_WARNING;
  }
}

/**
 * Check if storage is persistent (survives browser restart).
 *
 * @param mode - Current storage mode
 * @returns True if storage is persistent
 */
export function isPersistentStorage(mode: StorageMode): boolean {
  return mode === 'localStorage';
}

/**
 * Check if storage survives tab close.
 *
 * @param mode - Current storage mode
 * @returns True if storage survives tab close
 */
export function survivesTabClose(mode: StorageMode): boolean {
  return mode === 'localStorage' || mode === 'sessionStorage';
}

/**
 * Session-only storage implementation.
 * Wraps sessionStorage for temporary progress storage.
 */
export class SessionOnlyStorage implements ProgressStorage {
  private key: string;

  constructor(key: string = 'yen-go-progress') {
    this.key = key;
  }

  getMode(): StorageMode {
    return 'sessionStorage';
  }

  isAvailable(): boolean {
    try {
      const testKey = '__yen_go_test__';
      sessionStorage.setItem(testKey, 'test');
      sessionStorage.removeItem(testKey);
      return true;
    } catch {
      return false;
    }
  }

  get(): StorageResult<UserProgress> {
    try {
      const raw = sessionStorage.getItem(this.key);

      if (!raw) {
        return { success: true, data: createDefaultProgress() };
      }

      const parsed = JSON.parse(raw) as UserProgress;
      return { success: true, data: parsed };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return { success: false, error: `Failed to read progress: ${message}` };
    }
  }

  set(progress: UserProgress): StorageResult<void> {
    try {
      sessionStorage.setItem(this.key, JSON.stringify(progress));
      return { success: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return { success: false, error: `Failed to save progress: ${message}` };
    }
  }

  clear(): StorageResult<void> {
    try {
      sessionStorage.removeItem(this.key);
      return { success: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return { success: false, error: `Failed to clear progress: ${message}` };
    }
  }
}

/**
 * Memory-only storage implementation.
 * Used when all persistent storage is unavailable.
 */
export class MemoryOnlyStorage implements ProgressStorage {
  private data: UserProgress;

  constructor() {
    this.data = createDefaultProgress();
  }

  getMode(): StorageMode {
    return 'memory';
  }

  isAvailable(): boolean {
    return true; // Memory is always available
  }

  get(): StorageResult<UserProgress> {
    return { success: true, data: this.data };
  }

  set(progress: UserProgress): StorageResult<void> {
    this.data = progress;
    return { success: true };
  }

  clear(): StorageResult<void> {
    this.data = createDefaultProgress();
    return { success: true };
  }
}

/**
 * Storage status information.
 */
export interface StorageStatus {
  /** Current storage mode */
  readonly mode: StorageMode;
  /** Whether storage is persistent */
  readonly isPersistent: boolean;
  /** Whether data survives tab close */
  readonly survivesTabClose: boolean;
  /** Warning message (if any) */
  readonly warning: string | null;
  /** Human-readable description */
  readonly description: string;
}

/**
 * Get comprehensive storage status.
 *
 * @param mode - Current storage mode
 * @returns Storage status object
 */
export function getStorageStatus(mode: StorageMode): StorageStatus {
  const descriptions: Record<StorageMode, string> = {
    localStorage: 'Your progress is saved locally and will persist across browser sessions.',
    sessionStorage: 'Your progress is saved for this session only.',
    memory: 'Your progress is not being saved. It will be lost when you close this tab.',
  };

  return {
    mode,
    isPersistent: isPersistentStorage(mode),
    survivesTabClose: survivesTabClose(mode),
    warning: getStorageWarning(mode),
    description: descriptions[mode],
  };
}

/**
 * Create the best available storage implementation.
 *
 * @returns Storage implementation based on availability
 */
export function createBestAvailableStorage(): ProgressStorage {
  // Try localStorage first
  try {
    const testKey = '__yen_go_test__';
    localStorage.setItem(testKey, 'test');
    localStorage.removeItem(testKey);
    // Import and use main storage
    return new ProgressStorageService();
  } catch {
    // localStorage not available
  }

  // Try sessionStorage
  const sessionStorage = new SessionOnlyStorage();
  if (sessionStorage.isAvailable()) {
    return sessionStorage;
  }

  // Fall back to memory
  return new MemoryOnlyStorage();
}

/**
 * Export storage progress to JSON string.
 * Useful for backup/transfer when in non-persistent mode.
 *
 * @param storage - Storage implementation
 * @returns JSON string or null on error
 */
export function exportProgress(storage: ProgressStorage): string | null {
  const result = storage.get();
  if (!result.success || !result.data) {
    return null;
  }
  return JSON.stringify(result.data, null, 2);
}

/**
 * Import progress from JSON string.
 * Useful for restore/transfer.
 *
 * @param storage - Storage implementation
 * @param json - JSON string to import
 * @returns Success result
 */
export function importProgress(
  storage: ProgressStorage,
  json: string
): StorageResult<void> {
  try {
    const data = JSON.parse(json) as UserProgress;

    // Basic validation
    if (typeof data.version !== 'number') {
      return { success: false, error: 'Invalid progress data: missing version' };
    }

    return storage.set(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return { success: false, error: `Invalid JSON: ${message}` };
  }
}
