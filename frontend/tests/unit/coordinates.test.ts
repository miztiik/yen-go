/**
 * Tests for utils/coordinates.ts — lightweight SGF coordinate conversion.
 * @module tests/unit/coordinates
 *
 * Covers: FR-028 (T025)
 */

import { sgfToPosition, positionToSgf, sgfToPoint } from '../../src/utils/coordinates';
import type { SgfCoord } from '../../src/types';

describe('sgfToPosition', () => {
  it('converts "aa" to (0,0) — top-left', () => {
    expect(sgfToPosition('aa' as SgfCoord)).toEqual({ x: 0, y: 0 });
  });

  it('converts "ss" to (18,18) — bottom-right on 19x19', () => {
    expect(sgfToPosition('ss' as SgfCoord)).toEqual({ x: 18, y: 18 });
  });

  it('converts "dp" to (3,15)', () => {
    expect(sgfToPosition('dp' as SgfCoord)).toEqual({ x: 3, y: 15 });
  });

  it('converts "pd" to (15,3)', () => {
    expect(sgfToPosition('pd' as SgfCoord)).toEqual({ x: 15, y: 3 });
  });

  it('converts "jj" to (9,9) — center', () => {
    expect(sgfToPosition('jj' as SgfCoord)).toEqual({ x: 9, y: 9 });
  });

  it('returns null for empty string', () => {
    expect(sgfToPosition('' as SgfCoord)).toBeNull();
  });

  it('returns null for single character', () => {
    expect(sgfToPosition('a' as SgfCoord)).toBeNull();
  });

  it('returns null for three characters', () => {
    expect(sgfToPosition('abc' as SgfCoord)).toBeNull();
  });

  it('returns null for "tt" (out of range, used as pass)', () => {
    expect(sgfToPosition('tt' as SgfCoord)).toBeNull();
  });
});

describe('positionToSgf', () => {
  it('converts (0,0) to "aa"', () => {
    expect(positionToSgf(0, 0)).toBe('aa');
  });

  it('converts (18,18) to "ss"', () => {
    expect(positionToSgf(18, 18)).toBe('ss');
  });

  it('converts (15,3) to "pd"', () => {
    expect(positionToSgf(15, 3)).toBe('pd');
  });

  it('converts (3,15) to "dp"', () => {
    expect(positionToSgf(3, 15)).toBe('dp');
  });

  it('returns null for negative x', () => {
    expect(positionToSgf(-1, 0)).toBeNull();
  });

  it('returns null for x > 18', () => {
    expect(positionToSgf(19, 0)).toBeNull();
  });

  it('returns null for negative y', () => {
    expect(positionToSgf(0, -1)).toBeNull();
  });

  it('returns null for y > 18', () => {
    expect(positionToSgf(0, 19)).toBeNull();
  });
});

describe('sgfToPoint', () => {
  it('is equivalent to sgfToPosition', () => {
    const coord = 'dp' as SgfCoord;
    expect(sgfToPoint(coord)).toEqual(sgfToPosition(coord));
  });

  it('returns null for invalid input', () => {
    expect(sgfToPoint('' as SgfCoord)).toBeNull();
  });
});

describe('round-trip', () => {
  it('sgfToPosition → positionToSgf is identity', () => {
    const coord = 'pd' as SgfCoord;
    const pos = sgfToPosition(coord);
    expect(pos).not.toBeNull();
    expect(positionToSgf(pos!.x, pos!.y)).toBe(coord);
  });

  it('positionToSgf → sgfToPosition is identity', () => {
    const x = 7, y = 12;
    const coord = positionToSgf(x, y);
    expect(coord).not.toBeNull();
    const pos = sgfToPosition(coord!);
    expect(pos).toEqual({ x, y });
  });

  it('covers all valid coordinates without loss', () => {
    // Spot-check a few positions
    for (const [x, y] of [[0, 0], [9, 9], [18, 18], [3, 15], [15, 3]]) {
      const coord = positionToSgf(x, y)!;
      const pos = sgfToPosition(coord)!;
      expect(pos).toEqual({ x, y });
    }
  });
});
