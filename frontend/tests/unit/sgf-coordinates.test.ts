/**
 * SGF Coordinates Unit Tests
 * @module tests/unit/sgf-coordinates.test
 *
 * Tests for T006: Coordinate conversion utilities.
 * Tests sgfToPosition, positionToSgf, and related functions.
 */

import { describe, it, expect } from 'vitest';
import {
  sgfToPosition,
  positionToSgf,
  boardPositionToSgf,
  isValidSgfCoord,
  parseSgfCoords,
  positionsToSgf,
  distance,
  areAdjacent,
  getNeighbors,
  getNeighborCoords,
} from '../../src/lib/sgf/coordinates';

// ============================================================================
// sgfToPosition Tests
// ============================================================================

describe('sgfToPosition', () => {
  it('converts "aa" to (0,0) - top-left corner', () => {
    const result = sgfToPosition('aa');
    expect(result).toEqual({ x: 0, y: 0 });
  });

  it('converts "ss" to (18,18) - bottom-right on 19x19', () => {
    const result = sgfToPosition('ss');
    expect(result).toEqual({ x: 18, y: 18 });
  });

  it('converts "jj" to (9,9) - center of 19x19', () => {
    const result = sgfToPosition('jj');
    expect(result).toEqual({ x: 9, y: 9 });
  });

  it('converts "pd" to (15,3) - 4-4 point upper right', () => {
    const result = sgfToPosition('pd');
    expect(result).toEqual({ x: 15, y: 3 });
  });

  it('converts "dd" to (3,3) - 4-4 point upper left', () => {
    const result = sgfToPosition('dd');
    expect(result).toEqual({ x: 3, y: 3 });
  });

  it('converts "ba" to (1,0) - second column, first row', () => {
    const result = sgfToPosition('ba');
    expect(result).toEqual({ x: 1, y: 0 });
  });

  it('returns null for empty string', () => {
    expect(sgfToPosition('')).toBeNull();
  });

  it('returns null for single character', () => {
    expect(sgfToPosition('a')).toBeNull();
  });

  it('returns null for three characters', () => {
    expect(sgfToPosition('abc')).toBeNull();
  });

  it('returns null for invalid character (uppercase)', () => {
    expect(sgfToPosition('AA')).toBeNull();
  });

  it('returns null for out-of-range coordinate "tt"', () => {
    // 't' = 19, which is out of bounds for 0-18 range
    expect(sgfToPosition('tt')).toBeNull();
  });
});

// ============================================================================
// positionToSgf Tests
// ============================================================================

describe('positionToSgf', () => {
  it('converts (0,0) to "aa"', () => {
    expect(positionToSgf(0, 0)).toBe('aa');
  });

  it('converts (18,18) to "ss"', () => {
    expect(positionToSgf(18, 18)).toBe('ss');
  });

  it('converts (9,9) to "jj"', () => {
    expect(positionToSgf(9, 9)).toBe('jj');
  });

  it('converts (15,3) to "pd"', () => {
    expect(positionToSgf(15, 3)).toBe('pd');
  });

  it('converts (3,3) to "dd"', () => {
    expect(positionToSgf(3, 3)).toBe('dd');
  });

  it('returns null for negative x', () => {
    expect(positionToSgf(-1, 0)).toBeNull();
  });

  it('returns null for negative y', () => {
    expect(positionToSgf(0, -1)).toBeNull();
  });

  it('returns null for x > 18', () => {
    expect(positionToSgf(19, 0)).toBeNull();
  });

  it('returns null for y > 18', () => {
    expect(positionToSgf(0, 19)).toBeNull();
  });
});

// ============================================================================
// boardPositionToSgf Tests
// ============================================================================

describe('boardPositionToSgf', () => {
  it('converts position object to SGF coordinate', () => {
    expect(boardPositionToSgf({ x: 3, y: 3 })).toBe('dd');
    expect(boardPositionToSgf({ x: 0, y: 0 })).toBe('aa');
    expect(boardPositionToSgf({ x: 18, y: 18 })).toBe('ss');
  });

  it('returns null for invalid position', () => {
    expect(boardPositionToSgf({ x: -1, y: 0 })).toBeNull();
    expect(boardPositionToSgf({ x: 0, y: 19 })).toBeNull();
  });
});

// ============================================================================
// isValidSgfCoord Tests
// ============================================================================

describe('isValidSgfCoord', () => {
  it('returns true for valid coordinates', () => {
    expect(isValidSgfCoord('aa')).toBe(true);
    expect(isValidSgfCoord('ss')).toBe(true);
    expect(isValidSgfCoord('jj')).toBe(true);
    expect(isValidSgfCoord('pd')).toBe(true);
  });

  it('returns false for empty string', () => {
    expect(isValidSgfCoord('')).toBe(false);
  });

  it('returns false for wrong length', () => {
    expect(isValidSgfCoord('a')).toBe(false);
    expect(isValidSgfCoord('abc')).toBe(false);
  });

  it('returns false for uppercase', () => {
    expect(isValidSgfCoord('AA')).toBe(false);
    expect(isValidSgfCoord('Aa')).toBe(false);
  });

  it('returns false for out-of-range', () => {
    expect(isValidSgfCoord('tt')).toBe(false);
    expect(isValidSgfCoord('za')).toBe(false);
  });
});

// ============================================================================
// parseSgfCoords Tests
// ============================================================================

describe('parseSgfCoords', () => {
  it('parses array of valid coordinates', () => {
    const result = parseSgfCoords(['aa', 'bb', 'cc']);
    expect(result).toEqual([
      { x: 0, y: 0 },
      { x: 1, y: 1 },
      { x: 2, y: 2 },
    ]);
  });

  it('filters out invalid coordinates', () => {
    const result = parseSgfCoords(['aa', 'invalid', 'bb', 'tt', 'cc']);
    expect(result).toEqual([
      { x: 0, y: 0 },
      { x: 1, y: 1 },
      { x: 2, y: 2 },
    ]);
  });

  it('returns empty array for empty input', () => {
    expect(parseSgfCoords([])).toEqual([]);
  });

  it('returns empty array for all invalid', () => {
    expect(parseSgfCoords(['invalid', 'tt', 'ABC'])).toEqual([]);
  });
});

// ============================================================================
// positionsToSgf Tests
// ============================================================================

describe('positionsToSgf', () => {
  it('converts array of positions to SGF coordinates', () => {
    const result = positionsToSgf([
      { x: 0, y: 0 },
      { x: 1, y: 1 },
      { x: 2, y: 2 },
    ]);
    expect(result).toEqual(['aa', 'bb', 'cc']);
  });

  it('filters out invalid positions', () => {
    const result = positionsToSgf([
      { x: 0, y: 0 },
      { x: -1, y: 0 },
      { x: 1, y: 1 },
    ]);
    expect(result).toEqual(['aa', 'bb']);
  });

  it('returns empty array for empty input', () => {
    expect(positionsToSgf([])).toEqual([]);
  });
});

// ============================================================================
// distance Tests
// ============================================================================

describe('distance', () => {
  it('calculates Manhattan distance between positions', () => {
    expect(distance({ x: 0, y: 0 }, { x: 3, y: 4 })).toBe(7);
    expect(distance({ x: 3, y: 3 }, { x: 3, y: 3 })).toBe(0);
    expect(distance({ x: 0, y: 0 }, { x: 1, y: 0 })).toBe(1);
  });

  it('is symmetric', () => {
    const a = { x: 2, y: 5 };
    const b = { x: 7, y: 3 };
    expect(distance(a, b)).toBe(distance(b, a));
  });
});

// ============================================================================
// areAdjacent Tests
// ============================================================================

describe('areAdjacent', () => {
  it('returns true for horizontally adjacent', () => {
    expect(areAdjacent({ x: 3, y: 3 }, { x: 4, y: 3 })).toBe(true);
    expect(areAdjacent({ x: 3, y: 3 }, { x: 2, y: 3 })).toBe(true);
  });

  it('returns true for vertically adjacent', () => {
    expect(areAdjacent({ x: 3, y: 3 }, { x: 3, y: 4 })).toBe(true);
    expect(areAdjacent({ x: 3, y: 3 }, { x: 3, y: 2 })).toBe(true);
  });

  it('returns true for diagonally adjacent', () => {
    // Note: This implementation includes diagonals as adjacent
    expect(areAdjacent({ x: 3, y: 3 }, { x: 4, y: 4 })).toBe(true);
    expect(areAdjacent({ x: 3, y: 3 }, { x: 2, y: 2 })).toBe(true);
  });

  it('returns false for same position', () => {
    expect(areAdjacent({ x: 3, y: 3 }, { x: 3, y: 3 })).toBe(false);
  });

  it('returns false for non-adjacent', () => {
    expect(areAdjacent({ x: 0, y: 0 }, { x: 5, y: 5 })).toBe(false);
    expect(areAdjacent({ x: 3, y: 3 }, { x: 3, y: 5 })).toBe(false);
  });
});

// ============================================================================
// getNeighbors / getNeighborCoords Tests
// ============================================================================

describe('getNeighbors', () => {
  it('returns 4 neighbors for center position', () => {
    const neighbors = getNeighbors({ x: 5, y: 5 }, 9);
    expect(neighbors).toHaveLength(4);
    expect(neighbors).toContainEqual({ x: 4, y: 5 });
    expect(neighbors).toContainEqual({ x: 6, y: 5 });
    expect(neighbors).toContainEqual({ x: 5, y: 4 });
    expect(neighbors).toContainEqual({ x: 5, y: 6 });
  });

  it('returns 2 neighbors for corner position', () => {
    const neighbors = getNeighbors({ x: 0, y: 0 }, 9);
    expect(neighbors).toHaveLength(2);
    expect(neighbors).toContainEqual({ x: 1, y: 0 });
    expect(neighbors).toContainEqual({ x: 0, y: 1 });
  });

  it('returns 3 neighbors for edge position', () => {
    const neighbors = getNeighbors({ x: 0, y: 5 }, 9);
    expect(neighbors).toHaveLength(3);
    expect(neighbors).toContainEqual({ x: 1, y: 5 });
    expect(neighbors).toContainEqual({ x: 0, y: 4 });
    expect(neighbors).toContainEqual({ x: 0, y: 6 });
  });

  it('respects board size boundary', () => {
    const neighbors = getNeighbors({ x: 8, y: 8 }, 9);
    expect(neighbors).toHaveLength(2);
    expect(neighbors).not.toContainEqual({ x: 9, y: 8 });
    expect(neighbors).not.toContainEqual({ x: 8, y: 9 });
  });
});

describe('getNeighborCoords', () => {
  it('returns neighbor coordinates as SGF strings', () => {
    const neighbors = getNeighborCoords('dd', 9);
    expect(neighbors).toContain('cd');
    expect(neighbors).toContain('ed');
    expect(neighbors).toContain('dc');
    expect(neighbors).toContain('de');
  });

  it('returns fewer coords for corner', () => {
    const neighbors = getNeighborCoords('aa', 9);
    expect(neighbors).toHaveLength(2);
    expect(neighbors).toContain('ba');
    expect(neighbors).toContain('ab');
  });
});

// ============================================================================
// Roundtrip Tests
// ============================================================================

describe('Coordinate Roundtrip', () => {
  it('sgfToPosition -> positionToSgf is identity', () => {
    const coords = ['aa', 'dd', 'jj', 'pd', 'ss'];
    for (const coord of coords) {
      const pos = sgfToPosition(coord);
      expect(pos).not.toBeNull();
      if (pos) {
        const result = positionToSgf(pos.x, pos.y);
        expect(result).toBe(coord);
      }
    }
  });

  it('positionToSgf -> sgfToPosition is identity', () => {
    const positions = [
      { x: 0, y: 0 },
      { x: 3, y: 3 },
      { x: 9, y: 9 },
      { x: 15, y: 3 },
      { x: 18, y: 18 },
    ];
    for (const pos of positions) {
      const coord = positionToSgf(pos.x, pos.y);
      expect(coord).not.toBeNull();
      if (coord) {
        const result = sgfToPosition(coord);
        expect(result).toEqual(pos);
      }
    }
  });
});
