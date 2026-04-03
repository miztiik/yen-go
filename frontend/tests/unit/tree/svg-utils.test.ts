/**
 * SVG Utilities Tests
 * @module tests/unit/tree/svg-utils.test.ts
 *
 * Tests for SVG utility functions.
 *
 * Feature: 056-solution-tree-visualization
 */

import { describe, it, expect } from 'vitest';
import {
  createStoneAttributes,
  createLabelAttributes,
  createPathData,
  createPathAttributes,
  createCurrentMarkerAttributes,
  gridToSvg,
  svgToGrid,
  sgfToDisplayCoord,
  calculateViewBox,
} from '../../../src/lib/tree/svg-utils';
import { COLORS, GRID_SIZE, GRID_OFFSET } from '../../../src/lib/tree/constants';

describe('createStoneAttributes', () => {
  it('should create black stone attributes', () => {
    const attrs = createStoneAttributes(100, 200, 'B');

    expect(attrs.cx).toBe(100);
    expect(attrs.cy).toBe(200);
    expect(attrs.fill).toBe(COLORS.stone.black);
    expect(attrs.stroke).toBe(COLORS.stone.blackStroke);
  });

  it('should create white stone attributes', () => {
    const attrs = createStoneAttributes(100, 200, 'W');

    expect(attrs.fill).toBe(COLORS.stone.white);
    expect(attrs.stroke).toBe(COLORS.stone.whiteStroke);
  });
});

describe('createLabelAttributes', () => {
  it('should create label for black stone', () => {
    const attrs = createLabelAttributes(100, 200, 'B');

    expect(attrs.x).toBe(100);
    expect(attrs.y).toBe(200);
    expect(attrs.fill).toBe(COLORS.label.onBlack);
    expect(attrs.textAnchor).toBe('middle');
    expect(attrs.dominantBaseline).toBe('central');
  });

  it('should create label for white stone', () => {
    const attrs = createLabelAttributes(100, 200, 'W');

    expect(attrs.fill).toBe(COLORS.label.onWhite);
  });
});

describe('createPathData', () => {
  it('should create path from parent to child', () => {
    const path = createPathData(
      { svgX: 100, svgY: 100 },
      { svgX: 200, svgY: 100 }
    );

    expect(path).toBe('M 100 100 L 200 100');
  });

  it('should handle diagonal paths', () => {
    const path = createPathData(
      { svgX: 100, svgY: 100 },
      { svgX: 200, svgY: 200 }
    );

    expect(path).toBe('M 100 100 L 200 200');
  });
});

describe('createPathAttributes', () => {
  it('should create default path attributes', () => {
    const attrs = createPathAttributes(false);

    expect(attrs.stroke).toBe(COLORS.path.default);
    expect(attrs.fill).toBe('none');
  });

  it('should create current path attributes', () => {
    const attrs = createPathAttributes(true);

    expect(attrs.stroke).toBe(COLORS.path.current);
  });
});

describe('createCurrentMarkerAttributes', () => {
  it('should create marker centered on coordinates', () => {
    const attrs = createCurrentMarkerAttributes(100, 100);

    // Marker should be centered
    expect(attrs.x).toBeLessThan(100);
    expect(attrs.y).toBeLessThan(100);
    expect(attrs.width).toBeGreaterThan(0);
    expect(attrs.height).toBeGreaterThan(0);
    expect(attrs.fill).toBe(COLORS.state.current);
  });
});

describe('Coordinate Conversion', () => {
  describe('gridToSvg', () => {
    it('should convert grid (0,0) to SVG offset', () => {
      const result = gridToSvg(0, 0);

      expect(result.svgX).toBe(GRID_OFFSET);
      expect(result.svgY).toBe(GRID_OFFSET);
    });

    it('should convert grid position to SVG', () => {
      const result = gridToSvg(1, 2);

      expect(result.svgX).toBe(1 * GRID_SIZE + GRID_OFFSET);
      expect(result.svgY).toBe(2 * GRID_SIZE + GRID_OFFSET);
    });
  });

  describe('svgToGrid', () => {
    it('should convert SVG offset to grid (0,0)', () => {
      const result = svgToGrid(GRID_OFFSET, GRID_OFFSET);

      expect(result.gridX).toBe(0);
      expect(result.gridY).toBe(0);
    });

    it('should be inverse of gridToSvg', () => {
      const { svgX, svgY } = gridToSvg(3, 5);
      const { gridX, gridY } = svgToGrid(svgX, svgY);

      expect(gridX).toBe(3);
      expect(gridY).toBe(5);
    });
  });
});

describe('sgfToDisplayCoord', () => {
  it('should convert aa to A19', () => {
    expect(sgfToDisplayCoord('aa')).toBe('A19');
  });

  it('should convert ss to T1 (19x19 corner)', () => {
    expect(sgfToDisplayCoord('ss')).toBe('T1');
  });

  it('should skip I in column letters', () => {
    // Column 8 (0-indexed) should be 'J', not 'I'
    expect(sgfToDisplayCoord('ia')).toBe('J19');
  });

  it('should handle empty input', () => {
    expect(sgfToDisplayCoord('')).toBe('');
  });

  it('should handle star point dd (D16 on 19x19)', () => {
    expect(sgfToDisplayCoord('dd')).toBe('D16');
  });

  it('should handle center jj on 19x19', () => {
    // j = column 9 (0-indexed) = K (skipping I)
    // j = row 9 from top = row 10 from bottom
    expect(sgfToDisplayCoord('jj')).toBe('K10');
  });
});

describe('calculateViewBox', () => {
  it('should calculate viewBox with padding', () => {
    const viewBox = calculateViewBox(3, 2, 0.5);

    // Width: (3 + 0.5*2) * GRID_SIZE = 4 * 120 = 480
    // Height: (2 + 0.5*2) * GRID_SIZE = 3 * 120 = 360
    expect(viewBox.width).toBe(4 * GRID_SIZE);
    expect(viewBox.height).toBe(3 * GRID_SIZE);
    expect(viewBox.minX).toBe(-0.5 * GRID_SIZE);
    expect(viewBox.minY).toBe(-0.5 * GRID_SIZE);
  });

  it('should use default padding', () => {
    const viewBox = calculateViewBox(1, 1);

    // Default padding is 0.5
    expect(viewBox.width).toBe(2 * GRID_SIZE);
    expect(viewBox.height).toBe(2 * GRID_SIZE);
  });
});
