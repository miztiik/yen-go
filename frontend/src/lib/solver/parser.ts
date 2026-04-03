/**
 * Solution parser - parses puzzle solution trees.
 *
 * Solutions are stored as arrays of move sequences:
 * [["aa", "bb", "cc"], ["aa", "bd", "ce"]]
 *
 * Each sequence represents a correct line of play.
 */

import type { SgfCoord, Side } from '../../types';
import { isValidSgfCoord } from '../sgf/coordinates';

/**
 * A single move in a solution.
 */
export interface SolutionMove {
  coord: SgfCoord;
  side: Side;
  isPlayerMove: boolean;
}

/**
 * A complete solution line (sequence of moves).
 */
export interface SolutionLine {
  moves: readonly SolutionMove[];
  depth: number;
}

/**
 * Parsed solution tree with all variations.
 */
export interface ParsedSolution {
  /** All solution lines */
  lines: readonly SolutionLine[];
  /** First moves that are correct */
  correctFirstMoves: readonly SgfCoord[];
  /** Maximum depth of any line */
  maxDepth: number;
  /** Total number of variations */
  variationCount: number;
}

/**
 * Parse raw solution data from puzzle.
 *
 * @param solutions - Raw solution array from puzzle (e.g., [["aa", "bb"], ["aa", "bc"]])
 * @param playerSide - The side the player is playing
 * @returns Parsed solution structure
 */
export function parseSolution(
  solutions: readonly (readonly string[])[],
  playerSide: Side
): ParsedSolution {
  const lines: SolutionLine[] = [];
  const correctFirstMoves = new Set<SgfCoord>();
  let maxDepth = 0;

  for (const sequence of solutions) {
    const moves = parseLine(sequence, playerSide);

    if (moves.length > 0) {
      lines.push({
        moves,
        depth: moves.length,
      });

      // Track first move
      const firstMove = moves[0];
      if (firstMove) {
        correctFirstMoves.add(firstMove.coord);
      }

      // Track max depth
      maxDepth = Math.max(maxDepth, moves.length);
    }
  }

  return {
    lines,
    correctFirstMoves: Array.from(correctFirstMoves),
    maxDepth,
    variationCount: lines.length,
  };
}

/**
 * Parse a single solution line.
 *
 * @param sequence - Array of SGF coordinates
 * @param playerSide - Side the player is playing
 * @returns Array of solution moves
 */
export function parseLine(
  sequence: readonly string[],
  playerSide: Side
): SolutionMove[] {
  const moves: SolutionMove[] = [];
  let currentSide = playerSide;

  for (const coord of sequence) {
    if (!isValidSgfCoord(coord)) {
      continue;
    }

    moves.push({
      coord: coord,
      side: currentSide,
      isPlayerMove: currentSide === playerSide,
    });

    // Alternate sides
    currentSide = currentSide === 'B' ? 'W' : 'B';
  }

  return moves;
}

/**
 * Check if a move is a valid first move in the solution.
 *
 * @param solution - Parsed solution
 * @param coord - Move to check
 * @returns true if this is a correct first move
 */
export function isCorrectFirstMove(
  solution: ParsedSolution,
  coord: SgfCoord
): boolean {
  return solution.correctFirstMoves.includes(coord);
}

/**
 * Get all possible responses to a player move.
 *
 * @param solution - Parsed solution
 * @param moveHistory - Moves made so far
 * @returns Array of valid opponent responses
 */
export function getResponses(
  solution: ParsedSolution,
  moveHistory: readonly SgfCoord[]
): SgfCoord[] {
  const responses = new Set<SgfCoord>();
  const historyLength = moveHistory.length;

  for (const line of solution.lines) {
    // Check if this line matches the history
    if (!matchesHistory(line, moveHistory)) {
      continue;
    }

    // Get the next move (opponent response)
    const nextMoveIndex = historyLength;
    if (nextMoveIndex < line.moves.length) {
      const nextMove = line.moves[nextMoveIndex];
      if (nextMove && !nextMove.isPlayerMove) {
        responses.add(nextMove.coord);
      }
    }
  }

  return Array.from(responses);
}

/**
 * Check if a solution line matches the move history.
 *
 * @param line - Solution line to check
 * @param history - Move history
 * @returns true if line starts with history
 */
export function matchesHistory(
  line: SolutionLine,
  history: readonly SgfCoord[]
): boolean {
  if (history.length > line.moves.length) {
    return false;
  }

  for (let i = 0; i < history.length; i++) {
    const lineMove = line.moves[i];
    if (!lineMove || lineMove.coord !== history[i]) {
      return false;
    }
  }

  return true;
}

/**
 * Get solution lines that match the current history.
 *
 * @param solution - Parsed solution
 * @param history - Move history
 * @returns Matching solution lines
 */
export function getMatchingLines(
  solution: ParsedSolution,
  history: readonly SgfCoord[]
): SolutionLine[] {
  return solution.lines.filter((line) => matchesHistory(line, history));
}

/**
 * Check if the player has completed a solution.
 *
 * @param solution - Parsed solution
 * @param history - Move history
 * @returns true if any solution line is complete
 */
export function isSolutionComplete(
  solution: ParsedSolution,
  history: readonly SgfCoord[]
): boolean {
  for (const line of solution.lines) {
    if (
      matchesHistory(line, history) &&
      history.length >= line.moves.filter((m) => m.isPlayerMove).length * 2 - 1
    ) {
      // Check if all player moves are made
      const playerMoves = line.moves.filter((m) => m.isPlayerMove);
      if (history.length >= playerMoves.length) {
        return true;
      }
    }
  }

  return false;
}

/**
 * Get remaining moves in the best matching solution.
 *
 * @param solution - Parsed solution
 * @param history - Move history
 * @returns Remaining moves or empty array
 */
export function getRemainingMoves(
  solution: ParsedSolution,
  history: readonly SgfCoord[]
): SolutionMove[] {
  const matching = getMatchingLines(solution, history);

  if (matching.length === 0) {
    return [];
  }

  // Return remaining moves from shortest matching line
  const shortest = matching.reduce((a, b) =>
    a.depth < b.depth ? a : b
  );

  return shortest.moves.slice(history.length);
}

/**
 * Validate that a solution structure is well-formed.
 *
 * @param solutions - Raw solution data
 * @returns Validation result with errors
 */
export function validateSolutionStructure(
  solutions: unknown
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!Array.isArray(solutions)) {
    errors.push('Solution must be an array');
    return { valid: false, errors };
  }

  if (solutions.length === 0) {
    errors.push('Solution must have at least one variation');
    return { valid: false, errors };
  }

  for (let i = 0; i < solutions.length; i++) {
    const line = solutions[i];

    if (!Array.isArray(line)) {
      errors.push(`Solution line ${i} must be an array`);
      continue;
    }

    if (line.length === 0) {
      errors.push(`Solution line ${i} must have at least one move`);
      continue;
    }

    for (let j = 0; j < line.length; j++) {
      const move = line[j];

      if (typeof move !== 'string') {
        errors.push(`Solution line ${i} move ${j} must be a string`);
        continue;
      }

      if (!isValidSgfCoord(move)) {
        errors.push(`Solution line ${i} move ${j} is not a valid SGF coordinate: ${move}`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
