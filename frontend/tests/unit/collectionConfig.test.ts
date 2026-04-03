/**
 * Collection Config Tests — SHUFFLE_POLICY and shuffleArray
 * @module tests/unit/collectionConfig.test
 *
 * T6: Validates that collection types map to correct shuffle policies
 * and that the Fisher-Yates shuffle produces a valid permutation.
 */

import { describe, it, expect } from 'vitest';
import { SHUFFLE_POLICY, shuffleArray } from '@/constants/collectionConfig';

describe('collectionConfig', () => {
  describe('SHUFFLE_POLICY', () => {
    it('should preserve order for graded collections', () => {
      expect(SHUFFLE_POLICY.graded).toBe(false);
    });

    it('should preserve order for author collections', () => {
      expect(SHUFFLE_POLICY.author).toBe(false);
    });

    it('should shuffle technique collections', () => {
      expect(SHUFFLE_POLICY.technique).toBe(true);
    });

    it('should shuffle reference collections', () => {
      expect(SHUFFLE_POLICY.reference).toBe(true);
    });

    it('should preserve order for system collections', () => {
      expect(SHUFFLE_POLICY.system).toBe(false);
    });

    it('should have entries for all five collection types', () => {
      const types = Object.keys(SHUFFLE_POLICY).sort();
      expect(types).toEqual(['author', 'graded', 'reference', 'system', 'technique']);
    });
  });

  describe('shuffleArray', () => {
    it('should return a new array (not mutate original)', () => {
      const original = [1, 2, 3, 4, 5];
      const originalCopy = [...original];
      shuffleArray(original);
      expect(original).toEqual(originalCopy);
    });

    it('should preserve all elements (valid permutation)', () => {
      const original = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
      const result = shuffleArray(original);
      expect(result).toHaveLength(original.length);
      expect(result.sort((a, b) => a - b)).toEqual(original.sort((a, b) => a - b));
    });

    it('should handle empty array', () => {
      expect(shuffleArray([])).toEqual([]);
    });

    it('should handle single-element array', () => {
      expect(shuffleArray([42])).toEqual([42]);
    });

    it('should produce a different order at least sometimes (statistical)', () => {
      const original = Array.from({ length: 20 }, (_, i) => i);
      // Run 10 trials — at least one should differ from the original
      const allSame = Array.from({ length: 10 }, () => shuffleArray(original))
        .every(result => result.every((v, i) => v === original[i]));
      expect(allSame).toBe(false);
    });
  });
});
