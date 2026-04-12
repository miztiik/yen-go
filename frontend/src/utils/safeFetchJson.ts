/**
 * Safe JSON Fetch Utility
 * @module utils/safeFetchJson
 *
 * Centralizes all fetch→JSON parsing with proper error handling.
 * Guards against SPA fallback HTML responses (GitHub Pages 404 → index.html).
 *
 * Spec 129: FR-039 — safeFetchJson prevents JSON.parse crashes from HTML responses.
 */

// ============================================================================
// Error Types
// ============================================================================

/**
 * Error thrown when a fetch response cannot be parsed as JSON.
 * Provides structured error info for error boundaries and logging.
 */
export class FetchJsonError extends Error {
  /** HTTP status code (0 if network error) */
  readonly status: number;
  /** The URL that was fetched */
  readonly url: string;
  /** Error category for programmatic handling */
  readonly category: 'network' | 'http' | 'content-type' | 'parse';

  constructor(message: string, url: string, status: number, category: FetchJsonError['category']) {
    super(message);
    this.name = 'FetchJsonError';
    this.url = url;
    this.status = status;
    this.category = category;
  }
}

// ============================================================================
// Main Utility
// ============================================================================

/**
 * Fetch a URL and parse the response as JSON with safety guards.
 *
 * Guards:
 * 1. `response.ok` check — rejects 404/500 immediately
 * 2. Content-Type check — rejects `text/html` (SPA fallback detection)
 * 3. JSON parse try-catch — catches malformed JSON
 *
 * @param url - URL to fetch
 * @param init - Optional fetch init (headers, method, etc.)
 * @returns Parsed JSON response typed as T
 * @throws {FetchJsonError} on any error
 *
 * @example
 * ```ts
 * const data = await safeFetchJson<LevelIndex>('views/by-level/120/page-001.json');
 * ```
 */
export async function safeFetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = init !== undefined ? await fetch(url, init) : await fetch(url);
  } catch (error) {
    throw new FetchJsonError(
      `Network error fetching ${url}: ${error instanceof Error ? error.message : 'unknown'}`,
      url,
      0,
      'network'
    );
  }

  // Guard 1: HTTP status
  if (!response.ok) {
    throw new FetchJsonError(
      `HTTP ${response.status} fetching ${url}`,
      url,
      response.status,
      'http'
    );
  }

  // Guard 2: Content-Type (reject HTML SPA fallback)
  const contentType = response.headers?.get?.('content-type') ?? '';
  if (contentType.includes('text/html')) {
    throw new FetchJsonError(
      `Expected JSON but got HTML from ${url} (SPA fallback?)`,
      url,
      response.status,
      'content-type'
    );
  }

  // Guard 3: Parse JSON safely
  try {
    const data = (await response.json()) as T;
    return data;
  } catch (error) {
    throw new FetchJsonError(
      `Failed to parse JSON from ${url}: ${error instanceof Error ? error.message : 'unknown'}`,
      url,
      response.status,
      'parse'
    );
  }
}

// ============================================================================
// Lightweight Response Parser
// ============================================================================

/**
 * Safely parse an already-fetched Response as JSON.
 *
 * Use this when you already have a Response object (e.g., inside a retry
 * loop or a multi-URL fallback pattern) and just need the parse guards.
 * This does NOT check `response.ok` — the caller is responsible for that.
 *
 * Guards:
 * 1. Content-Type check — rejects `text/html` (SPA fallback detection)
 * 2. JSON parse try-catch — catches malformed JSON
 *
 * @param response - Already-fetched Response object (must be ok)
 * @param url - URL string for error context
 * @returns Parsed JSON response typed as T
 * @throws {FetchJsonError} on content-type mismatch or parse error
 */
export async function safeParseJson<T>(response: Response, url: string): Promise<T> {
  const contentType = response.headers?.get?.('content-type') ?? '';
  if (contentType.includes('text/html')) {
    throw new FetchJsonError(
      `Expected JSON but got HTML from ${url} (SPA fallback?)`,
      url,
      response.status,
      'content-type'
    );
  }

  try {
    return (await response.json()) as T;
  } catch (error) {
    throw new FetchJsonError(
      `Failed to parse JSON from ${url}: ${error instanceof Error ? error.message : 'unknown'}`,
      url,
      response.status,
      'parse'
    );
  }
}
