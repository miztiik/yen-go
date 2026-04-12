/**
 * Puzzle Adapter Service
 * @module services/puzzleAdapter
 *
 * Converts between SGF-native InternalPuzzle format and types/puzzle.ts Puzzle format.
 * This allows the SGF loading to work with pages/PuzzleView component.
 *
 * Constitution Compliance:
 * - VII. Deterministic: Same input always produces same output
 *
 * Note: Legacy adapter functions (adaptToLegacyPuzzle, adaptToLegacyPuzzles) have been
 * removed as part of spec 115 (Frontend PuzzleView Consolidation). The app now uses
 * the new puzzle format exclusively via adaptToPagesPuzzle.
 */

import type {
  InternalPuzzle,
  SolutionNode as SGFSolutionNode,
  Position,
} from '@/types/puzzle-internal';
import type { Puzzle as TypesPuzzle, SgfCoord, Side, BoardRegion, PuzzleTag } from '@/types/puzzle';
import { positionToSgf } from '@/lib/sgf/coordinates';

/**
 * Convert Position array to SGF coordinate strings.
 */
function positionsToSgfCoords(positions: Position[]): string[] {
  return positions.map((pos) => positionToSgf(pos.x, pos.y)).filter((s): s is string => s !== null);
}

/**
 * Extract solution sequences from solution tree.
 * Collects all correct paths as arrays of SGF coordinates.
 */
function extractSolutionSequences(
  node: SGFSolutionNode,
  currentPath: SgfCoord[] = []
): SgfCoord[][] {
  const sequences: SgfCoord[][] = [];

  // Skip empty root node
  if (node.move === '') {
    for (const child of node.children) {
      sequences.push(...extractSolutionSequences(child, currentPath));
    }
    return sequences;
  }

  const newPath = [...currentPath, node.move];

  // If no children, this is a leaf - complete sequence
  if (node.children.length === 0) {
    if (node.isCorrect) {
      sequences.push(newPath);
    }
    return sequences;
  }

  // Continue down correct paths
  for (const child of node.children) {
    if (child.isCorrect) {
      sequences.push(...extractSolutionSequences(child, newPath));
    }
  }

  return sequences;
}

/**
 * Calculate board region from stone positions.
 * Determines the minimal bounding box that contains all stones.
 */
function calculateBoardRegion(
  boardSize: number,
  blackStones: Position[],
  whiteStones: Position[]
): BoardRegion {
  const allStones = [...blackStones, ...whiteStones];

  if (allStones.length === 0) {
    return { w: boardSize, h: boardSize };
  }

  const xs = allStones.map((p) => p.x);
  const ys = allStones.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  // Add margin of 2
  const margin = 2;
  const x1 = Math.max(0, minX - margin);
  const y1 = Math.max(0, minY - margin);
  const x2 = Math.min(boardSize - 1, maxX + margin);
  const y2 = Math.min(boardSize - 1, maxY + margin);

  const w = x2 - x1 + 1;
  const h = y2 - y1 + 1;

  // Determine corner based on position
  let corner: BoardRegion['corner'] = 'C';
  const centerX = boardSize / 2;
  const centerY = boardSize / 2;
  const avgX = (minX + maxX) / 2;
  const avgY = (minY + maxY) / 2;

  if (avgY < centerY - 3) {
    corner = avgX < centerX - 3 ? 'TL' : avgX > centerX + 3 ? 'TR' : 'T';
  } else if (avgY > centerY + 3) {
    corner = avgX < centerX - 3 ? 'BL' : avgX > centerX + 3 ? 'BR' : 'B';
  } else {
    corner = avgX < centerX - 3 ? 'L' : avgX > centerX + 3 ? 'R' : 'C';
  }

  return { w, h, corner };
}

/**
 * Convert InternalPuzzle to types/puzzle.ts Puzzle format.
 * This is the format used by pages/PuzzleView.tsx with full desktop layout.
 */
export function adaptToPagesPuzzle(internal: InternalPuzzle): TypesPuzzle {
  const blackSgf = positionsToSgfCoords(internal.blackStones);
  const whiteSgf = positionsToSgfCoords(internal.whiteStones);

  // Extract solution sequences from tree
  const sol = extractSolutionSequences(internal.solutionTree);

  // Calculate board region for viewport
  const region = calculateBoardRegion(
    internal.boardSize,
    internal.blackStones,
    internal.whiteStones
  );

  return {
    v: 1,
    side: internal.sideToMove as Side,
    region,
    boardSize: internal.boardSize,
    ...(blackSgf.length > 0 ? { B: blackSgf } : {}),
    ...(whiteSgf.length > 0 ? { W: whiteSgf } : {}),
    sol: sol as (readonly SgfCoord[])[],
    level: internal.level,
    tags: (internal.tags ?? []) as readonly PuzzleTag[],
    ...('rank' in internal && typeof internal.rank === 'string' && internal.rank
      ? { rank: internal.rank }
      : {}),
    ...(internal.hints?.hints?.[0] ? { hint: internal.hints.hints[0] } : {}),
  };
}
