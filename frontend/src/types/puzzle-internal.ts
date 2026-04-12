/**
 * Internal Puzzle Type Definitions
 * @module types/puzzle-internal
 *
 * Types for the internal representation of puzzles after SGF parsing.
 * These types are used by components and services, not for external data.
 *
 * Spec 122 - Phase 4: Updated to use Coord and 1-indexed coordinates
 *
 * Constitution Compliance:
 * Types support validation
 */

import type { Coord } from './coordinate';

// ============================================================================
// Board Position Types (Besogo 1-indexed)
// ============================================================================

/**
 * @deprecated Use Coord from types/coordinate.ts instead.
 * Re-exported for backward compatibility during migration.
 *
 * Position is now 1-indexed (Besogo pattern):
 * - x=1 is left edge, x=19 is right edge
 * - y=1 is top edge, y=19 is bottom edge
 */
export type Position = Coord;

/**
 * @deprecated Legacy board state representation (position lists).
 * Goban-based components use goban's internal state instead.
 *
 * Board state at a point in time.
 * Used for rendering and rule validation.
 */
export interface BoardState {
  /** Board size (9, 13, or 19) */
  size: number;
  /** Current black stone positions (1-indexed Coords) */
  blackStones: Position[];
  /** Current white stone positions (1-indexed Coords) */
  whiteStones: Position[];
  /** Position of most recent move (for marking) */
  lastMove?: Position;
  /** @deprecated Ko computed from move history, not stored (Besogo pattern) */
  koPoint?: Position;
}

// ============================================================================
// Solution Tree Types
// ============================================================================

/**
 * A node in the solution tree.
 *
 * SGF Convention for Tsumego:
 * - All nodes parsed from SGF have isCorrect=true (they're solution paths)
 * - Wrong moves (not in SGF) create transient nodes with isCorrect=false
 * - The browser validates by checking if user's move exists in children
 * - Nodes with BM[] property or "wrong" in comment have isCorrect=false (Spec 012)
 * - Nodes with TE[] property have isTesuji=true (Spec 012)
 */
export interface SolutionNode {
  /** SGF coordinate of this move (e.g., "ba") */
  move: string;
  /** Who plays this move */
  player: 'B' | 'W';
  /**
   * Is this part of a correct solution path?
   * - true: Node was parsed from SGF (valid solution path)
   * - false: Node has BM[] property, "wrong" in comment, or is user's wrong move
   */
  isCorrect: boolean;
  /** Is this a player's move (vs opponent response)? */
  isUserMove: boolean;
  /**
   * Is this a tesuji (key tactical move)?
   * - true: Node has TE[] property in SGF
   * - false: Normal move (default)
   */
  isTesuji?: boolean;
  /** Child nodes (next moves in solution) */
  children: SolutionNode[];
  /** Optional comment for this node */
  comment?: string;
}

/**
 * Player's path through the solution tree.
 * Tracks current position and progress.
 */
export interface SolutionPath {
  /** Moves played so far (SGF coordinates) */
  moves: string[];
  /** Current position in solution tree (null if off-path) */
  currentNode: SolutionNode | null;
  /** Has the player reached end of solution? */
  isComplete: boolean;
  /** Have all moves been correct so far? */
  isCorrect: boolean;
}

// ============================================================================
// Puzzle Status Types
// ============================================================================

/**
 * Status of a puzzle in a set/daily challenge.
 */
export type PuzzleStatus = 'pending' | 'solved' | 'failed';

/**
 * Puzzle item in navigation carousel.
 */
export interface PuzzleNavItem {
  /** Puzzle identifier */
  id: string;
  /** Current completion status */
  status: PuzzleStatus;
}

// ============================================================================
// Hint Types
// ============================================================================

/**
 * Parsed hints from YenGo SGF properties.
 *
 * v7+ Format: YH[hint1|hint2|hint3] → stored in hints array
 * v6 Legacy: YH1/YH2/YH3 → also stored in hints array, legacy fields deprecated
 */
export interface PuzzleHints {
  /**
   * Compact hints array (v7+ format).
   * - hints[0]: Area/position hint
   * - hints[1]: Technique hint
   * - hints[2]: Full solution text
   */
  hints: string[];

  /** @deprecated Use hints[0] instead. Hint L1: Region to look at (position from YH1) */
  position?: Position;
  /** @deprecated Use hints[1] instead. Hint L2: Technique name (from YH2) */
  technique?: string;
  /** @deprecated Use hints[2] instead. Hint L3: Full text hint (from YH3) */
  text?: string;
}

// ============================================================================
// Internal Puzzle Type
// ============================================================================

/**
 * Internal puzzle representation.
 * This is the transformed type used by components after SGF parsing.
 */
export interface InternalPuzzle {
  /** Raw SGF content (required for SolverView) */
  rawSgf?: string;
  /** Unique puzzle identifier (hash-based from filename) */
  id: string;
  /** Board size (9, 13, or 19) */
  boardSize: number;
  /** Initial black stone positions */
  blackStones: Position[];
  /** Initial white stone positions */
  whiteStones: Position[];
  /** Which side moves first */
  sideToMove: 'B' | 'W';
  /** Solution tree root (for validation) */
  solutionTree: SolutionNode;

  // Metadata
  /** Skill level name (e.g., "beginner", "intermediate") */
  level: string;
  /** Sub-level within skill level (1-5) */
  subLevel?: number;
  /** Technique tags (e.g., ["killing", "ko"]) */
  tags: string[];

  // Hints
  /** Progressive hint data */
  hints: PuzzleHints;
}

// ============================================================================
// Puzzle Set Types
// ============================================================================

/**
 * A set of puzzles for a session (daily, level, etc.).
 */
export interface PuzzleSet {
  /** Type of puzzle set */
  type: 'daily' | 'level' | 'timed' | 'tag';
  /** Identifier (date for daily, level name, tag name) */
  identifier: string;
  /** Puzzle IDs in order */
  puzzleIds: string[];
  /** Status of each puzzle */
  statuses: Map<string, PuzzleStatus>;
}

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Check if a value is a valid PuzzleStatus.
 */
export function isPuzzleStatus(value: unknown): value is PuzzleStatus {
  return value === 'pending' || value === 'solved' || value === 'failed';
}

/**
 * Check if a position is valid for a given board size.
 * Now uses 1-indexed bounds (Besogo pattern).
 */
export function isValidPosition(pos: Position, boardSize: number): boolean {
  return pos.x >= 1 && pos.x <= boardSize && pos.y >= 1 && pos.y <= boardSize;
}

/**
 * Create an empty SolutionNode (for tree building).
 */
export function createSolutionNode(
  move: string,
  player: 'B' | 'W',
  isUserMove: boolean,
  isCorrect: boolean = true
): SolutionNode {
  return {
    move,
    player,
    isCorrect,
    isUserMove,
    children: [],
  };
}
