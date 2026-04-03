/**
 * Tests for PageNavigator component.
 * @module tests/unit/page-navigator.test
 */

import { describe, it, expect } from 'vitest';
import { computeVisiblePages } from '../../src/components/shared/PageNavigator';

// Note: Full component rendering tests require preact testing-library.
// These tests cover the pure algorithmic logic (page number computation).

describe('computeVisiblePages', () => {
  it('shows all pages when total <= MAX_VISIBLE_PAGES (7)', () => {
    expect(computeVisiblePages(1, 5)).toEqual([1, 2, 3, 4, 5]);
    expect(computeVisiblePages(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7]);
  });

  it('shows single page', () => {
    expect(computeVisiblePages(1, 1)).toEqual([1]);
  });

  it('shows 2 pages', () => {
    expect(computeVisiblePages(1, 2)).toEqual([1, 2]);
  });

  it('shows ellipsis at end when on first page of large set', () => {
    const pages = computeVisiblePages(1, 20);
    // [1, 2, null, 20]
    expect(pages[0]).toBe(1);
    expect(pages[1]).toBe(2);
    expect(pages).toContain(null);
    expect(pages[pages.length - 1]).toBe(20);
  });

  it('shows ellipsis at start when on last page of large set', () => {
    const pages = computeVisiblePages(20, 20);
    // [1, null, 19, 20]
    expect(pages[0]).toBe(1);
    expect(pages).toContain(null);
    expect(pages[pages.length - 1]).toBe(20);
    expect(pages[pages.length - 2]).toBe(19);
  });

  it('shows ellipsis on both sides when in middle', () => {
    const pages = computeVisiblePages(10, 20);
    // [1, null, 9, 10, 11, null, 20]
    expect(pages[0]).toBe(1);
    expect(pages[1]).toBeNull();
    expect(pages).toContain(9);
    expect(pages).toContain(10);
    expect(pages).toContain(11);
    expect(pages[pages.length - 1]).toBe(20);
  });

  it('always includes first page', () => {
    for (let current = 1; current <= 20; current++) {
      const pages = computeVisiblePages(current, 20);
      expect(pages[0]).toBe(1);
    }
  });

  it('always includes last page for multi-page sets', () => {
    for (let current = 1; current <= 20; current++) {
      const pages = computeVisiblePages(current, 20);
      expect(pages[pages.length - 1]).toBe(20);
    }
  });

  it('always includes current page', () => {
    for (let current = 1; current <= 20; current++) {
      const pages = computeVisiblePages(current, 20);
      expect(pages).toContain(current);
    }
  });

  it('page numbers are in ascending order (ignoring nulls)', () => {
    for (let current = 1; current <= 20; current++) {
      const pages = computeVisiblePages(current, 20);
      const numbers = pages.filter((p): p is number => p !== null);
      for (let i = 1; i < numbers.length; i++) {
        expect(numbers[i]!).toBeGreaterThan(numbers[i - 1]!);
      }
    }
  });

  it('no ellipsis when pages fit within window', () => {
    const pages = computeVisiblePages(4, 7);
    expect(pages).not.toContain(null);
    expect(pages).toEqual([1, 2, 3, 4, 5, 6, 7]);
  });
});
