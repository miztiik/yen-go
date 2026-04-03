/**
 * Tests for rank mapping utilities
 */

import { describe, it, expect } from 'vitest';
import {
  normalizeRank,
  rankToLevel,
  resolveRankRange,
  rankStringToLevel,
  getRanksForLevel,
} from '../../../src/lib/levels/mapping';

describe('normalizeRank', () => {
  it('normalizes uppercase K to lowercase', () => {
    expect(normalizeRank('8K')).toBe('8k');
    expect(normalizeRank('25K')).toBe('25k');
  });

  it('normalizes uppercase D to lowercase', () => {
    expect(normalizeRank('3D')).toBe('3d');
    expect(normalizeRank('9D')).toBe('9d');
  });

  it('converts kyu suffix to k', () => {
    expect(normalizeRank('8kyu')).toBe('8k');
    expect(normalizeRank('8 kyu')).toBe('8k');
    expect(normalizeRank('8-kyu')).toBe('8k');
  });

  it('converts dan suffix to d', () => {
    expect(normalizeRank('3dan')).toBe('3d');
    expect(normalizeRank('3 dan')).toBe('3d');
    expect(normalizeRank('3-dan')).toBe('3d');
  });

  it('leaves already normalized ranks unchanged', () => {
    expect(normalizeRank('8k')).toBe('8k');
    expect(normalizeRank('3d')).toBe('3d');
  });

  it('returns empty string for empty input', () => {
    expect(normalizeRank('')).toBe('');
  });

  it('strips whitespace', () => {
    expect(normalizeRank('  8k  ')).toBe('8k');
  });
});

describe('rankToLevel', () => {
  it('maps novice ranks (30k-26k) to level 1', () => {
    expect(rankToLevel('30k')).toBe(1);
    expect(rankToLevel('28k')).toBe(1);
    expect(rankToLevel('26k')).toBe(1);
  });

  it('maps beginner ranks (25k-21k) to level 2', () => {
    expect(rankToLevel('25k')).toBe(2);
    expect(rankToLevel('23k')).toBe(2);
    expect(rankToLevel('21k')).toBe(2);
  });

  it('maps elementary ranks (20k-16k) to level 3', () => {
    expect(rankToLevel('20k')).toBe(3);
    expect(rankToLevel('18k')).toBe(3);
    expect(rankToLevel('16k')).toBe(3);
  });

  it('maps intermediate ranks (15k-11k) to level 4', () => {
    expect(rankToLevel('15k')).toBe(4);
    expect(rankToLevel('13k')).toBe(4);
    expect(rankToLevel('11k')).toBe(4);
  });

  it('maps upper intermediate ranks (10k-6k) to level 5', () => {
    expect(rankToLevel('10k')).toBe(5);
    expect(rankToLevel('8k')).toBe(5);
    expect(rankToLevel('6k')).toBe(5);
  });

  it('maps advanced ranks (5k-1k) to level 6', () => {
    expect(rankToLevel('5k')).toBe(6);
    expect(rankToLevel('3k')).toBe(6);
    expect(rankToLevel('1k')).toBe(6);
  });

  it('maps low dan ranks (1d-3d) to level 7', () => {
    expect(rankToLevel('1d')).toBe(7);
    expect(rankToLevel('2d')).toBe(7);
    expect(rankToLevel('3d')).toBe(7);
  });

  it('maps high dan ranks (4d-6d) to level 8', () => {
    expect(rankToLevel('4d')).toBe(8);
    expect(rankToLevel('5d')).toBe(8);
    expect(rankToLevel('6d')).toBe(8);
  });

  it('maps expert ranks (7d-9d) to level 9', () => {
    expect(rankToLevel('7d')).toBe(9);
    expect(rankToLevel('8d')).toBe(9);
    expect(rankToLevel('9d')).toBe(9);
  });

  it('returns null for invalid ranks', () => {
    expect(rankToLevel('invalid')).toBeNull();
    expect(rankToLevel('100k')).toBeNull();
    expect(rankToLevel('')).toBeNull();
  });
});

describe('resolveRankRange', () => {
  it('returns stronger (lower number) kyu rank', () => {
    expect(resolveRankRange('10K-5K')).toBe('5k');
    expect(resolveRankRange('20k-15k')).toBe('15k');
  });

  it('returns stronger (higher number) dan rank', () => {
    expect(resolveRankRange('1D-3D')).toBe('3d');
    expect(resolveRankRange('4d-6d')).toBe('6d');
  });

  it('normalizes single ranks', () => {
    expect(resolveRankRange('8K')).toBe('8k');
    expect(resolveRankRange('3D')).toBe('3d');
  });
});

describe('rankStringToLevel', () => {
  it('combines normalization and mapping', () => {
    expect(rankStringToLevel('8K')).toBe(5);
    expect(rankStringToLevel('3D')).toBe(7);
    expect(rankStringToLevel('25 kyu')).toBe(2);
  });

  it('returns null for invalid input', () => {
    expect(rankStringToLevel('invalid')).toBeNull();
  });
});

describe('getRanksForLevel', () => {
  it('returns all ranks for level 1', () => {
    const ranks = getRanksForLevel(1);
    expect(ranks).toContain('30k');
    expect(ranks).toContain('26k');
    expect(ranks).toHaveLength(5); // 30k, 29k, 28k, 27k, 26k
  });

  it('returns all ranks for level 9', () => {
    const ranks = getRanksForLevel(9);
    expect(ranks).toContain('7d');
    expect(ranks).toContain('9d');
    expect(ranks).toHaveLength(3); // 7d, 8d, 9d
  });
});

describe('Integration: External rank to level', () => {
  it('maps 101weiqi rank "8K" to Level 5', () => {
    const normalized = normalizeRank('8K');
    const level = rankToLevel(normalized);
    expect(level).toBe(5);
  });

  it('maps 101weiqi rank "25K" to Level 2', () => {
    const normalized = normalizeRank('25K');
    const level = rankToLevel(normalized);
    expect(level).toBe(2);
  });

  it('maps 101weiqi rank "3D" to Level 7', () => {
    const normalized = normalizeRank('3D');
    const level = rankToLevel(normalized);
    expect(level).toBe(7);
  });

  it('resolves ambiguous "10K-5K" to Level 6 (Advanced)', () => {
    const resolved = resolveRankRange('10K-5K');
    const level = rankToLevel(resolved);
    expect(level).toBe(6); // 5k is in Advanced (Level 6)
  });
});
