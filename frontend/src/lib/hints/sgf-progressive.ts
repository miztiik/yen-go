/**
 * SGF-compatible progressive hint system.
 * Types and constants for SGF-based hint UI.
 * @module lib/hints/sgf-progressive
 *
 *
 * Covers: US3, T029
 */

import type { Position } from '@/types/puzzle-internal';

/**
 * Hint level indicating how much information is revealed.
 */
export type SGFHintLevel = 0 | 1 | 2 | 3;

/**
 * Highlight region for UI display.
 */
export interface SGFHighlightRegion {
  /** Center point of the hint region */
  readonly center: Position;
  /** Radius of the highlight (in intersections) */
  readonly radius: number;
}

/**
 * Hint state for SGF-based puzzles.
 */
export interface SGFHintState {
  /** Current hint level (0 = none, 1-3 = progressive) */
  readonly level: SGFHintLevel;
  /** Text hint to display */
  readonly text: string | null;
  /** Highlighted region (if level >= 3) */
  readonly highlightRegion: SGFHighlightRegion | null;
  /** Can show more hints? */
  readonly canAdvance: boolean;
}

/**
 * Default hint state (no hint).
 */
export const DEFAULT_SGF_HINT_STATE: SGFHintState = {
  level: 0,
  text: null,
  highlightRegion: null,
  canAdvance: true,
};
