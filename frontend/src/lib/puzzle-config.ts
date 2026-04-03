/**
 * Puzzle Config Builder — creates GobanConfig for puzzle mode.
 *
 * Accepts a PuzzleObject (from sgfToPuzzle) with `initial_state`, `move_tree`,
 * `width`, `height`, `initial_player`. Passes structured data to goban — no
 * monkey-patches needed, no `original_sgf`.
 *
 * Pipeline: Raw SGF → sgfToPuzzle() → PuzzleObject → buildPuzzleConfig() → goban
 *
 * Pure module: no side effects, no DOM access, no state.
 * @module puzzle-config
 */

import type { GobanConfig } from "goban";
import type { GobanBounds } from "../types/goban";
import type { PuzzleObject } from "./sgf-to-puzzle";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Options for building puzzle config. */
export interface PuzzleConfigOptions {
  /** Board container element. */
  boardDiv: HTMLElement;
  /** Move tree container element (optional). */
  moveTreeContainer?: HTMLElement | null;
  /** Board bounds for partial display (auto-viewport). */
  bounds?: GobanBounds | null;
  /** Initial display width for sizing. */
  displayWidth?: number;
  /** Label position for coordinate labels. */
  labelPosition?: 'all' | 'none';
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

/**
 * Sensible defaults for puzzle mode.
 * All coordinate labels default to true (show all sides).
 */
export const PUZZLE_CONFIG_DEFAULTS = {
  mode: "puzzle" as const,
  puzzle_opponent_move_mode: "automatic" as const,
  puzzle_player_move_mode: "free" as const,
  interactive: true,
  draw_top_labels: true,
  draw_left_labels: true,
  draw_bottom_labels: true,
  draw_right_labels: true,
  square_size: "auto" as unknown as number, // Let goban derive from display_width
  display_width: 320,                       // Initial fallback; GobanContainer resizes via setSquareSizeBasedOnDisplayWidth
  player_id: 1,    // Must be non-zero: goban's onMouseMove guard requires truthy player_id for hover stones
  dont_show_messages: true,
  getPuzzlePlacementSetting: () => ({ mode: "play" as const }),
} as const;

// ---------------------------------------------------------------------------
// Builder
// ---------------------------------------------------------------------------

/**
 * Build a GobanConfig from a structured PuzzleObject.
 *
 * Uses `initial_state`, `move_tree`, `width`, `height`, `initial_player`
 * from the puzzle object. No `original_sgf` — goban receives structured data
 * via its native puzzle loading path. Zero monkey-patches needed.
 *
 * @param puzzle  - PuzzleObject from sgfToPuzzle() with structured data
 * @param options - Board div, bounds, display width, label position
 * @returns GobanConfig ready for GobanCanvas or SVGRenderer constructor
 */
export function buildPuzzleConfig(
  puzzle: PuzzleObject,
  options: PuzzleConfigOptions,
): GobanConfig {
  const showLabels = (options.labelPosition ?? 'all') === 'all';

  // The goban library allocates gutter space for labels on ALL enabled sides
  // via computeMetrics(), but only DRAWS labels on sides where bounds touch
  // the board edge (drawCoordinateLabels). This creates empty gutters on
  // cropped sides. Fix: only enable labels for sides at the board edge.
  const bounds = options.bounds;
  const drawTop = showLabels && (!bounds || bounds.top === 0);
  const drawLeft = showLabels && (!bounds || bounds.left === 0);
  const drawBottom = showLabels && (!bounds || bounds.bottom === puzzle.height - 1);
  const drawRight = showLabels && (!bounds || bounds.right === puzzle.width - 1);

  const gobanConfig: GobanConfig = {
    ...PUZZLE_CONFIG_DEFAULTS,
    board_div: options.boardDiv,

    // Structured puzzle data — no original_sgf
    initial_state: puzzle.initial_state,
    move_tree: puzzle.move_tree,
    width: puzzle.width,
    height: puzzle.height,
    initial_player: puzzle.initial_player,

    // Coordinate labels — only on sides where bounds touch the board edge.
    // Prevents empty gutters on cropped sides.
    draw_top_labels: drawTop,
    draw_left_labels: drawLeft,
    draw_bottom_labels: drawBottom,
    draw_right_labels: drawRight,
  };

  if (options.moveTreeContainer) {
    gobanConfig.move_tree_container = options.moveTreeContainer;
  }

  if (bounds) {
    // Clamp bounds to valid board range [0, dimension-1] as defense-in-depth.
    // Prevents out-of-range bounds from reaching the goban renderer (e.g. if
    // computeBounds() is called with a mismatched boardSize).
    const maxX = puzzle.width - 1;
    const maxY = puzzle.height - 1;
    gobanConfig.bounds = {
      top: Math.max(0, Math.min(bounds.top, maxY)),
      left: Math.max(0, Math.min(bounds.left, maxX)),
      bottom: Math.max(0, Math.min(bounds.bottom, maxY)),
      right: Math.max(0, Math.min(bounds.right, maxX)),
    };
  }

  if (options.displayWidth) {
    gobanConfig.display_width = options.displayWidth;
  }

  return gobanConfig;
}
