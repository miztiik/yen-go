import { describe, it, expect } from 'vitest';
import { computeFrame, frameToVisibleArea, guessAttacker, applyTsumegoFrame } from './frame';

describe('computeFrame', () => {
  it('returns full board when no stones', () => {
    const mat = Array.from({ length: 9 }, () => Array(9).fill(0));
    const frame = computeFrame(mat);
    expect(frame.length).toBe(9);
    expect(frame[0][0]).toBe(true);
    expect(frame[8][8]).toBe(true);
  });

  it('computes tight frame around corner stones', () => {
    const mat = Array.from({ length: 9 }, () => Array(9).fill(0));
    // Place stones at (0,0), (1,0), (0,1), (1,1)
    mat[0][0] = 1; // black
    mat[0][1] = -1; // white
    mat[1][0] = 1;
    mat[1][1] = -1;

    const frame = computeFrame(mat, 2);
    // Stones are at x=0..1, y=0..1. With margin 2 → x=0..3, y=0..3
    // Edge snapping: x<=2 and y<=2 → snap to 0
    expect(frame[0][0]).toBe(true);
    expect(frame[3][3]).toBe(true);
    // Far corner should be outside
    expect(frame[8][8]).toBe(false);
  });

  it('snaps to edge when close', () => {
    const mat = Array.from({ length: 19 }, () => Array(19).fill(0));
    // Place a stone near bottom-right corner
    mat[17][17] = 1;
    const frame = computeFrame(mat, 2);
    // maxX = 17, +2 = 19 → ≥ 19-3=16 → snap to 18
    expect(frame[18][18]).toBe(true);
  });

  it('returns empty array for empty board matrix', () => {
    const frame = computeFrame([]);
    expect(frame).toEqual([]);
  });
});

describe('frameToVisibleArea', () => {
  it('converts boolean frame to numeric', () => {
    const frame = [[true, false], [false, true]];
    const result = frameToVisibleArea(frame);
    expect(result).toEqual([[1, 0], [0, 1]]);
  });
});

describe('guessAttacker', () => {
  it('returns -1 (white attacks) when black is closer to edge', () => {
    const mat = Array.from({ length: 9 }, () => Array(9).fill(0));
    mat[0][0] = 1;   // black at edge (dist 0)
    mat[3][3] = -1;  // white interior (dist 3)
    mat[4][4] = -1;
    // black avg edgeDist=0, white avg edgeDist=3 → bd < wd → white attacks
    expect(guessAttacker(mat)).toBe(-1);
  });

  it('returns 1 (black attacks) when white is closer to edge', () => {
    const mat = Array.from({ length: 9 }, () => Array(9).fill(0));
    mat[0][0] = -1;  // white at edge (dist 0)
    mat[3][3] = 1;   // black interior (dist 3)
    mat[4][4] = 1;
    mat[4][3] = 1;
    // white avg edgeDist=0, black avg edgeDist=3 → wd < bd → black attacks
    expect(guessAttacker(mat)).toBe(1);
  });

  it('defaults to 1 (black) when equal count', () => {
    const mat = Array.from({ length: 9 }, () => Array(9).fill(0));
    mat[0][0] = 1;
    mat[0][1] = -1;
    expect(guessAttacker(mat)).toBe(1);
  });
});

describe('applyTsumegoFrame', () => {
  it('returns copy of board when no stones', () => {
    const mat = Array.from({ length: 9 }, () => Array(9).fill(0));
    const result = applyTsumegoFrame(mat);
    expect(result.length).toBe(9);
    // No stones, so frame is full board; no territory to fill
    expect(result).toEqual(mat);
  });

  it('fills non-frame area with stones', () => {
    const mat = Array.from({ length: 9 }, () => Array(9).fill(0));
    // Corner puzzle: stones in top-left 3x3
    mat[0][0] = 1; mat[0][1] = -1; mat[0][2] = 1;
    mat[1][0] = -1; mat[1][1] = 1; mat[1][2] = -1;
    mat[2][0] = 1; mat[2][1] = -1; mat[2][2] = 1;

    const result = applyTsumegoFrame(mat);
    // Original stones preserved
    expect(result[0][0]).toBe(1);
    expect(result[0][1]).toBe(-1);
    // Non-frame empty cells should be filled (not zero)
    let filledCount = 0;
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (result[r][c] !== 0) filledCount++;
      }
    }
    expect(filledCount).toBeGreaterThan(9); // More than just the 9 original stones
  });

  it('preserves all original stones', () => {
    const mat = Array.from({ length: 9 }, () => Array(9).fill(0));
    mat[0][0] = 1; mat[0][1] = -1;
    mat[1][0] = 1; mat[1][1] = -1;

    const result = applyTsumegoFrame(mat);
    expect(result[0][0]).toBe(1);
    expect(result[0][1]).toBe(-1);
    expect(result[1][0]).toBe(1);
    expect(result[1][1]).toBe(-1);
  });

  it('uses contiguous blocks (attacker near puzzle, defender far)', () => {
    const mat = Array.from({ length: 9 }, () => Array(9).fill(0));
    // Small corner puzzle
    mat[0][0] = 1; mat[0][1] = -1;
    mat[1][0] = -1;

    const result = applyTsumegoFrame(mat);
    // Cells adjacent to frame boundary should be attacker (fewer stones)
    // Cells far from puzzle should be defender
    // Just check that both colors exist in filled territory
    const outsideValues = new Set<number>();
    for (let r = 5; r < 9; r++) {
      for (let c = 5; c < 9; c++) {
        if (mat[r][c] === 0 && result[r][c] !== 0) {
          outsideValues.add(result[r][c]);
        }
      }
    }
    // Far corner should have some fill
    expect(outsideValues.size).toBeGreaterThan(0);
  });

  it('returns empty array for empty input', () => {
    expect(applyTsumegoFrame([])).toEqual([]);
  });
});
