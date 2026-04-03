/**
 * Numbered Solution Unit Tests
 * @module tests/unit/numbered-solution.test
 *
 * Tests for T007-T008: Numbered solution display with collision detection.
 * Covers FR-001, FR-002, FR-015, FR-016.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import {
  buildNumberedSequence,
  formatCollisionCaption,
  getMovesAtFrame,
  getCollisionsAtFrame,
} from '../../src/lib/presentation/numberedSolution';
import type { NumberedSequenceResult, StoneColor } from '../../src/models/SolutionPresentation';

// ============================================================================
// Test Data - matches SolutionMove interface (x, y, color)
// ============================================================================

/** Simple linear sequence with no captures */
const SIMPLE_MOVES = [
  { x: 2, y: 2, color: 'B' as StoneColor },
  { x: 3, y: 3, color: 'W' as StoneColor },
  { x: 4, y: 4, color: 'B' as StoneColor },
  { x: 5, y: 5, color: 'W' as StoneColor },
];

/** Sequence with a recapture (moves at same position) */
const RECAPTURE_MOVES = [
  { x: 2, y: 2, color: 'B' as StoneColor },  // Move 1
  { x: 3, y: 3, color: 'W' as StoneColor },  // Move 2
  { x: 4, y: 4, color: 'B' as StoneColor },  // Move 3
  { x: 2, y: 2, color: 'W' as StoneColor },  // Move 4 at same position as 1 (recapture)
];

/** Sequence with multiple collisions */
const MULTI_COLLISION_MOVES = [
  { x: 0, y: 0, color: 'B' as StoneColor },  // Move 1
  { x: 1, y: 1, color: 'W' as StoneColor },  // Move 2
  { x: 0, y: 0, color: 'B' as StoneColor },  // Move 3 = 1
  { x: 1, y: 1, color: 'W' as StoneColor },  // Move 4 = 2
  { x: 0, y: 0, color: 'B' as StoneColor },  // Move 5 = 1, 3
];

// ============================================================================
// buildNumberedSequence Tests
// ============================================================================

describe('buildNumberedSequence', () => {
  it('should number moves sequentially starting from 1', () => {
    const result = buildNumberedSequence(SIMPLE_MOVES);
    
    expect(result.moves).toHaveLength(4);
    expect(result.moves[0].moveNumber).toBe(1);
    expect(result.moves[1].moveNumber).toBe(2);
    expect(result.moves[2].moveNumber).toBe(3);
    expect(result.moves[3].moveNumber).toBe(4);
  });

  it('should preserve coordinates from input', () => {
    const result = buildNumberedSequence(SIMPLE_MOVES);
    
    expect(result.moves[0].coord).toEqual({ x: 2, y: 2 });
    expect(result.moves[1].coord).toEqual({ x: 3, y: 3 });
    expect(result.moves[2].coord).toEqual({ x: 4, y: 4 });
    expect(result.moves[3].coord).toEqual({ x: 5, y: 5 });
  });

  it('should preserve stone colors', () => {
    const result = buildNumberedSequence(SIMPLE_MOVES);
    
    expect(result.moves[0].color).toBe('B');
    expect(result.moves[1].color).toBe('W');
    expect(result.moves[2].color).toBe('B');
    expect(result.moves[3].color).toBe('W');
  });

  it('should detect no collisions in simple sequence', () => {
    const result = buildNumberedSequence(SIMPLE_MOVES);
    
    expect(result.collisions).toHaveLength(0);
    result.moves.forEach((move: { collisionWith: number | null }) => {
      expect(move.collisionWith).toBeNull();
    });
  });

  it('should detect collision when moves at same position', () => {
    const result = buildNumberedSequence(RECAPTURE_MOVES);
    
    expect(result.collisions).toHaveLength(1);
    expect(result.collisions[0].laterMove).toBe(4);
    expect(result.collisions[0].originalMove).toBe(1);
    expect(result.collisions[0].coord).toEqual({ x: 2, y: 2 });
  });

  it('should mark collision reference on later move', () => {
    const result = buildNumberedSequence(RECAPTURE_MOVES);
    
    expect(result.moves[3].collisionWith).toBe(1);
    // Original move should not have collision reference
    expect(result.moves[0].collisionWith).toBeNull();
  });

  it('should detect multiple collisions', () => {
    const result = buildNumberedSequence(MULTI_COLLISION_MOVES);
    
    expect(result.collisions.length).toBeGreaterThanOrEqual(2);
  });

  it('should return empty result for empty input', () => {
    const result = buildNumberedSequence([]);
    
    expect(result.moves).toHaveLength(0);
    expect(result.collisions).toHaveLength(0);
    expect(result.totalMoves).toBe(0);
  });

  it('should handle single move', () => {
    const result = buildNumberedSequence([{ x: 0, y: 0, color: 'B' as StoneColor }]);
    
    expect(result.moves).toHaveLength(1);
    expect(result.moves[0].moveNumber).toBe(1);
    expect(result.totalMoves).toBe(1);
  });
});

// ============================================================================
// formatCollisionCaption Tests
// ============================================================================

describe('formatCollisionCaption', () => {
  it('should format single collision', () => {
    const collisions = [
      { laterMove: 7, originalMove: 3, coord: { x: 2, y: 2 } },
    ];
    
    const caption = formatCollisionCaption(collisions);
    
    expect(caption).toContain('7');
    expect(caption).toContain('3');
  });

  it('should format multiple collisions', () => {
    const collisions = [
      { laterMove: 4, originalMove: 1, coord: { x: 0, y: 0 } },
      { laterMove: 5, originalMove: 2, coord: { x: 1, y: 1 } },
    ];
    
    const caption = formatCollisionCaption(collisions);
    
    expect(caption).toContain('4');
    expect(caption).toContain('1');
    expect(caption).toContain('5');
    expect(caption).toContain('2');
  });

  it('should return empty string for no collisions', () => {
    const caption = formatCollisionCaption([]);
    
    expect(caption).toBe('');
  });
});

// ============================================================================
// getMovesAtFrame Tests
// ============================================================================

describe('getMovesAtFrame', () => {
  let sequence: NumberedSequenceResult;

  beforeAll(() => {
    sequence = buildNumberedSequence(SIMPLE_MOVES);
  });

  it('should return empty array for frame 0', () => {
    const moves = getMovesAtFrame(sequence, 0);
    
    expect(moves).toHaveLength(0);
  });

  it('should return first move for frame 1', () => {
    const moves = getMovesAtFrame(sequence, 1);
    
    expect(moves).toHaveLength(1);
    expect(moves[0].moveNumber).toBe(1);
  });

  it('should return all moves up to frame', () => {
    const moves = getMovesAtFrame(sequence, 3);
    
    expect(moves).toHaveLength(3);
    expect(moves.map((m) => m.moveNumber)).toEqual([1, 2, 3]);
  });

  it('should cap at total moves', () => {
    const moves = getMovesAtFrame(sequence, 100);
    
    expect(moves).toHaveLength(4);
  });

  it('should handle negative frame', () => {
    const moves = getMovesAtFrame(sequence, -5);
    
    expect(moves).toHaveLength(0);
  });
});

// ============================================================================
// getCollisionsAtFrame Tests
// ============================================================================

describe('getCollisionsAtFrame', () => {
  let sequence: NumberedSequenceResult;

  beforeAll(() => {
    sequence = buildNumberedSequence(RECAPTURE_MOVES);
  });

  it('should return empty before collision occurs', () => {
    const collisions = getCollisionsAtFrame(sequence, 3);
    
    expect(collisions).toHaveLength(0);
  });

  it('should return collision at frame when it occurs', () => {
    const collisions = getCollisionsAtFrame(sequence, 4);
    
    expect(collisions).toHaveLength(1);
    expect(collisions[0].laterMove).toBe(4);
  });

  it('should return all collisions up to frame', () => {
    const multiSequence = buildNumberedSequence(MULTI_COLLISION_MOVES);
    const collisions = getCollisionsAtFrame(multiSequence, 5);
    
    expect(collisions.length).toBeGreaterThanOrEqual(2);
  });
});
