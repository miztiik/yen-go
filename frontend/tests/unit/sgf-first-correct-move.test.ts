/**
 * Tests for firstCorrectMove extraction from SGF.
 * @module tests/unit/sgf-first-correct-move
 *
 * Tests T028 edge cases:
 * - Standard move
 * - Pass move
 * - Setup stones before solution
 * - Comment containing B[]
 * - Wrong first variation with BM
 * - Multi-variation
 */

import { extractYenGoProperties } from '../../src/lib/sgf-preprocessor';

describe('extractYenGoProperties — firstCorrectMove', () => {
  it('extracts standard move: (;FF[4]SZ[19];B[dp]) → "dp"', () => {
    const sgf = '(;FF[4]GM[1]SZ[19];B[dp])';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBe('dp');
  });

  it('returns null for pass move: (;FF[4]SZ[19];B[]) → null', () => {
    const sgf = '(;FF[4]GM[1]SZ[19];B[])';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBeNull();
  });

  it('returns null for pass move tt: (;FF[4]SZ[19];B[tt]) → null', () => {
    const sgf = '(;FF[4]GM[1]SZ[19];B[tt])';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBeNull();
  });

  it('extracts move after setup stones: (;FF[4]SZ[19]AB[dp]AW[dd](;B[qp])) → "qp"', () => {
    const sgf = '(;FF[4]GM[1]SZ[19]AB[dp]AW[dd](;B[qp]))';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBe('qp');
  });

  it('ignores B[] inside comments: (;FF[4]SZ[19]C[Play B[dp] here](;B[qp])) → "qp"', () => {
    const sgf = '(;FF[4]GM[1]SZ[19]C[Play B[dp] here](;B[qp]))';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBe('qp');
  });

  it('skips wrong first variation with BM: (;FF[4]SZ[19](;B[aa]BM[1])(;B[dp])) → "dp"', () => {
    const sgf = '(;FF[4]GM[1]SZ[19](;B[aa]BM[1])(;B[dp]))';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBe('dp');
  });

  it('picks first correct move from multi-variation: (;FF[4]SZ[19](;B[dp])(;B[aa]BM[1])) → "dp"', () => {
    const sgf = '(;FF[4]GM[1]SZ[19](;B[dp])(;B[aa]BM[1]))';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBe('dp');
  });

  it('returns null when all variations are bad moves', () => {
    const sgf = '(;FF[4]GM[1]SZ[19](;B[aa]BM[1])(;B[bb]BM[1]))';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBeNull();
  });

  it('handles white to play: (;FF[4]SZ[19]PL[W];W[dp]) → "dp"', () => {
    const sgf = '(;FF[4]GM[1]SZ[19]PL[W];W[dp])';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBe('dp');
  });

  it('handles SGF with YenGo properties before solution', () => {
    const sgf = '(;FF[4]GM[1]SZ[9]YG[beginner]YT[life-and-death]AB[cc]AW[cd](;B[dc]))';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBe('dc');
    expect(meta.level).toBe('beginner');
    expect(meta.tags).toEqual(['life-and-death']);
  });

  it('returns null for SGF with no moves at all', () => {
    const sgf = '(;FF[4]GM[1]SZ[19])';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBeNull();
  });

  it('handles nested variations correctly', () => {
    // First variation has a correct move, second is bad
    const sgf = '(;FF[4]GM[1]SZ[19]AB[dd]AW[dc](;B[cc];W[cb](;B[bb])(;B[db]))(;B[ec]BM[1]))';
    const meta = extractYenGoProperties(sgf);
    expect(meta.firstCorrectMove).toBe('cc');
  });
});
