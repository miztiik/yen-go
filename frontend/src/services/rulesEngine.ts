/**
 * Go Rules Engine - Enforces captures, ko, and legality
 * @module services/rulesEngine
 *
 * Constitution Compliance:
 * - V. No Browser AI: Pure validation only, no move generation
 * - III. Separation of Concerns: Rules only, no UI or persistence
 */

import type { BoardSize, Coordinate, Stone } from '@models/puzzle';
import { EMPTY } from '@models/puzzle';
import type { KoState, PlaceStoneResult, StoneGroup } from '@models/board';
import { getAdjacentCoords, getOpponent, getStone } from '@models/board';

/**
 * Find all stones connected to the given position (flood fill)
 * @param board - Current board state
 * @param start - Starting coordinate
 * @param boardSize - Size of the board
 * @returns Group of connected stones with liberties
 */
export function findGroup(
  board: readonly (readonly Stone[])[],
  start: Coordinate,
  boardSize: BoardSize
): StoneGroup | null {
  const color = getStone(board, start);
  if (color === EMPTY) return null;

  const stones: Coordinate[] = [];
  const liberties: Coordinate[] = [];
  const visited = new Set<string>();
  const queue: Coordinate[] = [start];

  const coordKey = (c: Coordinate): string => `${c.x},${c.y}`;

  while (queue.length > 0) {
    const current = queue.shift()!;
    const key = coordKey(current);

    if (visited.has(key)) continue;
    visited.add(key);

    const stone = getStone(board, current);
    if (stone === color) {
      stones.push(current);

      for (const adj of getAdjacentCoords(current, boardSize)) {
        const adjKey = coordKey(adj);
        if (!visited.has(adjKey)) {
          const adjStone = getStone(board, adj);
          if (adjStone === color) {
            queue.push(adj);
          } else if (adjStone === EMPTY) {
            // Check if liberty already recorded
            if (!liberties.some((l) => l.x === adj.x && l.y === adj.y)) {
              liberties.push(adj);
            }
          }
        }
      }
    }
  }

  return { color, stones, liberties };
}

/**
 * Count liberties of the group containing the stone at position
 * @param board - Current board state
 * @param coord - Position of stone to check
 * @param boardSize - Size of the board
 * @returns Number of liberties, or 0 if position is empty
 */
export function countLiberties(
  board: readonly (readonly Stone[])[],
  coord: Coordinate,
  boardSize: BoardSize
): number {
  const group = findGroup(board, coord, boardSize);
  return group?.liberties.length ?? 0;
}

/**
 * Find all groups that would be captured if a stone is placed
 * @param board - Current board state
 * @param coord - Position where stone will be placed
 * @param color - Color of stone being placed (Stone: -1 or 1)
 * @param boardSize - Size of the board
 * @returns Array of opponent groups that would have 0 liberties
 */
export function findCapturedGroups(
  board: Stone[][],
  coord: Coordinate,
  color: Stone,
  boardSize: BoardSize
): StoneGroup[] {
  const opponentColor = getOpponent(color);
  const captured: StoneGroup[] = [];
  const checked = new Set<string>();

  // Temporarily place the stone
  const testBoard = board.map((row) => [...row]);
  testBoard[coord.y]![coord.x] = color;

  // Check adjacent opponent groups
  for (const adj of getAdjacentCoords(coord, boardSize)) {
    const adjStone = getStone(testBoard, adj);
    if (adjStone === opponentColor) {
      const key = `${adj.x},${adj.y}`;
      if (!checked.has(key)) {
        const group = findGroup(testBoard, adj, boardSize);
        if (group && group.liberties.length === 0) {
          captured.push(group);
          // Mark all stones in group as checked
          for (const stone of group.stones) {
            checked.add(`${stone.x},${stone.y}`);
          }
        }
      }
    }
  }

  return captured;
}

/**
 * Check if a move would be suicide (illegal self-capture)
 * @param board - Current board state
 * @param coord - Position to place stone
 * @param color - Color of stone being placed (Stone: -1 or 1)
 * @param boardSize - Size of the board
 * @returns true if the move would be suicide
 */
export function isSuicide(
  board: Stone[][],
  coord: Coordinate,
  color: Stone,
  boardSize: BoardSize
): boolean {
  // First check if we capture anything - if so, not suicide
  const captures = findCapturedGroups(board, coord, color, boardSize);
  if (captures.length > 0) return false;

  // Place stone and check if resulting group has liberties
  const testBoard = board.map((row) => [...row]);
  testBoard[coord.y]![coord.x] = color;

  const group = findGroup(testBoard, coord, boardSize);
  return group !== null && group.liberties.length === 0;
}

/**
 * Check if a move violates the ko rule
 * @param coord - Position to place stone
 * @param koState - Current ko state
 * @returns true if the move violates ko
 */
export function isKoViolation(coord: Coordinate, koState: KoState): boolean {
  if (koState.position === null) return false;
  return coord.x === koState.position.x && coord.y === koState.position.y;
}

/**
 * Execute captures and update board state
 * @param board - Board to modify (mutated)
 * @param captured - Groups to remove
 * @returns Array of all captured stone coordinates
 */
export function executeCaptures(board: Stone[][], captured: readonly StoneGroup[]): Coordinate[] {
  const capturedStones: Coordinate[] = [];

  for (const group of captured) {
    for (const stone of group.stones) {
      board[stone.y]![stone.x] = EMPTY;
      capturedStones.push(stone);
    }
  }

  return capturedStones;
}

/**
 * Determine new ko state after a move
 * @param capturedStones - Stones captured by this move
 * @param coord - Position of placed stone
 * @param moveNumber - Current move number
 * @returns New ko state
 */
export function getNewKoState(
  capturedStones: readonly Coordinate[],
  _coord: Coordinate,
  moveNumber: number
): KoState {
  // Ko occurs when exactly one stone is captured
  if (capturedStones.length === 1) {
    return {
      position: capturedStones[0]!,
      capturedAt: moveNumber,
    };
  }

  return { position: null, capturedAt: 0 };
}

/**
 * Validate and execute a stone placement
 * @param board - Current board state (will be copied, not mutated)
 * @param coord - Position to place stone
 * @param color - Color of stone being placed
 * @param boardSize - Size of the board
 * @param koState - Current ko state
 * @returns Result of the move attempt
 */
export function placeStone(
  board: readonly (readonly Stone[])[],
  coord: Coordinate,
  color: Stone,
  boardSize: BoardSize,
  koState: KoState = { position: null, capturedAt: 0 }
): PlaceStoneResult {
  // Check bounds (1-indexed per Besogo)
  if (coord.x < 1 || coord.x > boardSize || coord.y < 1 || coord.y > boardSize) {
    return { success: false, error: 'occupied' };
  }

  // Check if position is occupied
  if (getStone(board, coord) !== EMPTY) {
    return { success: false, error: 'occupied' };
  }

  // Check ko rule
  if (isKoViolation(coord, koState)) {
    return { success: false, error: 'ko' };
  }

  // Create mutable copy
  const newBoard = board.map((row) => [...row]);

  // Find captures
  const capturedGroups = findCapturedGroups(newBoard, coord, color, boardSize);

  // Check suicide
  if (capturedGroups.length === 0 && isSuicide(newBoard, coord, color, boardSize)) {
    return { success: false, error: 'suicide' };
  }

  // Place stone
  newBoard[coord.y]![coord.x] = color;

  // Execute captures
  const capturedStones = executeCaptures(newBoard, capturedGroups);

  return {
    success: true,
    capturedStones,
    newBoard,
  };
}

/**
 * Check if a position is a valid move (without executing)
 * @param board - Current board state
 * @param coord - Position to check
 * @param color - Color of stone (Stone: -1 or 1)
 * @param boardSize - Size of the board
 * @param koState - Current ko state
 * @returns true if the move is legal
 */
export function isValidMove(
  board: readonly (readonly Stone[])[],
  coord: Coordinate,
  color: Stone,
  boardSize: BoardSize,
  koState: KoState = { position: null, capturedAt: 0 }
): boolean {
  const result = placeStone(board, coord, color, boardSize, koState);
  return result.success;
}
