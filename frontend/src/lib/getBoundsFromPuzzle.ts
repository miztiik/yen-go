/**
 * getBoundsFromPuzzle -- compute board bounds from puzzle objects (UI-032b)
 *
 * Unlike the old computeBounds() which only looks at setup stones,
 * this traverses the full move tree to include solution moves.
 * Follows OGS's getBounds() pattern.
 *
 * @module lib/getBoundsFromPuzzle
 */

import type { PuzzleObject, MoveTreeJson } from './sgf-to-puzzle';
import type { GobanBounds } from '../types/goban';

/**
 * Collect all (x, y) positions from the move tree recursively.
 */
function collectTreePositions(
  node: MoveTreeJson,
  positions: Array<[number, number]>,
): void {
  // Only add valid board positions (not pass moves which are -1,-1)
  if (node.x >= 0 && node.y >= 0) {
    positions.push([node.x, node.y]);
  }
  if (node.trunk_next) {
    collectTreePositions(node.trunk_next, positions);
  }
  if (node.branches) {
    for (const branch of node.branches) {
      collectTreePositions(branch, positions);
    }
  }
}

/**
 * Decode OGS-style encoded moves string to (x, y) pairs.
 * OGS uses 2-char encoding: 'aa' = (0,0), 'ba' = (1,0), etc.
 */
function decodePositions(encoded: string | undefined): Array<[number, number]> {
  if (!encoded) return [];
  const positions: Array<[number, number]> = [];
  for (let i = 0; i + 1 < encoded.length; i += 2) {
    const x = encoded.charCodeAt(i) - 97; // 'a' = 0
    const y = encoded.charCodeAt(i + 1) - 97;
    if (x >= 0 && x < 25 && y >= 0 && y < 25) {
      positions.push([x, y]);
    }
  }
  return positions;
}

/**
 * Compute board bounds from a PuzzleObject, including both setup stones
 * AND solution tree moves. This follows OGS's getBounds() pattern.
 *
 * @param puzzle - Structured puzzle object from sgfToPuzzle()
 * @param padding - Intersections of padding around stones (default 2)
 * @returns Computed bounds, or null if zoom is not beneficial
 */
export function getBoundsFromPuzzle(
  puzzle: PuzzleObject,
  padding: number = 2,
): GobanBounds | null {
  const boardSize = puzzle.width;
  const positions: Array<[number, number]> = [];

  // Collect setup stone positions
  positions.push(...decodePositions(puzzle.initial_state.black));
  positions.push(...decodePositions(puzzle.initial_state.white));

  // Collect ALL move tree positions (setup + solution + wrong branches)
  collectTreePositions(puzzle.move_tree, positions);

  if (positions.length === 0) {
    return null;
  }

  // Find bounding box
  let minX = boardSize;
  let maxX = 0;
  let minY = boardSize;
  let maxY = 0;

  for (const [x, y] of positions) {
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }

  // Add padding
  let left = Math.max(0, minX - padding);
  let right = Math.min(boardSize - 1, maxX + padding);
  let top = Math.max(0, minY - padding);
  let bottom = Math.min(boardSize - 1, maxY + padding);

  // Edge-snap: if bound is within 3 intersections of board edge, extend to edge
  const snapThreshold = 3;
  if (left <= snapThreshold) left = 0;
  if (top <= snapThreshold) top = 0;
  if (right >= boardSize - 1 - snapThreshold) right = boardSize - 1;
  if (bottom >= boardSize - 1 - snapThreshold) bottom = boardSize - 1;

  // Calculate zoomed area size
  const zoomWidth = right - left + 1;
  const zoomHeight = bottom - top + 1;

  // Don't zoom if the area is too large (> 75% of board in both dimensions)
  const threshold = boardSize * 0.75;
  if (zoomWidth >= threshold && zoomHeight >= threshold) {
    return null;
  }

  // Minimum zoom size: at least 5x5
  if (zoomWidth < 5 || zoomHeight < 5) {
    const centerX = (left + right) / 2;
    const centerY = (top + bottom) / 2;
    const halfMin = 2;
    return {
      left: Math.max(0, Math.floor(centerX - halfMin)),
      right: Math.min(boardSize - 1, Math.ceil(centerX + halfMin)),
      top: Math.max(0, Math.floor(centerY - halfMin)),
      bottom: Math.min(boardSize - 1, Math.ceil(centerY + halfMin)),
    };
  }

  return { top, left, bottom, right };
}
