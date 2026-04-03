/**
 * Tests for configService module.
 * @module tests/unit/config-service.test
 *
 * Ported from id-maps.test.ts (WP4 step 4.9).
 */

import { describe, it, expect } from 'vitest';
import {
  levelIdToSlug,
  tagIdToSlug,
  levelSlugToId,
  tagSlugToId,
  resolveDistribution,
  resolveLevelDistribution,
  resolveTagDistribution,
  getAllLevels,
  getAllTags,
  getLevelMeta,
  getLevelMetaById,
  getTagMeta,
  getTagMetaById,
  getTagsByCategory,
  LEVEL_ID_MAP,
  LEVEL_SLUG_MAP,
  TAG_ID_MAP,
  TAG_SLUG_MAP,
} from '../../src/services/configService';

describe('configService', () => {
  // ─── Level Lookups ─────────────────────────────────────────────

  describe('level maps', () => {
    it('has all 9 levels', () => {
      expect(LEVEL_ID_MAP.size).toBe(9);
    });

    it('maps kyu levels correctly', () => {
      expect(levelIdToSlug(110)).toBe('novice');
      expect(levelIdToSlug(120)).toBe('beginner');
      expect(levelIdToSlug(130)).toBe('elementary');
      expect(levelIdToSlug(140)).toBe('intermediate');
      expect(levelIdToSlug(150)).toBe('upper-intermediate');
      expect(levelIdToSlug(160)).toBe('advanced');
    });

    it('maps dan levels correctly', () => {
      expect(levelIdToSlug(210)).toBe('low-dan');
      expect(levelIdToSlug(220)).toBe('high-dan');
      expect(levelIdToSlug(230)).toBe('expert');
    });

    it('round-trips all levels via slug', () => {
      for (const [id, slug] of LEVEL_ID_MAP) {
        expect(levelSlugToId(slug)).toBe(id);
      }
    });

    it('LEVEL_SLUG_MAP has all 9 entries', () => {
      expect(LEVEL_SLUG_MAP.size).toBe(9);
    });
  });

  // ─── Tag Lookups ───────────────────────────────────────────────

  describe('tag maps', () => {
    it('has all 28 tags', () => {
      expect(TAG_ID_MAP.size).toBe(28);
    });

    it('maps objective tags', () => {
      expect(tagIdToSlug(10)).toBe('life-and-death');
      expect(tagIdToSlug(12)).toBe('ko');
      expect(tagIdToSlug(14)).toBe('living');
      expect(tagIdToSlug(16)).toBe('seki');
    });

    it('maps tesuji tags', () => {
      expect(tagIdToSlug(30)).toBe('snapback');
      expect(tagIdToSlug(36)).toBe('net');
      expect(tagIdToSlug(42)).toBe('nakade');
      expect(tagIdToSlug(52)).toBe('tesuji');
    });

    it('maps technique tags', () => {
      expect(tagIdToSlug(60)).toBe('capture-race');
      expect(tagIdToSlug(62)).toBe('eye-shape');
      expect(tagIdToSlug(74)).toBe('corner');
      expect(tagIdToSlug(82)).toBe('fuseki');
    });

    it('round-trips all tags via slug', () => {
      for (const [id, slug] of TAG_ID_MAP) {
        expect(tagSlugToId(slug)).toBe(id);
      }
    });

    it('TAG_SLUG_MAP has all 28 entries', () => {
      expect(TAG_SLUG_MAP.size).toBe(28);
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
    it('converts numeric keys to slugs (levels)', () => {
      const dist = { '120': 5, '160': 3, '210': 2 };
      const result = resolveLevelDistribution(dist);
      expect(result).toEqual({
        beginner: 5,
        advanced: 3,
        'low-dan': 2,
      });
    });

    it('keeps numeric key as string for unknown IDs', () => {
      const dist = { '120': 5, '999': 1 };
      const result = resolveLevelDistribution(dist);
      expect(result).toEqual({
        beginner: 5,
        '999': 1,
      });
    });

    it('works with tag IDs', () => {
      const dist = { '12': 8, '36': 3 };
      const result = resolveTagDistribution(dist);
      expect(result).toEqual({
        ko: 8,
        net: 3,
      });
    });

    it('handles empty distribution', () => {
      const result = resolveLevelDistribution({});
      expect(result).toEqual({});
    });

    it('works with generic function + custom resolver', () => {
      const dist = { '120': 5, '160': 3 };
      const result = resolveDistribution(dist, levelIdToSlug);
      expect(result).toEqual({ beginner: 5, advanced: 3 });
    });
  });

  // ─── Metadata Accessors ───────────────────────────────────────

  describe('getAllLevels', () => {
    it('returns 9 levels in order', () => {
      const levels = getAllLevels();
      expect(levels).toHaveLength(9);
      expect(levels[0].slug).toBe('novice');
      expect(levels[8].slug).toBe('expert');
    });

    it('each level has required fields', () => {
      for (const level of getAllLevels()) {
        expect(level.id).toBeGreaterThan(0);
        expect(level.slug).toBeTruthy();
        expect(level.name).toBeTruthy();
        expect(level.shortName).toBeTruthy();
        expect(level.rankRange.min).toBeTruthy();
        expect(level.rankRange.max).toBeTruthy();
      }
    });
  });

  describe('getAllTags', () => {
    it('returns all 28 tags', () => {
      const tags = getAllTags();
      expect(Object.keys(tags)).toHaveLength(28);
    });

    it('each tag has required fields', () => {
      for (const tag of Object.values(getAllTags())) {
        expect(tag.id).toBeGreaterThan(0);
        expect(tag.slug).toBeTruthy();
        expect(tag.name).toBeTruthy();
        expect(tag.category).toMatch(/^(objective|tesuji|technique)$/);
      }
    });
  });

  describe('getLevelMeta', () => {
    it('returns metadata for valid slug', () => {
      const meta = getLevelMeta('beginner');
      expect(meta).toBeDefined();
      expect(meta!.id).toBe(120);
      expect(meta!.name).toBe('Beginner');
    });

    it('returns undefined for invalid slug', () => {
      expect(getLevelMeta('nonexistent')).toBeUndefined();
    });
  });

  describe('getLevelMetaById', () => {
    it('returns metadata for valid ID', () => {
      const meta = getLevelMetaById(120);
      expect(meta).toBeDefined();
      expect(meta!.slug).toBe('beginner');
    });

    it('returns undefined for invalid ID', () => {
      expect(getLevelMetaById(999)).toBeUndefined();
    });
  });

  describe('getTagMeta', () => {
    it('returns metadata for valid slug', () => {
      const meta = getTagMeta('ladder');
      expect(meta).toBeDefined();
      expect(meta!.id).toBe(34);
      expect(meta!.name).toBe('Ladder');
    });

    it('returns undefined for invalid slug', () => {
      expect(getTagMeta('nonexistent')).toBeUndefined();
    });
  });

  describe('getTagMetaById', () => {
    it('returns metadata for valid ID', () => {
      const meta = getTagMetaById(34);
      expect(meta).toBeDefined();
      expect(meta!.slug).toBe('ladder');
    });

    it('returns undefined for invalid ID', () => {
      expect(getTagMetaById(999)).toBeUndefined();
    });
  });

  describe('getTagsByCategory', () => {
    it('returns objective tags', () => {
      const tags = getTagsByCategory('objective');
      expect(tags.length).toBe(4);
      expect(tags.map(t => t.slug)).toContain('life-and-death');
      expect(tags.map(t => t.slug)).toContain('ko');
    });

    it('returns tesuji tags', () => {
      const tags = getTagsByCategory('tesuji');
      expect(tags.length).toBe(12);
      expect(tags.map(t => t.slug)).toContain('ladder');
      expect(tags.map(t => t.slug)).toContain('snapback');
    });

    it('returns technique tags', () => {
      const tags = getTagsByCategory('technique');
      expect(tags.length).toBe(12);
      expect(tags.map(t => t.slug)).toContain('capture-race');
      expect(tags.map(t => t.slug)).toContain('fuseki');
    });
  });
});
