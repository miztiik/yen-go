/**
 * Tests for id-maps module.
 * @module tests/unit/id-maps.test
 */

import { describe, it, expect } from 'vitest';
import {
  LEVEL_ID_TO_SLUG,
  LEVEL_SLUG_TO_ID,
  TAG_ID_TO_SLUG,
  TAG_SLUG_TO_ID,
  levelIdToSlug,
  tagIdToSlug,
  levelSlugToId,
  tagSlugToId,
  resolveDistribution,
} from '../../src/lib/puzzle/id-maps';

describe('id-maps', () => {
  // ─── Level Maps ────────────────────────────────────────────────

  describe('LEVEL_ID_TO_SLUG', () => {
    it('maps all 9 levels', () => {
      expect(Object.keys(LEVEL_ID_TO_SLUG)).toHaveLength(9);
    });

    it('maps kyu levels correctly', () => {
      expect(LEVEL_ID_TO_SLUG[110]).toBe('novice');
      expect(LEVEL_ID_TO_SLUG[120]).toBe('beginner');
      expect(LEVEL_ID_TO_SLUG[130]).toBe('elementary');
      expect(LEVEL_ID_TO_SLUG[140]).toBe('intermediate');
      expect(LEVEL_ID_TO_SLUG[150]).toBe('upper-intermediate');
      expect(LEVEL_ID_TO_SLUG[160]).toBe('advanced');
    });

    it('maps dan levels correctly', () => {
      expect(LEVEL_ID_TO_SLUG[210]).toBe('low-dan');
      expect(LEVEL_ID_TO_SLUG[220]).toBe('high-dan');
      expect(LEVEL_ID_TO_SLUG[230]).toBe('expert');
    });
  });

  describe('LEVEL_SLUG_TO_ID (reverse)', () => {
    it('round-trips all levels', () => {
      for (const [idStr, slug] of Object.entries(LEVEL_ID_TO_SLUG)) {
        expect(LEVEL_SLUG_TO_ID[slug]).toBe(Number(idStr));
      }
    });
  });

  // ─── Tag Maps ──────────────────────────────────────────────────

  describe('TAG_ID_TO_SLUG', () => {
    it('maps all 28 tags', () => {
      expect(Object.keys(TAG_ID_TO_SLUG)).toHaveLength(28);
    });

    it('maps objective tags', () => {
      expect(TAG_ID_TO_SLUG[10]).toBe('life-and-death');
      expect(TAG_ID_TO_SLUG[12]).toBe('ko');
      expect(TAG_ID_TO_SLUG[14]).toBe('living');
      expect(TAG_ID_TO_SLUG[16]).toBe('seki');
    });

    it('maps tesuji tags', () => {
      expect(TAG_ID_TO_SLUG[30]).toBe('snapback');
      expect(TAG_ID_TO_SLUG[36]).toBe('net');
      expect(TAG_ID_TO_SLUG[42]).toBe('nakade');
      expect(TAG_ID_TO_SLUG[52]).toBe('tesuji');
    });

    it('maps technique tags', () => {
      expect(TAG_ID_TO_SLUG[60]).toBe('capture-race');
      expect(TAG_ID_TO_SLUG[62]).toBe('eye-shape');
      expect(TAG_ID_TO_SLUG[74]).toBe('corner');
      expect(TAG_ID_TO_SLUG[82]).toBe('fuseki');
    });
  });

  describe('TAG_SLUG_TO_ID (reverse)', () => {
    it('round-trips all tags', () => {
      for (const [idStr, slug] of Object.entries(TAG_ID_TO_SLUG)) {
        expect(TAG_SLUG_TO_ID[slug]).toBe(Number(idStr));
      }
    });
  });

  // ─── Lookup Helpers ────────────────────────────────────────────

  describe('levelIdToSlug', () => {
    it('resolves known IDs', () => {
      expect(levelIdToSlug(120)).toBe('beginner');
      expect(levelIdToSlug(210)).toBe('low-dan');
    });

    it('returns stringified ID for unknown values', () => {
      expect(levelIdToSlug(999)).toBe('999');
    });
  });

  describe('tagIdToSlug', () => {
    it('resolves known IDs', () => {
      expect(tagIdToSlug(36)).toBe('net');
      expect(tagIdToSlug(10)).toBe('life-and-death');
    });

    it('returns stringified ID for unknown values', () => {
      expect(tagIdToSlug(999)).toBe('999');
    });
  });

  describe('levelSlugToId', () => {
    it('resolves known slugs', () => {
      expect(levelSlugToId('beginner')).toBe(120);
      expect(levelSlugToId('expert')).toBe(230);
    });

    it('returns undefined for unknown slugs', () => {
      expect(levelSlugToId('nonexistent')).toBeUndefined();
    });
  });

  describe('tagSlugToId', () => {
    it('resolves known slugs', () => {
      expect(tagSlugToId('net')).toBe(36);
      expect(tagSlugToId('ko')).toBe(12);
    });

    it('returns undefined for unknown slugs', () => {
      expect(tagSlugToId('nonexistent')).toBeUndefined();
    });
  });

  // ─── Distribution Resolution ──────────────────────────────────

  describe('resolveDistribution', () => {
    it('converts numeric keys to slugs', () => {
      const dist = { '120': 5, '160': 3, '210': 2 };
      const result = resolveDistribution(dist, LEVEL_ID_TO_SLUG);
      expect(result).toEqual({
        beginner: 5,
        advanced: 3,
        'low-dan': 2,
      });
    });

    it('keeps numeric key as string for unknown IDs', () => {
      const dist = { '120': 5, '999': 1 };
      const result = resolveDistribution(dist, LEVEL_ID_TO_SLUG);
      expect(result).toEqual({
        beginner: 5,
        '999': 1,
      });
    });

    it('works with tag IDs', () => {
      const dist = { '12': 8, '36': 3 };
      const result = resolveDistribution(dist, TAG_ID_TO_SLUG);
      expect(result).toEqual({
        ko: 8,
        net: 3,
      });
    });

    it('handles empty distribution', () => {
      const result = resolveDistribution({}, LEVEL_ID_TO_SLUG);
      expect(result).toEqual({});
    });
  });
});
