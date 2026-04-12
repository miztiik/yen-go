/**
 * Explore Hints Extractor
 * @module lib/presentation/exploreHints
 *
 * Extracts valid and invalid move hints from the solution tree
 * at the current position for explore mode display.
 *
 * Constitution Compliance:
 * - V. No Browser AI: Extracts from pre-computed solution tree
 * - VI. Type Safety: Strict TypeScript types
 */

import type { Coordinate, ExploreHint, StoneColor } from '@models/SolutionPresentation';

/**
 * Solution tree node with children representing valid moves.
 */
export interface SolutionTreeNode {
  /** Coordinate of this move (null for root) */
  coord: Coordinate | null;
  /** Color of this move */
  color?: StoneColor;
  /** Child nodes (valid continuations) */
  children: SolutionTreeNode[];
  /** Whether this path leads to a winning result */
  isCorrect?: boolean;
  /** Optional comment at this node */
  comment?: string;
  /** Whether this is the optimal/main line */
  isMainLine?: boolean;
}

/**
 * Result of explore hint extraction.
 */
export interface ExploreHintsResult {
  /** All available hints at current position */
  hints: ExploreHint[];
  /** Valid moves (correct continuations) */
  validMoves: Coordinate[];
  /** Invalid moves (known wrong continuations) */
  invalidMoves: Coordinate[];
  /** Whether there are any hints available */
  hasHints: boolean;
}

/**
 * Get explore hints for the current position in the solution tree.
 * Valid moves are those that continue on a correct path.
 * Invalid moves are those that lead to a wrong result.
 *
 * @param currentNode - Current position in solution tree
 * @param allLegalMoves - All legal moves at this position (from rules engine)
 * @returns ExploreHintsResult with valid/invalid classification
 *
 * @example
 * ```ts
 * const hints = getExploreHints(currentTreeNode, legalMoves);
 * // hints.validMoves = moves that continue correct path
 * // hints.invalidMoves = moves that lead to loss
 * ```
 */
export function getExploreHints(
  currentNode: SolutionTreeNode | null,
  allLegalMoves: readonly Coordinate[] = []
): ExploreHintsResult {
  if (!currentNode) {
    return createEmptyResult();
  }

  const validMoves: Coordinate[] = [];
  const invalidMoves: Coordinate[] = [];
  const hints: ExploreHint[] = [];

  // Moves in the solution tree are known continuations
  const knownMoves = new Map<string, { isCorrect: boolean; outcome?: string | undefined }>();

  for (const child of currentNode.children) {
    if (child.coord) {
      const key = coordToKey(child.coord);
      const isCorrect = child.isCorrect !== false; // Default to true if not specified
      knownMoves.set(key, {
        isCorrect,
        outcome: child.comment,
      });
    }
  }

  // Classify all legal moves
  for (const move of allLegalMoves) {
    const key = coordToKey(move);
    const known = knownMoves.get(key);

    if (known) {
      // Move is in solution tree
      if (known.isCorrect) {
        validMoves.push(move);
        hints.push({
          coord: move,
          isValid: true,
          outcome: known.outcome,
        });
      } else {
        invalidMoves.push(move);
        hints.push({
          coord: move,
          isValid: false,
          outcome: known.outcome,
        });
      }
    } else {
      // Move is not in solution tree - treat as invalid/unknown
      invalidMoves.push(move);
      hints.push({
        coord: move,
        isValid: false,
        outcome: 'Not in solution tree',
      });
    }
  }

  return {
    hints,
    validMoves,
    invalidMoves,
    hasHints: hints.length > 0,
  };
}

/**
 * Get hints only from the solution tree children (without checking all legal moves).
 * Useful when we don't have access to the full legal moves list.
 *
 * @param currentNode - Current position in solution tree
 * @returns ExploreHintsResult with moves from solution tree only
 */
export function getExploreHintsFromTree(currentNode: SolutionTreeNode | null): ExploreHintsResult {
  if (!currentNode || currentNode.children.length === 0) {
    return createEmptyResult();
  }

  const validMoves: Coordinate[] = [];
  const invalidMoves: Coordinate[] = [];
  const hints: ExploreHint[] = [];

  for (const child of currentNode.children) {
    if (!child.coord) continue;

    const isCorrect = child.isCorrect !== false;

    if (isCorrect) {
      validMoves.push(child.coord);
    } else {
      invalidMoves.push(child.coord);
    }

    hints.push({
      coord: child.coord,
      isValid: isCorrect,
      outcome: child.comment,
    });
  }

  return {
    hints,
    validMoves,
    invalidMoves,
    hasHints: hints.length > 0,
  };
}

/**
 * Find the optimal (main line) move at current position.
 *
 * @param currentNode - Current position in solution tree
 * @returns Optimal move coordinate or null if none
 */
export function getOptimalMove(currentNode: SolutionTreeNode | null): Coordinate | null {
  if (!currentNode || currentNode.children.length === 0) {
    return null;
  }

  // First, look for explicitly marked main line
  const mainLineChild = currentNode.children.find((c) => c.isMainLine && c.coord);
  if (mainLineChild?.coord) {
    return mainLineChild.coord;
  }

  // Otherwise, return the first correct child
  const correctChild = currentNode.children.find((c) => c.isCorrect !== false && c.coord);
  return correctChild?.coord ?? null;
}

/**
 * Check if a move is valid at the current position.
 *
 * @param coord - Move to check
 * @param currentNode - Current position in solution tree
 * @returns True if move leads to correct continuation
 */
export function isMoveValid(coord: Coordinate, currentNode: SolutionTreeNode | null): boolean {
  if (!currentNode) return false;

  const key = coordToKey(coord);
  for (const child of currentNode.children) {
    if (child.coord && coordToKey(child.coord) === key) {
      return child.isCorrect !== false;
    }
  }

  return false;
}

/**
 * Create an empty result for when no hints are available.
 */
function createEmptyResult(): ExploreHintsResult {
  return {
    hints: [],
    validMoves: [],
    invalidMoves: [],
    hasHints: false,
  };
}

/**
 * Convert coordinate to map key.
 */
function coordToKey(coord: Coordinate): string {
  return `${coord.x},${coord.y}`;
}
