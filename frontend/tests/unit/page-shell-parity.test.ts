/**
 * Page-shell parity — unit tests.
 * T210: Verify PuzzleSetPlayer uses SolverView which uses the shared
 * goban initialization pipeline (useGoban hook) with the same renderer
 * preference, theme callbacks, and stone configuration.
 * Spec 132, SC-033, FR-060, FR-061
 *
 * Uses source analysis approach since pages import useGoban with heavy
 * goban library dependencies.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const puzzleSetPlayerSource = readFileSync(
  resolve(__dirname, '../../src/components/PuzzleSetPlayer/index.tsx'),
  'utf-8',
);

const solverViewSource = readFileSync(
  resolve(__dirname, '../../src/components/Solver/SolverView.tsx'),
  'utf-8',
);

const useGobanSource = readFileSync(
  resolve(__dirname, '../../src/hooks/useGoban.ts'),
  'utf-8',
);

const gobanInitSource = readFileSync(
  resolve(__dirname, '../../src/lib/goban-init.ts'),
  'utf-8',
);

describe('goban initialization parity (T210)', () => {
  // PuzzleSetPlayer uses SolverView, which calls useGoban internally.
  // All puzzle modes share the same goban config pipeline.

  describe('PuzzleSetPlayer goban initialization', () => {
    it('delegates to SolverView for puzzle rendering', () => {
      expect(puzzleSetPlayerSource).toContain('SolverView');
    });

    it('SolverView imports and uses useGoban hook', () => {
      expect(solverViewSource).toContain("from '../../hooks/useGoban'");
      expect(solverViewSource).toMatch(/useGoban\s*\(/);
    });
  });

  describe('shared renderer configuration', () => {
    it('useGoban defaults to SVG renderer', () => {
      expect(useGobanSource).toContain('return "svg"');
    });

    it('useGoban uses a single createRenderer function for all callsites', () => {
      expect(useGobanSource).toContain('function createRenderer');
      const createRendererCount = (useGobanSource.match(/function createRenderer/g) ?? []).length;
      expect(createRendererCount).toBe(1);
    });

    it('goban-init provides shared getSelectedThemes callback', () => {
      expect(gobanInitSource).toContain('getSelectedThemes');
    });

    it('getSelectedThemes returns Shell/Slate stones (Custom board)', () => {
      expect(gobanInitSource).toContain('"Shell"');
      expect(gobanInitSource).toContain('"Slate"');
      expect(gobanInitSource).toContain('"Custom"');
    });

    it('getSelectedThemes returns stone-shadows and removal-graphic settings', () => {
      expect(gobanInitSource).toContain('"stone-shadows"');
      expect(gobanInitSource).toContain('"removal-graphic"');
    });
  });

  describe('shared goban config pipeline', () => {
    it('useGoban uses preprocessSgf for all SGF input', () => {
      expect(useGobanSource).toContain('preprocessSgf');
    });

    it('useGoban uses buildPuzzleConfig for all goban configs', () => {
      expect(useGobanSource).toContain('buildPuzzleConfig');
    });

    it('there is exactly one useGoban hook implementation', () => {
      const exportCount = (useGobanSource.match(/export function useGoban/g) ?? []).length;
      expect(exportCount).toBe(1);
    });
  });
});
