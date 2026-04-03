/**
 * Tests for the canonical URL module.
 * @module tests/unit/canonical-url.test
 *
 * Covers parse/serialize helpers for context URLs, canonical filters,
 * offset/id parsing, and the canonicalize round-trip guarantee.
 */

import { describe, it, expect } from 'vitest';
import {
  parseCanonicalFilters,
  serializeCanonicalFilters,
  serializeContextUrl,
  parseContextUrl,
  canonicalize,
  parseOffset,
  parseId,
} from '../../src/lib/routing/canonicalUrl';
import type { CanonicalFilters, ContextRoute } from '../../src/lib/routing/canonicalUrl';

// ─── parseCanonicalFilters ─────────────────────────────────────────

describe('parseCanonicalFilters', () => {
  it('returns empty filters for empty search string', () => {
    expect(parseCanonicalFilters('')).toEqual({});
  });

  it('parses a single level', () => {
    expect(parseCanonicalFilters('?l=120')).toEqual({ l: [120] });
  });

  it('parses multi-level sorted', () => {
    expect(parseCanonicalFilters('?l=120,160')).toEqual({ l: [120, 160] });
  });

  it('parses multi-tag sorted ascending', () => {
    expect(parseCanonicalFilters('?t=36,10')).toEqual({ t: [10, 36] });
  });

  it('parses all dimensions', () => {
    expect(parseCanonicalFilters('?l=120&t=36&c=6&q=3')).toEqual({
      l: [120],
      t: [36],
      c: [6],
      q: [3],
    });
  });

  it('discards invalid (non-numeric) values', () => {
    expect(parseCanonicalFilters('?l=120,abc,160')).toEqual({ l: [120, 160] });
  });

  it('deduplicates repeated values', () => {
    expect(parseCanonicalFilters('?l=120,120,160')).toEqual({ l: [120, 160] });
  });

  it('parses match mode', () => {
    expect(parseCanonicalFilters('?match=any')).toEqual({ match: 'any' });
  });

  it('ignores invalid match value', () => {
    const result = parseCanonicalFilters('?match=foo');
    expect(result.match).toBeUndefined();
    expect(result).toEqual({});
  });

  it('ignores unknown params', () => {
    expect(parseCanonicalFilters('?l=120&foo=bar')).toEqual({ l: [120] });
  });

  it('parses dp (depth preset) param', () => {
    expect(parseCanonicalFilters('?dp=quick')).toEqual({ dp: 'quick' });
  });

  it('parses dp combined with numeric filters', () => {
    expect(parseCanonicalFilters('?l=120&dp=deep')).toEqual({ l: [120], dp: 'deep' });
  });

  it('ignores empty dp param', () => {
    expect(parseCanonicalFilters('?dp=')).toEqual({});
  });
});

// ─── serializeCanonicalFilters ─────────────────────────────────────

describe('serializeCanonicalFilters', () => {
  it('returns empty URLSearchParams for empty filters', () => {
    const params = serializeCanonicalFilters({});
    expect(params.toString()).toBe('');
  });

  it('serializes a single dimension', () => {
    const params = serializeCanonicalFilters({ l: [120] });
    expect(params.get('l')).toBe('120');
    expect(params.toString()).toBe('l=120');
  });

  it('serializes multiple dimensions in alphabetical order', () => {
    const params = serializeCanonicalFilters({
      t: [36],
      l: [120],
      c: [6],
      q: [3],
    });
    // Canonical order is c, l, q, t
    const keys = [...params.keys()];
    expect(keys).toEqual(['c', 'l', 'q', 't']);
  });

  it('includes match mode', () => {
    const params = serializeCanonicalFilters({ l: [120], match: 'any' });
    expect(params.get('l')).toBe('120');
    expect(params.get('match')).toBe('any');
  });

  it('serializes dp param', () => {
    const params = serializeCanonicalFilters({ dp: 'medium' });
    expect(params.get('dp')).toBe('medium');
  });

  it('serializes dp in canonical order (after ct, before id)', () => {
    const params = serializeCanonicalFilters({ l: [120], dp: 'quick' });
    const keys = [...params.keys()];
    const dpIdx = keys.indexOf('dp');
    const lIdx = keys.indexOf('l');
    expect(dpIdx).toBeLessThan(lIdx);
  });

  it('omits dp when undefined', () => {
    const params = serializeCanonicalFilters({ l: [120] });
    expect(params.has('dp')).toBe(false);
  });
});

// ─── serializeContextUrl ───────────────────────────────────────────

describe('serializeContextUrl', () => {
  it('serializes a simple route without filters', () => {
    const route: ContextRoute = {
      dimension: 'training',
      slug: 'beginner',
      filters: {},
    };
    expect(serializeContextUrl(route)).toBe('/contexts/training/beginner');
  });

  it('serializes a route with filters', () => {
    const route: ContextRoute = {
      dimension: 'training',
      slug: 'beginner',
      filters: { l: [120], t: [36] },
    };
    expect(serializeContextUrl(route)).toBe(
      '/contexts/training/beginner?l=120&t=36',
    );
  });

  it('includes offset when defined', () => {
    const route: ContextRoute = {
      dimension: 'training',
      slug: 'beginner',
      filters: {},
      offset: 42,
    };
    const url = serializeContextUrl(route);
    expect(url).toContain('offset=42');
  });

  it('includes id when defined', () => {
    const route: ContextRoute = {
      dimension: 'training',
      slug: 'beginner',
      filters: {},
      id: 'fc38f029',
    };
    const url = serializeContextUrl(route);
    expect(url).toContain('id=fc38f029');
  });

  it('serializes a full URL with all params in canonical order', () => {
    const route: ContextRoute = {
      dimension: 'technique',
      slug: 'net',
      filters: { l: [120], t: [36] },
      offset: 5,
      id: 'abc123',
    };
    const url = serializeContextUrl(route);
    // Canonical order: c, id, l, match, offset, q, t
    expect(url).toBe('/contexts/technique/net?id=abc123&l=120&offset=5&t=36');
  });
});

// ─── parseContextUrl ───────────────────────────────────────────────

describe('parseContextUrl', () => {
  it('parses a valid training context', () => {
    const result = parseContextUrl('/contexts/training/beginner', '');
    expect(result).toEqual({
      dimension: 'training',
      slug: 'beginner',
      filters: {},
    });
  });

  it('parses a valid technique context', () => {
    const result = parseContextUrl('/contexts/technique/net', '');
    expect(result).toEqual({
      dimension: 'technique',
      slug: 'net',
      filters: {},
    });
  });

  it('parses a valid collection context', () => {
    const result = parseContextUrl('/contexts/collection/cho-chikun', '');
    expect(result).toEqual({
      dimension: 'collection',
      slug: 'cho-chikun',
      filters: {},
    });
  });

  it('returns null for an invalid dimension', () => {
    expect(parseContextUrl('/contexts/invalid/slug', '')).toBeNull();
  });

  it('returns null for a missing slug', () => {
    expect(parseContextUrl('/contexts/training', '')).toBeNull();
    expect(parseContextUrl('/contexts/training/', '')).toBeNull();
  });

  it('returns null for a non-context path', () => {
    expect(parseContextUrl('/modes/daily', '')).toBeNull();
    expect(parseContextUrl('/', '')).toBeNull();
    expect(parseContextUrl('/training', '')).toBeNull();
  });

  it('includes filters parsed from search string', () => {
    const result = parseContextUrl('/contexts/training/beginner', '?l=120&t=36');
    expect(result).toEqual({
      dimension: 'training',
      slug: 'beginner',
      filters: { l: [120], t: [36] },
    });
  });

  it('round-trips: serialize → parse → same result', () => {
    const original: ContextRoute = {
      dimension: 'collection',
      slug: 'cho-chikun',
      filters: { l: [120, 160], t: [36] },
      offset: 10,
      id: 'abc',
    };
    const url = serializeContextUrl(original);
    const qIndex = url.indexOf('?');
    const pathname = qIndex >= 0 ? url.slice(0, qIndex) : url;
    const search = qIndex >= 0 ? url.slice(qIndex) : '';
    const parsed = parseContextUrl(pathname, search);

    expect(parsed).toEqual(original);
  });
});

// ─── canonicalize ──────────────────────────────────────────────────

describe('canonicalize', () => {
  it('returns null when URL is already canonical', () => {
    const url = new URL('http://localhost/contexts/training/beginner?l=120&t=36');
    expect(canonicalize(url)).toBeNull();
  });

  it('sorts unsorted params', () => {
    // t before l is not canonical order
    const url = new URL('http://localhost/contexts/training/beginner?t=36&l=120');
    const result = canonicalize(url);
    expect(result).not.toBeNull();
    expect(result!.search).toBe('?l=120&t=36');
  });

  it('deduplicates filter values', () => {
    const url = new URL('http://localhost/contexts/training/beginner?l=120,120,160');
    const result = canonicalize(url);
    expect(result).not.toBeNull();
    expect(result!.searchParams.get('l')).toBe('120,160');
  });

  it('removes invalid filter values', () => {
    const url = new URL('http://localhost/contexts/training/beginner?l=120,abc');
    const result = canonicalize(url);
    expect(result).not.toBeNull();
    expect(result!.searchParams.get('l')).toBe('120');
  });

  it('removes empty filter arrays (all-invalid values)', () => {
    const url = new URL('http://localhost/contexts/training/beginner?l=abc');
    const result = canonicalize(url);
    expect(result).not.toBeNull();
    // l param should be completely removed
    expect(result!.searchParams.has('l')).toBe(false);
  });

  it('preserves unknown params (pass-through for future dimensions)', () => {
    const url = new URL('http://localhost/contexts/training/beginner?l=120&foo=bar');
    const result = canonicalize(url);
    // Unknown params are preserved after known canonical params
    if (result) {
      expect(result.searchParams.get('l')).toBe('120');
      expect(result.searchParams.get('foo')).toBe('bar');
    } else {
      // If already canonical (l=120 + foo=bar in that order), result is null
      expect(url.searchParams.get('foo')).toBe('bar');
    }
  });

  it('preserves dp in canonical form', () => {
    const url = new URL('http://localhost/contexts/training/beginner?dp=quick&l=120');
    // dp before l is canonical order, so should be null
    expect(canonicalize(url)).toBeNull();
  });

  it('reorders dp to canonical position', () => {
    const url = new URL('http://localhost/contexts/training/beginner?l=120&dp=deep');
    const result = canonicalize(url);
    expect(result).not.toBeNull();
    // dp comes before l in canonical order
    const search = result!.search.replace(/^\?/, '');
    expect(search).toBe('dp=deep&l=120');
  });
});

// ─── parseOffset ───────────────────────────────────────────────────

describe('parseOffset', () => {
  it('returns the offset for a valid value', () => {
    expect(parseOffset('?offset=42')).toBe(42);
  });

  it('returns undefined for a negative value', () => {
    expect(parseOffset('?offset=-1')).toBeUndefined();
  });

  it('returns undefined for a non-integer value', () => {
    expect(parseOffset('?offset=3.14')).toBeUndefined();
  });

  it('returns undefined when offset is missing', () => {
    expect(parseOffset('')).toBeUndefined();
    expect(parseOffset('?l=120')).toBeUndefined();
  });
});

// ─── parseId ───────────────────────────────────────────────────────

describe('parseId', () => {
  it('returns the id when present', () => {
    expect(parseId('?id=fc38f029')).toBe('fc38f029');
  });

  it('returns undefined for empty id', () => {
    expect(parseId('?id=')).toBeUndefined();
  });

  it('returns undefined when id is missing', () => {
    expect(parseId('')).toBeUndefined();
    expect(parseId('?l=120')).toBeUndefined();
  });
});
