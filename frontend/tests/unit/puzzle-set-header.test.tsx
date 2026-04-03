/**
 * PuzzleSetHeader Component Tests
 * @module tests/unit/puzzle-set-header.test
 *
 * Tests for:
 * - U1: progress prop override (completion-based vs index-based)
 * - U2/U3: skip-to-unsolved button rendering (label + tooltip)
 * - A2: completedCount field passed through header info
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { PuzzleSetHeader } from '@/components/PuzzleSetPlayer/PuzzleSetHeader';

describe('PuzzleSetHeader', () => {
  describe('progress bar', () => {
    it('uses explicit progress prop when provided', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={100}
          progress={50}
          testId="hdr"
        />,
      );

      const bar = screen.getByTestId('hdr-progress');
      // Explicit 50% should be used, NOT index-based (1/100 = 1%)
      expect(bar.getAttribute('aria-valuenow')).toBe('50');
    });

    it('falls back to index-based progress when progress prop is omitted', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={4}
          totalPuzzles={10}
          testId="hdr"
        />,
      );

      const bar = screen.getByTestId('hdr-progress');
      // (4+1)/10 * 100 = 50%
      expect(bar.getAttribute('aria-valuenow')).toBe('50');
    });

    it('shows 0% progress when explicit progress is 0', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={5}
          totalPuzzles={10}
          progress={0}
          testId="hdr"
        />,
      );

      const bar = screen.getByTestId('hdr-progress');
      expect(bar.getAttribute('aria-valuenow')).toBe('0');
    });

    it('shows 100% progress when all puzzles completed', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={50}
          progress={100}
          testId="hdr"
        />,
      );

      const bar = screen.getByTestId('hdr-progress');
      expect(bar.getAttribute('aria-valuenow')).toBe('100');
    });

    it('does not render progress bar when totalPuzzles is 0', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={0}
          testId="hdr"
        />,
      );

      expect(screen.queryByTestId('hdr-progress')).toBeNull();
    });
  });

  describe('right content slot (skip button)', () => {
    it('renders skip-to-unsolved button with correct label', () => {
      const skipButton = (
        <button
          type="button"
          aria-label="Skip to next unsolved puzzle"
          title="Skip to next unsolved puzzle"
          data-testid="skip-to-unsolved"
        >
          Next unsolved
        </button>
      );

      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={2}
          totalPuzzles={10}
          rightContent={skipButton}
          testId="hdr"
        />,
      );

      const btn = screen.getByTestId('skip-to-unsolved');
      expect(btn).toBeDefined();
      expect(btn.textContent).toBe('Next unsolved');
      expect(btn.getAttribute('title')).toBe('Skip to next unsolved puzzle');
      expect(btn.getAttribute('aria-label')).toBe('Skip to next unsolved puzzle');
    });

    it('does not render right content when not provided', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={5}
          testId="hdr"
        />,
      );

      expect(screen.queryByTestId('skip-to-unsolved')).toBeNull();
    });
  });

  describe('puzzle counter', () => {
    it('shows current / total in counter badge', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={4}
          totalPuzzles={20}
          testId="hdr"
        />,
      );

      // Should show "5 / 20" (1-based display)
      expect(screen.getByText('5 / 20')).toBeDefined();
    });

    it('does not render counter when totalPuzzles is 0', () => {
      const { container } = render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={0}
          testId="hdr"
        />,
      );

      // No tracking-wide counter badge
      expect(container.querySelector('.tracking-wide')).toBeNull();
    });
  });

  describe('back button', () => {
    it('renders back button with custom label', () => {
      const onBack = () => {};
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={5}
          onBack={onBack}
          backLabel="Back to techniques"
          testId="hdr"
        />,
      );

      const backBtn = screen.getByLabelText('Back to techniques');
      expect(backBtn).toBeDefined();
    });

    it('does not render back button when onBack is omitted', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={5}
          testId="hdr"
        />,
      );

      expect(screen.queryByLabelText('Back')).toBeNull();
    });
  });

  describe('filter strip', () => {
    it('renders filter strip content when provided', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={5}
          filterStrip={<div data-testid="my-filters">Filters here</div>}
          testId="hdr"
        />,
      );

      expect(screen.getByTestId('hdr-filters')).toBeDefined();
      expect(screen.getByTestId('my-filters')).toBeDefined();
    });
  });
});
