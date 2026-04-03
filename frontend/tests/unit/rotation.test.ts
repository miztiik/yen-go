/**
 * Board Rotation Unit Tests
 * @module tests/unit/rotation.test
 *
 * Tests for T009: Board rotation transform
 */

import { describe, it, expect } from 'vitest';
import {
  rotateCoordinate,
  rotatePosition,
  rotatePositions,
  getInverseRotation,
  inverseRotatePosition,
  getNextRotation,
  getPreviousRotation,
  isValidRotation,
  parseRotation,
  getRotationLabel,
  ROTATION_VALUES,
  type BoardRotation,
} from '../../src/components/Board/rotation';
import type { Position } from '../../src/types/puzzle-internal';

describe('Board Rotation', () => {
  const BOARD_SIZE = 9;

  describe('rotateCoordinate()', () => {
    it('returns same coordinates for 0° rotation', () => {
      expect(rotateCoordinate(0, 0, BOARD_SIZE, 0)).toEqual([0, 0]);
      expect(rotateCoordinate(4, 4, BOARD_SIZE, 0)).toEqual([4, 4]);
      expect(rotateCoordinate(8, 8, BOARD_SIZE, 0)).toEqual([8, 8]);
    });

    it('rotates 90° clockwise correctly', () => {
      // Top-left (0,0) → Top-right (8,0)
      expect(rotateCoordinate(0, 0, BOARD_SIZE, 90)).toEqual([8, 0]);
      // Top-right (8,0) → Bottom-right (8,8)
      expect(rotateCoordinate(8, 0, BOARD_SIZE, 90)).toEqual([8, 8]);
      // Bottom-right (8,8) → Bottom-left (0,8)
      expect(rotateCoordinate(8, 8, BOARD_SIZE, 90)).toEqual([0, 8]);
      // Bottom-left (0,8) → Top-left (0,0)
      expect(rotateCoordinate(0, 8, BOARD_SIZE, 90)).toEqual([0, 0]);
      // Center stays at center
      expect(rotateCoordinate(4, 4, BOARD_SIZE, 90)).toEqual([4, 4]);
    });

    it('rotates 180° correctly', () => {
      // Top-left (0,0) → Bottom-right (8,8)
      expect(rotateCoordinate(0, 0, BOARD_SIZE, 180)).toEqual([8, 8]);
      // Top-right (8,0) → Bottom-left (0,8)
      expect(rotateCoordinate(8, 0, BOARD_SIZE, 180)).toEqual([0, 8]);
      // Center stays at center
      expect(rotateCoordinate(4, 4, BOARD_SIZE, 180)).toEqual([4, 4]);
    });

    it('rotates 270° clockwise (90° counter-clockwise) correctly', () => {
      // Top-left (0,0) → Bottom-left (0,8)
      expect(rotateCoordinate(0, 0, BOARD_SIZE, 270)).toEqual([0, 8]);
      // Top-right (8,0) → Top-left (0,0)
      expect(rotateCoordinate(8, 0, BOARD_SIZE, 270)).toEqual([0, 0]);
      // Center stays at center
      expect(rotateCoordinate(4, 4, BOARD_SIZE, 270)).toEqual([4, 4]);
    });

    it('handles 19x19 board', () => {
      expect(rotateCoordinate(0, 0, 19, 90)).toEqual([18, 0]);
      expect(rotateCoordinate(18, 18, 19, 90)).toEqual([0, 18]);
    });

    it('handles 13x13 board', () => {
      expect(rotateCoordinate(0, 0, 13, 90)).toEqual([12, 0]);
    });
  });

  describe('rotatePosition()', () => {
    it('rotates Position object correctly', () => {
      const pos: Position = { x: 2, y: 3 };
      const rotated = rotatePosition(pos, BOARD_SIZE, 90);
      expect(rotated).toEqual({ x: 5, y: 2 });
    });

    it('creates new Position object (no mutation)', () => {
      const pos: Position = { x: 2, y: 3 };
      const rotated = rotatePosition(pos, BOARD_SIZE, 90);
      expect(rotated).not.toBe(pos);
      expect(pos).toEqual({ x: 2, y: 3 }); // Original unchanged
    });
  });

  describe('rotatePositions()', () => {
    it('rotates array of positions', () => {
      const positions: Position[] = [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 2, y: 0 },
      ];
      const rotated = rotatePositions(positions, BOARD_SIZE, 90);
      expect(rotated).toEqual([
        { x: 8, y: 0 },
        { x: 8, y: 1 },
        { x: 8, y: 2 },
      ]);
    });

    it('returns empty array for empty input', () => {
      expect(rotatePositions([], BOARD_SIZE, 90)).toEqual([]);
    });
  });

  describe('getInverseRotation()', () => {
    it('returns correct inverse rotations', () => {
      expect(getInverseRotation(0)).toBe(0);
      expect(getInverseRotation(90)).toBe(270);
      expect(getInverseRotation(180)).toBe(180);
      expect(getInverseRotation(270)).toBe(90);
    });

    it('is symmetric (inverse of inverse equals original)', () => {
      for (const rotation of ROTATION_VALUES) {
        expect(getInverseRotation(getInverseRotation(rotation))).toBe(rotation);
      }
    });
  });

  describe('inverseRotatePosition()', () => {
    it('undoes a rotation', () => {
      const original: Position = { x: 2, y: 3 };
      const rotated = rotatePosition(original, BOARD_SIZE, 90);
      const restored = inverseRotatePosition(rotated, BOARD_SIZE, 90);
      expect(restored).toEqual(original);
    });

    it('works for all rotation angles', () => {
      const original: Position = { x: 5, y: 2 };
      for (const rotation of ROTATION_VALUES) {
        const rotated = rotatePosition(original, BOARD_SIZE, rotation);
        const restored = inverseRotatePosition(rotated, BOARD_SIZE, rotation);
        expect(restored).toEqual(original);
      }
    });
  });

  describe('Rotation cycle', () => {
    describe('getNextRotation()', () => {
      it('cycles through rotations correctly', () => {
        expect(getNextRotation(0)).toBe(90);
        expect(getNextRotation(90)).toBe(180);
        expect(getNextRotation(180)).toBe(270);
        expect(getNextRotation(270)).toBe(0);
      });

      it('returns to 0 after full cycle', () => {
        let rotation: BoardRotation = 0;
        for (let i = 0; i < 4; i++) {
          rotation = getNextRotation(rotation);
        }
        expect(rotation).toBe(0);
      });
    });

    describe('getPreviousRotation()', () => {
      it('cycles through rotations in reverse', () => {
        expect(getPreviousRotation(0)).toBe(270);
        expect(getPreviousRotation(90)).toBe(0);
        expect(getPreviousRotation(180)).toBe(90);
        expect(getPreviousRotation(270)).toBe(180);
      });
    });
  });

  describe('Validation', () => {
    describe('isValidRotation()', () => {
      it('returns true for valid rotations', () => {
        expect(isValidRotation(0)).toBe(true);
        expect(isValidRotation(90)).toBe(true);
        expect(isValidRotation(180)).toBe(true);
        expect(isValidRotation(270)).toBe(true);
      });

      it('returns false for invalid values', () => {
        expect(isValidRotation(45)).toBe(false);
        expect(isValidRotation(360)).toBe(false);
        expect(isValidRotation(-90)).toBe(false);
        expect(isValidRotation('90')).toBe(false);
        expect(isValidRotation(null)).toBe(false);
        expect(isValidRotation(undefined)).toBe(false);
      });
    });

    describe('parseRotation()', () => {
      it('returns valid rotation as-is', () => {
        expect(parseRotation(90)).toBe(90);
        expect(parseRotation(180)).toBe(180);
      });

      it('returns 0 for invalid values', () => {
        expect(parseRotation(45)).toBe(0);
        expect(parseRotation('90')).toBe(0);
        expect(parseRotation(null)).toBe(0);
        expect(parseRotation(undefined)).toBe(0);
      });
    });
  });

  describe('getRotationLabel()', () => {
    it('returns correct labels', () => {
      expect(getRotationLabel(0)).toBe('Normal');
      expect(getRotationLabel(90)).toBe('90°');
      expect(getRotationLabel(180)).toBe('180°');
      expect(getRotationLabel(270)).toBe('270°');
    });
  });

  describe('Full rotation cycle identity', () => {
    it('four 90° rotations return to original position', () => {
      const original: Position = { x: 3, y: 7 };
      let current = original;

      for (let i = 0; i < 4; i++) {
        current = rotatePosition(current, BOARD_SIZE, 90);
      }

      expect(current).toEqual(original);
    });

    it('two 180° rotations return to original position', () => {
      const original: Position = { x: 3, y: 7 };
      const once = rotatePosition(original, BOARD_SIZE, 180);
      const twice = rotatePosition(once, BOARD_SIZE, 180);
      expect(twice).toEqual(original);
    });
  });
});
