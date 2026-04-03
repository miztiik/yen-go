/**
 * Tests for colorTextTransform utility (UI-011)
 */
import { describe, it, expect } from 'vitest';
import { swapColorText } from '../../src/lib/colorTextTransform';

describe('swapColorText', () => {
  it('swaps "Black" with "White" and vice versa', () => {
    expect(swapColorText('Black plays at C3')).toBe('White plays at C3');
    expect(swapColorText('White responds at D4')).toBe('Black responds at D4');
  });

  it('handles bidirectional swap in one string', () => {
    expect(swapColorText('Black plays, White responds')).toBe('White plays, Black responds');
  });

  it('preserves case variants', () => {
    expect(swapColorText('BLACK stones capture WHITE group')).toBe('WHITE stones capture BLACK group');
    expect(swapColorText('black to play')).toBe('white to play');
  });

  it('returns empty string for empty input', () => {
    expect(swapColorText('')).toBe('');
  });

  it('handles strings with no color references', () => {
    const text = 'Play at the vital point';
    expect(swapColorText(text)).toBe(text);
  });

  it('swaps Korean color words', () => {
    expect(swapColorText('흑 plays')).toBe('백 plays');
    expect(swapColorText('백 responds')).toBe('흑 responds');
  });

  it('swaps Chinese color words (黑/白)', () => {
    expect(swapColorText('黑 plays')).toBe('白 plays');
    expect(swapColorText('白 responds')).toBe('黑 responds');
  });

  it('does not modify Japanese 黒 (shares 白 with Chinese)', () => {
    // Japanese 黒 is not swapped to avoid interfering with Chinese 黑/白 pair
    // This is acceptable — Go comments are typically in Chinese or English
    expect(swapColorText('黒')).toBe('黒');
  });

  it('swaps French color words', () => {
    expect(swapColorText('Noir joue')).toBe('Blanc joue');
    expect(swapColorText('Blanc répond')).toBe('Noir répond');
  });
});
