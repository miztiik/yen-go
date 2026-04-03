/**
 * Common utility types for frontend services
 * @module types/common
 *
 * Shared across collection and daily challenge services.
 */

// ============================================================================
// Loader Result Types
// ============================================================================

/**
 * Error types for data loading operations
 */
export type LoaderError =
  | 'network_error' // Failed to fetch from CDN
  | 'not_found' // 404 - Resource doesn't exist
  | 'parse_error' // JSON/SGF parsing failed
  | 'invalid_data'; // Data doesn't match expected schema

/**
 * Result wrapper for all loader operations.
 * Consistent error handling across services.
 */
export interface LoaderResult<T> {
  /** Whether the operation succeeded */
  success: boolean;
  /** Data if successful */
  data?: T;
  /** Error type if failed */
  error?: LoaderError;
  /** Human-readable error message */
  message?: string;
}

/**
 * Create a successful loader result
 */
export function successResult<T>(data: T): LoaderResult<T> {
  return { success: true, data };
}

/**
 * Create a failed loader result
 */
export function errorResult<T>(error: LoaderError, message: string): LoaderResult<T> {
  return { success: false, error, message };
}

// ============================================================================
// Progress Result Types
// ============================================================================

/**
 * Error types for progress operations
 */
export type ProgressError =
  | 'storage_unavailable' // localStorage not available
  | 'save_failed' // Failed to save to localStorage
  | 'quota_exceeded' // localStorage quota exceeded
  | 'parse_error' // Failed to parse stored data
  | 'not_found'; // Progress data not found

/**
 * Result wrapper for progress operations.
 */
export interface ProgressResult<T> {
  /** Whether the operation succeeded */
  success: boolean;
  /** Data if successful */
  data?: T;
  /** Error type if failed */
  error?: ProgressError;
  /** Human-readable error message */
  message?: string;
}

/**
 * Create a successful progress result
 */
export function successProgress<T>(data: T): ProgressResult<T> {
  return { success: true, data };
}

/**
 * Create a failed progress result
 */
export function errorProgress<T>(error: ProgressError, message: string): ProgressResult<T> {
  return { success: false, error, message };
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Generic callback for async operations with progress
 */
export type ProgressCallback = (loaded: number, total: number) => void;

/**
 * Cancellation token for long-running operations
 */
export interface CancellationToken {
  isCancelled: boolean;
  cancel(): void;
}

/**
 * Create a cancellation token
 */
export function createCancellationToken(): CancellationToken {
  const token: CancellationToken = {
    isCancelled: false,
    cancel() {
      this.isCancelled = true;
    },
  };
  return token;
}

// ============================================================================
// Async Utilities
// ============================================================================

/**
 * Delay execution for specified milliseconds
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Retry an async operation with exponential backoff
 */
export async function retryWithBackoff<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 1000
): Promise<T> {
  let lastError: Error | undefined;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      if (attempt < maxRetries) {
        const delayMs = baseDelayMs * Math.pow(2, attempt);
        await delay(delayMs);
      }
    }
  }

  throw lastError;
}
