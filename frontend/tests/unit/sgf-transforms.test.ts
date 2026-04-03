/**
 * Unit tests for SGF coordinate transforms.
 * @module tests/unit/sgf-transforms
 *
 * Covers: transformPuzzleSgf, transformSgfCoordinate, transformCoordinate
 * Regression: flipDiag-only guard bypass (the early-return guard in
 * transformAllCoordinates previously omitted flipDiag, causing diagonal
 * flip to have no effect when used alone).
 */

import { describe, it, expect } from 'vitest';
import {
  transformPuzzleSgf,
  transformSgfCoordinate,
  transformCoordinate,
  DEFAULT_TRANSFORM_SETTINGS,
  type TransformSettings,
} from '../../src/lib/sgf-preprocessor';

// Minimal valid SGF with a 9x9 board, setup stones, and a move
const SIMPLE_SGF_9x9 =
  '(;FF[4]GM[1]SZ[9]AB[cc][gc]AW[cd][gd]PL[B];B[dd];W[ee])';

// Helper: create settings with only one transform active
function withOnly(overrides: Partial<TransformSettings>): TransformSettings {
  return { ...DEFAULT_TRANSFORM_SETTINGS, ...overrides };
}

describe('transformCoordinate', () => {
  it('swaps x,y when flipDiag is true (9x9)', () => {
    // cc = (2,2) on 9x9 — diagonal flip should keep it as (2,2) (symmetric)
    expect(transformCoordinate(2, 2, 9, withOnly({ flipDiag: true }))).toEqual([2, 2]);

    // gc = (6,2) on 9x9 — diagonal flip should give (2,6)
    expect(transformCoordinate(6, 2, 9, withOnly({ flipDiag: true }))).toEqual([2, 6]);

    // cd = (2,3) on 9x9 — diagonal flip should give (3,2)
    expect(transformCoordinate(2, 3, 9, withOnly({ flipDiag: true }))).toEqual([3, 2]);
  });

  it('returns identity when no transforms active', () => {
    expect(transformCoordinate(6, 2, 9, DEFAULT_TRANSFORM_SETTINGS)).toEqual([6, 2]);
  });
});

describe('transformSgfCoordinate', () => {
  it('transposes SGF coordinate with flipDiag only', () => {
    // 'gc' = (6, 2) → flipDiag → (2, 6) = 'cg'
    expect(transformSgfCoordinate('gc', 9, withOnly({ flipDiag: true }))).toBe('cg');

    // 'cd' = (2, 3) → flipDiag → (3, 2) = 'dc'
    expect(transformSgfCoordinate('cd', 9, withOnly({ flipDiag: true }))).toBe('dc');
  });
});

describe('transformPuzzleSgf', () => {
  it('transforms coordinates when only flipDiag is active (regression)', () => {
    const settings = withOnly({ flipDiag: true });
    const result = transformPuzzleSgf(SIMPLE_SGF_9x9, settings, 9);

    // AB[cc][gc] → cc stays cc (symmetric), gc → cg
    expect(result).toContain('AB[cc][cg]');

    // AW[cd][gd] → cd → dc, gd → dg
    expect(result).toContain('AW[dc][dg]');

    // B[dd] → dd stays dd (symmetric)
    expect(result).toContain('B[dd]');

    // W[ee] → ee stays ee (symmetric)
    expect(result).toContain('W[ee]');
  });

  it('returns SGF unchanged when no transforms are active', () => {
    const result = transformPuzzleSgf(SIMPLE_SGF_9x9, DEFAULT_TRANSFORM_SETTINGS, 9);
    expect(result).toBe(SIMPLE_SGF_9x9);
  });

  it('applies flipDiag together with flipH', () => {
    const settings = withOnly({ flipDiag: true, flipH: true });
    const result = transformPuzzleSgf(SIMPLE_SGF_9x9, settings, 9);

    // gc = (6,2) → flipDiag → (2,6) → flipH → (8-2, 6) = (6, 6) = 'gg'
    expect(result).toContain('gg');
    // The SGF should differ from the original
    expect(result).not.toBe(SIMPLE_SGF_9x9);
  });
});
