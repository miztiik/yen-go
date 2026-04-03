/**
 * Unit tests for puzzle-config builder.
 *
 * OGS-native format: buildPuzzleConfig now takes PuzzleObject (not raw SGF).
 * Uses initial_state + move_tree — no original_sgf, no monkey-patches.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { PUZZLE_CONFIG_DEFAULTS, buildPuzzleConfig } from '../../src/lib/puzzle-config';
import type { PuzzleObject } from '../../src/lib/sgf-to-puzzle';

// A mock PuzzleObject for testing
const MOCK_PUZZLE: PuzzleObject = {
  initial_state: { black: 'dppp', white: 'ddpd' },
  move_tree: { x: -1, y: -1, trunk_next: { x: 5, y: 15, correct_answer: true } },
  width: 19,
  height: 19,
  initial_player: 'black',
};

describe('PUZZLE_CONFIG_DEFAULTS', () => {
  it('sets mode to "puzzle"', () => {
    expect(PUZZLE_CONFIG_DEFAULTS.mode).toBe('puzzle');
  });

  it('sets player_id to 1 (non-zero required for hover stones in puzzle mode)', () => {
    expect(PUZZLE_CONFIG_DEFAULTS.player_id).toBe(1);
  });

  it('draws all 4 coordinate labels by default', () => {
    expect(PUZZLE_CONFIG_DEFAULTS.draw_top_labels).toBe(true);
    expect(PUZZLE_CONFIG_DEFAULTS.draw_left_labels).toBe(true);
    expect(PUZZLE_CONFIG_DEFAULTS.draw_bottom_labels).toBe(true);
    expect(PUZZLE_CONFIG_DEFAULTS.draw_right_labels).toBe(true);
  });

  it('uses auto square size with display_width fallback', () => {
    expect(PUZZLE_CONFIG_DEFAULTS.square_size).toBe('auto');
    expect(PUZZLE_CONFIG_DEFAULTS.display_width).toBe(320);
  });

  it('sets interactive to true', () => {
    expect(PUZZLE_CONFIG_DEFAULTS.interactive).toBe(true);
  });

  it('sets automatic opponent moves', () => {
    expect(PUZZLE_CONFIG_DEFAULTS.puzzle_opponent_move_mode).toBe('automatic');
  });

  it('sets free player moves', () => {
    expect(PUZZLE_CONFIG_DEFAULTS.puzzle_player_move_mode).toBe('free');
  });

  it('suppresses messages', () => {
    expect(PUZZLE_CONFIG_DEFAULTS.dont_show_messages).toBe(true);
  });
});

describe('buildPuzzleConfig', () => {
  let mockBoardDiv: HTMLElement;

  beforeEach(() => {
    mockBoardDiv = document.createElement('div');
  });

  it('includes all defaults in generated config', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    expect(config.mode).toBe('puzzle');
    expect(config.player_id).toBe(1);
    expect(config.interactive).toBe(true);
  });

  it('sets board_div from options', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    expect(config.board_div).toBe(mockBoardDiv);
  });

  it('passes initial_state from puzzle object', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    expect(config.initial_state).toEqual(MOCK_PUZZLE.initial_state);
  });

  it('passes move_tree from puzzle object', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    expect(config.move_tree).toBe(MOCK_PUZZLE.move_tree);
  });

  it('passes width/height/initial_player from puzzle object', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    expect(config.width).toBe(19);
    expect(config.height).toBe(19);
    expect(config.initial_player).toBe('black');
  });

  it('does NOT set original_sgf', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    expect((config as Record<string, unknown>).original_sgf).toBeUndefined();
  });

  it('shows all labels when labelPosition is "all" (default)', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
      labelPosition: 'all',
    });

    expect(config.draw_top_labels).toBe(true);
    expect(config.draw_left_labels).toBe(true);
    expect(config.draw_bottom_labels).toBe(true);
    expect(config.draw_right_labels).toBe(true);
  });

  it('hides all labels when labelPosition is "none"', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
      labelPosition: 'none',
    });

    expect(config.draw_top_labels).toBe(false);
    expect(config.draw_left_labels).toBe(false);
    expect(config.draw_bottom_labels).toBe(false);
    expect(config.draw_right_labels).toBe(false);
  });

  it('defaults to "all" labels when labelPosition not specified', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    expect(config.draw_top_labels).toBe(true);
    expect(config.draw_left_labels).toBe(true);
    expect(config.draw_bottom_labels).toBe(true);
    expect(config.draw_right_labels).toBe(true);
  });

  it('sets bounds when provided', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
      bounds: { top: 0, left: 0, bottom: 9, right: 9 },
    });

    expect(config.bounds).toEqual({ top: 0, left: 0, bottom: 9, right: 9 });
  });

  it('does not set bounds when not provided', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    expect(config.bounds).toBeUndefined();
  });

  it('sets display_width when provided', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
      displayWidth: 400,
    });

    expect(config.display_width).toBe(400);
  });

  it('sets move_tree_container when provided', () => {
    const treeDiv = document.createElement('div');
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
      moveTreeContainer: treeDiv,
    });

    expect(config.move_tree_container).toBe(treeDiv);
  });

  it('preserves display_width and square_size defaults', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    expect(config.display_width).toBe(320);
    expect(config.square_size).toBe('auto');
  });

  // ── Bounds-aware label tests ──

  it('enables labels only on sides touching board edge (top-left corner)', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
      bounds: { top: 0, left: 0, bottom: 9, right: 9 },
    });

    // top/left touch the board edge → labels shown
    expect(config.draw_top_labels).toBe(true);
    expect(config.draw_left_labels).toBe(true);
    // bottom/right are cropped → no labels (prevents empty gutters)
    expect(config.draw_bottom_labels).toBe(false);
    expect(config.draw_right_labels).toBe(false);
  });

  it('enables labels only on sides touching board edge (bottom-right corner)', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
      bounds: { top: 10, left: 10, bottom: 18, right: 18 },
    });

    expect(config.draw_top_labels).toBe(false);
    expect(config.draw_left_labels).toBe(false);
    expect(config.draw_bottom_labels).toBe(true);
    expect(config.draw_right_labels).toBe(true);
  });

  it('enables all labels when bounds span full board', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
      bounds: { top: 0, left: 0, bottom: 18, right: 18 },
    });

    expect(config.draw_top_labels).toBe(true);
    expect(config.draw_left_labels).toBe(true);
    expect(config.draw_bottom_labels).toBe(true);
    expect(config.draw_right_labels).toBe(true);
  });

  it('disables all labels when labelPosition is "none" even with edge bounds', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
      labelPosition: 'none',
      bounds: { top: 0, left: 0, bottom: 18, right: 18 },
    });

    expect(config.draw_top_labels).toBe(false);
    expect(config.draw_left_labels).toBe(false);
    expect(config.draw_bottom_labels).toBe(false);
    expect(config.draw_right_labels).toBe(false);
  });

  it('enables labels on all sides when no bounds are set', () => {
    const config = buildPuzzleConfig(MOCK_PUZZLE, {
      boardDiv: mockBoardDiv,
    });

    // No bounds = full board → all labels
    expect(config.draw_top_labels).toBe(true);
    expect(config.draw_left_labels).toBe(true);
    expect(config.draw_bottom_labels).toBe(true);
    expect(config.draw_right_labels).toBe(true);
  });
});
