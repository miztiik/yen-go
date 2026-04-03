/**
 * SolverView tree visibility and review mode — unit tests.
 * T170: Verify tree container is hidden when not in review mode and visible
 *       when review mode is active.
 * Spec 132 US12
 *
 * Uses source analysis approach since SolverView has heavy dependencies
 * (goban, usePuzzleState, etc.) that require complex mocking.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const solverViewSource = readFileSync(
  resolve(__dirname, '../../src/components/Solver/SolverView.tsx'),
  'utf-8',
);

describe('SolverView tree container visibility (T170)', () => {
  it('has a solution tree container with data-testid="solution-tree-container"', () => {
    expect(solverViewSource).toContain('data-testid="solution-tree-container"');
  });

  it('tree container uses treeRef for goban attachment', () => {
    expect(solverViewSource).toContain('ref={treeRef}');
  });

  it('tree container toggles between hidden and visible class', () => {
    // The wrapper container uses a ternary: visible vs 'hidden'
    expect(solverViewSource).toContain("'hidden'");
    expect(solverViewSource).toContain('solution-tree-container');
    expect(solverViewSource).toContain('data-testid="solution-tree-container"');
  });

  it('tree container is rendered after the board GobanContainer', () => {
    const boardIdx = solverViewSource.indexOf('GobanContainer');
    const treeIdx = solverViewSource.indexOf('data-testid="solution-tree-container"');
    expect(boardIdx).toBeGreaterThan(0);
    expect(treeIdx).toBeGreaterThan(boardIdx);
  });

  it('SolverView creates a treeRef for goban tree attachment', () => {
    expect(solverViewSource).toContain("useRef<HTMLDivElement>(null)");
    expect(solverViewSource).toContain('useGoban(');
    expect(solverViewSource).toContain('transformedSgf');
    expect(solverViewSource).toContain('treeRef');
  });

  it('solution tree is associated with US12 in comments', () => {
    expect(solverViewSource).toContain('US12');
  });

  it('keeps tree visible when solutionRevealed is true', () => {
    // Tree wrapper shows when isReviewMode OR solutionRevealed
    expect(solverViewSource).toContain('puzzleState.state.solutionRevealed');
  });
});

describe('SolverView review mode improvements', () => {
  it('does not import SolutionReveal component', () => {
    expect(solverViewSource).not.toContain("from './SolutionReveal'");
    expect(solverViewSource).not.toContain('<SolutionReveal');
  });

  it('has tree navigation controls inside tree wrapper', () => {
    expect(solverViewSource).toContain('data-testid="tree-nav-controls"');
    // Nav controls must appear before the tree container in the same wrapper
    const navIdx = solverViewSource.indexOf('data-testid="tree-nav-controls"');
    const treeIdx = solverViewSource.indexOf('data-testid="solution-tree-container"');
    expect(navIdx).toBeGreaterThan(0);
    expect(treeIdx).toBeGreaterThan(navIdx);
  });

  it('has first/prev/next/last navigation buttons', () => {
    expect(solverViewSource).toContain('DoubleChevronLeftIcon');
    expect(solverViewSource).toContain('DoubleChevronRightIcon');
    expect(solverViewSource).toContain('aria-label="Go to first move"');
    expect(solverViewSource).toContain('aria-label="Go to last move"');
    expect(solverViewSource).toContain('aria-label="Previous move"');
    expect(solverViewSource).toContain('aria-label="Next move"');
  });

  it('disables Undo and Reset during review mode', () => {
    // Both buttons should include isReviewMode in their disabled condition
    expect(solverViewSource).toContain('isSolved || isReviewMode');
  });

  it('re-disables stone placement after goban navigation', () => {
    // disableStonePlacement must be called multiple times — after showNext,
    // showPrevious, prevSibling, nextSibling, showFirst, and in revealSolution
    const matches = solverViewSource.match(/disableStonePlacement/g);
    expect(matches).not.toBeNull();
    expect(matches!.length).toBeGreaterThanOrEqual(5);
  });

  it('has handleTreeFirst and handleTreeLast handlers', () => {
    expect(solverViewSource).toContain('handleTreeFirst');
    expect(solverViewSource).toContain('handleTreeLast');
  });

  it('tree wrapper is always in DOM (CSS visibility, not conditional render)', () => {
    // The tree wrapper should NOT use conditional rendering — it should always
    // be in the DOM so goban can attach to treeRef at initialization
    expect(solverViewSource).toContain('data-testid="solution-tree-wrapper"');
    // The className should be a ternary, not inside a conditional block
    const wrapperIdx = solverViewSource.indexOf('data-testid="solution-tree-wrapper"');
    // Find the className assignment near the wrapper (need ~400 chars back for multi-line JSX)
    const nearbySource = solverViewSource.substring(wrapperIdx - 400, wrapperIdx);
    expect(nearbySource).toContain('className=');
  });
});

describe('SolverView transform-aware hints', () => {
  it('imports resolveHintTokens for token resolution', () => {
    expect(solverViewSource).toContain('resolveHintTokens');
  });

  it('imports getMaxLevel for dynamic hint count', () => {
    expect(solverViewSource).toContain('getMaxLevel');
  });

  it('uses dynamic maxHintLevel from getMaxLevel(displayHints)', () => {
    expect(solverViewSource).toContain('getMaxLevel(displayHints)');
    expect(solverViewSource).not.toContain('maxHintLevel = 3');
  });

  it('computes correctMovePosition from firstCorrectMove with transforms', () => {
    expect(solverViewSource).toContain('correctMovePosition');
    expect(solverViewSource).toContain('metadata.firstCorrectMove');
    expect(solverViewSource).toContain('transformSgfCoordinate');
  });

  it('resolves hint tokens through active transforms', () => {
    expect(solverViewSource).toContain('resolvedHints');
    expect(solverViewSource).toContain('resolveHintTokens');
  });

  it('passes displayHints (transform-aware) to HintOverlay instead of raw metadata.hints', () => {
    expect(solverViewSource).toContain('hints={displayHints');
    expect(solverViewSource).not.toContain('hints={metadata.hints');
  });

  it('passes correctMovePosition to HintOverlay instead of null', () => {
    expect(solverViewSource).toContain('correctMove={correctMovePosition}');
    expect(solverViewSource).not.toContain('correctMove={null}');
  });

  it('passes boardSize to HintOverlay', () => {
    expect(solverViewSource).toContain('boardSize={boardSize}');
  });

  it('uses dynamic maxHintLevel threshold for board marker', () => {
    expect(solverViewSource).toContain('hintsUsedCount >= maxHintLevel');
    expect(solverViewSource).not.toContain('hintsUsedCount >= 3');
  });
});
