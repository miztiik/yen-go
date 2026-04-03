/**
 * useMediaQuery — React hook for responsive design via CSS media queries.
 * @module hooks/useMediaQuery
 *
 * H6 audit fix: Responsive pill collapsing for mobile/desktop.
 */

import { useState, useEffect } from 'preact/hooks';

/**
 * Subscribe to a CSS media query and return whether it currently matches.
 *
 * @param query - CSS media query string (e.g., '(min-width: 768px)')
 * @returns boolean indicating if the query currently matches
 *
 * @example
 * const isDesktop = useMediaQuery('(min-width: 768px)');
 * const prefersDark = useMediaQuery('(prefers-color-scheme: dark)');
 */
export function useMediaQuery(query: string): boolean {
  // SSR-safe: default to false if window is undefined
  const getMatches = (): boolean => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  };

  const [matches, setMatches] = useState<boolean>(getMatches);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQueryList = window.matchMedia(query);

    // Handler for query changes
    const handleChange = (e: MediaQueryListEvent) => {
      setMatches(e.matches);
    };

    // Set initial state
    setMatches(mediaQueryList.matches);

    // Modern browsers support addEventListener
    mediaQueryList.addEventListener('change', handleChange);

    return () => {
      mediaQueryList.removeEventListener('change', handleChange);
    };
  }, [query]);

  return matches;
}

/**
 * Convenience hook for desktop breakpoint (≥768px).
 * @returns true if viewport is at least 768px wide
 */
export function useIsDesktop(): boolean {
  return useMediaQuery('(min-width: 768px)');
}

/**
 * Convenience hook for mobile breakpoint (<768px).
 * @returns true if viewport is less than 768px wide
 */
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 767px)');
}
