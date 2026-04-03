/**
 * usePuzzleState reducer guard tests.
 *
 * Validates that review mode is protected from state transitions
 * that would exit it (WRONG_ANSWER, MOVE_PLACED, UNDO).
 *
 * Uses source analysis approach consistent with SolverView.test.ts.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const stateSource = readFileSync(
  resolve(__dirname, '../../src/hooks/usePuzzleState.ts'),
  'utf-8',
);

describe('usePuzzleState reducer review mode guards', () => {
  it('guards WRONG_ANSWER during review mode', () => {
    // WRONG_ANSWER case must check for review status before transitioning
    const wrongIdx = stateSource.indexOf("case 'WRONG_ANSWER':");
    expect(wrongIdx).toBeGreaterThan(0);
    const nextCaseIdx = stateSource.indexOf('case ', wrongIdx + 1);
    const wrongBlock = stateSource.substring(wrongIdx, nextCaseIdx);
    expect(wrongBlock).toContain("if (state.status === 'review') return state;");
  });

  it('guards MOVE_PLACED during review mode', () => {
    const placedIdx = stateSource.indexOf("case 'MOVE_PLACED':");
    expect(placedIdx).toBeGreaterThan(0);
    const nextCaseIdx = stateSource.indexOf('case ', placedIdx + 1);
    const placedBlock = stateSource.substring(placedIdx, nextCaseIdx);
    expect(placedBlock).toContain("if (state.status === 'review') return state;");
  });

  it('guards UNDO during review mode', () => {
    const undoIdx = stateSource.indexOf("case 'UNDO':");
    expect(undoIdx).toBeGreaterThan(0);
    const nextCaseIdx = stateSource.indexOf('case ', undoIdx + 1);
    // UNDO may be last case before default, so also check for 'default:'
    const endIdx = nextCaseIdx > 0 ? nextCaseIdx : stateSource.indexOf('default:', undoIdx);
    const undoBlock = stateSource.substring(undoIdx, endIdx);
    expect(undoBlock).toContain("if (state.status === 'review') return state;");
  });

  it('CORRECT_ANSWER does not guard for review (should not happen in review)', () => {
    // CORRECT_ANSWER doesn't need a guard because stone placement is disabled
    const correctIdx = stateSource.indexOf("case 'CORRECT_ANSWER':");
    expect(correctIdx).toBeGreaterThan(0);
    const nextCaseIdx = stateSource.indexOf('case ', correctIdx + 1);
    const correctBlock = stateSource.substring(correctIdx, nextCaseIdx);
    // It's fine if it doesn't have a review guard
    expect(correctBlock).not.toContain("if (state.status === 'review') return state;");
  });
});

describe('usePuzzleState revealSolution action', () => {
  it('disables stone placement on reveal', () => {
    expect(stateSource).toContain('disableStonePlacement');
  });

  it('dispatches REVEAL_SOLUTION to set solutionRevealed flag', () => {
    expect(stateSource).toContain("type: 'REVEAL_SOLUTION'");
    expect(stateSource).toContain('solutionRevealed: true');
  });

  it('dispatches ENTER_REVIEW to transition to review status', () => {
    expect(stateSource).toContain("type: 'ENTER_REVIEW'");
  });

  it('calls goban.showFirst() to reset board position', () => {
    expect(stateSource).toContain('goban.showFirst');
  });
});
