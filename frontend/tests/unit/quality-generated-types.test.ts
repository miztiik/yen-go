/**
 * Tests for quality config types.
 * @module tests/unit/quality-config.test
 */

import { describe, it, expect } from 'vitest';
import {
  QUALITY_SLUGS,
  QUALITY_COUNT,
  QUALITY_ID_MAP,
  QUALITY_SLUG_MAP,
  QUALITIES,
  getQualityId,
  getQualitySlug,
  isValidQuality,
  PUZZLE_QUALITY_INFO,
  DEFAULT_QUALITY_METRICS,
  DEFAULT_COMPLEXITY_METRICS,
  parseQualityMetrics,
  parseComplexityMetrics,
  getPuzzleQualityInfo,
  isValidPuzzleQualityLevel,
} from '../../src/lib/quality/config';

describe('Quality Generated Types', () => {
  describe('QUALITY_SLUGS', () => {
    it('contains exactly 5 quality slugs', () => {
      expect(QUALITY_SLUGS).toHaveLength(5);
      expect(QUALITY_COUNT).toBe(5);
    });

    it('is ordered from worst to best', () => {
      expect(QUALITY_SLUGS).toEqual([
        'unverified',
        'basic',
        'standard',
        'high',
        'premium',
      ]);
    });
  });

  describe('QUALITY_ID_MAP', () => {
    it('maps IDs 1-5 to slugs', () => {
      expect(QUALITY_ID_MAP.get(1)).toBe('unverified');
      expect(QUALITY_ID_MAP.get(2)).toBe('basic');
      expect(QUALITY_ID_MAP.get(3)).toBe('standard');
      expect(QUALITY_ID_MAP.get(4)).toBe('high');
      expect(QUALITY_ID_MAP.get(5)).toBe('premium');
    });

    it('returns undefined for ID 0 (unassigned)', () => {
      expect(QUALITY_ID_MAP.get(0)).toBeUndefined();
    });

    it('returns undefined for invalid IDs', () => {
      expect(QUALITY_ID_MAP.get(6)).toBeUndefined();
      expect(QUALITY_ID_MAP.get(-1)).toBeUndefined();
    });
  });

  describe('QUALITY_SLUG_MAP', () => {
    it('maps all slugs to IDs', () => {
      expect(QUALITY_SLUG_MAP.get('unverified')).toBe(1);
      expect(QUALITY_SLUG_MAP.get('basic')).toBe(2);
      expect(QUALITY_SLUG_MAP.get('standard')).toBe(3);
      expect(QUALITY_SLUG_MAP.get('high')).toBe(4);
      expect(QUALITY_SLUG_MAP.get('premium')).toBe(5);
    });
  });

  describe('getQualitySlug', () => {
    it('resolves valid ID to slug', () => {
      expect(getQualitySlug(3)).toBe('standard');
    });

    it('returns undefined for unknown ID', () => {
      expect(getQualitySlug(99)).toBeUndefined();
    });
  });

  describe('getQualityId', () => {
    it('resolves valid slug to ID', () => {
      expect(getQualityId('premium')).toBe(5);
    });

    it('returns undefined for unknown slug', () => {
      expect(getQualityId('godlike')).toBeUndefined();
    });
  });

  describe('isValidQuality', () => {
    it('returns true for valid slugs', () => {
      expect(isValidQuality('standard')).toBe(true);
      expect(isValidQuality('premium')).toBe(true);
    });

    it('returns false for invalid slugs', () => {
      expect(isValidQuality('amazing')).toBe(false);
      expect(isValidQuality('')).toBe(false);
    });
  });

  describe('QUALITIES', () => {
    it('contains 5 entries in ascending order', () => {
      expect(QUALITIES).toHaveLength(5);
      expect(QUALITIES[0]!.id).toBe(1);
      expect(QUALITIES[4]!.id).toBe(5);
    });

    it('each entry has required fields', () => {
      for (const q of QUALITIES) {
        expect(q).toHaveProperty('id');
        expect(q).toHaveProperty('slug');
        expect(q).toHaveProperty('name');
        expect(q).toHaveProperty('stars');
        expect(q).toHaveProperty('description');
        expect(q.stars).toBe(q.id);
      }
    });
  });

  describe('PUZZLE_QUALITY_INFO', () => {
    it('has all 5 levels', () => {
      for (const id of [1, 2, 3, 4, 5] as const) {
        expect(PUZZLE_QUALITY_INFO[id]).toBeDefined();
        expect(PUZZLE_QUALITY_INFO[id].stars).toBe(id);
      }
    });

    it('has correct display labels', () => {
      expect(PUZZLE_QUALITY_INFO[1].displayLabel).toBe('Unverified');
      expect(PUZZLE_QUALITY_INFO[3].displayLabel).toBe('Standard');
      expect(PUZZLE_QUALITY_INFO[5].displayLabel).toBe('Premium');
    });

    it('is derived from QUALITIES (not hardcoded)', () => {
      for (const q of QUALITIES) {
        const info = PUZZLE_QUALITY_INFO[q.id as 1 | 2 | 3 | 4 | 5];
        expect(info.name).toBe(q.slug);
        expect(info.displayLabel).toBe(q.name);
        expect(info.stars).toBe(q.stars);
        expect(info.description).toBe(q.description);
        expect(info.color).toBe(q.displayColor);
      }
    });
  });

  describe('parseQualityMetrics', () => {
    it('parses valid YQ string', () => {
      const result = parseQualityMetrics('q:3;rc:5;hc:2');
      expect(result.level).toBe(3);
      expect(result.refutationCount).toBe(5);
      expect(result.commentLevel).toBe(2);
    });

    it('handles missing fields with defaults', () => {
      const result = parseQualityMetrics('q:2');
      expect(result.level).toBe(2);
      expect(result.refutationCount).toBe(0);
      expect(result.commentLevel).toBe(0);
    });

    it('handles empty string', () => {
      const result = parseQualityMetrics('');
      expect(result.level).toBe(1);
      expect(result.refutationCount).toBe(0);
      expect(result.commentLevel).toBe(0);
    });

    it('clamps commentLevel to max 2', () => {
      const result = parseQualityMetrics('q:1;rc:0;hc:5');
      expect(result.commentLevel).toBe(2);
    });
  });

  describe('parseComplexityMetrics', () => {
    it('parses valid YX string', () => {
      const result = parseComplexityMetrics('d:5;r:13;s:24;u:1');
      expect(result.solutionDepth).toBe(5);
      expect(result.readingCount).toBe(13);
      expect(result.stoneCount).toBe(24);
      expect(result.uniqueness).toBe(1);
    });

    it('handles missing fields with defaults', () => {
      const result = parseComplexityMetrics('d:3');
      expect(result.solutionDepth).toBe(3);
      expect(result.readingCount).toBe(0);
      expect(result.stoneCount).toBe(0);
      expect(result.uniqueness).toBe(1);
    });
  });

  describe('getPuzzleQualityInfo', () => {
    it('returns info for valid level', () => {
      const info = getPuzzleQualityInfo(3);
      expect(info.name).toBe('standard');
      expect(info.displayLabel).toBe('Standard');
    });

    it('falls back to level 1 for invalid level', () => {
      const info = getPuzzleQualityInfo(99 as any);
      expect(info.name).toBe('unverified');
    });
  });

  describe('isValidPuzzleQualityLevel', () => {
    it('returns true for valid levels 1-5', () => {
      for (const level of [1, 2, 3, 4, 5]) {
        expect(isValidPuzzleQualityLevel(level)).toBe(true);
      }
    });

    it('returns false for invalid levels', () => {
      expect(isValidPuzzleQualityLevel(0)).toBe(false);
      expect(isValidPuzzleQualityLevel(6)).toBe(false);
      expect(isValidPuzzleQualityLevel(1.5)).toBe(false);
      expect(isValidPuzzleQualityLevel(-1)).toBe(false);
    });
  });

  describe('DEFAULT_QUALITY_METRICS', () => {
    it('has correct default values', () => {
      expect(DEFAULT_QUALITY_METRICS.level).toBe(1);
      expect(DEFAULT_QUALITY_METRICS.refutationCount).toBe(0);
      expect(DEFAULT_QUALITY_METRICS.commentLevel).toBe(0);
    });
  });

  describe('DEFAULT_COMPLEXITY_METRICS', () => {
    it('has correct default values', () => {
      expect(DEFAULT_COMPLEXITY_METRICS.solutionDepth).toBe(0);
      expect(DEFAULT_COMPLEXITY_METRICS.readingCount).toBe(0);
      expect(DEFAULT_COMPLEXITY_METRICS.stoneCount).toBe(0);
      expect(DEFAULT_COMPLEXITY_METRICS.uniqueness).toBe(1);
    });
  });
});
