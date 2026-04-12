/**
 * Route type union and parse / serialize module.
 *
 * Every application URL is represented as a discriminated-union {@link Route}.
 * The module provides pure parse/serialize helpers plus thin wrappers around
 * `window.history` for navigation.
 *
 * @module
 */

import type { ContextDimension, CanonicalFilters } from './canonicalUrl';
import { parseCanonicalFilters, serializeContextUrl, parseOffset, parseId } from './canonicalUrl';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Mode routes for non-context pages. */
export type ModeType = 'daily' | 'daily-date' | 'random' | 'rush';

/** Full route union type. */
export type Route =
  | { readonly type: 'home' }
  | {
      readonly type: 'context';
      readonly dimension: ContextDimension;
      readonly slug: string;
      readonly filters: CanonicalFilters;
      readonly offset?: number;
      readonly id?: string;
    }
  | { readonly type: 'modes-daily' }
  | {
      readonly type: 'modes-daily-date';
      readonly date: string;
      readonly mode?: 'standard' | 'timed';
    }
  | { readonly type: 'modes-random' }
  | { readonly type: 'modes-rush' }
  | { readonly type: 'collections-browse' }
  | { readonly type: 'technique-browse' }
  | { readonly type: 'training-browse' }
  | { readonly type: 'learning-browse' }
  | { readonly type: 'progress' }
  | { readonly type: 'smart-practice'; readonly techniques?: readonly string[] };

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** ISO-date pattern (YYYY-MM-DD). */
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** Context path pattern: `/contexts/{dimension}/{slug}`. */
const CONTEXT_RE = /^\/contexts\/(training|technique|collection|quality)\/([^/?#]+)$/;

/**
 * Base URL path from Vite config (e.g. `'/yen-go'`), without trailing slash.
 * Used to strip the base prefix from incoming pathnames before matching and
 * to prepend it when serializing route URLs.
 */
const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Parse a URL into a {@link Route}.
 *
 * Handles all known path shapes. Unknown paths fall back to `home`.
 *
 * @param pathname - The URL pathname (e.g. `/contexts/training/beginner`).
 * @param search   - The URL search string including leading `?` (or empty).
 */
export function parseRoute(pathname: string, search: string): Route {
  // Strip the base-path prefix so route patterns remain base-agnostic.
  const stripped =
    BASE && pathname.startsWith(BASE) ? pathname.slice(BASE.length) || '/' : pathname;

  // Normalise trailing slash (but not the root `/`).
  const path = stripped.length > 1 ? stripped.replace(/\/+$/, '') : stripped;

  // --- Home ---
  if (path === '/' || path === '') {
    return { type: 'home' };
  }

  // --- Context routes ---
  const ctxMatch = CONTEXT_RE.exec(path);
  if (ctxMatch) {
    const dimension = ctxMatch[1]! as ContextDimension;
    const slug = decodeURIComponent(ctxMatch[2]!);
    const filters = parseCanonicalFilters(search);
    const offset = parseOffset(search);
    const id = parseId(search);

    const route: Route = {
      type: 'context',
      dimension,
      slug,
      filters,
      ...(offset !== undefined ? { offset } : {}),
      ...(id !== undefined ? { id } : {}),
    };

    return route;
  }

  // --- Modes ---
  if (path === '/modes/daily') {
    return { type: 'modes-daily' };
  }

  const dailyDateMatch = /^\/modes\/daily\/(\d{4}-\d{2}-\d{2})$/.exec(path);
  if (dailyDateMatch && DATE_RE.test(dailyDateMatch[1]!)) {
    const params = new URLSearchParams(search);
    const mode = params.get('mode') === 'timed' ? ('timed' as const) : undefined;
    return { type: 'modes-daily-date', date: dailyDateMatch[1]!, ...(mode ? { mode } : {}) };
  }

  if (path === '/modes/random') {
    return { type: 'modes-random' };
  }

  if (path === '/modes/rush') {
    return { type: 'modes-rush' };
  }

  // --- Browse pages ---
  if (path === '/collections') {
    return { type: 'collections-browse' };
  }

  if (path === '/technique') {
    return { type: 'technique-browse' };
  }

  if (path === '/training') {
    return { type: 'training-browse' };
  }

  if (path === '/learn') {
    return { type: 'learning-browse' };
  }

  // --- Progress & Smart Practice ---
  if (path === '/progress') {
    return { type: 'progress' };
  }

  if (path === '/smart-practice') {
    const params = new URLSearchParams(search);
    const techniques = params.get('techniques')?.split(',').filter(Boolean);
    return { type: 'smart-practice', ...(techniques?.length ? { techniques } : {}) };
  }

  // --- Shorthand context aliases ---
  // e.g. /collection/cho-chikun-elementary → context collection route
  const collectionShorthand = /^\/collection\/([^/?#]+)$/.exec(path);
  if (collectionShorthand) {
    return {
      type: 'context',
      dimension: 'collection',
      slug: decodeURIComponent(collectionShorthand[1]!),
      filters: parseCanonicalFilters(search),
      ...((o) => (o !== undefined ? { offset: o } : {}))(parseOffset(search)),
      ...((i) => (i !== undefined ? { id: i } : {}))(parseId(search)),
    };
  }

  const trainingShorthand = /^\/training\/([^/?#]+)$/.exec(path);
  if (trainingShorthand) {
    return {
      type: 'context',
      dimension: 'training',
      slug: decodeURIComponent(trainingShorthand[1]!),
      filters: parseCanonicalFilters(search),
      ...((o) => (o !== undefined ? { offset: o } : {}))(parseOffset(search)),
      ...((i) => (i !== undefined ? { id: i } : {}))(parseId(search)),
    };
  }

  const techniqueShorthand = /^\/technique\/([^/?#]+)$/.exec(path);
  if (techniqueShorthand) {
    return {
      type: 'context',
      dimension: 'technique',
      slug: decodeURIComponent(techniqueShorthand[1]!),
      filters: parseCanonicalFilters(search),
      ...((o) => (o !== undefined ? { offset: o } : {}))(parseOffset(search)),
      ...((i) => (i !== undefined ? { id: i } : {}))(parseId(search)),
    };
  }

  // --- Fallback ---
  return { type: 'home' };
}

/**
 * Serialize a {@link Route} to a URL string (pathname + query string).
 *
 * Context routes include all filter params in canonical (alphabetical) order.
 */
export function serializeRoute(route: Route): string {
  let path: string;

  switch (route.type) {
    case 'home':
      path = '/';
      break;

    case 'context':
      path = serializeContextUrl({
        dimension: route.dimension,
        slug: route.slug,
        filters: route.filters,
        offset: route.offset,
        id: route.id,
      });
      break;

    case 'modes-daily':
      path = '/modes/daily';
      break;

    case 'modes-daily-date':
      path = `/modes/daily/${route.date}${route.mode === 'timed' ? '?mode=timed' : ''}`;
      break;

    case 'modes-random':
      path = '/modes/random';
      break;

    case 'modes-rush':
      path = '/modes/rush';
      break;

    case 'collections-browse':
      path = '/collections';
      break;

    case 'technique-browse':
      path = '/technique';
      break;

    case 'training-browse':
      path = '/training';
      break;

    case 'learning-browse':
      path = '/learn';
      break;

    case 'progress':
      path = '/progress';
      break;

    case 'smart-practice': {
      const techniques = route.techniques?.length
        ? `?techniques=${route.techniques.join(',')}`
        : '';
      path = `/smart-practice${techniques}`;
      break;
    }
  }

  // Prepend the base path so browser URLs are correct (e.g. '/yen-go/training').
  return path === '/' ? `${BASE}/` : `${BASE}${path}`;
}

/**
 * Navigate to a route by pushing a new history entry.
 *
 * Only pushes if the serialized URL differs from the current location.
 */
export function navigateTo(route: Route): void {
  const url = serializeRoute(route);
  const current = window.location.pathname + window.location.search;

  if (url !== current) {
    window.history.pushState(null, '', url);
  }
}

/**
 * Replace the current history entry with the given route.
 *
 * Uses `replaceState` so the back button is unaffected.
 */
export function replaceRoute(route: Route): void {
  const url = serializeRoute(route);
  window.history.replaceState(null, '', url);
}

/**
 * Type guard: narrows a {@link Route} to a context route.
 */
export function isContextRoute(route: Route): route is Extract<Route, { type: 'context' }> {
  return route.type === 'context';
}

/**
 * Returns `true` for routes where the goban is displayed.
 *
 * Context routes and daily-date mode (when solving a puzzle) show the board,
 * which is used to determine compact header rendering.
 */
export function isPuzzleSolvingRoute(route: Route): boolean {
  return route.type === 'context' || route.type === 'modes-daily-date';
}
