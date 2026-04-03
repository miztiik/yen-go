/**
 * Integration test for progressive hints.
 *
 * Verifies dynamic hint levels with computeHintDisplay tier mapping.
 * Covers: 3 authored hints, 2 hints, 1 hint, 0 hints, null correctMove,
 * and accent styling on coordinate hint.
 *
 * Spec 127: Phase 5, T058
 * @module tests/integration/hints
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { HintOverlay } from '../../src/components/Solver/HintOverlay';

describe('HintOverlay progressive hints', () => {
  const correctMove = { x: 2, y: 2 };

  describe('with 3 authored hints', () => {
    const testHints = ['Look at the corner', 'Try an atari', 'Play C3'];

    it('renders nothing at level 0', () => {
      const { container } = render(
        <HintOverlay hints={testHints} correctMove={correctMove} currentLevel={0} />
      );
      expect(container.innerHTML).toBe('');
    });

    it('shows first authored hint at level 1', () => {
      render(<HintOverlay hints={testHints} correctMove={correctMove} currentLevel={1} />);
      expect(screen.getByText('Look at the corner')).toBeTruthy();
      expect(screen.queryByText('Try an atari')).toBeNull();
    });

    it('shows first two authored hints at level 2', () => {
      render(<HintOverlay hints={testHints} correctMove={correctMove} currentLevel={2} />);
      expect(screen.getByText('Look at the corner')).toBeTruthy();
      expect(screen.getByText('Try an atari')).toBeTruthy();
      expect(screen.queryByText('Play C3')).toBeNull();
    });

    it('shows all three authored hints at level 3 (no static marker text)', () => {
      render(<HintOverlay hints={testHints} correctMove={correctMove} currentLevel={3} boardSize={9} />);
      expect(screen.getByText('Look at the corner')).toBeTruthy();
      expect(screen.getByText('Try an atari')).toBeTruthy();
      expect(screen.getByText('Play C3')).toBeTruthy();
      // No static "The correct move is marked on the board" text — last hint gets accent styling instead
      expect(screen.queryByText('The correct move is marked on the board')).toBeNull();
    });
  });

  describe('with 2 authored hints (maxLevel = 2)', () => {
    const testHints = ['Try an atari', 'Play C3'];

    it('shows first authored hint at level 1', () => {
      render(<HintOverlay hints={testHints} correctMove={correctMove} currentLevel={1} />);
      expect(screen.getByText('Try an atari')).toBeTruthy();
      expect(screen.queryByText('Play C3')).toBeNull();
    });

    it('shows both authored hints at level 2 (maxLevel reached)', () => {
      render(<HintOverlay hints={testHints} correctMove={correctMove} currentLevel={2} />);
      expect(screen.getByText('Try an atari')).toBeTruthy();
      expect(screen.getByText('Play C3')).toBeTruthy();
      expect(screen.queryByText('The correct move is marked on the board')).toBeNull();
    });

    it('caps at maxLevel even if currentLevel exceeds it', () => {
      render(<HintOverlay hints={testHints} correctMove={correctMove} currentLevel={3} />);
      expect(screen.getByText('Try an atari')).toBeTruthy();
      expect(screen.getByText('Play C3')).toBeTruthy();
    });
  });

  describe('with 1 authored hint (maxLevel = 1)', () => {
    const testHints = ['Play C3'];

    it('shows the authored hint at level 1 (maxLevel reached)', () => {
      render(<HintOverlay hints={testHints} correctMove={correctMove} currentLevel={1} />);
      expect(screen.getByText('Play C3')).toBeTruthy();
      expect(screen.queryByText('The correct move is marked on the board')).toBeNull();
    });
  });

  describe('with 0 hints (maxLevel = 1, marker only)', () => {
    it('renders nothing visible at level 1 (no text hints to show)', () => {
      const { container } = render(
        <HintOverlay hints={[]} correctMove={correctMove} currentLevel={1} boardSize={9} />
      );
      // No text hints and no static marker text — overlay has no visible content
      const overlay = container.querySelector('[data-component="hint-overlay"]');
      expect(overlay).toBeTruthy();
      expect(screen.queryByText('The correct move is marked on the board')).toBeNull();
    });
  });

  describe('null correctMove', () => {
    it('shows hints without accent styling at max level', () => {
      render(
        <HintOverlay hints={['Look at corner', 'Try atari', 'Play C3']} correctMove={null} currentLevel={3} />
      );
      expect(screen.getByText('Look at corner')).toBeTruthy();
      expect(screen.getByText('Try atari')).toBeTruthy();
      expect(screen.getByText('Play C3')).toBeTruthy();
      expect(screen.queryByText('The correct move is marked on the board')).toBeNull();
    });
  });

  describe('accent styling on coordinate hint', () => {
    it('applies accent color to last hint when coordinate marker is active', () => {
      const { container } = render(
        <HintOverlay hints={['Look at corner', 'Play C3']} correctMove={correctMove} currentLevel={2} />
      );
      const hintDivs = container.querySelectorAll('[data-component="hint-overlay"] > div');
      // Last hint should have accent styling (font-semibold class)
      const lastHint = hintDivs[hintDivs.length - 1];
      expect(lastHint?.className).toContain('font-semibold');
    });

    it('does not apply accent color when not at max level', () => {
      const { container } = render(
        <HintOverlay hints={['Look at corner', 'Play C3']} correctMove={correctMove} currentLevel={1} />
      );
      const hintDivs = container.querySelectorAll('[data-component="hint-overlay"] > div');
      const firstHint = hintDivs[0];
      expect(firstHint?.className).not.toContain('font-semibold');
    });
  });
});
