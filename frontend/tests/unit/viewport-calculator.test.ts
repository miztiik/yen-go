/**
 * Viewport Calculator Unit Tests
 * @module tests/unit/viewport-calculator.test
 *
 * Tests for T026: Auto-crop viewport calculation.
 * Covers FR-011, FR-012, FR-013, FR-014.
 */

import { describe, it, expect } from 'vitest';
import {
  calculateViewport,
  expandViewport,
  transformToViewport,
  transformFromViewport,
} from '../../src/lib/presentation/viewportCalculator';
import type { BoardViewport, Coordinate } from '../../src/models/SolutionPresentation';

// ============================================================================
// Test Data
// ============================================================================

/** Stones in a corner (should snap to edge) */
const CORNER_STONES: Coordinate[] = [
  { x: 0, y: 0 },
  { x: 1, y: 0 },
  { x: 2, y: 0 },
  { x: 0, y: 1 },
  { x: 1, y: 1 },
];

/** Stones in center (no edge snapping) */
const CENTER_STONES: Coordinate[] = [
  { x: 8, y: 8 },
  { x: 9, y: 8 },
  { x: 8, y: 9 },
  { x: 9, y: 9 },
];

/** Stones spread across board (full board needed) */
const FULL_BOARD_STONES: Coordinate[] = [
  { x: 0, y: 0 },
  { x: 18, y: 0 },
  { x: 0, y: 18 },
  { x: 18, y: 18 },
];

// ============================================================================
// calculateViewport Tests
// ============================================================================

describe('calculateViewport', () => {
  describe('basic functionality', () => {
    it('should return full board when no stones', () => {
      const viewport = calculateViewport([], 19);
      
      expect(viewport.isFullBoard).toBe(true);
      expect(viewport.width).toBe(19);
      expect(viewport.height).toBe(19);
    });

    it('should calculate bounding box around stones', () => {
      const viewport = calculateViewport(CENTER_STONES, 19, { padding: 0 });
      
      // Stones at (8,8), (9,8), (8,9), (9,9)
      expect(viewport.minX).toBeLessThanOrEqual(8);
      expect(viewport.maxX).toBeGreaterThanOrEqual(9);
      expect(viewport.minY).toBeLessThanOrEqual(8);
      expect(viewport.maxY).toBeGreaterThanOrEqual(9);
    });

    it('should add padding around stones', () => {
      // Use minSize: 1 to ensure minSize constraint doesn't override padding effect
      const noPadding = calculateViewport(CENTER_STONES, 19, { padding: 0, snapToEdge: false, minSize: 1 });
      const withPadding = calculateViewport(CENTER_STONES, 19, { padding: 2, snapToEdge: false, minSize: 1 });
      
      // With minSize: 1, padding should now properly expand the viewport
      expect(withPadding.width).toBeGreaterThan(noPadding.width);
      expect(withPadding.height).toBeGreaterThan(noPadding.height);
    });
  });

  describe('edge snapping', () => {
    it('should snap to edge when stones near corner', () => {
      const viewport = calculateViewport(CORNER_STONES, 19, { 
        padding: 1, 
        snapToEdge: true 
      });
      
      // Should snap to top-left corner
      expect(viewport.minX).toBe(0);
      expect(viewport.minY).toBe(0);
    });

    it('should not snap when disabled', () => {
      const viewport = calculateViewport(CORNER_STONES, 19, { 
        padding: 2, 
        snapToEdge: false 
      });
      
      // With padding but no snap, minX/minY could be 0 due to clamping
      // but the width should be based on stones + padding
      expect(viewport.isFullBoard).toBe(false);
    });
  });

  describe('minimum size', () => {
    it('should respect minimum size option', () => {
      const viewport = calculateViewport([{ x: 0, y: 0 }], 19, { 
        minSize: 7,
        padding: 0,
      });
      
      expect(Math.min(viewport.width, viewport.height)).toBeGreaterThanOrEqual(7);
    });

    it('should not exceed board size', () => {
      const viewport = calculateViewport(FULL_BOARD_STONES, 19);
      
      expect(viewport.width).toBeLessThanOrEqual(19);
      expect(viewport.height).toBeLessThanOrEqual(19);
      expect(viewport.maxX).toBeLessThan(19);
      expect(viewport.maxY).toBeLessThan(19);
    });
  });

  describe('full board detection', () => {
    it('should detect when full board is needed', () => {
      const viewport = calculateViewport(FULL_BOARD_STONES, 19, { padding: 1 });
      
      expect(viewport.isFullBoard).toBe(true);
    });

    it('should not be full board for localized stones', () => {
      const viewport = calculateViewport(CORNER_STONES, 19);
      
      expect(viewport.isFullBoard).toBe(false);
    });
  });
});

// ============================================================================
// expandViewport Tests
// ============================================================================

describe('expandViewport', () => {
  it('should expand viewport to include additional points', () => {
    const original = calculateViewport(CORNER_STONES, 19, { padding: 1 });
    // Add points further from the viewport
    const additionalPoints = [{ x: 10, y: 10 }];
    const expanded = expandViewport(original, additionalPoints, 19, 2);
    
    expect(expanded.maxX).toBeGreaterThanOrEqual(10);
    expect(expanded.maxY).toBeGreaterThanOrEqual(10);
  });

  it('should not expand if already full board', () => {
    const fullBoard = calculateViewport(FULL_BOARD_STONES, 19, { padding: 1 });
    const expanded = expandViewport(fullBoard, [{ x: 5, y: 5 }], 19, 1);
    
    expect(expanded.isFullBoard).toBe(true);
  });

  it('should not expand for empty points array', () => {
    const original = calculateViewport(CENTER_STONES, 19, { padding: 1 });
    const expanded = expandViewport(original, [], 19, 1);
    
    expect(expanded).toEqual(original);
  });

  it('should convert to full board if expanded too much', () => {
    const original = calculateViewport(CORNER_STONES, 19, { padding: 0 });
    // Add points at opposite corner
    const additionalPoints = [{ x: 17, y: 17 }];
    const expanded = expandViewport(original, additionalPoints, 19, 2);
    
    // Should be full board since it spans the entire board
    expect(expanded.isFullBoard).toBe(true);
  });
});

// ============================================================================
// Coordinate Transform Tests
// ============================================================================

describe('coordinate transforms', () => {
  describe('transformToViewport', () => {
    it('should return identity for full board', () => {
      const viewport: BoardViewport = {
        minX: 0,
        minY: 0,
        maxX: 18,
        maxY: 18,
        width: 19,
        height: 19,
        isFullBoard: true,
      };
      
      const coord = { x: 5, y: 10 };
      const transformed = transformToViewport(coord, viewport);
      
      expect(transformed).toEqual(coord);
    });

    it('should offset coordinates for cropped viewport', () => {
      const viewport: BoardViewport = {
        minX: 5,
        minY: 5,
        maxX: 12,
        maxY: 12,
        width: 8,
        height: 8,
        isFullBoard: false,
      };
      
      const coord = { x: 7, y: 8 };
      const transformed = transformToViewport(coord, viewport);
      
      expect(transformed.x).toBe(2); // 7 - 5
      expect(transformed.y).toBe(3); // 8 - 5
    });
  });

  describe('transformFromViewport', () => {
    it('should reverse viewport transform', () => {
      const viewport: BoardViewport = {
        minX: 5,
        minY: 5,
        maxX: 12,
        maxY: 12,
        width: 8,
        height: 8,
        isFullBoard: false,
      };
      
      const original = { x: 7, y: 8 };
      const toViewport = transformToViewport(original, viewport);
      const backToBoard = transformFromViewport(toViewport, viewport);
      
      expect(backToBoard).toEqual(original);
    });

    it('should return identity for full board', () => {
      const viewport: BoardViewport = {
        minX: 0,
        minY: 0,
        maxX: 18,
        maxY: 18,
        width: 19,
        height: 19,
        isFullBoard: true,
      };
      
      const coord = { x: 5, y: 10 };
      const transformed = transformFromViewport(coord, viewport);
      
      expect(transformed).toEqual(coord);
    });
  });
});
