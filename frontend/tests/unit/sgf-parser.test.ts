/**
 * SGF Parser Unit Tests
 * @module tests/unit/sgf-parser.test
 *
 * Tests for T005: SGF parser covering parsing, property extraction, and error handling.
 * TDD approach: Tests written before implementation.
 */

import { describe, it, expect } from 'vitest';
import { parseSGF, validateSGF, SGFParseErrorImpl } from '../../src/lib/sgf-parser';
import type { ParsedSGF, SGFNode, SGFProperties, GameInfo } from '../../src/types/sgf';

// ============================================================================
// Test Data: Valid SGF Files
// ============================================================================

/**
 * Minimal valid SGF for a 9x9 puzzle.
 * Black to play, simple setup with AB/AW stones.
 */
const MINIMAL_SGF = `(;FF[4]GM[1]SZ[9]
AB[aa][ba][ca]
AW[ab][bb]
PL[B]
;B[cb]
;W[da])`;

/**
 * SGF with YenGo custom properties.
 * Simple structure with separate properties on one line.
 */
const YENGO_SGF = `(;FF[4]GM[1]SZ[9]YV[1]YG[beginner]YT[killing]YH1[cb]YH2[Look for snapback]YH3[Black can play C2]YR[25k]AB[aa][ba][ca]AW[ab][bb]PL[B];B[cb];W[da];B[db])`;

/**
 * SGF with multiple variations (branching solution tree).
 */
const MULTI_VARIATION_SGF = `(;FF[4]GM[1]SZ[9]
AB[aa][ba]
AW[ab]
PL[B]
(;B[ca];W[da];B[ea])
(;B[cb];W[db];B[eb]))`;

/**
 * 19x19 board setup.
 */
const LARGE_BOARD_SGF = `(;FF[4]GM[1]SZ[19]
AB[dd][pd][dp][pp]
AW[dc][pc][cp][pq]
PL[B]
;B[qc])`;

// ============================================================================
// Test Data: Invalid SGF Files
// ============================================================================

const INVALID_SGFS = {
  empty: '',
  noParens: 'FF[4]GM[1]SZ[9]',
  noSemicolon: '(FF[4]GM[1])',
  unclosedBracket: '(;FF[4]GM[1]SZ[',  // Truly unclosed bracket at end
  noClosingParen: '(;FF[4]GM[1]SZ[9]',
  invalidPlayer: '(;FF[4]GM[1]SZ[9]PL[X])',
};

// ============================================================================
// SGF Parsing Tests (T005)
// ============================================================================

describe('SGF Parser', () => {
  describe('parseSGF()', () => {
    it('parses minimal valid SGF', () => {
      const result = parseSGF(MINIMAL_SGF);
      expect(result).toBeDefined();
      expect(result.root).toBeDefined();
      expect(result.gameInfo).toBeDefined();
    });

    it('extracts standard properties (FF, GM, SZ)', () => {
      const result = parseSGF(MINIMAL_SGF);
      const props = result.root.properties;
      expect(props.FF).toBe('4');
      expect(props.GM).toBe('1');
      expect(props.SZ).toBe('9');
    });

    it('parses AB (Add Black) as array', () => {
      const result = parseSGF(MINIMAL_SGF);
      expect(result.root.properties.AB).toEqual(['aa', 'ba', 'ca']);
    });

    it('parses AW (Add White) as array', () => {
      const result = parseSGF(MINIMAL_SGF);
      expect(result.root.properties.AW).toEqual(['ab', 'bb']);
    });

    it('parses PL (Player to move)', () => {
      const result = parseSGF(MINIMAL_SGF);
      expect(result.root.properties.PL).toBe('B');
    });

    it('parses YenGo custom properties', () => {
      const result = parseSGF(YENGO_SGF);
      const props = result.root.properties;
      expect(props.YV).toBe('1');
      expect(props.YG).toBe('beginner');
      expect(props.YT).toBe('killing');
      expect(props.YH1).toBe('cb');
      expect(props.YH2).toBe('Look for snapback');
      expect(props.YH3).toBe('Black can play C2');
      expect(props.YR).toBe('25k');
    });

    it('parses child nodes (moves)', () => {
      const result = parseSGF(MINIMAL_SGF);
      expect(result.root.children.length).toBeGreaterThan(0);
      expect(result.root.children[0]?.properties.B).toBe('cb');
    });

    it('parses multiple variations', () => {
      const result = parseSGF(MULTI_VARIATION_SGF);
      const root = result.root;
      expect(root.children.length).toBe(2);
      expect(root.children[0]?.properties.B).toBe('ca');
      expect(root.children[1]?.properties.B).toBe('cb');
    });

    it('parses 19x19 board', () => {
      const result = parseSGF(LARGE_BOARD_SGF);
      expect(result.gameInfo.boardSize).toBe(19);
    });

    it('handles whitespace and newlines correctly', () => {
      const sgfWithWhitespace = `(; FF[4] GM[1] SZ[9] \n\n AB[aa]  [ba] )`;
      const result = parseSGF(sgfWithWhitespace);
      expect(result.root.properties.AB).toEqual(['aa', 'ba']);
    });

    it('handles escaped characters in values', () => {
      const sgfWithEscape = `(;FF[4]GM[1]SZ[9]C[Test \\] bracket])`;
      const result = parseSGF(sgfWithEscape);
      expect(result.root.properties.C).toBe('Test ] bracket');
    });
  });

  describe('extractGameInfo()', () => {
    it('extracts board size from SZ property', () => {
      const result = parseSGF(MINIMAL_SGF);
      expect(result.gameInfo.boardSize).toBe(9);
    });

    it('extracts black stones from AB property', () => {
      const result = parseSGF(MINIMAL_SGF);
      expect(result.gameInfo.blackStones).toEqual(['aa', 'ba', 'ca']);
    });

    it('extracts white stones from AW property', () => {
      const result = parseSGF(MINIMAL_SGF);
      expect(result.gameInfo.whiteStones).toEqual(['ab', 'bb']);
    });

    it('extracts side to move from PL property', () => {
      const result = parseSGF(MINIMAL_SGF);
      expect(result.gameInfo.sideToMove).toBe('B');
    });

    it('defaults side to move to B if PL missing', () => {
      const sgfNoPL = '(;FF[4]GM[1]SZ[9]AB[aa])';
      const result = parseSGF(sgfNoPL);
      expect(result.gameInfo.sideToMove).toBe('B');
    });

    it('handles empty stone lists', () => {
      const sgfNoStones = '(;FF[4]GM[1]SZ[9]PL[B])';
      const result = parseSGF(sgfNoStones);
      expect(result.gameInfo.blackStones).toEqual([]);
      expect(result.gameInfo.whiteStones).toEqual([]);
    });
  });

  describe('validateSGF()', () => {
    it('returns true for valid SGF', () => {
      expect(validateSGF(MINIMAL_SGF)).toBe(true);
      expect(validateSGF(YENGO_SGF)).toBe(true);
    });

    it('returns false for empty string', () => {
      expect(validateSGF(INVALID_SGFS.empty)).toBe(false);
    });

    it('returns false for missing parentheses', () => {
      expect(validateSGF(INVALID_SGFS.noParens)).toBe(false);
    });

    it('returns false for missing semicolon', () => {
      expect(validateSGF(INVALID_SGFS.noSemicolon)).toBe(false);
    });

    it('returns false for unclosed bracket', () => {
      expect(validateSGF(INVALID_SGFS.unclosedBracket)).toBe(false);
    });

    it('returns false for missing closing paren', () => {
      expect(validateSGF(INVALID_SGFS.noClosingParen)).toBe(false);
    });
  });

  describe('Error Handling', () => {
    it('throws SGFParseError for invalid input', () => {
      expect(() => parseSGF(INVALID_SGFS.empty)).toThrow();
    });

    it('includes position in error for unclosed bracket', () => {
      try {
        parseSGF(INVALID_SGFS.unclosedBracket);
        expect.fail('Should have thrown');
      } catch (e) {
        expect((e as SGFParseErrorImpl).position).toBeDefined();
      }
    });

    it('includes line number in error when determinable', () => {
      // SGF with unclosed bracket at end - will hit EOF and report line number
      const multiLineInvalid = `(;FF[4]
GM[1]
SZ[9]
PL[B`;  // Missing closing ] and )
      try {
        parseSGF(multiLineInvalid);
        expect.fail('Should have thrown');
      } catch (e) {
        const error = e as SGFParseErrorImpl;
        expect(error.line).toBeDefined();
        expect(error.line).toBeGreaterThan(1);  // Should be on line 4
      }
    });
  });
});

// ============================================================================
// Export Test Data for Integration Tests
// ============================================================================

export const SGF_TEST_DATA = {
  MINIMAL_SGF,
  YENGO_SGF,
  MULTI_VARIATION_SGF,
  LARGE_BOARD_SGF,
  INVALID_SGFS,
};