/**
 * Unit tests for useContentType hook.
 *
 * Tests:
 * - Returns default value (0 = All Types) when no localStorage
 * - Persists to localStorage on set
 * - Validates invalid values
 * - getContentType snapshot
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  getContentType,
  setContentType,
  _resetContentTypeForTesting,
  CONTENT_TYPE_KEY,
  DEFAULT_CONTENT_TYPE,
} from '@/hooks/useContentType';

describe('useContentType store', () => {
  beforeEach(() => {
    _resetContentTypeForTesting();
    localStorage.clear();
  });

  it('returns default (0 = All Types) when localStorage is empty', () => {
    expect(getContentType()).toBe(DEFAULT_CONTENT_TYPE);
    expect(DEFAULT_CONTENT_TYPE).toBe(0);
  });

  it('reads stored value from localStorage', () => {
    localStorage.setItem(CONTENT_TYPE_KEY, '2');
    _resetContentTypeForTesting(); // Reset cache so it re-reads
    expect(getContentType()).toBe(2);
  });

  it('persists value to localStorage on set', () => {
    setContentType(1);
    expect(localStorage.getItem(CONTENT_TYPE_KEY)).toBe('1');
    expect(getContentType()).toBe(1);
  });

  it('validates invalid stored value', () => {
    localStorage.setItem(CONTENT_TYPE_KEY, '99');
    _resetContentTypeForTesting();
    expect(getContentType()).toBe(DEFAULT_CONTENT_TYPE);
  });

  it('validates non-numeric stored value', () => {
    localStorage.setItem(CONTENT_TYPE_KEY, '"bad"');
    _resetContentTypeForTesting();
    expect(getContentType()).toBe(DEFAULT_CONTENT_TYPE);
  });
});
