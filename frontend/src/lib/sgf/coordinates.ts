/**
 * SGF coordinate utilities.
 *
 * SGF uses lowercase letters a-s for 19x19 board coordinates.
 * Coordinate "aa" = top-left (0,0), "ss" = bottom-right (18,18).
 */

import type { SgfCoord } from '../../types';
import type { Coordinate as Coord } from '../../types/coordinate';

/** Board position (row, col) — alias for Coord until this file is deleted in Phase 3c */
type BoardPosition = Coord;

/**
 * Convert SGF coordinate string to board position.
 *
 * @param coord - SGF coordinate (e.g., "pd", "dd")
 * @returns Board position {x, y} or null if invalid
 *
 * @example
 * sgfToPosition("aa") // { x: 0, y: 0 }
 * sgfToPosition("pd") // { x: 15, y: 3 }
 */
export function sgfToPosition(coord: SgfCoord): BoardPosition | null {
  if (!coord || coord.length !== 2) {
    return null;
  }

  const x = coord.charCodeAt(0) - 'a'.charCodeAt(0);
  const y = coord.charCodeAt(1) - 'a'.charCodeAt(0);

  // Validate range (0-18 for 19x19)
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
 * @returns SGF coordinate or null if invalid
 *
 * @example
 * positionToSgf(0, 0) // "aa"
 * positionToSgf(15, 3) // "pd"
 */
export function positionToSgf(x: number, y: number): SgfCoord | null {
  if (x < 0 || x > 18 || y < 0 || y > 18) {
    return null;
  }

  const col = String.fromCharCode('a'.charCodeAt(0) + x);
  const row = String.fromCharCode('a'.charCodeAt(0) + y);

  return `${col}${row}`;
}

/**
 * Convert board position object to SGF coordinate.
 *
 * @param pos - Board position
 * @returns SGF coordinate or null if invalid
 */
export function boardPositionToSgf(pos: BoardPosition): SgfCoord | null {
  return positionToSgf(pos.x, pos.y);
}

/**
 * Validate if a string is a valid SGF coordinate.
 *
 * @param coord - String to validate
 * @returns True if valid SGF coordinate
 */
export function isValidSgfCoord(coord: string): coord is SgfCoord {
  if (!coord || coord.length !== 2) {
    return false;
  }

  const x = coord.charCodeAt(0) - 'a'.charCodeAt(0);
  const y = coord.charCodeAt(1) - 'a'.charCodeAt(0);

  return x >= 0 && x <= 18 && y >= 0 && y <= 18;
}

/**
 * Parse a list of SGF coordinates.
 *
 * @param coords - Array of SGF coordinate strings
 * @returns Array of valid board positions
 */
export function parseSgfCoords(coords: readonly SgfCoord[]): BoardPosition[] {
  const positions: BoardPosition[] = [];

  for (const coord of coords) {
    const pos = sgfToPosition(coord);
    if (pos) {
      positions.push(pos);
    }
  }

  return positions;
}

/**
 * Convert positions to SGF coordinates.
 *
 * @param positions - Array of board positions
 * @returns Array of SGF coordinates
 */
export function positionsToSgf(positions: readonly BoardPosition[]): SgfCoord[] {
  const coords: SgfCoord[] = [];

  for (const pos of positions) {
    const coord = boardPositionToSgf(pos);
    if (coord) {
      coords.push(coord);
    }
  }

  return coords;
}

/**
 * Calculate distance between two positions.
 *
 * @param a - First position (SGF coord or BoardPosition)
 * @param b - Second position (SGF coord or BoardPosition)
 * @returns Manhattan distance or -1 if invalid
 */
export function distance(a: SgfCoord | BoardPosition, b: SgfCoord | BoardPosition): number {
  const posA = typeof a === 'string' ? sgfToPosition(a) : a;
  const posB = typeof b === 'string' ? sgfToPosition(b) : b;

  if (!posA || !posB) {
    return -1;
  }

  return Math.abs(posA.x - posB.x) + Math.abs(posA.y - posB.y);
}

/**
 * Check if two coordinates are adjacent (including diagonals).
 *
 * @param a - First coordinate
 * @param b - Second coordinate
 * @returns True if adjacent
 */
export function areAdjacent(a: SgfCoord | BoardPosition, b: SgfCoord | BoardPosition): boolean {
  const posA = typeof a === 'string' ? sgfToPosition(a) : a;
  const posB = typeof b === 'string' ? sgfToPosition(b) : b;

  if (!posA || !posB) {
    return false;
  }

  const dx = Math.abs(posA.x - posB.x);
  const dy = Math.abs(posA.y - posB.y);

  // Adjacent = max 1 step in any direction
  return dx <= 1 && dy <= 1 && dx + dy > 0;
}

/**
 * Get orthogonally adjacent positions (up, down, left, right).
 *
 * @param coord - Center coordinate
 * @param boardSize - Board size (default 19)
 * @returns Array of adjacent positions within bounds
 */
export function getNeighbors(
  coord: SgfCoord | BoardPosition,
  boardSize: number = 19
): BoardPosition[] {
  const pos = typeof coord === 'string' ? sgfToPosition(coord) : coord;

  if (!pos) {
    return [];
  }

  const neighbors: BoardPosition[] = [];
  const directions = [
    { dx: 0, dy: -1 }, // up
    { dx: 0, dy: 1 }, // down
    { dx: -1, dy: 0 }, // left
    { dx: 1, dy: 0 }, // right
  ];

  for (const { dx, dy } of directions) {
    const nx = pos.x + dx;
    const ny = pos.y + dy;

    if (nx >= 0 && nx < boardSize && ny >= 0 && ny < boardSize) {
      neighbors.push({ x: nx, y: ny });
    }
  }

  return neighbors;
}

/**
 * Get neighbors as SGF coordinates.
 *
 * @param coord - Center coordinate
 * @param boardSize - Board size (default 19)
 * @returns Array of adjacent SGF coordinates
 */
export function getNeighborCoords(coord: SgfCoord, boardSize: number = 19): SgfCoord[] {
  const neighbors = getNeighbors(coord, boardSize);
  return positionsToSgf(neighbors);
}

/**
 * Point type - uses x,y coordinate system.
 * Used in hints and review modules.
 */
export interface Point {
  readonly x: number;
  readonly y: number;
}

/**
 * Convert SGF coordinate to Point.
 * Alias for sgfToPosition for Point type.
 */
export function sgfToPoint(coord: SgfCoord): Point | null {
  return sgfToPosition(coord);
}
