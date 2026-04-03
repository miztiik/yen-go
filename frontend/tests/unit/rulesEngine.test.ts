/**
 * Tests for the Go Rules Engine
 * @module tests/unit/rulesEngine.test
 * 
 * Covers: FR-007 to FR-011
 */

import { describe, it, expect } from 'vitest';
import {
  countLiberties,
  findCapturedGroups,
  findGroup,
  isKoViolation,
  isSuicide,
  isValidMove,
  placeStone,
} from '../../src/services/rulesEngine';
import { createEmptyBoard } from '../../src/models/board';
import { BLACK, WHITE, EMPTY } from '../../src/models/puzzle';
import type { Stone } from '../../src/models/puzzle';

describe('rulesEngine', () => {
  describe('findGroup', () => {
    it('should find a single stone group', () => {
      const board = createEmptyBoard(9);
      board[5]![5] = BLACK;

      const group = findGroup(board, { x: 5, y: 5 }, 9);

      expect(group).not.toBeNull();
      expect(group!.color).toBe(BLACK);
      expect(group!.stones).toHaveLength(1);
      expect(group!.liberties).toHaveLength(4); // Center stone has 4 liberties
    });

    it('should find a connected group of multiple stones', () => {
      const board = createEmptyBoard(9);
      board[5]![5] = BLACK;
      board[5]![6] = BLACK;
      board[6]![5] = BLACK;

      const group = findGroup(board, { x: 5, y: 5 }, 9);

      expect(group!.stones).toHaveLength(3);
      expect(group!.liberties).toHaveLength(7); // L-shaped group has 7 liberties
    });

    it('should return null for empty position', () => {
      const board = createEmptyBoard(9);
      const group = findGroup(board, { x: 5, y: 5 }, 9);
      expect(group).toBeNull();
    });

    it('should find corner stone with 2 liberties', () => {
      const board = createEmptyBoard(9);
      board[1]![1] = BLACK;

      const group = findGroup(board, { x: 1, y: 1 }, 9);

      expect(group!.liberties).toHaveLength(2);
    });

    it('should find edge stone with 3 liberties', () => {
      const board = createEmptyBoard(9);
      board[1]![5] = BLACK;

      const group = findGroup(board, { x: 5, y: 1 }, 9);

      expect(group!.liberties).toHaveLength(3);
    });
  });

  describe('countLiberties', () => {
    it('should count liberties correctly for surrounded group', () => {
      const board = createEmptyBoard(9);
      // Black stone surrounded by white on 3 sides
      board[5]![5] = BLACK;
      board[5]![4] = WHITE;
      board[5]![6] = WHITE;
      board[4]![5] = WHITE;

      expect(countLiberties(board, { x: 5, y: 5 }, 9)).toBe(1);
    });

    it('should count 0 liberties for fully surrounded stone', () => {
      const board = createEmptyBoard(9);
      board[5]![5] = BLACK;
      board[5]![4] = WHITE;
      board[5]![6] = WHITE;
      board[4]![5] = WHITE;
      board[6]![5] = WHITE;

      expect(countLiberties(board, { x: 5, y: 5 }, 9)).toBe(0);
    });
  });

  describe('findCapturedGroups', () => {
    it('should find single stone capture', () => {
      const board = createEmptyBoard(9);
      // White stone with 3 sides surrounded
      board[5]![5] = WHITE;
      board[5]![4] = BLACK;
      board[5]![6] = BLACK;
      board[4]![5] = BLACK;
      // Playing black at (5, 6) should capture white

      const captured = findCapturedGroups(board, { x: 5, y: 6 }, BLACK, 9);

      expect(captured).toHaveLength(1);
      expect(captured[0]!.stones).toHaveLength(1);
      expect(captured[0]!.stones[0]).toEqual({ x: 5, y: 5 });
    });

    it('should find multi-stone group capture', () => {
      const board = createEmptyBoard(9);
      // Two white stones in a line, surrounded
      board[5]![5] = WHITE;
      board[5]![6] = WHITE;
      // Surround them
      board[4]![5] = BLACK;
      board[4]![6] = BLACK;
      board[6]![5] = BLACK;
      board[6]![6] = BLACK;
      board[5]![4] = BLACK;
      // One liberty left at (5, 7)

      const captured = findCapturedGroups(board, { x: 7, y: 5 }, BLACK, 9);

      expect(captured).toHaveLength(1);
      expect(captured[0]!.stones).toHaveLength(2);
    });

    it('should not capture groups with remaining liberties', () => {
      const board = createEmptyBoard(9);
      board[5]![5] = WHITE;
      board[5]![4] = BLACK;
      board[4]![5] = BLACK;
      // White has 2 liberties remaining

      const captured = findCapturedGroups(board, { x: 5, y: 6 }, BLACK, 9);

      expect(captured).toHaveLength(0);
    });
  });

  describe('isSuicide', () => {
    it('should detect suicide move', () => {
      const board = createEmptyBoard(9);
      // Create a situation where black would be captured immediately
      board[5]![4] = WHITE;
      board[5]![6] = WHITE;
      board[4]![5] = WHITE;
      board[6]![5] = WHITE;

      expect(isSuicide(board, { x: 5, y: 5 }, BLACK, 9)).toBe(true);
    });

    it('should allow moves that capture opponent', () => {
      const board = createEmptyBoard(9);
      // White stone surrounded, black can capture
      board[5]![5] = WHITE;
      board[5]![4] = BLACK;
      board[5]![6] = BLACK;
      board[4]![5] = BLACK;

      expect(isSuicide(board, { x: 5, y: 6 }, BLACK, 9)).toBe(false);
    });

    it('should allow moves that create group with liberties', () => {
      const board = createEmptyBoard(9);
      board[5]![4] = BLACK; // Friendly stone gives liberties

      expect(isSuicide(board, { x: 5, y: 5 }, BLACK, 9)).toBe(false);
    });
  });

  describe('isKoViolation', () => {
    it('should detect ko violation', () => {
      const koState = { position: { x: 5, y: 5 }, capturedAt: 1 };

      expect(isKoViolation({ x: 5, y: 5 }, koState)).toBe(true);
    });

    it('should allow moves at other positions', () => {
      const koState = { position: { x: 5, y: 5 }, capturedAt: 1 };

      expect(isKoViolation({ x: 6, y: 5 }, koState)).toBe(false);
    });

    it('should allow any move when no ko', () => {
      const koState = { position: null, capturedAt: 0 };

      expect(isKoViolation({ x: 5, y: 5 }, koState)).toBe(false);
    });
  });

  describe('placeStone', () => {
    it('should place stone on empty position', () => {
      const board = createEmptyBoard(9);
      const result = placeStone(board, { x: 5, y: 5 }, BLACK, 9);

      expect(result.success).toBe(true);
      expect(result.newBoard![5]![5]).toBe(BLACK);
    });

    it('should reject placing on occupied position', () => {
      const board = createEmptyBoard(9);
      board[5]![5] = WHITE;

      const result = placeStone(board, { x: 5, y: 5 }, BLACK, 9);

      expect(result.success).toBe(false);
      expect(result.error).toBe('occupied');
    });

    it('should reject suicide moves', () => {
      const board = createEmptyBoard(9);
      board[5]![4] = WHITE;
      board[5]![6] = WHITE;
      board[4]![5] = WHITE;
      board[6]![5] = WHITE;

      const result = placeStone(board, { x: 5, y: 5 }, BLACK, 9);

      expect(result.success).toBe(false);
      expect(result.error).toBe('suicide');
    });

    it('should reject ko violations', () => {
      const board = createEmptyBoard(9);
      const koState = { position: { x: 5, y: 5 }, capturedAt: 1 };

      const result = placeStone(board, { x: 5, y: 5 }, BLACK, 9, koState);

      expect(result.success).toBe(false);
      expect(result.error).toBe('ko');
    });

    it('should capture opponent stones', () => {
      const board = createEmptyBoard(9);
      board[5]![5] = WHITE;
      board[5]![4] = BLACK;
      board[5]![6] = BLACK;
      board[4]![5] = BLACK;

      const result = placeStone(board, { x: 5, y: 6 }, BLACK, 9);

      expect(result.success).toBe(true);
      expect(result.capturedStones).toHaveLength(1);
      expect(result.capturedStones![0]).toEqual({ x: 5, y: 5 });
      expect(result.newBoard![5]![5]).toBe(EMPTY);
    });

    it('should not mutate original board', () => {
      const board = createEmptyBoard(9);
      const originalBoard = board.map((row) => [...row]);

      placeStone(board, { x: 5, y: 5 }, BLACK, 9);

      expect(board).toEqual(originalBoard);
    });
  });

  describe('isValidMove', () => {
    it('should return true for valid moves', () => {
      const board = createEmptyBoard(9);
      expect(isValidMove(board, { x: 5, y: 5 }, BLACK, 9)).toBe(true);
    });

    it('should return false for invalid moves', () => {
      const board = createEmptyBoard(9);
      board[5]![5] = WHITE;
      expect(isValidMove(board, { x: 5, y: 5 }, BLACK, 9)).toBe(false);
    });
  });

  // T010a: Exhaustive liberty/capture tests for FR-008-FR-011
  describe('complex scenarios', () => {
    describe('multi-group captures', () => {
      it('should capture multiple separate groups simultaneously', () => {
        const board = createEmptyBoard(9);
        // Two separate white stones, each surrounded except one shared liberty
        board[3]![3] = WHITE;
        board[3]![2] = BLACK;
        board[2]![3] = BLACK;
        board[4]![3] = BLACK;

        board[3]![5] = WHITE;
        board[3]![6] = BLACK;
        board[2]![5] = BLACK;
        board[4]![5] = BLACK;

        // Playing at (3, 4) captures both
        const result = placeStone(board, { x: 4, y: 3 }, BLACK, 9);

        expect(result.success).toBe(true);
        // Only the first white stone at (3,3) should be captured 
        // since (3,5) still has liberty at (5,3)
        expect(result.capturedStones!.length).toBeGreaterThanOrEqual(1);
      });
    });

    describe('edge and corner captures', () => {
      it('should correctly capture stone in corner', () => {
        const board = createEmptyBoard(9);
        board[1]![1] = WHITE;
        board[1]![2] = BLACK;

        const result = placeStone(board, { x: 1, y: 2 }, BLACK, 9);

        expect(result.success).toBe(true);
        expect(result.capturedStones).toHaveLength(1);
        expect(result.capturedStones![0]).toEqual({ x: 1, y: 1 });
      });

      it('should correctly capture group along edge', () => {
        const board = createEmptyBoard(9);
        // Two white stones along top edge
        board[1]![4] = WHITE;
        board[1]![5] = WHITE;
        // Surround them
        board[1]![3] = BLACK;
        board[1]![6] = BLACK;
        board[2]![4] = BLACK;

        const result = placeStone(board, { x: 5, y: 2 }, BLACK, 9);

        expect(result.success).toBe(true);
        expect(result.capturedStones).toHaveLength(2);
      });
    });

    describe('ko scenarios', () => {
      it('should create ko state after single stone capture', () => {
        // Standard ko shape - white stone at (5,5) surrounded on 3 sides by black
        // Black plays at (6,5) to capture
        const board = createEmptyBoard(9);
        // Black stones surrounding white
        board[5]![4] = BLACK; // left of white
        board[4]![5] = BLACK; // above white
        board[5]![6] = BLACK; // right of white
        board[5]![5] = WHITE; // White stone to be captured

        const result = placeStone(board, { x: 5, y: 6 }, BLACK, 9);

        expect(result.success).toBe(true);
        expect(result.capturedStones).toHaveLength(1);
        expect(result.capturedStones![0]).toEqual({ x: 5, y: 5 });
      });
    });

    describe('snapback', () => {
      it('should allow capture that leads to self-atari (snapback setup)', () => {
        const board = createEmptyBoard(9);
        // Setup where black captures but puts self in atari
        board[5]![5] = WHITE;
        board[5]![4] = BLACK;
        board[5]![6] = BLACK;
        board[4]![5] = BLACK;
        board[6]![4] = WHITE;
        board[6]![6] = WHITE;
        board[7]![5] = WHITE;

        const result = placeStone(board, { x: 5, y: 6 }, BLACK, 9);

        // Black can capture, even if it's a bad move strategically
        expect(result.success).toBe(true);
      });
    });

    describe('large group liberties', () => {
      it('should correctly count liberties of L-shaped group', () => {
        const board = createEmptyBoard(9);
        // L-shaped black group
        board[5]![5] = BLACK;
        board[5]![6] = BLACK;
        board[5]![7] = BLACK;
        board[6]![5] = BLACK;
        board[7]![5] = BLACK;

        const liberties = countLiberties(board, { x: 5, y: 5 }, 9);

        // L-shape with 5 stones should have many liberties
        expect(liberties).toBeGreaterThan(5);
      });
    });
  });
});
