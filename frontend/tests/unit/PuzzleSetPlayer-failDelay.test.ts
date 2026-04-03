/**
 * PuzzleSetPlayer failOnWrongDelayMs and autoAdvanceEnabled — source analysis tests.
 * T14: Verify configurable delay and auto-advance override props.
 *
 * Uses source analysis approach since PuzzleSetPlayer has heavy dependencies.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const pspSource = readFileSync(
  resolve(__dirname, '../../src/components/PuzzleSetPlayer/index.tsx'),
  'utf-8',
);

describe('PuzzleSetPlayer failOnWrongDelayMs (T14)', () => {
  it('declares failOnWrongDelayMs as optional number prop with default 400', () => {
    expect(pspSource).toContain('failOnWrongDelayMs?: number');
    expect(pspSource).toContain('failOnWrongDelayMs = 400');
  });

  it('uses failOnWrongDelayMs in setTimeout for fail handling', () => {
    // The delay is used in setTimeout, not a hardcoded 400
    expect(pspSource).toContain('failOnWrongDelayMs);');
    // Verify it appears in a setTimeout context
    const idx = pspSource.indexOf('failOnWrongDelayMs);');
    const nearby = pspSource.substring(idx - 200, idx);
    expect(nearby).toContain('setTimeout');
  });

  it('includes failOnWrongDelayMs in handleFail dependency array', () => {
    expect(pspSource).toContain('failOnWrongDelayMs]');
  });
});

describe('PuzzleSetPlayer autoAdvanceEnabled (T14)', () => {
  it('declares autoAdvanceEnabled as optional boolean prop', () => {
    expect(pspSource).toContain('autoAdvanceEnabled?: boolean');
  });

  it('uses autoAdvanceEnabled to override global auto-advance setting', () => {
    // Should reference both autoAdvanceEnabled and appSettings.autoAdvance
    expect(pspSource).toContain('autoAdvanceEnabled');
    expect(pspSource).toContain('appSettings');
  });
});

describe('PuzzleSetPlayer minimal prop (T14)', () => {
  it('declares minimal as optional boolean with false default', () => {
    expect(pspSource).toContain('minimal?: boolean');
    expect(pspSource).toContain('minimal = false');
  });

  it('passes minimal to SolverView', () => {
    expect(pspSource).toContain('minimal={minimal}');
  });
});

describe('PuzzleSetPlayer streaming loader detection (T14)', () => {
  it('detects streaming loaders via hasMore check', () => {
    expect(pspSource).toContain("'hasMore' in loader");
  });
});
