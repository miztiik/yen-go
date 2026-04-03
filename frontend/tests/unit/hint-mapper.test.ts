/**
 * Hint Mapper Unit Tests
 * Tests: T026 - Unit test for hint mapping from SGF properties
 */
import { describe, it, expect } from 'vitest';
import {
  extractHints,
  generateFallbackHint,
  getTechniqueHint,
  getProgressiveHint,
  createHighlightRegion,
  positionToHumanCoord,
  columnToLetter,
} from '@/lib/hints/sgf-mapper';
import type { SolutionNode } from '@/types/puzzle-internal';

// First correct move from the sample solution tree ('ce')
const sampleFirstCorrectMove: string | null = 'ce';

// Sample solution tree for fallback hint tests
const sampleSolutionTree: SolutionNode = {
  move: '',
  player: 'B',
  isCorrect: true,
  isUserMove: false,
  children: [
    {
      move: 'ce',
      player: 'B',
      isCorrect: true,
      isUserMove: true,
      children: [],
    },
    {
      move: 'de',
      player: 'B',
      isCorrect: false,
      isUserMove: true,
      children: [],
    },
  ],
};

describe('Hint Mapper', () => {
  describe('extractHints', () => {
    // v7+ compact format tests
    describe('v7 compact format (YH)', () => {
      it('should extract single hint from YH', () => {
        const properties = { YH: 'Focus on corner' };
        const hints = extractHints(properties);

        expect(hints.hints).toEqual(['Focus on corner']);
      });

      it('should extract multiple hints from YH with pipe separator', () => {
        const properties = { YH: 'Focus on corner|snapback|Capture via snapback' };
        const hints = extractHints(properties);

        expect(hints.hints).toEqual(['Focus on corner', 'snapback', 'Capture via snapback']);
      });

      it('should populate legacy fields for backward compatibility', () => {
        const properties = { YH: 'ce|ladder|Start the ladder' };
        const hints = extractHints(properties);

        expect(hints.hints).toEqual(['ce', 'ladder', 'Start the ladder']);
        expect(hints.position).toEqual({ x: 2, y: 4 }); // 'ce' parsed as position
        expect(hints.technique).toBe('ladder');
        expect(hints.text).toBe('Start the ladder');
      });

      it('should prefer YH over YH1/YH2/YH3 when both present', () => {
        const properties = { 
          YH: 'v7 hint 1|v7 hint 2', 
          YH1: 'v6 position',
          YH2: 'v6 technique',
          YH3: 'v6 text'
        };
        const hints = extractHints(properties);

        expect(hints.hints).toEqual(['v7 hint 1', 'v7 hint 2']);
        expect(hints.hints.length).toBe(2);
      });

      it('should trim whitespace from hints', () => {
        const properties = { YH: '  Focus on corner  |  snapback  ' };
        const hints = extractHints(properties);

        expect(hints.hints).toEqual(['Focus on corner', 'snapback']);
      });

      it('should filter out empty hints after split', () => {
        const properties = { YH: 'hint1||hint3' };
        const hints = extractHints(properties);

        expect(hints.hints).toEqual(['hint1', 'hint3']);
      });

      it('should handle empty YH string', () => {
        const properties = { YH: '' };
        const hints = extractHints(properties);

        expect(hints.hints).toEqual([]);
      });
    });

    // v6 legacy format tests
    describe('v6 legacy format (YH1/YH2/YH3)', () => {
      it('should extract YH1 position hint', () => {
        const properties = { YH1: 'ce' };
        const hints = extractHints(properties);

        expect(hints.position).toEqual({ x: 2, y: 4 }); // 'c' = 2, 'e' = 4
        expect(hints.hints).toEqual(['ce']);
      });

      it('should extract YH2 technique hint', () => {
        const properties = { YH2: 'snapback' };
        const hints = extractHints(properties);

        expect(hints.technique).toBe('snapback');
        expect(hints.hints).toEqual(['snapback']);
      });

      it('should extract YH3 text hint', () => {
        const properties = { YH3: 'Capture the cutting stone' };
        const hints = extractHints(properties);

        expect(hints.text).toBe('Capture the cutting stone');
        expect(hints.hints).toEqual(['Capture the cutting stone']);
      });

      it('should extract all hints when present', () => {
        const properties = {
          YH1: 'ab',
          YH2: 'ladder',
          YH3: 'Start the ladder to capture',
        };
        const hints = extractHints(properties);

        expect(hints.position).toEqual({ x: 0, y: 1 });
        expect(hints.technique).toBe('ladder');
        expect(hints.text).toBe('Start the ladder to capture');
        expect(hints.hints).toEqual(['ab', 'ladder', 'Start the ladder to capture']);
      });

      it('should handle missing hints gracefully', () => {
        const properties = {};
        const hints = extractHints(properties);

        expect(hints.position).toBeUndefined();
        expect(hints.technique).toBeUndefined();
        expect(hints.text).toBeUndefined();
        expect(hints.hints).toEqual([]);
      });

      it('should handle invalid YH1 coordinates', () => {
        const properties = { YH1: 'xyz' };
        const hints = extractHints(properties);

        expect(hints.position).toBeUndefined();
        expect(hints.hints).toEqual(['xyz']); // Still in hints array
      });

      it('should handle empty string values', () => {
        const properties = { YH1: '', YH2: '', YH3: '' };
        const hints = extractHints(properties);

        // Empty strings should not create hint entries
        expect(hints.position).toBeUndefined();
        expect(hints.technique).toBeUndefined();
        expect(hints.text).toBeUndefined();
        expect(hints.hints).toEqual([]);
      });
    });
  });

  describe('generateFallbackHint', () => {
    it('should generate hint from first correct move', () => {
      const hint = generateFallbackHint(sampleFirstCorrectMove, 9);

      // 'ce' = x:2, y:4 - near center on 9x9
      expect(hint).toBeTruthy();
      expect(typeof hint).toBe('string');
    });

    it('should return default hint if no moves in tree', () => {
      const hint = generateFallbackHint(null, 9);

      expect(hint).toBe('Look carefully at the position.');
    });

    it('should describe corner positions', () => {
      const hint = generateFallbackHint('aa', 9); // Top-left corner
      expect(hint.toLowerCase()).toContain('corner');
    });

    it('should describe edge positions', () => {
      const hint = generateFallbackHint('ea', 9); // Top edge, middle column
      expect(hint.toLowerCase()).toContain('edge');
    });
  });

  describe('getTechniqueHint', () => {
    it('should return hint for snapback', () => {
      const hint = getTechniqueHint('snapback');
      expect(hint).toBe('Look for a snapback opportunity.');
    });

    it('should return hint for ladder', () => {
      const hint = getTechniqueHint('ladder');
      expect(hint).toBe('Can you start a ladder?');
    });

    it('should return hint for ko', () => {
      const hint = getTechniqueHint('ko');
      expect(hint).toBe('This problem involves ko.');
    });

    it('should return hint for net', () => {
      const hint = getTechniqueHint('net');
      expect(hint).toBe('Consider using a net (geta) to capture.');
    });

    it('should return generic hint for unknown technique', () => {
      const hint = getTechniqueHint('unknown-technique');
      expect(hint).toBe('This problem uses the unknown-technique technique.');
    });

    it('should be case-insensitive', () => {
      const hintLower = getTechniqueHint('snapback');
      const hintUpper = getTechniqueHint('SNAPBACK');
      expect(hintLower).toBe(hintUpper);
    });
  });

  describe('getProgressiveHint', () => {
    const hints = {
      position: { x: 2, y: 4 },
      technique: 'snapback',
      text: 'Capture the stone with a snapback',
    };

    it('should return position hint for level 1', () => {
      const hint = getProgressiveHint(hints, sampleFirstCorrectMove, 1, 9);
      expect(hint).toBeTruthy();
      expect(typeof hint).toBe('string');
    });

    it('should return technique hint for level 2', () => {
      const hint = getProgressiveHint(hints, sampleFirstCorrectMove, 2, 9);
      expect(hint).toContain('snapback');
    });

    it('should return text hint for level 3', () => {
      const hint = getProgressiveHint(hints, sampleFirstCorrectMove, 3, 9);
      expect(hint).toBe('Capture the stone with a snapback');
    });

    it('should fall back to position for level 2 if no technique', () => {
      const hintsNoTechnique = { position: { x: 2, y: 4 } };
      const hint = getProgressiveHint(hintsNoTechnique, sampleFirstCorrectMove, 2, 9);
      expect(hint).toContain('C5'); // Human coordinate for x:2, y:4 on 9x9
    });

    it('should fall back to generated hint for level 3 if no text', () => {
      const hintsNoText = { position: { x: 2, y: 4 } };
      const hint = getProgressiveHint(hintsNoText, sampleFirstCorrectMove, 3, 9);
      expect(hint).toBeTruthy();
    });
  });

  describe('createHighlightRegion', () => {
    it('should create region from YH1 position', () => {
      const hints = { position: { x: 5, y: 5 } };
      const region = createHighlightRegion(hints, sampleFirstCorrectMove);

      expect(region).not.toBeNull();
      expect(region?.center).toEqual({ x: 5, y: 5 });
      expect(region?.radius).toBe(1);
    });

    it('should fall back to first move if no position hint', () => {
      const hints = {};
      const region = createHighlightRegion(hints, sampleFirstCorrectMove);

      expect(region).not.toBeNull();
      expect(region?.center).toEqual({ x: 2, y: 4 }); // 'ce'
      expect(region?.radius).toBe(2); // Larger radius for fallback
    });

    it('should return null if no hints and no first move', () => {
      const region = createHighlightRegion({}, null);

      expect(region).toBeNull();
    });
  });

  describe('positionToHumanCoord', () => {
    it('should convert position to human coordinate on 9x9', () => {
      expect(positionToHumanCoord({ x: 0, y: 0 }, 9)).toBe('A9');
      expect(positionToHumanCoord({ x: 8, y: 8 }, 9)).toBe('J1');
      expect(positionToHumanCoord({ x: 4, y: 4 }, 9)).toBe('E5');
    });

    it('should convert position to human coordinate on 19x19', () => {
      expect(positionToHumanCoord({ x: 0, y: 0 }, 19)).toBe('A19');
      expect(positionToHumanCoord({ x: 18, y: 18 }, 19)).toBe('T1');
      expect(positionToHumanCoord({ x: 9, y: 9 }, 19)).toBe('K10');
    });

    it('should skip I in column letters', () => {
      // Column 8 should be J, not I
      expect(positionToHumanCoord({ x: 8, y: 0 }, 19)).toBe('J19');
    });
  });

  describe('columnToLetter', () => {
    it('should convert column index to letter', () => {
      expect(columnToLetter(0)).toBe('a');
      expect(columnToLetter(7)).toBe('h');
      expect(columnToLetter(8)).toBe('j'); // Skips 'i'
      expect(columnToLetter(18)).toBe('t');
    });

    it('should return ? for out of range', () => {
      expect(columnToLetter(19)).toBe('?');
      expect(columnToLetter(-1)).toBe('?');
    });
  });
});
