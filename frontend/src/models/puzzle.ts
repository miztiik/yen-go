/**
 * Puzzle types for tsumego puzzle data
 * @module models/puzzle
 *
 * Uses Besogo integer Stone type convention
 */

/**
 * Stone constants (Besogo integer pattern)
 * Defined inline after types/board.ts deletion (spec 129)
 */
export const BLACK = -1 as const;
export const WHITE = 1 as const;
export const EMPTY = 0 as const;

/**
 * @deprecated Use Coord from types/coordinate.ts (1-indexed).
 * Board coordinate (legacy 0-indexed).
 */
export interface Coordinate {
  readonly x: number;
  readonly y: number;
}

/**
 * Stone state at a board intersection.
 * Besogo integer pattern: BLACK=-1, WHITE=1, EMPTY=0
 */
export type Stone = typeof BLACK | typeof WHITE | typeof EMPTY;

/** Supported board sizes */
export type BoardSize = 9 | 13 | 19;

/** Side to move */
export type SideToMove = 'black' | 'white';

/** A node in the solution tree */
export interface SolutionNode {
  readonly move: Coordinate;
  readonly response?: Coordinate | null;
  readonly branches?: readonly SolutionNode[];
  readonly isWinning?: boolean;
}

/** Move explanation with optional highlight points */
export interface Explanation {
  readonly move: Coordinate;
  readonly text: string;
  readonly highlightPoints?: readonly Coordinate[];
}

/** Puzzle metadata */
export interface PuzzleMetadata {
  readonly difficulty: string; // e.g., "15kyu", "3dan"
  readonly difficultyScore: number; // 0-10
  readonly tags: readonly string[];
  readonly level: string; // YYYY-MM-DD
  readonly source?: string;
  readonly createdAt: string; // ISO 8601
}

/** A single Go tsumego puzzle */
export interface Puzzle {
  readonly version: '1.0';
  readonly id: string;
  readonly boardSize: BoardSize;
  readonly initialState: readonly (readonly Stone[])[];
  readonly sideToMove: SideToMove;
  readonly solutionTree: SolutionNode;
  readonly hints: readonly string[];
  readonly explanations: readonly Explanation[];
  readonly metadata: PuzzleMetadata;
}

/** Board state for runtime use (mutable copy of initialState) */
export type BoardState = Stone[][];

/** A move with color */
export interface Move {
  readonly x: number;
  readonly y: number;
  readonly color: Stone;
}

/** Result of validating a move against the solution tree */
export interface MoveValidationResult {
  readonly isCorrect: boolean;
  readonly response?: Coordinate | null;
  readonly nextNode?: SolutionNode;
  readonly isWinning?: boolean;
  readonly explanation?: string;
}

/** Current state of puzzle solving */
export interface PuzzleSolveState {
  readonly puzzle: Puzzle;
  readonly currentBoard: BoardState;
  readonly currentNode: SolutionNode;
  readonly moveHistory: readonly Move[];
  readonly hintsUsed: number;
  readonly attempts: number;
  readonly startTime: number;
  readonly isComplete: boolean;
}

/** Helper to create a deep copy of board state */
export function cloneBoardState(board: readonly (readonly Stone[])[]): BoardState {
  return board.map((row) => [...row]);
}

/** Helper to check if coordinates are equal */
export function coordsEqual(a: Coordinate, b: Coordinate): boolean {
  return a.x === b.x && a.y === b.y;
}

/** Helper to check if coordinate is within board bounds */
export function isValidCoord(coord: Coordinate, boardSize: BoardSize): boolean {
  return coord.x >= 0 && coord.x < boardSize && coord.y >= 0 && coord.y < boardSize;
}
