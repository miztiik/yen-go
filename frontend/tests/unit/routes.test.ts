/**
 * Tests for the routes module.
 * @module tests/unit/routes.test
 *
 * Covers parseRoute, serializeRoute, navigateTo, replaceRoute,
 * isContextRoute, and isPuzzleSolvingRoute.
 *
 * Note: In the test environment, `import.meta.env.BASE_URL` defaults to `'/'`
 * so `BASE` resolves to `''`.  All serialized paths appear without a base
 * prefix (e.g. `/training`).  In production builds with `base: '/yen-go/'`,
 * paths are prefixed (e.g. `/yen-go/training`).  The base-stripping and
 * base-prepending logic is trivial string manipulation — correctness is
 * validated by the dev server integration and the round-trip tests below.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  parseRoute,
  serializeRoute,
  navigateTo,
  replaceRoute,
  isContextRoute,
  isPuzzleSolvingRoute,
} from '../../src/lib/routing/routes';
import type { Route } from '../../src/lib/routing/routes';

// ─── Helpers ───────────────────────────────────────────────────────

/**
 * Replace `window.location` with a minimal stub for testing route
 * serialization checks inside navigateTo / replaceRoute.
 */
function mockWindowLocation(pathname: string, search: string = ''): void {
  Object.defineProperty(window, 'location', {
    value: { pathname, search, hash: '' },
    writable: true,
    configurable: true,
  });
}

// ─── parseRoute ────────────────────────────────────────────────────

describe('parseRoute', () => {
  it('parses "/" as home', () => {
    expect(parseRoute('/', '')).toEqual({ type: 'home' });
  });

  it('parses empty string as home', () => {
    expect(parseRoute('', '')).toEqual({ type: 'home' });
  });

  it('parses a training context route', () => {
    const route = parseRoute('/contexts/training/beginner', '');
    expect(route).toEqual({
      type: 'context',
      dimension: 'training',
      slug: 'beginner',
      filters: {},
    });
  });

  it('parses a technique context with filters', () => {
    const route = parseRoute('/contexts/technique/net', '?l=120');
    expect(route).toEqual({
      type: 'context',
      dimension: 'technique',
      slug: 'net',
      filters: { l: [120] },
    });
  });

  it('parses a collection context with offset and id', () => {
    const route = parseRoute('/contexts/collection/cho-chikun', '?offset=42&id=abc');
    expect(route).toEqual({
      type: 'context',
      dimension: 'collection',
      slug: 'cho-chikun',
      filters: {},
      offset: 42,
      id: 'abc',
    });
  });

  it('parses a quality context route', () => {
    const route = parseRoute('/contexts/quality/standard', '');
    expect(route).toEqual({
      type: 'context',
      dimension: 'quality',
      slug: 'standard',
      filters: {},
    });
  });

  it('parses /modes/daily', () => {
    expect(parseRoute('/modes/daily', '')).toEqual({ type: 'modes-daily' });
  });

  it('parses /modes/daily/{date}', () => {
    expect(parseRoute('/modes/daily/2026-02-22', '')).toEqual({
      type: 'modes-daily-date',
      date: '2026-02-22',
    });
  });

  it('parses /modes/random', () => {
    expect(parseRoute('/modes/random', '')).toEqual({ type: 'modes-random' });
  });

  it('parses /modes/rush', () => {
    expect(parseRoute('/modes/rush', '')).toEqual({ type: 'modes-rush' });
  });

  it('parses /collections', () => {
    expect(parseRoute('/collections', '')).toEqual({ type: 'collections-browse' });
  });

  it('parses /technique', () => {
    expect(parseRoute('/technique', '')).toEqual({ type: 'technique-browse' });
  });

  it('parses /training', () => {
    expect(parseRoute('/training', '')).toEqual({ type: 'training-browse' });
  });

  it('parses /progress', () => {
    expect(parseRoute('/progress', '')).toEqual({ type: 'progress' });
  });

  it('parses /smart-practice without techniques', () => {
    expect(parseRoute('/smart-practice', '')).toEqual({ type: 'smart-practice' });
  });

  it('parses /smart-practice with techniques', () => {
    expect(parseRoute('/smart-practice', '?techniques=ladder,snapback')).toEqual({
      type: 'smart-practice',
      techniques: ['ladder', 'snapback'],
    });
  });

  it('parses /smart-practice ignoring empty technique segments', () => {
    expect(parseRoute('/smart-practice', '?techniques=ladder,,snapback')).toEqual({
      type: 'smart-practice',
      techniques: ['ladder', 'snapback'],
    });
  });

  it('falls back to home for unknown path', () => {
    expect(parseRoute('/unknown/path', '')).toEqual({ type: 'home' });
  });

  it('normalises trailing slash', () => {
    const withSlash = parseRoute('/training/', '');
    const withoutSlash = parseRoute('/training', '');
    expect(withSlash).toEqual(withoutSlash);
  });

  it('falls back to home for invalid daily date format', () => {
    expect(parseRoute('/modes/daily/not-a-date', '')).toEqual({ type: 'home' });
  });

  // ─── Shorthand route aliases (T8) ─────────────────────────────────

  it('parses /collection/{slug} as context route (shorthand)', () => {
    const route = parseRoute('/collection/cho-chikun-elementary', '');
    expect(route).toEqual({
      type: 'context',
      dimension: 'collection',
      slug: 'cho-chikun-elementary',
      filters: {},
    });
  });

  it('parses /training/{slug} as context route (shorthand)', () => {
    const route = parseRoute('/training/intermediate', '');
    expect(route).toEqual({
      type: 'context',
      dimension: 'training',
      slug: 'intermediate',
      filters: {},
    });
  });

  it('parses /technique/{slug} as context route (shorthand)', () => {
    const route = parseRoute('/technique/life-and-death', '');
    expect(route).toEqual({
      type: 'context',
      dimension: 'technique',
      slug: 'life-and-death',
      filters: {},
    });
  });

  it('shorthand /collection/{slug} preserves filters from query string', () => {
    const route = parseRoute('/collection/cho-chikun', '?l=120&t=36');
    expect(route).toEqual({
      type: 'context',
      dimension: 'collection',
      slug: 'cho-chikun',
      filters: { l: [120], t: [36] },
    });
  });

  it('shorthand /collection/{slug} parses offset and id', () => {
    const route = parseRoute('/collection/cho-chikun', '?offset=10&id=abc');
    expect(route).toEqual({
      type: 'context',
      dimension: 'collection',
      slug: 'cho-chikun',
      filters: {},
      offset: 10,
      id: 'abc',
    });
  });

  it('existing /contexts/collection/... still works (AC-11 regression)', () => {
    const canonical = parseRoute('/contexts/collection/cho-chikun', '?l=120');
    expect(canonical).toEqual({
      type: 'context',
      dimension: 'collection',
      slug: 'cho-chikun',
      filters: { l: [120] },
    });
  });

  it('shorthand routes decode URI components in slug', () => {
    const route = parseRoute('/technique/life%20and%20death', '');
    expect(route).toEqual({
      type: 'context',
      dimension: 'technique',
      slug: 'life and death',
      filters: {},
    });
  });
});

// ─── serializeRoute ────────────────────────────────────────────────

describe('serializeRoute', () => {
  it('serializes home to "/"', () => {
    expect(serializeRoute({ type: 'home' })).toBe('/');
  });

  it('serializes a context route', () => {
    const route: Route = {
      type: 'context',
      dimension: 'training',
      slug: 'beginner',
      filters: { l: [120] },
    };
    expect(serializeRoute(route)).toBe('/contexts/training/beginner?l=120');
  });

  it('serializes modes-daily', () => {
    expect(serializeRoute({ type: 'modes-daily' })).toBe('/modes/daily');
  });

  it('serializes modes-daily-date', () => {
    expect(serializeRoute({ type: 'modes-daily-date', date: '2026-02-22' })).toBe(
      '/modes/daily/2026-02-22',
    );
  });

  it('serializes modes-random', () => {
    expect(serializeRoute({ type: 'modes-random' })).toBe('/modes/random');
  });

  it('serializes modes-rush', () => {
    expect(serializeRoute({ type: 'modes-rush' })).toBe('/modes/rush');
  });

  it('serializes collections-browse', () => {
    expect(serializeRoute({ type: 'collections-browse' })).toBe('/collections');
  });

  it('serializes technique-browse', () => {
    expect(serializeRoute({ type: 'technique-browse' })).toBe('/technique');
  });

  it('serializes training-browse', () => {
    expect(serializeRoute({ type: 'training-browse' })).toBe('/training');
  });

  it('serializes progress', () => {
    expect(serializeRoute({ type: 'progress' })).toBe('/progress');
  });

  it('serializes smart-practice without techniques', () => {
    expect(serializeRoute({ type: 'smart-practice' })).toBe('/smart-practice');
  });

  it('serializes smart-practice with techniques', () => {
    expect(serializeRoute({ type: 'smart-practice', techniques: ['ladder', 'snapback'] })).toBe(
      '/smart-practice?techniques=ladder,snapback',
    );
  });

  it('round-trips: parse → serialize → same URL', () => {
    const cases: Array<[string, string]> = [
      ['/', ''],
      ['/modes/daily', ''],
      ['/modes/daily/2026-02-22', ''],
      ['/modes/random', ''],
      ['/modes/rush', ''],
      ['/collections', ''],
      ['/technique', ''],
      ['/training', ''],
      ['/contexts/training/beginner', ''],
      ['/contexts/training/beginner', '?l=120&t=36'],
      ['/contexts/collection/cho-chikun', '?id=abc&offset=42'],
      ['/progress', ''],
      ['/smart-practice', ''],
    ];

    for (const [pathname, search] of cases) {
      const route = parseRoute(pathname, search);
      const url = serializeRoute(route);
      const expectedUrl = search ? `${pathname}${search}` : pathname;
      expect(url).toBe(expectedUrl);
    }
  });
});

// ─── isContextRoute ────────────────────────────────────────────────

describe('isContextRoute', () => {
  it('returns true for a context route', () => {
    const route: Route = {
      type: 'context',
      dimension: 'training',
      slug: 'beginner',
      filters: {},
    };
    expect(isContextRoute(route)).toBe(true);
  });

  it('returns false for a non-context route', () => {
    expect(isContextRoute({ type: 'home' })).toBe(false);
    expect(isContextRoute({ type: 'modes-daily' })).toBe(false);
    expect(isContextRoute({ type: 'training-browse' })).toBe(false);
  });
});

// ─── isPuzzleSolvingRoute ──────────────────────────────────────────

describe('isPuzzleSolvingRoute', () => {
  it('returns true for a context route', () => {
    const route: Route = {
      type: 'context',
      dimension: 'training',
      slug: 'beginner',
      filters: {},
    };
    expect(isPuzzleSolvingRoute(route)).toBe(true);
  });

  it('returns true for modes-daily-date', () => {
    expect(
      isPuzzleSolvingRoute({ type: 'modes-daily-date', date: '2026-02-22' }),
    ).toBe(true);
  });

  it('returns false for home', () => {
    expect(isPuzzleSolvingRoute({ type: 'home' })).toBe(false);
  });

  it('returns false for modes-rush', () => {
    expect(isPuzzleSolvingRoute({ type: 'modes-rush' })).toBe(false);
  });
});

// ─── navigateTo ────────────────────────────────────────────────────

describe('navigateTo', () => {
  let pushStateSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    pushStateSpy = vi.fn();
    Object.defineProperty(window, 'history', {
      value: { pushState: pushStateSpy, replaceState: vi.fn() },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('calls pushState with the correct URL', () => {
    mockWindowLocation('/');
    navigateTo({ type: 'training-browse' });
    expect(pushStateSpy).toHaveBeenCalledWith(null, '', '/training');
  });

  it('does not push when URL matches current location', () => {
    mockWindowLocation('/training', '');
    navigateTo({ type: 'training-browse' });
    expect(pushStateSpy).not.toHaveBeenCalled();
  });

  it('pushes context routes with query string', () => {
    mockWindowLocation('/');
    const route: Route = {
      type: 'context',
      dimension: 'training',
      slug: 'beginner',
      filters: { l: [120] },
    };
    navigateTo(route);
    expect(pushStateSpy).toHaveBeenCalledWith(
      null,
      '',
      '/contexts/training/beginner?l=120',
    );
  });
});

// ─── replaceRoute ──────────────────────────────────────────────────

describe('replaceRoute', () => {
  let replaceStateSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    replaceStateSpy = vi.fn();
    Object.defineProperty(window, 'history', {
      value: { pushState: vi.fn(), replaceState: replaceStateSpy },
      writable: true,
      configurable: true,
    });
    mockWindowLocation('/');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('calls replaceState with the correct URL', () => {
    replaceRoute({ type: 'modes-daily' });
    expect(replaceStateSpy).toHaveBeenCalledWith(null, '', '/modes/daily');
  });

  it('calls replaceState even when URL matches current (unconditional)', () => {
    mockWindowLocation('/modes/daily', '');
    replaceRoute({ type: 'modes-daily' });
    // replaceRoute does NOT check current URL — always replaces
    expect(replaceStateSpy).toHaveBeenCalledWith(null, '', '/modes/daily');
  });
});
