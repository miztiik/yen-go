/**
 * Type declarations for preact-iso (not installed, but referenced by ReviewPage).
 * This provides stub types for the module until it's properly installed.
 */

declare module 'preact-iso' {
  export interface RouteParams {
    [key: string]: string | undefined;
  }

  export interface Route {
    params: RouteParams;
    path: string;
  }

  export interface Location {
    url: string;
    path: string;
    query: Record<string, string>;
    route: (url: string) => void;
  }

  export function useRoute(): Route;
  export function useLocation(): Location;
}
