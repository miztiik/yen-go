/**
 * SGF coordinate utilities.
 *
 * Lightweight coordinate conversion functions for SGF.
 * SGF uses lowercase letters a-s for 19x19 board coordinates.
 * Coordinate "aa" = top-left (0,0), "ss" = bottom-right (18,18).
 *
 * @module utils/coordinates
 */

import type { SgfCoord } from '../types';

/**
 * A 2D point using x,y coordinate system.
 * Used in hints and highlight regions.
 */
export interface Point {
  readonly x: number;
  readonly y: number;
}

/**
 * Convert SGF coordinate string to board position {x, y}.
 *
 * @param coord - SGF coordinate (e.g., "pd", "dd")
 * @returns Position {x, y} or null if invalid
 *
 * @example
 * sgfToPosition("aa") // { x: 0, y: 0 }
 * sgfToPosition("pd") // { x: 15, y: 3 }
 */
export function sgfToPosition(coord: SgfCoord): Point | null {
  if (!coord || coord.length !== 2) {
    return null;
  }

  const x = coord.charCodeAt(0) - 97; // 'a' = 97
  const y = coord.charCodeAt(1) - 97;

  if (x < 0 || x > 18 || y < 0 || y > 18) {
    return null;
  }

  return { x, y };
}

/**
 * Convert board position to SGF coordinate string.
 *
 * @param x - Column (0 = left)
 * @param y - Row (0 = top)
 * @returns SGF coordinate or null if out of range
 *
 * @example
 * positionToSgf(0, 0) // "aa"
 * positionToSgf(15, 3) // "pd"
 */
export function positionToSgf(x: number, y: number): SgfCoord | null {
  if (x < 0 || x > 18 || y < 0 || y > 18) {
    return null;
  }

  return `${String.fromCharCode(97 + x)}${String.fromCharCode(97 + y)}`;
}

/**
 * Convert SGF coordinate to Point.
 * Alias for sgfToPosition with Point return type.
 *
 * @param coord - SGF coordinate string
 * @returns Point or null if invalid
 */
export function sgfToPoint(coord: SgfCoord): Point | null {
  return sgfToPosition(coord);
}
