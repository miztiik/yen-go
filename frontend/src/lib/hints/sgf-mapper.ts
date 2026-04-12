/**
 * SGF Hint Mapper - Extracts and maps hints from SGF properties
 * @module lib/hints/sgf-mapper
 *
 * YenGo SGF Hint Properties:
 * - YH: Compact hint format (v7+) - pipe-separated: hint1|hint2|hint3
 * - YH1: Position hint (SGF coordinate, e.g., "cb") - deprecated in v7
 * - YH2: Technique hint (string, e.g., "snapback") - deprecated in v7
 * - YH3: Full text hint (string) - deprecated in v7
 *
 *
 * Covers: US3, FR-016
 */

import type { PuzzleHints, Position } from '@/types/puzzle-internal';
import { sgfToPosition } from '@/utils/coordinates';

/**
 * YenGo SGF hint properties structure.
 */
export interface SGFHintProperties {
  /** Compact hints (v7+) - pipe-separated */
  YH?: string;
  /** @deprecated Position hint - SGF coordinate */
  YH1?: string;
  /** @deprecated Technique hint - technique name */
  YH2?: string;
  /** @deprecated Text hint - full explanation */
  YH3?: string;
}

/**
 * Extract hints from SGF properties.
 * Supports both v7+ compact format (YH) and v6 legacy format (YH1/YH2/YH3).
 *
 * @param properties - SGF root node properties containing YH or YH1/YH2/YH3
 * @returns PuzzleHints object with parsed hints
 */
export function extractHints(properties: Record<string, unknown>): PuzzleHints {
  const hints: PuzzleHints = { hints: [] };

  // Try v7+ compact format first
  const yh = properties.YH as string | undefined;
  if (yh !== undefined && yh !== '') {
    hints.hints = yh
      .split('|')
      .map((h) => h.trim())
      .filter((h) => h.length > 0);
    // Populate legacy fields for backward compatibility
    if (hints.hints[0] !== undefined) {
      const position = sgfToPosition(hints.hints[0]);
      if (position) {
        hints.position = position;
      }
    }
    if (hints.hints[1] !== undefined) {
      hints.technique = hints.hints[1];
    }
    if (hints.hints[2] !== undefined) {
      hints.text = hints.hints[2];
    }
    return hints;
  }

  // Fall back to v6 legacy format
  const hintsList: string[] = [];

  // YH1: Position hint
  const yh1 = properties.YH1 as string | undefined;
  if (yh1) {
    hintsList.push(yh1);
    const position = sgfToPosition(yh1);
    if (position) {
      hints.position = position;
    }
  }

  // YH2: Technique hint
  const yh2 = properties.YH2 as string | undefined;
  if (yh2) {
    hintsList.push(yh2);
    hints.technique = yh2;
  }

  // YH3: Text hint
  const yh3 = properties.YH3 as string | undefined;
  if (yh3) {
    hintsList.push(yh3);
    hints.text = yh3;
  }

  hints.hints = hintsList;
  return hints;
}

/**
 * Generate fallback hint from first correct move coordinate.
 * Used when YH3 (text hint) is not provided.
 *
 * @param firstCorrectMove - SGF coordinate of the first correct move, or null
 * @param boardSize - Board size for coordinate description
 * @returns Generated hint text
 */
export function generateFallbackHint(
  firstCorrectMove: string | null,
  boardSize: number = 9
): string {
  if (!firstCorrectMove) {
    return 'Look carefully at the position.';
  }

  // Convert SGF coordinate to position
  const position = sgfToPosition(firstCorrectMove);
  if (!position) {
    return 'Look carefully at the position.';
  }

  // Generate descriptive hint based on position
  return generatePositionDescription(position, boardSize);
}

/**
 * Generate a positional description for a hint.
 */
function generatePositionDescription(position: Position, boardSize: number): string {
  const { x, y } = position;
  const mid = Math.floor(boardSize / 2);
  const nearEdge = 2; // Near edge if within 2 intersections

  const nearLeft = x < nearEdge;
  const nearRight = x >= boardSize - nearEdge;
  const nearTop = y < nearEdge;
  const nearBottom = y >= boardSize - nearEdge;

  // Corner positions
  if (nearTop && nearLeft) {
    return 'The key move is in the upper-left corner area.';
  }
  if (nearTop && nearRight) {
    return 'The key move is in the upper-right corner area.';
  }
  if (nearBottom && nearLeft) {
    return 'The key move is in the lower-left corner area.';
  }
  if (nearBottom && nearRight) {
    return 'The key move is in the lower-right corner area.';
  }

  // Edge positions
  if (nearTop) {
    return 'The key move is along the top edge.';
  }
  if (nearBottom) {
    return 'The key move is along the bottom edge.';
  }
  if (nearLeft) {
    return 'The key move is along the left edge.';
  }
  if (nearRight) {
    return 'The key move is along the right edge.';
  }

  // Center positions
  const nearCenter = Math.abs(x - mid) <= 2 && Math.abs(y - mid) <= 2;
  if (nearCenter) {
    return 'The key move is in the center area.';
  }

  // Default
  return 'Look for the critical point in the position.';
}

/**
 * Convert column to letter (a-s for 19x19).
 */
export function columnToLetter(col: number): string {
  // Skip 'i' as per Go convention
  const letters = 'abcdefghjklmnopqrst';
  return letters[col] ?? '?';
}

/**
 * Convert position to human-readable coordinate (e.g., "C4").
 */
export function positionToHumanCoord(position: Position, boardSize: number = 19): string {
  const col = columnToLetter(position.x).toUpperCase();
  // Row numbers count from bottom in human notation
  const row = boardSize - position.y;
  return `${col}${row}`;
}

/**
 * Get technique-based hint text.
 *
 * @param technique - Technique name from YH2
 * @returns Hint text for the technique
 */
export function getTechniqueHint(technique: string): string {
  const techniqueHints: Record<string, string> = {
    snapback: 'Look for a snapback opportunity.',
    ladder: 'Can you start a ladder?',
    net: 'Consider using a net (geta) to capture.',
    ko: 'This problem involves ko.',
    seki: 'Consider the possibility of seki.',
    'throw-in': 'Think about a throw-in move.',
    sacrifice: 'A sacrifice might be the key.',
    squeeze: 'Look for a squeeze play.',
    'connect-and-die': 'Connecting might lead to death.',
    'under-the-stones': 'Look for an under-the-stones play.',
    'bent-four': 'This involves bent four in the corner.',
    'l-group': 'Consider the L-group shape.',
    'bulky-five': 'Think about bulky five.',
    'false-eye': 'Can you create a false eye?',
  };

  return techniqueHints[technique.toLowerCase()] ?? `This problem uses the ${technique} technique.`;
}

/**
 * Get progressive hint based on level.
 *
 * @param hints - Puzzle hints from SGF
 * @param firstCorrectMove - First correct move coordinate or null
 * @param level - Hint level (1, 2, or 3)
 * @param boardSize - Board size
 * @returns Hint text for the specified level
 */
export function getProgressiveHint(
  hints: PuzzleHints,
  firstCorrectMove: string | null,
  level: 1 | 2 | 3,
  boardSize: number = 9
): string {
  switch (level) {
    case 1:
      // Level 1: General guidance or region hint
      if (hints.position) {
        return generatePositionDescription(hints.position, boardSize);
      }
      return 'Look carefully at the position.';

    case 2:
      // Level 2: Technique hint
      if (hints.technique) {
        return getTechniqueHint(hints.technique);
      }
      // Fall back to position hint if no technique
      if (hints.position) {
        return `Focus on the ${positionToHumanCoord(hints.position, boardSize)} area.`;
      }
      return generateFallbackHint(firstCorrectMove, boardSize);

    case 3:
      // Level 3: Full text hint or generated fallback
      if (hints.text) {
        return hints.text;
      }
      // Generate fallback from first move
      return generateFallbackHint(firstCorrectMove, boardSize);

    default:
      return '';
  }
}

/**
 * Create highlight region from hints.
 *
 * @param hints - Puzzle hints
 * @param firstCorrectMove - First correct move coordinate or null
 * @returns Highlight region or null
 */
export function createHighlightRegion(
  hints: PuzzleHints,
  firstCorrectMove: string | null
): { center: Position; radius: number } | null {
  // Prefer YH1 position
  if (hints.position) {
    return {
      center: hints.position,
      radius: 1,
    };
  }

  // Fall back to first correct move
  if (firstCorrectMove) {
    const position = sgfToPosition(firstCorrectMove);
    if (position) {
      return {
        center: position,
        radius: 2, // Larger radius to not give away exact point
      };
    }
  }

  return null;
}
