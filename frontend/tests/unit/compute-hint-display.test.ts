/**
 * Unit tests for computeHintDisplay and cornerPositionToLabel.
 * 
 * Tests the pure-function tier mapping logic independently of rendering.
 * Updated for no-filler design: hints map directly to tiers without padding.
 * @module tests/unit/compute-hint-display
 */
import { describe, it, expect } from 'vitest';
import { computeHintDisplay, cornerPositionToLabel, getMaxLevel } from '../../src/components/Solver/HintOverlay';

describe('computeHintDisplay', () => {
  const corner = 'top-left corner';

  describe('with 3 authored hints', () => {
    const hints = ['Technique hint', 'Reasoning hint', 'Coordinate hint'];

    it('tier 1 returns first authored hint', () => {
      const result = computeHintDisplay(1, hints, corner);
      expect(result).toEqual({ text: 'Technique hint', isGenerated: false });
    });

    it('tier 2 returns second authored hint', () => {
      const result = computeHintDisplay(2, hints, corner);
      expect(result).toEqual({ text: 'Reasoning hint', isGenerated: false });
    });

    it('tier 3 returns third authored hint', () => {
      const result = computeHintDisplay(3, hints, corner);
      expect(result).toEqual({ text: 'Coordinate hint', isGenerated: false });
    });
  });

  describe('with 4+ authored hints (clamped)', () => {
    const hints = ['H1', 'H2', 'H3', 'H4'];

    it('tier 3 returns third hint', () => {
      const result = computeHintDisplay(3, hints, corner);
      expect(result).toEqual({ text: 'H3', isGenerated: false });
    });

    it('tier 4 returns fourth hint', () => {
      const result = computeHintDisplay(4, hints, corner);
      expect(result).toEqual({ text: 'H4', isGenerated: false });
    });
  });

  describe('with 2 authored hints (no filler)', () => {
    const hints = ['Technique hint', 'Reasoning hint'];

    it('tier 1 returns first authored hint directly', () => {
      const result = computeHintDisplay(1, hints, corner);
      expect(result).toEqual({ text: 'Technique hint', isGenerated: false });
    });

    it('tier 2 returns second authored hint', () => {
      const result = computeHintDisplay(2, hints, corner);
      expect(result).toEqual({ text: 'Reasoning hint', isGenerated: false });
    });

    it('tier 3 returns fallback (beyond available hints)', () => {
      const result = computeHintDisplay(3, hints, corner);
      expect(result.isGenerated).toBe(true);
    });
  });

  describe('with 1 authored hint (no filler)', () => {
    const hints = ['Look for a net (geta).'];

    it('tier 1 returns the authored hint directly', () => {
      const result = computeHintDisplay(1, hints, corner);
      expect(result).toEqual({ text: 'Look for a net (geta).', isGenerated: false });
    });

    it('tier 2 returns fallback', () => {
      const result = computeHintDisplay(2, hints, corner);
      expect(result.isGenerated).toBe(true);
    });
  });

  describe('with 0 hints', () => {
    const hints: string[] = [];

    it('tier 1 returns fallback', () => {
      const result = computeHintDisplay(1, hints, corner);
      expect(result.isGenerated).toBe(true);
    });
  });
});

describe('getMaxLevel', () => {
  it('returns 3 for 3 hints', () => {
    expect(getMaxLevel(['a', 'b', 'c'])).toBe(3);
  });

  it('returns 2 for 2 hints', () => {
    expect(getMaxLevel(['a', 'b'])).toBe(2);
  });

  it('returns 1 for 1 hint', () => {
    expect(getMaxLevel(['a'])).toBe(1);
  });

  it('returns 1 for 0 hints (marker only)', () => {
    expect(getMaxLevel([])).toBe(1);
  });
});

describe('cornerPositionToLabel', () => {
  it('maps TL to "top-left corner"', () => {
    expect(cornerPositionToLabel('TL')).toBe('top-left corner');
  });

  it('maps TR to "top-right corner"', () => {
    expect(cornerPositionToLabel('TR')).toBe('top-right corner');
  });

  it('maps BL to "bottom-left corner"', () => {
    expect(cornerPositionToLabel('BL')).toBe('bottom-left corner');
  });

  it('maps BR to "bottom-right corner"', () => {
    expect(cornerPositionToLabel('BR')).toBe('bottom-right corner');
  });

  it('maps C to "center"', () => {
    expect(cornerPositionToLabel('C')).toBe('center');
  });

  it('maps E to "edge"', () => {
    expect(cornerPositionToLabel('E')).toBe('edge');
  });

  it('returns "board" for undefined', () => {
    expect(cornerPositionToLabel(undefined)).toBe('board');
  });

  it('returns "board" for unknown values', () => {
    expect(cornerPositionToLabel('XX')).toBe('board');
  });
});
