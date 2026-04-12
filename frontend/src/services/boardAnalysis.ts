/**
 * Board Analysis - Besogo Extensions
 * @module services/boardAnalysis
 *
 * Read-only analysis functions built on top of the Besogo Core rules engine.
 * All functions are pure and stateless, operating on board grids.
 *
 * Architecture:
 *   UI Integration → Besogo Extensions (this) → Besogo Core (rulesEngine.ts)
 *   One-way dependency: extensions depend on core, never the reverse.
 *
 * Feature flags: All analysis functions check ENABLE_BESOGO_EXTENSIONS.
 * When disabled, functions return safe defaults (isMoveLegal→true, isSelfAtari→false).
 */

import type { Stone } from '../types/board';
import { EMPTY } from '../types/board';
import type { Coordinate, BoardSize } from '../models/puzzle';
import type { KoState, StoneGroup } from '../models/board';
import { getAdjacentCoords } from '../models/board';
import {
  findGroup,
  countLiberties,
  findCapturedGroups,
  isValidMove,
  placeStone,
} from './rulesEngine';
import { ENABLE_BESOGO_EXTENSIONS } from './featureFlags';

// ─── Extension #1: Move Legality (Hover Blocking) ──────────────────────────

/**
 * Check if a move is legal (not suicide, not ko violation, not occupied).
 * Used for hover blocking — prevents ghost stone from showing on illegal positions.
 *
 * @param grid - Board grid (1-indexed)
 * @param coord - Position to check (1-indexed)
 * @param color - Stone color (-1 or 1)
 * @param boardSize - Board size
 * @param koState - Current ko state
 * @returns true if the move is legal. When extensions are disabled, always returns true
 *          (allows hover on all empty positions, click still validates).
 */
export function isMoveLegal(
  grid: readonly (readonly Stone[])[],
  coord: Coordinate,
  color: Stone,
  boardSize: BoardSize,
  koState: KoState
): boolean {
  if (!ENABLE_BESOGO_EXTENSIONS) return true;
  return isValidMove(grid, coord, color, boardSize, koState);
}

// ─── Extension #2 + #4: Self-Atari Detection ───────────────────────────────

/**
 * Check if placing a stone would put the resulting group in atari (1 liberty).
 *
 * Handles captures correctly: a move that captures opponent stones first,
 * then leaves you with 1 liberty, is still self-atari.
 *
 * @param grid - Board grid (1-indexed)
 * @param coord - Position to check (1-indexed)
 * @param color - Stone color (-1 or 1)
 * @param boardSize - Board size
 * @returns true if the move is self-atari. When extensions are disabled, returns false.
 */
export function isSelfAtari(
  grid: readonly (readonly Stone[])[],
  coord: Coordinate,
  color: Stone,
  boardSize: BoardSize
): boolean {
  if (!ENABLE_BESOGO_EXTENSIONS) return false;
  if (grid[coord.y]?.[coord.x] !== EMPTY) return false;

  // Simulate the move using placeStone (handles captures automatically)
  const result = placeStone(
    grid,
    coord,
    color,
    boardSize,
    { position: null, capturedAt: 0 } // Ko doesn't affect self-atari analysis
  );

  if (!result.success || !result.newBoard) return false;

  // Check liberties of the resulting group
  const libs = countLiberties(result.newBoard, coord, boardSize);
  return libs === 1;
}

// ─── Extension #9: Atari Check ─────────────────────────────────────────────

/**
 * Check if the group at a position is in atari (exactly 1 liberty).
 *
 * @param grid - Board grid (1-indexed)
 * @param coord - Position of a stone in the group (1-indexed)
 * @param boardSize - Board size
 * @returns true if the group is in atari. When extensions are disabled, returns false.
 */
export function isInAtari(
  grid: readonly (readonly Stone[])[],
  coord: Coordinate,
  boardSize: BoardSize
): boolean {
  if (!ENABLE_BESOGO_EXTENSIONS) return false;
  return countLiberties(grid, coord, boardSize) === 1;
}

// ─── Extension #3: Enumerate Legal Moves ────────────────────────────────────

/**
 * Get all legal moves for a given color on the board.
 *
 * @param grid - Board grid (1-indexed)
 * @param color - Stone color (-1 or 1)
 * @param boardSize - Board size
 * @param koState - Current ko state
 * @returns Array of legal move coordinates (1-indexed). When extensions are disabled, returns [].
 */
export function getLegalMoves(
  grid: readonly (readonly Stone[])[],
  color: Stone,
  boardSize: BoardSize,
  koState: KoState
): Coordinate[] {
  if (!ENABLE_BESOGO_EXTENSIONS) return [];

  const moves: Coordinate[] = [];
  for (let y = 1; y <= boardSize; y++) {
    for (let x = 1; x <= boardSize; x++) {
      const coord: Coordinate = { x, y };
      if (grid[y]?.[x] === EMPTY && isValidMove(grid, coord, color, boardSize, koState)) {
        moves.push(coord);
      }
    }
  }
  return moves;
}

// ─── Extension #5: Would-Save-Group ─────────────────────────────────────────

/**
 * Check if a move would save a friendly group from atari/capture.
 *
 * @param grid - Board grid (1-indexed)
 * @param groupCoord - Position of a stone in the endangered group (1-indexed)
 * @param moveCoord - Position of the proposed saving move (1-indexed)
 * @param color - Color of the friendly group
 * @param boardSize - Board size
 * @returns true if the move increases the group's liberties above 1.
 *          When extensions are disabled, returns false.
 */
export function wouldSaveGroup(
  grid: readonly (readonly Stone[])[],
  groupCoord: Coordinate,
  moveCoord: Coordinate,
  color: Stone,
  boardSize: BoardSize
): boolean {
  if (!ENABLE_BESOGO_EXTENSIONS) return false;

  // Group must be friendly and in atari
  if (grid[groupCoord.y]?.[groupCoord.x] !== color) return false;
  const currentLiberties = countLiberties(grid, groupCoord, boardSize);
  if (currentLiberties > 1) return false; // Not in danger

  // Simulate the move
  const result = placeStone(grid, moveCoord, color, boardSize, { position: null, capturedAt: 0 });

  if (!result.success || !result.newBoard) return false;

  // Check if group has more liberties now
  const newLiberties = countLiberties(result.newBoard, groupCoord, boardSize);
  return newLiberties > currentLiberties;
}

// ─── Extension #6: Liberties After Move ─────────────────────────────────────

/**
 * Count liberties the resulting group would have after placing a stone.
 *
 * @param grid - Board grid (1-indexed)
 * @param coord - Position to place stone (1-indexed)
 * @param color - Stone color (-1 or 1)
 * @param boardSize - Board size
 * @returns Liberty count after move, or -1 if move is invalid.
 *          When extensions are disabled, returns -1.
 */
export function countLibertiesAfterMove(
  grid: readonly (readonly Stone[])[],
  coord: Coordinate,
  color: Stone,
  boardSize: BoardSize
): number {
  if (!ENABLE_BESOGO_EXTENSIONS) return -1;

  const result = placeStone(grid, coord, color, boardSize, { position: null, capturedAt: 0 });

  if (!result.success || !result.newBoard) return -1;
  return countLiberties(result.newBoard, coord, boardSize);
}

// ─── Extension #7: Count Potential Captures ─────────────────────────────────

/**
 * Count opponent stones that would be captured by a move.
 *
 * @param grid - Board grid (1-indexed)
 * @param coord - Position to place stone (1-indexed)
 * @param color - Stone color (-1 or 1)
 * @param boardSize - Board size
 * @returns Number of stones captured. When extensions are disabled, returns 0.
 */
export function countPotentialCaptures(
  grid: readonly (readonly Stone[])[],
  coord: Coordinate,
  color: Stone,
  boardSize: BoardSize
): number {
  if (!ENABLE_BESOGO_EXTENSIONS) return 0;

  const captured = findCapturedGroups(
    grid.map((row) => [...row]),
    coord,
    color,
    boardSize
  );
  return captured.reduce((sum, group) => sum + group.stones.length, 0);
}

// ─── Extension #8: Board State Comparison ───────────────────────────────────

/**
 * Compare two board grids for equality.
 *
 * @param gridA - First board grid (1-indexed)
 * @param gridB - Second board grid (1-indexed)
 * @param boardSize - Board size
 * @returns true if boards are identical. When extensions are disabled, returns false.
 */
export function boardsEqual(
  gridA: readonly (readonly Stone[])[],
  gridB: readonly (readonly Stone[])[],
  boardSize: BoardSize
): boolean {
  if (!ENABLE_BESOGO_EXTENSIONS) return false;

  for (let y = 1; y <= boardSize; y++) {
    for (let x = 1; x <= boardSize; x++) {
      if ((gridA[y]?.[x] ?? EMPTY) !== (gridB[y]?.[x] ?? EMPTY)) {
        return false;
      }
    }
  }
  return true;
}

// ─── Extension #10: Adjacent Groups Lookup ──────────────────────────────────

/**
 * Info about a group adjacent to a position.
 */
export interface AdjacentGroupInfo {
  readonly color: Stone;
  readonly stones: readonly Coordinate[];
  readonly liberties: number;
}

/**
 * Find all distinct groups adjacent to a coordinate.
 *
 * @param grid - Board grid (1-indexed)
 * @param coord - Center coordinate (1-indexed)
 * @param boardSize - Board size
 * @returns Array of adjacent groups. When extensions are disabled, returns [].
 */
export function getAdjacentGroupsInfo(
  grid: readonly (readonly Stone[])[],
  coord: Coordinate,
  boardSize: BoardSize
): AdjacentGroupInfo[] {
  if (!ENABLE_BESOGO_EXTENSIONS) return [];

  const groups: AdjacentGroupInfo[] = [];
  const seen = new Set<string>();

  for (const adj of getAdjacentCoords(coord, boardSize as 9 | 13 | 19)) {
    const stone = grid[adj.y]?.[adj.x] ?? EMPTY;
    if (stone === EMPTY) continue;

    const key = `${adj.x},${adj.y}`;
    if (seen.has(key)) continue;

    const group: StoneGroup | null = findGroup(grid, adj, boardSize);
    if (!group) continue;

    // Mark all stones in group as seen
    for (const s of group.stones) {
      seen.add(`${s.x},${s.y}`);
    }

    groups.push({
      color: group.color,
      stones: group.stones,
      liberties: group.liberties.length,
    });
  }

  return groups;
}
