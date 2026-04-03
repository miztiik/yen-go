/**
 * Unit tests for formatSlug utility.
 *
 * Spec 132 — T103
 */

import { describe, it, expect } from 'vitest';
import { formatSlug } from '../../src/lib/slug-formatter';

describe('formatSlug', () => {
  describe('prefix stripping', () => {
    it('should strip "tag-" prefix and format', () => {
      expect(formatSlug('tag-life-and-death')).toBe('Life & Death');
    });

    it('should strip "level-" prefix and title-case', () => {
      expect(formatSlug('level-beginner')).toBe('Beginner');
    });

    it('should strip "level-" prefix for multi-word levels', () => {
      expect(formatSlug('level-upper-intermediate')).toBe('Upper Intermediate');
    });
  });

  describe('overrides', () => {
    it('should use override for "life-and-death"', () => {
      expect(formatSlug('life-and-death')).toBe('Life & Death');
    });

    it('should use override for "ko"', () => {
      expect(formatSlug('ko')).toBe('Ko');
    });

    it('should use override for "capturing-race"', () => {
      expect(formatSlug('capturing-race')).toBe('Capturing Race');
    });

    it('should use override for tag-prefixed overrides', () => {
      expect(formatSlug('tag-snapback')).toBe('Snapback');
    });
  });

  describe('title-casing', () => {
    it('should title-case unknown slugs', () => {
      expect(formatSlug('cho-chikun-elementary')).toBe('Cho Chikun Elementary');
    });

    it('should title-case single word slugs', () => {
      expect(formatSlug('advanced')).toBe('Advanced');
    });

    it('should title-case multi-hyphen slugs', () => {
      expect(formatSlug('some-long-slug-name')).toBe('Some Long Slug Name');
    });
  });

  describe('edge cases', () => {
    it('should return empty string for empty input', () => {
      expect(formatSlug('')).toBe('');
    });

    it('should handle single character slug', () => {
      expect(formatSlug('a')).toBe('A');
    });

    it('should handle slug with no hyphens', () => {
      expect(formatSlug('intermediate')).toBe('Intermediate');
    });
  });

  describe('config-driven lookups', () => {
    it('should use tag config for life-and-death', () => {
      expect(formatSlug('life-and-death')).toBe('Life & Death');
    });

    it('should use tag config for under-the-stones', () => {
      expect(formatSlug('under-the-stones')).toBe('Under the Stones');
    });
  });
});
