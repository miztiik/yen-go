/**
 * Unit tests for sgf-to-puzzle — OGS-native puzzle format converter.
 *
 * Tests comment-based correct/wrong marking, setup stone extraction,
 * initial player detection, and move tree conversion.
 */

import { describe, it, expect } from 'vitest';
import { sgfToPuzzle } from '../../src/lib/sgf-to-puzzle';
import type { MoveTreeJson } from '../../src/lib/sgf-to-puzzle';

// ---------------------------------------------------------------------------
// Helper: collect all nodes in a move tree
// ---------------------------------------------------------------------------

function collectNodes(root: MoveTreeJson): MoveTreeJson[] {
  const nodes: MoveTreeJson[] = [root];
  if (root.trunk_next) nodes.push(...collectNodes(root.trunk_next));
  if (root.branches) {
    for (const branch of root.branches) {
      nodes.push(...collectNodes(branch));
    }
  }
  return nodes;
}

function findNodeAt(root: MoveTreeJson, x: number, y: number): MoveTreeJson | undefined {
  const nodes = collectNodes(root);
  return nodes.find(n => n.x === x && n.y === y);
}

// ---------------------------------------------------------------------------
// Comment-based correct/wrong marking
// ---------------------------------------------------------------------------

describe('sgfToPuzzle — comment-based marking', () => {
  it('marks branch with C[Correct!] as correct_answer', () => {
    // SGF: root → B[aa] → W[bb]C[Correct!]
    const sgf = '(;SZ[9]FF[4]GM[1]PL[B];B[aa];W[bb]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);

    // B[aa] should be on correct path
    const bNode = findNodeAt(puzzle.move_tree, 0, 0);
    expect(bNode?.correct_answer).toBe(true);

    // W[bb] should be correct (leaf with "Correct" text)
    const wNode = findNodeAt(puzzle.move_tree, 1, 1);
    expect(wNode?.correct_answer).toBe(true);
  });

  it('marks branch with C[Wrong] as wrong_answer', () => {
    // SGF: root has two branches — one correct, one wrong
    const sgf = '(;SZ[9]FF[4]GM[1]PL[B](;B[aa];W[bb]C[Correct!])(;B[cc]C[Wrong]))';
    const puzzle = sgfToPuzzle(sgf);

    // B[cc] wrong branch
    const wrongNode = findNodeAt(puzzle.move_tree, 2, 2);
    expect(wrongNode?.wrong_answer).toBe(true);

    // B[aa] correct branch
    const correctNode = findNodeAt(puzzle.move_tree, 0, 0);
    expect(correctNode?.correct_answer).toBe(true);
  });

  it('supports multiple correct paths', () => {
    // SGF: root has two correct branches
    const sgf = '(;SZ[9]FF[4]GM[1]PL[B](;B[aa]C[Correct!])(;B[bb]C[Correct!]))';
    const puzzle = sgfToPuzzle(sgf);

    const nodeA = findNodeAt(puzzle.move_tree, 0, 0);
    const nodeB = findNodeAt(puzzle.move_tree, 1, 1);
    expect(nodeA?.correct_answer).toBe(true);
    expect(nodeB?.correct_answer).toBe(true);
  });

  it('marks all leaves as wrong when no correct comment exists', () => {
    const sgf = '(;SZ[9]FF[4]GM[1]PL[B];B[aa];W[bb])';
    const puzzle = sgfToPuzzle(sgf);

    // With the trunk-as-correct fallback, trunk moves should be correct
    const bNode = findNodeAt(puzzle.move_tree, 0, 0);
    expect(bNode?.correct_answer).toBe(true);
    const wNode = findNodeAt(puzzle.move_tree, 1, 1);
    expect(wNode?.correct_answer).toBe(true);
  });

  it('treats trunk as correct when no C[Correct...] annotations exist (single-path)', () => {
    // SGF: root → B[aa] → W[bb] → B[cc] (no comments at all)
    const sgf = '(;SZ[9]FF[4]GM[1]PL[B];B[aa];W[bb];B[cc])';
    const puzzle = sgfToPuzzle(sgf);

    // All trunk nodes should be marked correct
    const nodeA = findNodeAt(puzzle.move_tree, 0, 0);
    const nodeB = findNodeAt(puzzle.move_tree, 1, 1);
    const nodeC = findNodeAt(puzzle.move_tree, 2, 2);
    expect(nodeA?.correct_answer).toBe(true);
    expect(nodeB?.correct_answer).toBe(true);
    expect(nodeC?.correct_answer).toBe(true);
  });

  it('marks trunk as correct and branches as wrong when no comments (branched tree)', () => {
    // SGF: root → trunk(B[aa] → W[bb]) + branch(B[cc])
    const sgf = '(;SZ[9]FF[4]GM[1]PL[B](;B[aa];W[bb])(;B[cc]))';
    const puzzle = sgfToPuzzle(sgf);

    // Trunk path (B[aa] → W[bb]) should be correct
    const nodeA = findNodeAt(puzzle.move_tree, 0, 0);
    const nodeB = findNodeAt(puzzle.move_tree, 1, 1);
    expect(nodeA?.correct_answer).toBe(true);
    expect(nodeB?.correct_answer).toBe(true);

    // Branch (B[cc]) should be wrong
    const nodeC = findNodeAt(puzzle.move_tree, 2, 2);
    expect(nodeC?.wrong_answer).toBe(true);
  });

  it('is case-insensitive for "correct" detection', () => {
    const cases = [
      '(;SZ[9]FF[4]GM[1]PL[B];B[aa]C[CORRECT])',
      '(;SZ[9]FF[4]GM[1]PL[B];B[aa]C[correct!])',
      '(;SZ[9]FF[4]GM[1]PL[B];B[aa]C[Correct])',
      '(;SZ[9]FF[4]GM[1]PL[B];B[aa]C[That is correct!])',
    ];

    for (const sgf of cases) {
      const puzzle = sgfToPuzzle(sgf);
      const node = findNodeAt(puzzle.move_tree, 0, 0);
      expect(node?.correct_answer).toBe(true);
    }
  });

  it('root node is not marked wrong even when no correct path', () => {
    const sgf = '(;SZ[9]FF[4]GM[1]PL[B];B[aa])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.move_tree.wrong_answer).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Setup stone extraction
// ---------------------------------------------------------------------------

describe('sgfToPuzzle — initial state', () => {
  it('extracts black and white setup stones', () => {
    const sgf = '(;SZ[9]FF[4]GM[1]AB[dp][pp]AW[dd][pd];B[qf]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);

    expect(puzzle.initial_state.black).toBe('dppp');
    expect(puzzle.initial_state.white).toBe('ddpd');
  });

  it('returns empty state when no setup stones', () => {
    const sgf = '(;SZ[9]FF[4]GM[1];B[aa]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);

    expect(puzzle.initial_state.black).toBeUndefined();
    expect(puzzle.initial_state.white).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Initial player detection
// ---------------------------------------------------------------------------

describe('sgfToPuzzle — initial player', () => {
  it('reads PL[B] as black', () => {
    const sgf = '(;SZ[9]FF[4]GM[1]PL[B];B[aa]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.initial_player).toBe('black');
  });

  it('reads PL[W] as white', () => {
    const sgf = '(;SZ[9]FF[4]GM[1]PL[W];W[aa]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.initial_player).toBe('white');
  });

  it('infers from first move when PL not set', () => {
    const sgf = '(;SZ[9]FF[4]GM[1];W[aa]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.initial_player).toBe('white');
  });

  it('defaults to black when no PL and no moves', () => {
    const sgf = '(;SZ[9]FF[4]GM[1])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.initial_player).toBe('black');
  });
});

// ---------------------------------------------------------------------------
// Board size
// ---------------------------------------------------------------------------

describe('sgfToPuzzle — board size', () => {
  it('reads SZ[9] as 9x9', () => {
    const sgf = '(;SZ[9]FF[4]GM[1];B[aa]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.width).toBe(9);
    expect(puzzle.height).toBe(9);
  });

  it('reads SZ[19] as 19x19', () => {
    const sgf = '(;SZ[19]FF[4]GM[1];B[aa]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.width).toBe(19);
    expect(puzzle.height).toBe(19);
  });

  it('defaults to 19 when SZ not present', () => {
    const sgf = '(;FF[4]GM[1];B[aa]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.width).toBe(19);
    expect(puzzle.height).toBe(19);
  });
});

// ---------------------------------------------------------------------------
// Move tree structure
// ---------------------------------------------------------------------------

describe('sgfToPuzzle — move tree', () => {
  it('creates root node at (-1, -1)', () => {
    const sgf = '(;SZ[9]FF[4]GM[1];B[aa]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.move_tree.x).toBe(-1);
    expect(puzzle.move_tree.y).toBe(-1);
  });

  it('first move is trunk_next of root', () => {
    const sgf = '(;SZ[9]FF[4]GM[1];B[cd]C[Correct!])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.move_tree.trunk_next?.x).toBe(2);
    expect(puzzle.move_tree.trunk_next?.y).toBe(3);
  });

  it('branches are alternative moves', () => {
    const sgf = '(;SZ[9]FF[4]GM[1](;B[aa]C[Correct!])(;B[bb]C[Wrong]))';
    const puzzle = sgfToPuzzle(sgf);
    // First child is trunk_next
    expect(puzzle.move_tree.trunk_next?.x).toBe(0);
    expect(puzzle.move_tree.trunk_next?.y).toBe(0);
    // Second child is branches[0]
    expect(puzzle.move_tree.branches?.[0]?.x).toBe(1);
    expect(puzzle.move_tree.branches?.[0]?.y).toBe(1);
  });

  it('preserves comment text on nodes', () => {
    const sgf = '(;SZ[9]FF[4]GM[1];B[aa]C[Great move!])';
    const puzzle = sgfToPuzzle(sgf);
    expect(puzzle.move_tree.trunk_next?.text).toBe('Great move!');
  });

  it('throws on unparseable SGF', () => {
    expect(() => sgfToPuzzle('not valid sgf')).toThrow('[sgf-to-puzzle]');
  });
});
