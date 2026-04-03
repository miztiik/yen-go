/**
 * useBrowseParams — Generic URL parameter sync for browse pages.
 *
 * Manages non-canonical URL search params (e.g. `cat`, `s`, `q`) alongside
 * the canonical params managed by {@link useCanonicalUrl}. Uses a
 * read-merge-write pattern so that both hooks can coexist on the same page
 * without clobbering each other's params.
 *
 * @module hooks/useBrowseParams
 */

import { useState, useEffect, useCallback, useRef } from 'preact/hooks';

/**
 * Read current values of managed keys from the URL, falling back to defaults.
 */
function readParams<T extends Record<string, string>>(
  defaults: T,
): T {
  const params = new URLSearchParams(window.location.search);
  const result = { ...defaults };
  for (const key of Object.keys(defaults)) {
    const value = params.get(key);
    if (value !== null) {
      (result as Record<string, string>)[key] = value;
    }
  }
  return result;
}

/**
 * Write managed params to the URL using read-merge-write.
 *
 * Reads the current URL search string, updates only `managedKeys`,
 * writes back ALL params (preserving keys owned by other hooks).
 * Omits params whose value matches the default (clean URLs).
 */
function writeParams<T extends Record<string, string>>(
  values: T,
  defaults: T,
): void {
  const params = new URLSearchParams(window.location.search);

  for (const key of Object.keys(defaults)) {
    const value = values[key];
    if (value === undefined || value === defaults[key]) {
      params.delete(key);
    } else {
      params.set(key, value);
    }
  }

  const search = params.toString();
  const url = search
    ? `${window.location.pathname}?${search}${window.location.hash}`
    : `${window.location.pathname}${window.location.hash}`;

  window.history.replaceState(window.history.state, '', url);
}

/**
 * Sync browse-page filter state with URL search params.
 *
 * @typeParam T - Record of param key → default string value.
 * @param defaults - Default values for each managed param key.
 * @returns `{ params, setParam, clearParams }`
 *
 * @example
 * ```tsx
 * const { params, setParam, clearParams } = useBrowseParams({ cat: 'all', s: 'name' });
 * // params.cat === 'all' (or URL value)
 * setParam('cat', 'tesuji');  // updates URL + state
 * clearParams();              // resets to defaults, cleans URL
 * ```
 */
export function useBrowseParams<T extends Record<string, string>>(
  defaults: T,
): {
  readonly params: T;
  readonly setParam: <K extends keyof T & string>(key: K, value: T[K]) => void;
  readonly clearParams: () => void;
} {
  const defaultsRef = useRef(defaults);

  const [params, setParamsState] = useState<T>(() => readParams(defaults));

  const setParam = useCallback(
    <K extends keyof T & string>(key: K, value: T[K]): void => {
      setParamsState((prev) => {
        const next = { ...prev, [key]: value };
        writeParams(next, defaultsRef.current);
        return next;
      });
    },
    [],
  );

  const clearParams = useCallback((): void => {
    const defs = defaultsRef.current;
    setParamsState({ ...defs });
    writeParams(defs, defs);
  }, []);

  // RC-1: popstate listener with pathname guard.
  // Only re-read params when the pathname is unchanged (same browse page).
  useEffect(() => {
    const pathOnMount = window.location.pathname;

    const handlePopState = (): void => {
      if (window.location.pathname === pathOnMount) {
        setParamsState(readParams(defaultsRef.current));
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  return { params, setParam, clearParams };
}
