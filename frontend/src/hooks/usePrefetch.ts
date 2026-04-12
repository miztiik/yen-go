/**
 * usePrefetch — Speculative next-puzzle SGF prefetching.
 *
 * Fetches the next puzzle's SGF in the background while the user
 * solves the current one. Returns cached SGF for instant transitions.
 *
 * Spec 132, US19, Tasks T202–T206
 * @module hooks/usePrefetch
 */

import { useRef, useEffect, useCallback } from 'preact/hooks';

export interface UsePrefetchResult {
  /** Get cached SGF for a path. Returns undefined if not cached yet. */
  getCached: (path: string) => string | undefined;
  /** Trigger prefetch for a given SGF path. */
  prefetch: (path: string) => void;
  /** Cancel any in-flight prefetch. */
  cancel: () => void;
}

/**
 * Hook for speculative SGF prefetching.
 *
 * @example
 * ```tsx
 * const { getCached, prefetch } = usePrefetch();
 *
 * // After current puzzle loads, prefetch next
 * useEffect(() => {
 *   if (nextPuzzlePath) prefetch(nextPuzzlePath);
 * }, [nextPuzzlePath]);
 *
 * // On "Next" click, use cached if available
 * const handleNext = () => {
 *   const cached = getCached(nextPuzzlePath);
 *   if (cached) loadPuzzle(cached); // instant
 *   else loadPuzzleFromNetwork(nextPuzzlePath); // fallback
 * };
 * ```
 */
export function usePrefetch(): UsePrefetchResult {
  const cacheRef = useRef<Map<string, string>>(new Map());
  const controllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  const prefetch = useCallback((path: string) => {
    // Don't re-fetch if already cached
    if (cacheRef.current.has(path)) return;

    // Cancel any in-flight prefetch
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    void fetch(path, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then((sgf) => {
        cacheRef.current.set(path, sgf);
      })
      .catch((err: unknown) => {
        // Silent fallback — prefetch failures are non-critical (FR-087)
        if (err instanceof Error && err.name !== 'AbortError') {
          console.debug('[usePrefetch] Failed to prefetch:', path, err.message);
        }
      });
  }, []);

  const getCached = useCallback((path: string): string | undefined => {
    return cacheRef.current.get(path);
  }, []);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
  }, []);

  return { getCached, prefetch, cancel };
}
