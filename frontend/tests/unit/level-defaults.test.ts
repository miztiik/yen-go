/**
 * Unit tests for level default constants.
 * Spec WP6 — named constants replacing LEVEL_SLUGS[N]! pattern.
 */

import { describe, it, expect } from 'vitest';
import { DEFAULT_LEVEL, FALLBACK_LEVEL, FIRST_LEVEL, LAST_LEVEL } from '../../src/lib/levels/level-defaults';

describe('level-defaults', () => {
  it('should export DEFAULT_LEVEL as a valid string', () => {
    expect(typeof DEFAULT_LEVEL).toBe('string');
    expect(DEFAULT_LEVEL).toBe('elementary');
  });

  it('should export FALLBACK_LEVEL as a valid string', () => {
    expect(typeof FALLBACK_LEVEL).toBe('string');
    expect(FALLBACK_LEVEL).toBe('beginner');
  });

  it('should export FIRST_LEVEL as a valid string', () => {
    expect(typeof FIRST_LEVEL).toBe('string');
    expect(FIRST_LEVEL).toBe('novice');
  });

  it('should export LAST_LEVEL as a valid string', () => {
    expect(typeof LAST_LEVEL).toBe('string');
    expect(LAST_LEVEL).toBe('expert');
  });

  it('should have distinct values for all constants', () => {
    const values = new Set([DEFAULT_LEVEL, FALLBACK_LEVEL, FIRST_LEVEL, LAST_LEVEL]);
    expect(values.size).toBe(4);
  });
});
