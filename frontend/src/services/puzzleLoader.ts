/**
 * SGF-Based Puzzle Loader Service
 * @module services/puzzleLoader
 *
 * Loads individual puzzles from static SGF files in the yengo-puzzle-collections directory.
 * Provides the core fetchSGFContent and loadPuzzleFromPath functions used by
 * higher-level services (level browsing, daily challenges, timed modes).
 *
 * Constitution Compliance:
 * - I. Zero Runtime Backend: Loads from static files only
 */

import type { InternalPuzzle, Position } from '@/types/puzzle-internal';
import { parseSGF } from '@/lib/sgf-parser';
import { buildSolutionTree } from '@/lib/sgf-solution';
import { sgfToPosition } from '@/utils/coordinates';
import type { ParsedSGF } from '@/types/sgf';
import { FALLBACK_LEVEL } from '@/lib/levels/level-defaults';
import { APP_CONSTANTS } from '@/config/constants';
import { extractHints } from '@/lib/hints/sgf-mapper';

const CDN_BASE_PATH = APP_CONSTANTS.paths.cdnBase;

// ============================================================================
// Types
// ============================================================================

/** Error types for loader operations */
export type LoaderError =
  | 'network_error'
  | 'not_found'
  | 'parse_error'
  | 'invalid_data';

/** Result wrapper for all loader operations */
export interface LoaderResult<T> {
  success: boolean;
  data?: T;
  error?: LoaderError;
  message?: string;
}

/**
 * A loaded puzzle with its SGF content and metadata.
 * Used by PuzzleRushPage and PuzzleSetPlayer.
 */
export interface LoadedPuzzle {
  id: string;
  sgf: string;
  level: string;
  path: string;
}

/** Re-export InternalPuzzle as Puzzle for convenience */
export type { InternalPuzzle as Puzzle } from '@/types/puzzle-internal';

// ============================================================================
// SGF Fetching
// ============================================================================

/**
 * Fetch raw SGF content from CDN.
 * Path is relative to CDN root (e.g., "sgf/0001/abc123.sgf")
 */
export async function fetchSGFContent(path: string): Promise<LoaderResult<string>> {
  try {
    const response = await fetch(`${CDN_BASE_PATH}/${path}`);

    if (!response.ok) {
      if (response.status === 404) {
        return { success: false, error: 'not_found', message: `SGF file not found: ${path}` };
      }
      return {
        success: false,
        error: 'network_error',
        message: `HTTP ${response.status}: ${response.statusText}`,
      };
    }

    const content = await response.text();
    return { success: true, data: content };
  } catch (error) {
    return {
      success: false,
      error: 'network_error',
      message: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// ============================================================================
// Puzzle Loading
// ============================================================================

/**
 * Load and parse a puzzle from its SGF path.
 * Returns the internal puzzle representation.
 */
export async function loadPuzzleFromPath(
  id: string,
  path: string,
  levelHint?: string
): Promise<LoaderResult<InternalPuzzle>> {
  // Fetch SGF content
  const sgfResult = await fetchSGFContent(path);
  if (!sgfResult.success || sgfResult.data === undefined) {
    return {
      success: false,
      error: sgfResult.error ?? 'not_found',
      message: sgfResult.message ?? `Could not fetch SGF: ${path}`,
    };
  }

  // Parse SGF
  let parsed: ParsedSGF;
  try {
    parsed = parseSGF(sgfResult.data);
  } catch (error) {
    return {
      success: false,
      error: 'parse_error',
      message: error instanceof Error ? `SGF parse error: ${error.message}` : 'Unknown parse error',
    };
  }

  // Convert to internal puzzle format
  const puzzle = convertParsedSGFToInternal(id, parsed, levelHint);

  return { success: true, data: puzzle };
}

// ============================================================================
// Internal Helpers
// ============================================================================

/**
 * Helper to filter out null values from coordinate mapping.
 */
function filterValidPositions(coords: string[]): Position[] {
  const positions: Position[] = [];
  for (const coord of coords) {
    const pos = sgfToPosition(coord);
    if (pos !== null) {
      positions.push(pos);
    }
  }
  return positions;
}

/**
 * Convert parsed SGF to internal puzzle format.
 */
function convertParsedSGFToInternal(
  id: string,
  parsed: ParsedSGF,
  levelHint?: string
): InternalPuzzle {
  const { root, gameInfo } = parsed;
  const props = root.properties;

  // Extract YenGo properties
  const yg = props.YG ?? '';
  const yt = props.YT ?? '';

  // Parse level from YG (format: "beginner:1" or just "beginner")
  let level = levelHint ?? FALLBACK_LEVEL;
  let subLevel: number | undefined;
  if (yg !== '') {
    const parts = yg.split(':');
    const levelPart = parts[0];
    if (levelPart !== undefined && levelPart !== '') {
      level = levelPart;
    }
    const subLevelPart = parts[1];
    if (subLevelPart !== undefined) {
      const parsedSubLevel = parseInt(subLevelPart, 10);
      if (!isNaN(parsedSubLevel)) {
        subLevel = parsedSubLevel;
      }
    }
  }

  // Parse tags from YT (comma-separated)
  const tags = yt !== '' ? yt.split(',').map(t => t.trim()).filter(t => t !== '') : [];

  // Extract hints using consolidated hint parser
  const hints = extractHints(props as Record<string, unknown>);

  // Convert stone positions from SGF coordinates (filter out invalid)
  const blackStones = filterValidPositions(gameInfo.blackStones);
  const whiteStones = filterValidPositions(gameInfo.whiteStones);

  // Build solution tree
  const solutionTree = buildSolutionTree(root, gameInfo.sideToMove);

  // Build puzzle object, only including optional properties when defined
  const puzzle: InternalPuzzle = {
    id,
    boardSize: gameInfo.boardSize,
    blackStones,
    whiteStones,
    sideToMove: gameInfo.sideToMove,
    solutionTree,
    level,
    tags,
    hints,
  };

  // Add optional properties only if they have values
  if (subLevel !== undefined) {
    puzzle.subLevel = subLevel;
  }

  return puzzle;
}
