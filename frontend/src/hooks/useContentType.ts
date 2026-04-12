/**
 * useContentType — global content-type preference hook.
 *
 * Stores user's preferred content-type filter (Curated/Practice/All) in
 * localStorage. Uses the module-level store pattern from useSettings.ts:
 * all consumers share state and re-render automatically on changes.
 *
 * Content types:
 *   0 = All (no filter)
 *   1 = Curated (highest quality puzzles)
 *   2 = Practice (proper puzzles without training noise)
 *   3 = Training (teaching material + drills)
 *
 * @module hooks/useContentType
 */

import { useEffect, useState, useCallback } from 'preact/hooks';

// ============================================================================
// Constants
// ============================================================================

/** localStorage key for content-type preference. */
export const CONTENT_TYPE_KEY = 'yengo:content-type' as const;

/** Default content type: All (show every puzzle regardless of content type). */
export const DEFAULT_CONTENT_TYPE = 0 as const;

/** Valid content-type values. 0 = All, 1 = Curated, 2 = Practice, 3 = Training. */
export type ContentTypeValue = 0 | 1 | 2 | 3;

// ============================================================================
// Module-Level Store
// ============================================================================

type Listener = () => void;
const listeners = new Set<Listener>();
let currentContentType: ContentTypeValue | null = null;

function notifyListeners(): void {
  for (const listener of listeners) listener();
}

/** Validate a content-type value. Returns DEFAULT_CONTENT_TYPE if invalid. */
export function validateContentType(value: unknown): ContentTypeValue {
  if (value === 0 || value === 1 || value === 2 || value === 3) return value;
  return DEFAULT_CONTENT_TYPE;
}

/** Load content-type preference from localStorage. */
function loadContentType(): ContentTypeValue {
  try {
    const stored = localStorage.getItem(CONTENT_TYPE_KEY);
    if (stored !== null) {
      return validateContentType(JSON.parse(stored));
    }
  } catch {
    // localStorage unavailable or corrupt — use default
  }
  return DEFAULT_CONTENT_TYPE;
}

/** Save content-type preference to localStorage. Non-fatal on failure. */
function saveContentType(value: ContentTypeValue): void {
  try {
    localStorage.setItem(CONTENT_TYPE_KEY, JSON.stringify(value));
  } catch {
    // Quota exceeded or private browsing — ignore
  }
}

function ensureLoaded(): ContentTypeValue {
  if (currentContentType === null) {
    currentContentType = loadContentType();
  }
  return currentContentType;
}

// ============================================================================
// Public API
// ============================================================================

/**
 * Get the current content-type preference (non-reactive snapshot).
 * Safe to call outside of hooks — returns the current value.
 */
export function getContentType(): ContentTypeValue {
  return ensureLoaded();
}

/**
 * Set the global content-type preference.
 * All subscribed components re-render automatically.
 */
export function setContentType(value: ContentTypeValue): void {
  const validated = validateContentType(value);
  currentContentType = validated;
  saveContentType(validated);
  notifyListeners();
}

// ============================================================================
// Hook
// ============================================================================

export interface UseContentTypeReturn {
  /** Current content-type preference. 0=All, 1=Curated, 2=Practice, 3=Training. */
  contentType: ContentTypeValue;
  /** Update the content-type preference. */
  setContentType: (value: ContentTypeValue) => void;
}

/**
 * Hook for reading/writing the global content-type preference.
 *
 * All consumers share the same module-level store and re-render
 * automatically when the content type changes. No prop drilling needed.
 */
export function useContentType(): UseContentTypeReturn {
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    const listener = (): void => forceUpdate((c) => c + 1);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  const contentType = ensureLoaded();

  const setter = useCallback((value: ContentTypeValue) => {
    setContentType(value);
  }, []);

  return { contentType, setContentType: setter };
}

/**
 * Reset content-type state for testing only.
 * @internal
 */
export function _resetContentTypeForTesting(): void {
  currentContentType = null;
  listeners.clear();
}
