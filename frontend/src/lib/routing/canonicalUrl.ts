/**
 * Canonical URL contract for context routes.
 *
 * Defines the canonical shape of context URLs (`/contexts/{dim}/{slug}?...`)
 * and provides pure parse/serialize helpers that guarantee deterministic
 * output (sorted params, deduplicated numeric IDs, empty arrays omitted).
 *
 * @see plan-composable-fragments-architecture.md §3.2
 * @module
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Context dimensions that map to query filter dimensions. */
export type ContextDimension = 'training' | 'technique' | 'collection' | 'quality';

/** Canonical filter params using compact single-char keys. */
export interface CanonicalFilters {
  /** Level numeric IDs */
  readonly l?: readonly number[];
  /** Tag numeric IDs */
  readonly t?: readonly number[];
  /** Collection numeric IDs */
  readonly c?: readonly number[];
  /** Quality numeric IDs */
  readonly q?: readonly number[];
  /** Content-type numeric IDs (1=curated, 2=practice, 3=training) */
  readonly ct?: readonly number[];
  /** Depth preset slug (e.g., "quick", "medium", "deep") */
  readonly dp?: string;
  /** Match mode for multi-value filters */
  readonly match?: 'all' | 'any';
}

/** A fully parsed context route. */
export interface ContextRoute {
  readonly dimension: ContextDimension;
  readonly slug: string;
  readonly filters: CanonicalFilters;
  readonly offset?: number | undefined;
  readonly id?: string | undefined;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Map dimension name to data domain for configService lookups. */
export const DIMENSION_TO_DOMAIN = {
  training: 'level',
  technique: 'tag',
  collection: 'collection',
  quality: 'quality',
} as const;

/** All valid context dimensions. */
export const CONTEXT_DIMENSIONS: readonly ContextDimension[] = [
  'training',
  'technique',
  'collection',
  'quality',
];

/** Deterministic param ordering: alphabetical. */
export const CANONICAL_PARAM_ORDER = [
  'c',
  'ct',
  'dp',
  'id',
  'l',
  'match',
  'offset',
  'q',
  't',
] as const;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

const NUMERIC_FILTER_KEYS = ['c', 'ct', 'l', 'q', 't'] as const;

/**
 * Parse a comma-separated string of numeric IDs into a sorted, deduplicated
 * array. Non-finite or non-integer values are silently discarded.
 */
function parseNumericList(raw: string | null): number[] | undefined {
  if (raw == null || raw === '') return undefined;

  const seen = new Set<number>();
  for (const token of raw.split(',')) {
    const trimmed = token.trim();
    if (trimmed === '') continue;
    const n = Number(trimmed);
    if (Number.isFinite(n) && Number.isInteger(n)) {
      seen.add(n);
    }
  }

  if (seen.size === 0) return undefined;
  return [...seen].sort((a, b) => a - b);
}

/**
 * Serialize a numeric array to a comma-separated string.
 * Returns `undefined` when the array is empty or absent.
 */
function serializeNumericList(ids: readonly number[] | undefined): string | undefined {
  if (!ids || ids.length === 0) return undefined;
  return [...ids].sort((a, b) => a - b).join(',');
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Parse canonical filters from a URL search string.
 *
 * Reads `l`, `t`, `c`, `q`, and `match` query parameters.
 * Comma-separated values are parsed into sorted, deduplicated number arrays.
 * Invalid (non-integer / non-finite) numbers are silently discarded.
 */
export function parseCanonicalFilters(search: string): CanonicalFilters {
  const params = new URLSearchParams(search);

  const filters: {
    l?: readonly number[];
    t?: readonly number[];
    c?: readonly number[];
    q?: readonly number[];
    dp?: string;
    match?: 'all' | 'any';
  } = {};

  for (const key of NUMERIC_FILTER_KEYS) {
    const parsed = parseNumericList(params.get(key));
    if (parsed) {
      (filters as Record<string, readonly number[]>)[key] = parsed;
    }
  }

  const dpRaw = params.get('dp');
  if (dpRaw != null && dpRaw !== '') {
    (filters as Record<string, unknown>)['dp'] = dpRaw;
  }

  const matchRaw = params.get('match');
  if (matchRaw === 'all' || matchRaw === 'any') {
    filters.match = matchRaw;
  }

  return filters;
}

/**
 * Convert canonical filters to URLSearchParams with deterministic ordering.
 *
 * - Numeric arrays are sorted ascending and joined with commas.
 * - Empty arrays are omitted.
 * - Parameters appear in {@link CANONICAL_PARAM_ORDER} order.
 */
export function serializeCanonicalFilters(filters: CanonicalFilters): URLSearchParams {
  const params = new URLSearchParams();

  // Build a map of key → serialized value, then append in canonical order.
  const entries: Record<string, string> = {};

  for (const key of NUMERIC_FILTER_KEYS) {
    const value = serializeNumericList(filters[key]);
    if (value !== undefined) {
      entries[key] = value;
    }
  }

  if (filters.dp) {
    entries['dp'] = filters.dp;
  }

  if (filters.match) {
    entries['match'] = filters.match;
  }

  // Append in deterministic order.
  for (const key of CANONICAL_PARAM_ORDER) {
    const value = entries[key];
    if (value !== undefined) {
      params.set(key, value);
    }
  }

  return params;
}

/**
 * Build a full context URL string: `/contexts/{dim}/{slug}?...`.
 *
 * All query parameters are emitted in {@link CANONICAL_PARAM_ORDER}.
 * `offset` is only included when defined. `id` is only included when defined.
 */
export function serializeContextUrl(route: ContextRoute): string {
  const params = serializeCanonicalFilters(route.filters);

  if (route.id !== undefined) {
    params.set('id', route.id);
  }

  if (route.offset !== undefined) {
    params.set('offset', String(route.offset));
  }

  // Re-sort into canonical order by rebuilding.
  const ordered = new URLSearchParams();
  for (const key of CANONICAL_PARAM_ORDER) {
    const value = params.get(key);
    if (value !== undefined && value !== null) {
      ordered.set(key, value);
    }
  }

  const qs = ordered.toString();
  const path = `/contexts/${route.dimension}/${route.slug}`;
  return qs ? `${path}?${qs}` : path;
}

/**
 * Parse a context URL from pathname + search string.
 *
 * Expects pathname of shape `/contexts/{dimension}/{slug}`.
 * Returns `null` if the pathname does not match a valid context pattern.
 */
export function parseContextUrl(pathname: string, search: string): ContextRoute | null {
  const match = /^\/contexts\/(training|technique|collection|quality)\/([^/?#]+)$/.exec(pathname);
  if (!match) return null;

  const dimension = match[1]! as ContextDimension;
  const slug = decodeURIComponent(match[2]!);
  const filters = parseCanonicalFilters(search);
  const offset = parseOffset(search);
  const id = parseId(search);

  const route: ContextRoute = { dimension, slug, filters };

  // Build with optional properties only when present.
  if (offset !== undefined || id !== undefined) {
    return {
      ...route,
      ...(offset !== undefined ? { offset } : {}),
      ...(id !== undefined ? { id } : {}),
    };
  }

  return route;
}

/**
 * Produce the canonical form of a URL.
 *
 * Returns a new `URL` with sorted params, deduplicated + ascending numeric
 * IDs in filter params, and empty arrays removed. Returns `null` if the URL
 * is already in canonical form (no `replaceState` needed).
 */
export function canonicalize(currentUrl: URL): URL | null {
  const params = new URLSearchParams(currentUrl.search);
  const canonical = new URLSearchParams();

  // Collect all keys we recognise and re-serialize them canonically.
  const rebuiltEntries: Record<string, string> = {};

  for (const key of NUMERIC_FILTER_KEYS) {
    const raw = params.get(key);
    if (raw != null) {
      const parsed = parseNumericList(raw);
      if (parsed) {
        rebuiltEntries[key] = parsed.join(',');
      }
      // If parsed is undefined (all invalid), the param is dropped.
    }
  }

  const dpRaw = params.get('dp');
  if (dpRaw != null && dpRaw !== '') {
    rebuiltEntries['dp'] = dpRaw;
  }

  const matchRaw = params.get('match');
  if (matchRaw === 'all' || matchRaw === 'any') {
    rebuiltEntries['match'] = matchRaw;
  }

  const idRaw = params.get('id');
  if (idRaw != null && idRaw !== '') {
    rebuiltEntries['id'] = idRaw;
  }

  const offsetRaw = params.get('offset');
  if (offsetRaw != null) {
    const n = Number(offsetRaw);
    if (Number.isFinite(n) && Number.isInteger(n) && n >= 0) {
      rebuiltEntries['offset'] = String(n);
    }
  }

  // Append in deterministic alphabetical order.
  for (const key of CANONICAL_PARAM_ORDER) {
    const value = rebuiltEntries[key];
    if (value !== undefined) {
      canonical.set(key, value);
    }
  }

  // Preserve unknown params (pass-through for future dimensions).
  // Append any params not in CANONICAL_PARAM_ORDER in their original order.
  const knownKeys = new Set<string>(CANONICAL_PARAM_ORDER);
  for (const [key, value] of params.entries()) {
    if (!knownKeys.has(key)) {
      canonical.set(key, value);
    }
  }

  const canonicalSearch = canonical.toString();
  const currentSearch = currentUrl.search.replace(/^\?/, '');

  if (canonicalSearch === currentSearch) {
    return null; // Already canonical.
  }

  const result = new URL(currentUrl.href);
  result.search = canonicalSearch ? `?${canonicalSearch}` : '';
  return result;
}

/**
 * Parse the `offset` query parameter from a search string.
 *
 * Returns `undefined` when absent, non-numeric, or negative.
 */
export function parseOffset(search: string): number | undefined {
  const params = new URLSearchParams(search);
  const raw = params.get('offset');
  if (raw == null) return undefined;

  const n = Number(raw);
  if (Number.isFinite(n) && Number.isInteger(n) && n >= 0) {
    return n;
  }
  return undefined;
}

/**
 * Parse the `id` query parameter from a search string.
 *
 * Returns `undefined` when absent or empty.
 */
export function parseId(search: string): string | undefined {
  const params = new URLSearchParams(search);
  const raw = params.get('id');
  if (raw == null || raw === '') return undefined;
  return raw;
}
