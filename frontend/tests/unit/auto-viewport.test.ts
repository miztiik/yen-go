/**
 * Auto-Viewport Unit Tests (T194)
 *
 * Verifies YC property parsing and corner-to-bounds mapping.
 * Spec 132, US18
 */

import { describe, it, expect } from 'vitest';
import { parseYCProperty, getCornerBounds } from '../../src/lib/auto-viewport';

describe('Auto-Viewport', () => {
  describe('parseYCProperty', () => {
    it('parses YC[TL] → TL', () => {
      expect(parseYCProperty('(;FF[4]GM[1]SZ[19]YC[TL])')).toBe('TL');
    });

    it('parses YC[TR] → TR', () => {
      expect(parseYCProperty('(;FF[4]YC[TR])')).toBe('TR');
    });

    it('parses YC[BL] → BL', () => {
      expect(parseYCProperty('(;FF[4]SZ[19]YC[BL])')).toBe('BL');
    });

    it('parses YC[BR] → BR', () => {
      expect(parseYCProperty('(;FF[4]YC[BR])')).toBe('BR');
    });

    it('parses YC[C] → C (center)', () => {
      expect(parseYCProperty('(;FF[4]YC[C])')).toBe('C');
    });

    it('parses YC[E] → E (edge)', () => {
      expect(parseYCProperty('(;FF[4]YC[E])')).toBe('E');
    });

    it('returns undefined when YC is missing', () => {
      expect(parseYCProperty('(;FF[4]GM[1]SZ[19])')).toBeUndefined();
    });

    it('handles case-insensitive YC values', () => {
      expect(parseYCProperty('(;FF[4]YC[tl])')).toBe('TL');
      expect(parseYCProperty('(;FF[4]YC[br])')).toBe('BR');
    });

    it('returns undefined for invalid YC values', () => {
      expect(parseYCProperty('(;FF[4]YC[XX])')).toBeUndefined();
    });
  });

  describe('getCornerBounds', () => {
    it('TL → top-left quadrant', () => {
      const bounds = getCornerBounds('TL', 19);
      expect(bounds).toBeDefined();
      expect(bounds!.top).toBe(0);
      expect(bounds!.left).toBe(0);
      expect(bounds!.bottom).toBeGreaterThan(0);
      expect(bounds!.right).toBeGreaterThan(0);
    });

    it('TR → top-right quadrant', () => {
      const bounds = getCornerBounds('TR', 19);
      expect(bounds).toBeDefined();
      expect(bounds!.top).toBe(0);
      expect(bounds!.right).toBe(18); // boardSize - 1
    });

    it('BL → bottom-left quadrant', () => {
      const bounds = getCornerBounds('BL', 19);
      expect(bounds).toBeDefined();
      expect(bounds!.bottom).toBe(18);
      expect(bounds!.left).toBe(0);
    });

    it('BR → bottom-right quadrant', () => {
      const bounds = getCornerBounds('BR', 19);
      expect(bounds).toBeDefined();
      expect(bounds!.bottom).toBe(18);
      expect(bounds!.right).toBe(18);
    });

    it('C → no zoom (undefined)', () => {
      expect(getCornerBounds('C')).toBeUndefined();
    });

    it('E → no zoom (undefined)', () => {
      expect(getCornerBounds('E')).toBeUndefined();
    });

    it('undefined → no zoom (undefined)', () => {
      expect(getCornerBounds(undefined)).toBeUndefined();
    });

    it('works with 9×9 board', () => {
      const bounds = getCornerBounds('TL', 9);
      expect(bounds).toBeDefined();
      expect(bounds!.bottom).toBeLessThan(9);
      expect(bounds!.right).toBeLessThan(9);
    });

    it('9×9 BR bounds are within board', () => {
      const bounds = getCornerBounds('BR', 9);
      expect(bounds).toBeDefined();
      expect(bounds!.bottom).toBe(8); // boardSize - 1
      expect(bounds!.right).toBe(8);
      expect(bounds!.top).toBeGreaterThan(0);
      expect(bounds!.left).toBeGreaterThan(0);
    });

    it('13×13 TL bounds scale proportionally', () => {
      const bounds = getCornerBounds('TL', 13);
      expect(bounds).toBeDefined();
      expect(bounds!.top).toBe(0);
      expect(bounds!.left).toBe(0);
      // extent = ceil(13 * 0.6) = 8 → bottom and right should be 8
      expect(bounds!.bottom).toBe(8);
      expect(bounds!.right).toBe(8);
    });

    it('5×5 corner still produces valid bounds', () => {
      const bounds = getCornerBounds('BR', 5);
      expect(bounds).toBeDefined();
      expect(bounds!.bottom).toBe(4); // boardSize - 1
      expect(bounds!.right).toBe(4);
      expect(bounds!.top).toBeGreaterThanOrEqual(0);
      expect(bounds!.left).toBeGreaterThanOrEqual(0);
    });

    it('returns undefined for unrecognized corner value', () => {
      // Type system prevents this, but defensive at runtime
      expect(getCornerBounds('X' as any)).toBeUndefined();
    });
  });
});
