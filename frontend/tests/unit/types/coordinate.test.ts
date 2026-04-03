/**
 * Unified Coordinate Type Tests (1-indexed Besogo pattern)
 * @module tests/unit/types/coordinate.test
 *
 * Unit tests for the unified Coord type and utility functions.
 * Spec 122 - Phase 4, T4.13 (Besogo Gold Standard)
 *
 * CRITICAL: All coordinates are 1-indexed (Besogo pattern)
 * - x=1 is left edge, x=19 is right edge
 * - y=1 is top edge, y=19 is bottom edge
 */

import { describe, it, expect } from 'vitest';
import {
  coordEqual,
  coord,
  coordToSgf,
  sgfToCoord,
  coordToDisplay,
  displayToCoord,
  isValidCoord,
  isValidXY,
  getAdjacentCoords,
  coordKey,
  keyToCoord,
  coordToLinear,
  type Coord,
  type Coordinate,
} from '../../../src/types/coordinate';

describe('Coordinate Type (1-indexed Besogo pattern)', () => {
  describe('coord()', () => {
    it('should create a coordinate object (1-indexed)', () => {
      const c = coord(3, 5);
      expect(c.x).toBe(3);
      expect(c.y).toBe(5);
    });

    it('should create top-left corner at (1,1)', () => {
      const c = coord(1, 1);
      expect(c.x).toBe(1);
      expect(c.y).toBe(1);
    });

    it('should create bottom-right corner at (19,19) for standard board', () => {
      const c = coord(19, 19);
      expect(c.x).toBe(19);
      expect(c.y).toBe(19);
    });
  });

  describe('coordEqual()', () => {
    it('should return true for equal coordinates', () => {
      const a: Coord = { x: 3, y: 5 };
      const b: Coord = { x: 3, y: 5 };
      expect(coordEqual(a, b)).toBe(true);
    });

    it('should return false for different x values', () => {
      const a: Coord = { x: 3, y: 5 };
      const b: Coord = { x: 4, y: 5 };
      expect(coordEqual(a, b)).toBe(false);
    });

    it('should return false for different y values', () => {
      const a: Coord = { x: 3, y: 5 };
      const b: Coord = { x: 3, y: 6 };
      expect(coordEqual(a, b)).toBe(false);
    });
  });

  describe('coordToSgf() - 1-indexed to SGF', () => {
    it('should convert corner coordinates (1-indexed)', () => {
      // Top-left: (1,1) -> "aa"
      expect(coordToSgf({ x: 1, y: 1 })).toBe('aa');
      // Bottom-right of 19x19: (19,19) -> "ss"
      expect(coordToSgf({ x: 19, y: 19 })).toBe('ss');
    });

    it('should convert middle coordinates', () => {
      // Besogo: x=4, y=16 -> "dp"
      expect(coordToSgf({ x: 4, y: 16 })).toBe('dp');
      // Center point: x=10, y=10 -> "jj"
      expect(coordToSgf({ x: 10, y: 10 })).toBe('jj');
    });

    it('should verify Besogo formula: 96 + x where x is 1-indexed', () => {
      // 'a'.charCodeAt(0) = 97 = 96 + 1
      // So x=1 -> charCode 97 -> 'a'
      expect(coordToSgf({ x: 1, y: 1 })).toBe('aa');
      expect(coordToSgf({ x: 2, y: 1 })).toBe('ba');
    });
  });

  describe('sgfToCoord() - SGF to 1-indexed', () => {
    it('should convert corner coordinates to 1-indexed', () => {
      // "aa" -> (1,1) top-left
      expect(sgfToCoord('aa')).toEqual({ x: 1, y: 1 });
      // "ss" -> (19,19) bottom-right
      expect(sgfToCoord('ss')).toEqual({ x: 19, y: 19 });
    });

    it('should convert middle coordinates', () => {
      // "dp" -> (4,16)
      expect(sgfToCoord('dp')).toEqual({ x: 4, y: 16 });
      // "jj" -> (10,10)
      expect(sgfToCoord('jj')).toEqual({ x: 10, y: 10 });
    });

    it('should throw for invalid coordinates', () => {
      expect(() => sgfToCoord('')).toThrow();
      expect(() => sgfToCoord('a')).toThrow();
    });

    it('should verify Besogo formula: charCodeAt - 96', () => {
      // 'a'.charCodeAt(0) = 97, 97 - 96 = 1 (1-indexed)
      expect(sgfToCoord('aa').x).toBe(1);
      expect(sgfToCoord('ba').x).toBe(2);
    });
  });

  describe('coordToDisplay() - 1-indexed to human format', () => {
    it('should convert to human-readable format', () => {
      // Note: Go notation skips 'I' and counts rows from bottom
      // (1,1) = top-left = A19 (column A, row 19)
      expect(coordToDisplay({ x: 1, y: 1 })).toBe('A19');
      // (1,19) = bottom-left = A1 (column A, row 1)
      expect(coordToDisplay({ x: 1, y: 19 })).toBe('A1');
      // (4,4) = D16
      expect(coordToDisplay({ x: 4, y: 4 })).toBe('D16');
    });

    it('should handle column J (after I is skipped)', () => {
      // x=9 -> J (index 8 in ABCDEFGHJK... string, but x is 1-indexed so x-1=8)
      expect(coordToDisplay({ x: 9, y: 1 })).toBe('J19');
      // x=10 -> K
      expect(coordToDisplay({ x: 10, y: 1 })).toBe('K19');
    });

    it('should work with different board sizes', () => {
      // 9x9 board: (5,5) = E5
      expect(coordToDisplay({ x: 5, y: 5 }, 9)).toBe('E5');
      // 9x9 board: (1,1) = A9
      expect(coordToDisplay({ x: 1, y: 1 }, 9)).toBe('A9');
    });
  });

  describe('displayToCoord() - human format to 1-indexed', () => {
    it('should parse human-readable format to 1-indexed', () => {
      // A19 = top-left = (1,1)
      expect(displayToCoord('A19')).toEqual({ x: 1, y: 1 });
      // A1 = bottom-left = (1,19)
      expect(displayToCoord('A1')).toEqual({ x: 1, y: 19 });
      // D16 = (4,4)
      expect(displayToCoord('D16')).toEqual({ x: 4, y: 4 });
    });

    it('should handle lowercase input', () => {
      expect(displayToCoord('a19')).toEqual({ x: 1, y: 1 });
      expect(displayToCoord('d16')).toEqual({ x: 4, y: 4 });
    });

    it('should handle column J (after I is skipped)', () => {
      // J19 -> x=9, y=1
      expect(displayToCoord('J19')).toEqual({ x: 9, y: 1 });
      // K19 -> x=10, y=1
      expect(displayToCoord('K19')).toEqual({ x: 10, y: 1 });
    });

    it('should throw for invalid formats', () => {
      expect(() => displayToCoord('')).toThrow();
      expect(() => displayToCoord('A')).toThrow();
      expect(() => displayToCoord('I19')).toThrow(); // I is not valid in Go
    });
  });

  describe('isValidCoord() - 1-indexed bounds', () => {
    it('should return true for valid 1-indexed coordinates', () => {
      // Top-left corner: (1,1)
      expect(isValidCoord({ x: 1, y: 1 })).toBe(true);
      // Bottom-right corner: (19,19)
      expect(isValidCoord({ x: 19, y: 19 })).toBe(true);
      // Center: (10,10)
      expect(isValidCoord({ x: 10, y: 10 })).toBe(true);
    });

    it('should return false for 0-indexed (invalid in Besogo)', () => {
      // x=0 and y=0 are NOT valid in 1-indexed system
      expect(isValidCoord({ x: 0, y: 1 })).toBe(false);
      expect(isValidCoord({ x: 1, y: 0 })).toBe(false);
      expect(isValidCoord({ x: 0, y: 0 })).toBe(false);
    });

    it('should return false for out of bounds coordinates', () => {
      expect(isValidCoord({ x: -1, y: 1 })).toBe(false);
      expect(isValidCoord({ x: 1, y: -1 })).toBe(false);
      expect(isValidCoord({ x: 20, y: 1 })).toBe(false);
      expect(isValidCoord({ x: 1, y: 20 })).toBe(false);
    });

    it('should respect custom board size', () => {
      // 9x9 board: valid range is 1-9
      expect(isValidCoord({ x: 9, y: 9 }, 9)).toBe(true);
      expect(isValidCoord({ x: 10, y: 10 }, 9)).toBe(false);
    });
  });

  describe('isValidXY() - x,y bounds check', () => {
    it('should validate x,y values', () => {
      expect(isValidXY(1, 1, 19)).toBe(true);
      expect(isValidXY(0, 0, 19)).toBe(false);
      expect(isValidXY(20, 20, 19)).toBe(false);
    });
  });

  describe('getAdjacentCoords() - 1-indexed', () => {
    it('should return 4 adjacent coords for center position', () => {
      // Center of 19x19: (10,10)
      const adjacent = getAdjacentCoords({ x: 10, y: 10 });
      expect(adjacent).toHaveLength(4);
      expect(adjacent).toContainEqual({ x: 10, y: 9 }); // up
      expect(adjacent).toContainEqual({ x: 10, y: 11 }); // down
      expect(adjacent).toContainEqual({ x: 9, y: 10 }); // left
      expect(adjacent).toContainEqual({ x: 11, y: 10 }); // right
    });

    it('should return 2 adjacent coords for corner (1,1)', () => {
      // Top-left corner at (1,1)
      const adjacent = getAdjacentCoords({ x: 1, y: 1 });
      expect(adjacent).toHaveLength(2);
      expect(adjacent).toContainEqual({ x: 1, y: 2 }); // down
      expect(adjacent).toContainEqual({ x: 2, y: 1 }); // right
    });

    it('should return 3 adjacent coords for edge', () => {
      // Left edge, middle: (1, 10)
      const adjacent = getAdjacentCoords({ x: 1, y: 10 });
      expect(adjacent).toHaveLength(3);
    });
  });

  describe('coordToLinear() - Besogo fromXY pattern', () => {
    it('should convert to linear index', () => {
      // Besogo: (x-1)*sizeY + (y-1)
      expect(coordToLinear({ x: 1, y: 1 }, 19)).toBe(0);
      expect(coordToLinear({ x: 2, y: 1 }, 19)).toBe(19);
      expect(coordToLinear({ x: 1, y: 2 }, 19)).toBe(1);
    });
  });

  describe('coordKey() and keyToCoord()', () => {
    it('should be reversible', () => {
      const original: Coord = { x: 4, y: 16 };
      const key = coordKey(original);
      const restored = keyToCoord(key);
      expect(restored).toEqual(original);
    });

    it('should create unique keys', () => {
      const key1 = coordKey({ x: 4, y: 16 });
      const key2 = coordKey({ x: 16, y: 4 });
      expect(key1).not.toBe(key2);
    });
  });

  // Backward compatibility
  describe('Coordinate type alias', () => {
    it('should support Coordinate as alias for Coord', () => {
      const c: Coordinate = { x: 1, y: 1 };
      expect(c.x).toBe(1);
      expect(c.y).toBe(1);
    });
  });
});
