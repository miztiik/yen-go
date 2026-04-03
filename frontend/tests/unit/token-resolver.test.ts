/**
 * Token Resolver Unit Tests
 *
 * Tests for {!xy} coordinate token resolution with board transforms.
 * Validates that hint tokens are correctly transformed and converted
 * to human-readable Go notation.
 */
import { describe, it, expect } from 'vitest';
import { resolveHintTokens, hasTokens } from '@/lib/hints/token-resolver';
import type { TransformSettings } from '@/lib/sgf-preprocessor';

const NO_TRANSFORMS: TransformSettings = {
  flipH: false,
  flipV: false,
  rotation: 0,
  swapColors: false,
};

describe('resolveHintTokens', () => {
  describe('without transforms (identity)', () => {
    it('replaces {!bb} with B18 on 19x19', () => {
      const result = resolveHintTokens(
        'The first move is at {!bb}.',
        19,
        NO_TRANSFORMS,
      );
      expect(result).toBe('The first move is at B18.');
    });

    it('replaces {!jj} with K10 on 19x19 (tengen)', () => {
      const result = resolveHintTokens('Play at {!jj}.', 19, NO_TRANSFORMS);
      expect(result).toBe('Play at K10.');
    });

    it('replaces {!aa} with A19 on 19x19 (top-left)', () => {
      const result = resolveHintTokens('Move at {!aa}.', 19, NO_TRANSFORMS);
      expect(result).toBe('Move at A19.');
    });

    it('replaces {!ss} with T1 on 19x19 (bottom-right)', () => {
      const result = resolveHintTokens('Move at {!ss}.', 19, NO_TRANSFORMS);
      expect(result).toBe('Move at T1.');
    });
  });

  describe('with flipH transform', () => {
    it('mirrors {!bb} horizontally', () => {
      const transforms: TransformSettings = { ...NO_TRANSFORMS, flipH: true };
      // {!bb} = Point(1,1) -> flipH -> Point(17,1) = S18
      const result = resolveHintTokens('Move at {!bb}.', 19, transforms);
      expect(result).toBe('Move at S18.');
    });
  });

  describe('with flipV transform', () => {
    it('mirrors {!bb} vertically', () => {
      const transforms: TransformSettings = { ...NO_TRANSFORMS, flipV: true };
      // {!bb} = Point(1,1) -> flipV -> Point(1,17) = B2
      const result = resolveHintTokens('Move at {!bb}.', 19, transforms);
      expect(result).toBe('Move at B2.');
    });
  });

  describe('with 90° rotation', () => {
    it('rotates {!cd} 90° clockwise', () => {
      const transforms: TransformSettings = {
        ...NO_TRANSFORMS,
        rotation: 90,
      };
      // {!cd} = Point(2,3) -> 90° CW -> Point(15,2) = Q17
      const result = resolveHintTokens('Move at {!cd}.', 19, transforms);
      expect(result).toBe('Move at Q17.');
    });
  });

  describe('with combined transforms', () => {
    it('applies flipH + flipV (180-degree rotation)', () => {
      const transforms: TransformSettings = {
        ...NO_TRANSFORMS,
        flipH: true,
        flipV: true,
      };
      // {!aa} = Point(0,0) -> flipH -> Point(18,0) -> flipV -> Point(18,18) = T1
      const result = resolveHintTokens('Move at {!aa}.', 19, transforms);
      expect(result).toBe('Move at T1.');
    });
  });

  describe('multiple tokens', () => {
    it('resolves multiple tokens in a single string', () => {
      const result = resolveHintTokens(
        'If you play {!cd}, the opponent responds at {!ef}.',
        19,
        NO_TRANSFORMS,
      );
      expect(result).toBe(
        'If you play C16, the opponent responds at E14.',
      );
    });
  });

  describe('passthrough', () => {
    it('leaves text without tokens unchanged', () => {
      const text = 'Focus on the corner. Look for a ladder.';
      expect(resolveHintTokens(text, 19, NO_TRANSFORMS)).toBe(text);
    });

    it('leaves empty string unchanged', () => {
      expect(resolveHintTokens('', 19, NO_TRANSFORMS)).toBe('');
    });
  });

  describe('board size variations', () => {
    it('handles 9x9 board', () => {
      // {!dd} = Point(3,3) on 9x9 -> D6
      const result = resolveHintTokens('Move at {!dd}.', 9, NO_TRANSFORMS);
      expect(result).toBe('Move at D6.');
    });

    it('handles 13x13 board', () => {
      // {!dd} = Point(3,3) on 13x13 -> D10
      const result = resolveHintTokens('Move at {!dd}.', 13, NO_TRANSFORMS);
      expect(result).toBe('Move at D10.');
    });
  });
});

describe('hasTokens', () => {
  it('returns true for text with a single token', () => {
    expect(hasTokens('Move at {!bb}.')).toBe(true);
  });

  it('returns true for text with multiple tokens', () => {
    expect(hasTokens('Play {!aa} or {!bb}.')).toBe(true);
  });

  it('returns false for text without tokens', () => {
    expect(hasTokens('Focus on the corner.')).toBe(false);
  });

  it('returns false for empty string', () => {
    expect(hasTokens('')).toBe(false);
  });

  it('returns false for similar but invalid token formats', () => {
    expect(hasTokens('Value is {!zz}')).toBe(false); // z > s
    expect(hasTokens('Value is {!a}')).toBe(false); // too short
    expect(hasTokens('Value is {abc}')).toBe(false); // no !
  });
});
