/**
 * Progressive hint system types and constants.
 * @module lib/hints/progressive
 */

import type { Point } from '../../utils/coordinates';

/**
 * Hint level indicating how much information is revealed.
 */
export type HintLevel = 0 | 1 | 2 | 3;

/**
 * Hint state for a puzzle.
 */
export interface HintState {
  /** Current hint level (0 = none, 1-3 = progressive) */
  readonly level: HintLevel;
  /** Text hint to display */
  readonly text: string | null;
  /** Highlighted region (if level >= 3) */
  readonly highlightRegion: HighlightRegion | null;
  /** Can show more hints? */
  readonly canAdvance: boolean;
}

/**
 * Highlighted region on the board.
 */
export interface HighlightRegion {
  /** Center point of the hint region */
  readonly center: Point;
  /** Radius of the highlight (in intersections) */
  readonly radius: number;
  /** Type of highlight */
  readonly type: 'area' | 'point';
}

/**
 * Default hint state (no hint).
 */
export const DEFAULT_HINT_STATE: HintState = {
  level: 0,
  text: null,
  highlightRegion: null,
  canAdvance: true,
};


