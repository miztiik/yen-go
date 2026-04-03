/**
 * Safe localStorage Utilities
 * @module utils/storage
 *
 * Provides quota-aware localStorage operations with graceful degradation.
 * Covers: EC-001, FR-017
 */

import type { ProgressError } from '@/types/common';

// ============================================================================
// Constants
// ============================================================================

/** Estimate of localStorage quota (typically 5-10MB) */
const ESTIMATED_QUOTA_BYTES = 5 * 1024 * 1024; // 5MB conservative estimate

/** Warning threshold (80% of estimated quota) */
const QUOTA_WARNING_THRESHOLD = 0.8;

/** Key for storing quota warning acknowledgment */
const QUOTA_WARNING_KEY = 'yen-go-quota-warning-ack';

// ============================================================================
// Types
// ============================================================================

export interface StorageResult<T> {
  success: boolean;
  data: T | null;
  error: ProgressError | null;
  quotaInfo: QuotaInfo | null;
}

export interface QuotaInfo {
  used: number;
  estimated: number;
  percentage: number;
  isNearQuota: boolean;
}

export interface StorageListeners {
  onQuotaWarning?: (info: QuotaInfo) => void;
  onQuotaExceeded?: (key: string) => void;
  onStorageUnavailable?: () => void;
}

// ============================================================================
// Storage availability check
// ============================================================================

let storageAvailable: boolean | null = null;

/**
 * Check if localStorage is available
 */
export function isStorageAvailable(): boolean {
  if (storageAvailable !== null) {
    return storageAvailable;
  }

  try {
    const test = '__storage_test__';
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    storageAvailable = true;
    return true;
  } catch {
    storageAvailable = false;
    return false;
  }
}

// ============================================================================
// Quota management
// ============================================================================

/**
 * Estimate current localStorage usage
 */
export function getStorageUsage(): QuotaInfo {
  if (!isStorageAvailable()) {
    return {
      used: 0,
      estimated: 0,
      percentage: 0,
      isNearQuota: false,
    };
  }

  let totalSize = 0;
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key) {
      const value = localStorage.getItem(key);
      if (value) {
        // Approximate: key length + value length in UTF-16
        totalSize += (key.length + value.length) * 2;
      }
    }
  }

  const percentage = totalSize / ESTIMATED_QUOTA_BYTES;

  return {
    used: totalSize,
    estimated: ESTIMATED_QUOTA_BYTES,
    percentage,
    isNearQuota: percentage >= QUOTA_WARNING_THRESHOLD,
  };
}

/**
 * Check if user has acknowledged quota warning
 */
export function hasAcknowledgedQuotaWarning(): boolean {
  if (!isStorageAvailable()) return true;
  return localStorage.getItem(QUOTA_WARNING_KEY) === 'true';
}

/**
 * Acknowledge quota warning
 */
export function acknowledgeQuotaWarning(): void {
  if (isStorageAvailable()) {
    localStorage.setItem(QUOTA_WARNING_KEY, 'true');
  }
}

// ============================================================================
// Safe storage operations
// ============================================================================

const listeners: StorageListeners = {};

/**
 * Register storage event listeners
 */
export function setStorageListeners(newListeners: StorageListeners): void {
  Object.assign(listeners, newListeners);
}

/**
 * Safely get item from localStorage with type checking
 */
export function safeGetItem<T>(key: string): StorageResult<T> {
  if (!isStorageAvailable()) {
    listeners.onStorageUnavailable?.();
    return {
      success: false,
      data: null,
      error: 'storage_unavailable',
      quotaInfo: null,
    };
  }

  try {
    const value = localStorage.getItem(key);
    if (value === null) {
      return {
        success: true, // Not finding data is not an error
        data: null,
        error: null,
        quotaInfo: getStorageUsage(),
      };
    }

    const parsed = JSON.parse(value) as T;
    return {
      success: true,
      data: parsed,
      error: null,
      quotaInfo: getStorageUsage(),
    };
  } catch {
    return {
      success: false,
      data: null,
      error: 'parse_error',
      quotaInfo: getStorageUsage(),
    };
  }
}

/**
 * Safely set item in localStorage with quota handling
 */
export function safeSetItem<T>(key: string, value: T): StorageResult<T> {
  if (!isStorageAvailable()) {
    listeners.onStorageUnavailable?.();
    return {
      success: false,
      data: null,
      error: 'storage_unavailable',
      quotaInfo: null,
    };
  }

  // Check quota before attempting write
  const quotaInfo = getStorageUsage();
  if (quotaInfo.isNearQuota && !hasAcknowledgedQuotaWarning()) {
    listeners.onQuotaWarning?.(quotaInfo);
  }

  try {
    const serialized = JSON.stringify(value);
    localStorage.setItem(key, serialized);

    return {
      success: true,
      data: value,
      error: null,
      quotaInfo: getStorageUsage(),
    };
  } catch (error) {
    // Check if it's a quota exceeded error
    if (
      error instanceof DOMException &&
      (error.name === 'QuotaExceededError' ||
        error.name === 'NS_ERROR_DOM_QUOTA_REACHED')
    ) {
      listeners.onQuotaExceeded?.(key);
      return {
        success: false,
        data: null,
        error: 'quota_exceeded',
        quotaInfo: getStorageUsage(),
      };
    }

    return {
      success: false,
      data: null,
      error: 'save_failed',
      quotaInfo: getStorageUsage(),
    };
  }
}

/**
 * Safely remove item from localStorage
 */
export function safeRemoveItem(key: string): StorageResult<null> {
  if (!isStorageAvailable()) {
    return {
      success: false,
      data: null,
      error: 'storage_unavailable',
      quotaInfo: null,
    };
  }

  try {
    localStorage.removeItem(key);
    return {
      success: true,
      data: null,
      error: null,
      quotaInfo: getStorageUsage(),
    };
  } catch {
    return {
      success: false,
      data: null,
      error: 'save_failed',
      quotaInfo: null,
    };
  }
}

// ============================================================================
// Cleanup utilities for quota management
// ============================================================================

/** Keys that can be safely cleared to free space */
const CLEARABLE_KEYS = [
  'yen-go-rush-history', // Rush session history
  'yen-go-quota-warning-ack',
] as const;

/** Keys that should be preserved (user progress) */
const PROTECTED_KEYS = [
  'yen-go-progress',
  'yen-go-technique-progress',
  'yen-go-training-progress',
  'yen-go-rush-best-score',
  'yen-go-achievements',
] as const;

/**
 * Clear old data to free up space
 * Returns bytes freed
 */
export function clearOldData(): number {
  if (!isStorageAvailable()) return 0;

  let freedBytes = 0;

  for (const key of CLEARABLE_KEYS) {
    const value = localStorage.getItem(key);
    if (value) {
      freedBytes += (key.length + value.length) * 2;
      localStorage.removeItem(key);
    }
  }

  return freedBytes;
}

/**
 * Get list of storage keys by category
 */
export function getStorageKeysByCategory(): {
  protected: string[];
  clearable: string[];
  other: string[];
} {
  if (!isStorageAvailable()) {
    return { protected: [], clearable: [], other: [] };
  }

  const protectedSet = new Set(PROTECTED_KEYS as readonly string[]);
  const clearableSet = new Set(CLEARABLE_KEYS as readonly string[]);

  const result = {
    protected: [] as string[],
    clearable: [] as string[],
    other: [] as string[],
  };

  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key) {
      if (key.startsWith('yen-go-')) {
        if (protectedSet.has(key)) {
          result.protected.push(key);
        } else if (clearableSet.has(key)) {
          result.clearable.push(key);
        } else {
          result.other.push(key);
        }
      }
    }
  }

  return result;
}

/**
 * Format bytes for display
 */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
