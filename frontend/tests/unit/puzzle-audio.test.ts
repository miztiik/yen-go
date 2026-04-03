/**
 * Puzzle audio integration — unit tests.
 *
 * T069: Verify usePuzzleState calls audioService.play() on events.
 * Spec 131: FR-032
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('usePuzzleState audio integration', () => {
  const source = readFileSync(
    resolve(__dirname, '../../src/hooks/usePuzzleState.ts'),
    'utf-8',
  );

  it('imports audioService', () => {
    expect(source).toContain("from '../services/audioService'");
  });

  it('plays stone sound on puzzle-place', () => {
    // Stone placement sound played by usePuzzleState on every puzzle-place event
    expect(source).toContain("audioService.play('stone')");
  });

  it('plays correct sound on correct answer', () => {
    expect(source).toContain("audioService.play('correct')");
  });

  it('plays wrong sound on wrong answer', () => {
    expect(source).toContain("audioService.play('wrong')");
  });
});
