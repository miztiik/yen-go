/**
 * Unit tests for level categories module.
 * Spec WP6 — config-derived category grouping.
 */

import { describe, it, expect } from 'vitest';
import { getCategoryLevels, getLevelCategory, CATEGORY_OPTIONS } from '../../src/lib/levels/categories';

describe('categories', () => {
  describe('getCategoryLevels', () => {
    it('should return all levels for "all" category', () => {
      const levels = getCategoryLevels('all');
      expect(levels.length).toBe(9);
    });

    it('should return kyu-low levels for "beginner" category', () => {
      const levels = getCategoryLevels('beginner');
      expect(levels).toContain('novice');
      expect(levels).toContain('beginner');
      expect(levels).toContain('elementary');
      expect(levels).not.toContain('intermediate');
    });

    it('should return kyu-mid levels for "intermediate" category', () => {
      const levels = getCategoryLevels('intermediate');
      expect(levels).toContain('intermediate');
      expect(levels).toContain('upper-intermediate');
      expect(levels).toContain('advanced');
      expect(levels).not.toContain('elementary');
      expect(levels).not.toContain('low-dan');
    });

    it('should return dan levels for "advanced" category', () => {
      const levels = getCategoryLevels('advanced');
      expect(levels).toContain('low-dan');
      expect(levels).toContain('high-dan');
      expect(levels).toContain('expert');
      expect(levels).not.toContain('advanced');
    });
  });

  describe('getLevelCategory', () => {
    it('should return "beginner" for novice (ID 110)', () => {
      expect(getLevelCategory('novice')).toBe('beginner');
    });

    it('should return "beginner" for elementary (ID 130, boundary)', () => {
      expect(getLevelCategory('elementary')).toBe('beginner');
    });

    it('should return "intermediate" for intermediate (ID 140, boundary)', () => {
      expect(getLevelCategory('intermediate')).toBe('intermediate');
    });

    it('should return "intermediate" for advanced (ID 160)', () => {
      expect(getLevelCategory('advanced')).toBe('intermediate');
    });

    it('should return "advanced" for low-dan (ID 210, boundary)', () => {
      expect(getLevelCategory('low-dan')).toBe('advanced');
    });

    it('should return "advanced" for expert (ID 230)', () => {
      expect(getLevelCategory('expert')).toBe('advanced');
    });

    it('should return "beginner" for unknown slug', () => {
      expect(getLevelCategory('unknown-level')).toBe('beginner');
    });
  });

  describe('CATEGORY_OPTIONS', () => {
    it('should have 4 options', () => {
      expect(CATEGORY_OPTIONS).toHaveLength(4);
    });

    it('should start with "all"', () => {
      expect(CATEGORY_OPTIONS[0]?.id).toBe('all');
    });
  });
});
