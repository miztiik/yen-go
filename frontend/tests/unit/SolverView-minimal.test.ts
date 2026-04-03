/**
 * SolverView minimal mode — source analysis tests.
 * T13: Verify minimal prop hides sidebar, board still renders.
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

describe('SolverView minimal mode (T13)', () => {
  it('accepts minimal prop with false default', () => {
    expect(solverViewSource).toContain('minimal?: boolean');
    expect(solverViewSource).toContain('minimal = false');
  });

  it('conditionally hides sidebar when minimal is true', () => {
    expect(solverViewSource).toContain('{!minimal && <div className="solver-sidebar-col"');
  });

  it('always renders board column regardless of minimal', () => {
    // Board column should not be conditionally rendered on minimal
    const boardColMatch = solverViewSource.match(/solver-board-col/g);
    expect(boardColMatch).toBeTruthy();
    expect(boardColMatch!.length).toBeGreaterThanOrEqual(1);
    // Board col is NOT wrapped in a !minimal guard
    const boardColIdx = solverViewSource.indexOf('solver-board-col');
    const nearbySource = solverViewSource.substring(boardColIdx - 30, boardColIdx);
    expect(nearbySource).not.toContain('!minimal');
  });

  it('renders GobanContainer regardless of minimal mode', () => {
    expect(solverViewSource).toContain('<GobanContainer');
  });
});
