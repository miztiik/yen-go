/**
 * Tests for the useBrowseParams hook.
 * @module tests/unit/useBrowseParams.test
 *
 * Covers: default reading, URL sync, setParam, clearParams,
 * read-merge-write preservation, popstate handling, and RC-1 guard.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useBrowseParams } from '../../src/hooks/useBrowseParams';

// ─── Helpers ───────────────────────────────────────────────────────

let replaceStateSpy: ReturnType<typeof vi.fn>;
const originalLocation = window.location;
const originalHistory = window.history;

function mockLocation(pathname: string, search: string = '', hash: string = ''): void {
  Object.defineProperty(window, 'location', {
    value: { pathname, search, hash },
    writable: true,
    configurable: true,
  });
}

beforeEach(() => {
  replaceStateSpy = vi.fn();
  Object.defineProperty(window, 'history', {
    value: { ...originalHistory, replaceState: replaceStateSpy, state: null },
    writable: true,
    configurable: true,
  });
  mockLocation('/technique', '');
});

afterEach(() => {
  Object.defineProperty(window, 'location', {
    value: originalLocation,
    writable: true,
    configurable: true,
  });
  Object.defineProperty(window, 'history', {
    value: originalHistory,
    writable: true,
    configurable: true,
  });
});

// ─── Defaults ──────────────────────────────────────────────────────

describe('useBrowseParams — defaults', () => {
  it('returns defaults when URL has no params', () => {
    const { result } = renderHook(() => useBrowseParams({ cat: 'all', s: 'name' }));
    expect(result.current.params).toEqual({ cat: 'all', s: 'name' });
  });

  it('reads existing URL params on mount', () => {
    mockLocation('/technique', '?cat=tesuji&s=count');
    const { result } = renderHook(() => useBrowseParams({ cat: 'all', s: 'name' }));
    expect(result.current.params).toEqual({ cat: 'tesuji', s: 'count' });
  });

  it('uses default for missing params, URL value for present ones', () => {
    mockLocation('/technique', '?cat=tesuji');
    const { result } = renderHook(() => useBrowseParams({ cat: 'all', s: 'name' }));
    expect(result.current.params).toEqual({ cat: 'tesuji', s: 'name' });
  });
});

// ─── setParam ──────────────────────────────────────────────────────

describe('useBrowseParams — setParam', () => {
  it('updates state and calls replaceState', () => {
    const { result } = renderHook(() => useBrowseParams({ cat: 'all', s: 'name' }));

    act(() => {
      result.current.setParam('cat', 'tesuji');
    });

    expect(result.current.params.cat).toBe('tesuji');
    expect(replaceStateSpy).toHaveBeenCalled();
    // URL should contain cat=tesuji but not s= (since s='name' is default)
    const url = replaceStateSpy.mock.calls[0][2] as string;
    expect(url).toContain('cat=tesuji');
    expect(url).not.toContain('s=');
  });

  it('omits default-valued params from URL', () => {
    mockLocation('/technique', '?cat=tesuji');
    const { result } = renderHook(() => useBrowseParams({ cat: 'all', s: 'name' }));

    act(() => {
      result.current.setParam('cat', 'all'); // reset to default
    });

    expect(result.current.params.cat).toBe('all');
    const url = replaceStateSpy.mock.calls[0][2] as string;
    expect(url).not.toContain('cat=');
  });

  it('preserves params NOT in managed keys (read-merge-write, RC-2)', () => {
    mockLocation('/technique', '?l=120&t=36');
    const { result } = renderHook(() => useBrowseParams({ cat: 'all' }));

    act(() => {
      result.current.setParam('cat', 'tesuji');
    });

    const url = replaceStateSpy.mock.calls[0][2] as string;
    expect(url).toContain('l=120');
    expect(url).toContain('t=36');
    expect(url).toContain('cat=tesuji');
  });
});

// ─── clearParams ───────────────────────────────────────────────────

describe('useBrowseParams — clearParams', () => {
  it('resets managed keys to defaults', () => {
    mockLocation('/technique', '?cat=tesuji&s=count');
    const { result } = renderHook(() => useBrowseParams({ cat: 'all', s: 'name' }));

    act(() => {
      result.current.clearParams();
    });

    expect(result.current.params).toEqual({ cat: 'all', s: 'name' });
  });

  it('preserves unmanaged params in URL', () => {
    mockLocation('/technique', '?cat=tesuji&l=120');
    const { result } = renderHook(() => useBrowseParams({ cat: 'all' }));

    act(() => {
      result.current.clearParams();
    });

    const url = replaceStateSpy.mock.calls[0][2] as string;
    expect(url).toContain('l=120');
    expect(url).not.toContain('cat=');
  });
});

// ─── popstate ──────────────────────────────────────────────────────

describe('useBrowseParams — popstate', () => {
  it('re-reads params on popstate with same pathname', () => {
    const { result } = renderHook(() => useBrowseParams({ cat: 'all' }));
    expect(result.current.params.cat).toBe('all');

    // Simulate browser back: URL changes but pathname stays the same
    mockLocation('/technique', '?cat=objective');
    act(() => {
      window.dispatchEvent(new PopStateEvent('popstate'));
    });

    expect(result.current.params.cat).toBe('objective');
  });

  it('ignores popstate with different pathname (RC-1 guard)', () => {
    const { result } = renderHook(() => useBrowseParams({ cat: 'all' }));
    expect(result.current.params.cat).toBe('all');

    // Simulate navigation to a different page
    mockLocation('/collections', '?cat=featured');
    act(() => {
      window.dispatchEvent(new PopStateEvent('popstate'));
    });

    // Should NOT update — pathname changed
    expect(result.current.params.cat).toBe('all');
  });
});

// ─── Dual-hook integration (RC-5) ─────────────────────────────────

describe('useBrowseParams — dual-hook coexistence (RC-5)', () => {
  it('useBrowseParams preserves canonical params written by useCanonicalUrl', () => {
    // Simulate: useCanonicalUrl has already written l=120 to URL
    mockLocation('/technique', '?l=120');
    const { result } = renderHook(() => useBrowseParams({ cat: 'all' }));

    act(() => {
      result.current.setParam('cat', 'tesuji');
    });

    const url = replaceStateSpy.mock.calls[0][2] as string;
    expect(url).toContain('l=120');
    expect(url).toContain('cat=tesuji');
  });

  it('useBrowseParams preserves multiple canonical params', () => {
    mockLocation('/technique', '?l=120&t=36&offset=10');
    const { result } = renderHook(() => useBrowseParams({ cat: 'all', s: 'name' }));

    act(() => {
      result.current.setParam('s', 'count');
    });

    const url = replaceStateSpy.mock.calls[0][2] as string;
    expect(url).toContain('l=120');
    expect(url).toContain('t=36');
    expect(url).toContain('offset=10');
    expect(url).toContain('s=count');
  });
});
