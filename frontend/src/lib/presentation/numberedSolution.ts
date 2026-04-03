/**
 * Numbered Solution Builder
 * @module lib/presentation/numberedSolution
 *
 * Builds a numbered move sequence from solution path with collision detection.
 * Collisions occur when a move is played at a previously occupied point
 * (e.g., capture-recapture sequences like ko or snapback).
 *
 * Constitution Compliance:
 * - V. No Browser AI: Pure data transformation from SGF solution tree
 * - VI. Type Safety: Strict TypeScript with comprehensive types
 */

import type {
  Coordinate,
  NumberedMove,
  NumberedSequenceResult,
  MoveCollision,
  StoneColor,
} from '@models/SolutionPresentation';

/**
 * Move input from solution tree.
 */
export interface SolutionMove {
  /** Board coordinate */
  x: number;
  y: number;
  /** Stone color - 'B' for black, 'W' for white */
  color: 'B' | 'W';
}

/**
 * Build a numbered sequence from solution moves.
 * Tracks position history to detect collisions (moves at same point).
 *
 * @param moves - Array of solution moves in sequence order
 * @returns NumberedSequenceResult with moves, collisions, and total count
 *
 * @example
 * ```ts
 * const result = buildNumberedSequence([
 *   { x: 3, y: 3, color: 'B' },
 *   { x: 4, y: 3, color: 'W' },
 *   { x: 3, y: 4, color: 'B' },
 * ]);
 * // result.moves[0].moveNumber === 1
 * // result.collisions.length === 0 (no captures/recaptures)
 * ```
 */
export function buildNumberedSequence(moves: readonly SolutionMove[]): NumberedSequenceResult {
  const positionToMoveNum = new Map<string, number>();
  const numberedMoves: NumberedMove[] = [];
  const collisions: MoveCollision[] = [];

  moves.forEach((move, index) => {
    const key = coordToKey(move.x, move.y);
    const moveNum = index + 1;

    const existingMove = positionToMoveNum.get(key);
    if (existingMove !== undefined) {
      collisions.push({
        laterMove: moveNum,
        originalMove: existingMove,
        coord: { x: move.x, y: move.y },
      });
    }

    positionToMoveNum.set(key, moveNum);
    numberedMoves.push({
      moveNumber: moveNum,
      coord: { x: move.x, y: move.y },
      color: move.color,
      collisionWith: existingMove ?? null,
    });
  });

  return {
    moves: numberedMoves,
    collisions,
    totalMoves: moves.length,
  };
}

/**
 * Format collision list for display as caption.
 * Example: "5 = 3, 9 = 7" for multiple collisions.
 *
 * @param collisions - Array of collision records
 * @returns Formatted string or empty if no collisions
 */
export function formatCollisionCaption(collisions: readonly MoveCollision[]): string {
  if (collisions.length === 0) {
    return '';
  }

  return collisions.map((c) => `${c.laterMove} = ${c.originalMove}`).join(', ');
}

/**
 * Get numbered moves up to a specific frame (for animation).
 *
 * @param result - Full numbered sequence result
 * @param frame - Current frame (0 = none, 1 = first move, etc.)
 * @returns Slice of numbered moves visible at this frame
 */
export function getMovesAtFrame(
  result: NumberedSequenceResult,
  frame: number
): NumberedMove[] {
  if (frame <= 0) {
    return [];
  }
  return result.moves.slice(0, frame);
}

/**
 * Get collisions visible up to a specific frame.
 *
 * @param result - Full numbered sequence result
 * @param frame - Current frame
 * @returns Collisions that occurred up to this frame
 */
export function getCollisionsAtFrame(
  result: NumberedSequenceResult,
  frame: number
): MoveCollision[] {
  return result.collisions.filter((c) => c.laterMove <= frame);
}

/**
 * Calculate text color for move number based on stone color.
 * White text on black stones, black text on white stones.
 *
 * @param stoneColor - 'B' for black, 'W' for white
 * @returns CSS color string
 */
export function getNumberTextColor(stoneColor: StoneColor): string {
  return stoneColor === 'B' ? '#ffffff' : '#000000';
}

/**
 * Convert coordinate to map key string.
 */
function coordToKey(x: number, y: number): string {
  return `${x},${y}`;
}

/**
 * Extract moves from solution tree path.
 * Converts the internal representation to SolutionMove format.
 *
 * @param path - Solution path from solution tree
 * @returns Array of SolutionMove objects
 */
export function extractMovesFromPath(
  path: readonly { coord: Coordinate; color: StoneColor }[]
): SolutionMove[] {
  return path.map((move) => ({
    x: move.coord.x,
    y: move.coord.y,
    color: move.color,
  }));
}
