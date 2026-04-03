/**
 * Puzzle type definitions
 * Core puzzle type definitions
 * @module types/puzzle
 */

import type { LevelSlug } from '@/lib/levels/config';

/**
 * SGF coordinate string (e.g., "aa", "ba", "ss")
 * Two letters: first is column (a=0), second is row (a=0)
 * Range: a-s for 19x19 board (19 letters)
 */
export type SgfCoord = string;

/**
 * Stone color (black or white) - used for display/ARIA
 * Note: differs from Side ('B' | 'W') which uses SGF notation
 */
export type StoneColor = 'black' | 'white';

/**
 * @deprecated Use Coord from types/coordinate.ts instead (Besogo 1-indexed).
 * Board coordinate with row,col values - legacy pattern.
 */
export interface Coordinate {
  readonly row: number;
  readonly col: number;
}

/**
 * @deprecated Use Coord from types/coordinate.ts instead.
 * Point type - uses x,y coordinate system (legacy).
 */
export interface Point {
  readonly x: number;
  readonly y: number;
}

/**
 * Board corner positions for partial board puzzles
 * - TL: Top-Left
 * - TR: Top-Right
 * - BL: Bottom-Left
 * - BR: Bottom-Right
 * - T/B/L/R: Edge centers
 * - C: Center
 */
export type BoardCorner = 'TL' | 'TR' | 'BL' | 'BR' | 'T' | 'B' | 'L' | 'R' | 'C';

/**
 * Board region definition for partial board display
 */
export interface BoardRegion {
  /** Width in intersections (3-19) */
  readonly w: number;
  /** Height in intersections (3-19) */
  readonly h: number;
  /** Position on full board */
  readonly corner?: BoardCorner;
}

/**
 * Side to move in puzzle
 */
export type Side = 'B' | 'W';

/**
 * Skill Level slug (9-level system from config/puzzle-levels.json)
 */
export type SkillLevel = LevelSlug;

/**
 * Puzzle category tags
 */
export type PuzzleTag =
  | 'living'
  | 'killing'
  | 'ko'
  | 'capturing-race'
  | 'oiotoshi'
  | 'connecting'
  | 'cutting'
  | 'throw-in'
  | 'snapback'
  | 'ladder'
  | 'squeeze'
  | 'under-the-stones'
  | 'seki'
  | 'false-eye';

/**
 * A single tsumego puzzle (optimized format)
 * ~300-500 bytes per puzzle
 */
export interface Puzzle {
  /** Schema version */
  readonly v: number;
  /** Side to move: B=Black, W=White */
  readonly side: Side;
  /** Board region (partial board support) */
  readonly region: BoardRegion;
  /** Full board size (e.g., 9, 13, 19) - used for game logic grid */
  readonly boardSize?: number;
  /** Black stone positions (SGF coordinates) */
  readonly B?: readonly SgfCoord[];
  /** White stone positions (SGF coordinates) */
  readonly W?: readonly SgfCoord[];
  /** Solution sequences (array of move sequences) */
  readonly sol: readonly (readonly SgfCoord[])[];
  /** Common wrong first moves (for feedback) */
  readonly wrong?: readonly SgfCoord[];
  /** Skill Level slug (9-level system) */
  readonly level: SkillLevel;
  /** Problem categories/techniques */
  readonly tags?: readonly PuzzleTag[];
  /** Estimated rank (e.g., '20k', '3d') */
  readonly rank?: string;
  /** Source collection (e.g., 'cho-elem', 'gokyo-shumyo') */
  readonly src?: string;
  /** Optional hint text */
  readonly hint?: string;
}

/**
 * Puzzle with ID (used when loaded from storage)
 */
export interface PuzzleWithId extends Puzzle {
  /** Puzzle ID (e.g., '2026-01-20-001') */
  readonly id: string;
}
