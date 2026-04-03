/**
 * Tests for levelRanks utility (UI-037)
 */
import { describe, it, expect } from 'vitest';
import { getRankRange, formatRankRange, humanizeCollectionName } from '../../src/lib/levelRanks';

describe('getRankRange', () => {
  it('returns rank range for known levels', () => {
    expect(getRankRange('novice')).toEqual({ min: '30k', max: '26k' });
    expect(getRankRange('beginner')).toEqual({ min: '25k', max: '21k' });
    expect(getRankRange('upper-intermediate')).toEqual({ min: '10k', max: '6k' });
    expect(getRankRange('advanced')).toEqual({ min: '5k', max: '1k' });
    expect(getRankRange('expert')).toEqual({ min: '7d', max: '9d' });
  });

  it('returns null for unknown levels', () => {
    expect(getRankRange('unknown')).toBeNull();
    expect(getRankRange('')).toBeNull();
  });
});

describe('formatRankRange', () => {
  it('formats rank range as display string', () => {
    expect(formatRankRange('novice')).toBe('30k–26k');
    expect(formatRankRange('upper-intermediate')).toBe('10k–6k');
    expect(formatRankRange('advanced')).toBe('5k–1k');
  });

  it('returns null for unknown levels', () => {
    expect(formatRankRange('unknown')).toBeNull();
  });
});

describe('humanizeCollectionName', () => {
  it('converts kebab-case to Title Case', () => {
    expect(humanizeCollectionName('cho-chikun-elementary')).toBe('Cho Chikun Elementary');
  });

  it('shows full name without truncation', () => {
    expect(humanizeCollectionName('cho-chikun-life-death-elementary-volume-one'))
      .toBe('Cho Chikun Life Death Elementary Volume One');
  });

  it('handles single word', () => {
    expect(humanizeCollectionName('curated')).toBe('Curated');
  });
});
