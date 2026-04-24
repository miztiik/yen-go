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
import { render, screen, fireEvent } from '@testing-library/preact';
import { PuzzleSetHeader } from '@/components/PuzzleSetPlayer/PuzzleSetHeader';

describe('PuzzleSetHeader', () => {
  describe('progress bar', () => {
    // Phase 4 (Issue 3): the header progress bar is hidden by default via
    // UI_HEADER_DROP_PROGRESS_BAR=true. ProblemNav's sidebar progress bar is
    // the single source of truth. These tests now assert the bar is suppressed
    // even when totalPuzzles > 0 / progress is supplied.
    it('does not render progress bar when explicit progress prop is provided', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={100}
          progress={50}
          testId="hdr"
        />,
      );

      expect(screen.queryByTestId('hdr-progress')).toBeNull();
    });

    it('does not render progress bar when falling back to index-based progress', () => {
      render(
        <PuzzleSetHeader title="Test" currentIndex={4} totalPuzzles={10} testId="hdr" />,
      );

      expect(screen.queryByTestId('hdr-progress')).toBeNull();
    });

    it('does not render progress bar when explicit progress is 0', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={5}
          totalPuzzles={10}
          progress={0}
          testId="hdr"
        />,
      );

      expect(screen.queryByTestId('hdr-progress')).toBeNull();
    });

    it('does not render progress bar when all puzzles completed', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={50}
          progress={100}
          testId="hdr"
        />,
      );

      expect(screen.queryByTestId('hdr-progress')).toBeNull();
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
    // Phase 1 chrome shrink: counter is suppressed under UI_HEADER_DROP_COUNTER
    // because ProblemNav in the sidebar already shows the same data. To revert,
    // flip UI_HEADER_DROP_COUNTER to false in services/featureFlags.ts.
    it('does not render counter badge in header (deduped against ProblemNav)', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={4}
          totalPuzzles={20}
          testId="hdr"
        />,
      );

      // The counter "5 / 20" should NOT appear in the header
      expect(screen.queryByText('5 / 20')).toBeNull();
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
    // Phase 2 (UI_FILTERS_IN_SHEET): the filter strip is no longer rendered
    // inline below the toolbar. A "Filters" trigger button replaces it; the
    // strip content lives inside a BottomSheet that opens on click. To revert,
    // flip UI_FILTERS_IN_SHEET to false in services/featureFlags.ts.
    it('renders a Filters trigger button when filterStrip is provided', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={5}
          filterStrip={<div data-testid="my-filters">Filters here</div>}
          testId="hdr"
        />,
      );

      expect(screen.getByTestId('hdr-filters-trigger')).toBeDefined();
      // Sheet content is not in the DOM until the trigger is clicked.
      expect(screen.queryByTestId('my-filters')).toBeNull();
    });

    it('opens the filters sheet and reveals the strip when trigger is clicked', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={5}
          filterStrip={<div data-testid="my-filters">Filters here</div>}
          testId="hdr"
        />,
      );

      fireEvent.click(screen.getByTestId('hdr-filters-trigger'));
      expect(screen.getByTestId('my-filters')).toBeDefined();
      expect(screen.getByTestId('hdr-filters-sheet')).toBeDefined();
    });

    it('renders activeFilterCount badge on the trigger when count > 0', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={5}
          filterStrip={<div data-testid="my-filters">Filters here</div>}
          activeFilterCount={3}
          testId="hdr"
        />,
      );

      const trigger = screen.getByTestId('hdr-filters-trigger');
      expect(trigger.getAttribute('data-active')).toBe('true');
      expect(trigger.textContent).toContain('3');
    });

    it('omits the trigger entirely when no filterStrip is provided', () => {
      render(
        <PuzzleSetHeader
          title="Test"
          currentIndex={0}
          totalPuzzles={5}
          testId="hdr"
        />,
      );

      expect(screen.queryByTestId('hdr-filters-trigger')).toBeNull();
    });
  });
});
