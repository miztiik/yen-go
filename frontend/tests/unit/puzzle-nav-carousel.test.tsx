/**
 * PuzzleNavCarousel Component Tests
 * @module tests/unit/puzzle-nav-carousel.test
 *
 * Spec 118 - T3.8: Unit Tests for Carousel Components
 * Tests for main carousel navigation with keyboard, touch, and accessibility features
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/preact';
import { PuzzleNavCarousel, type PuzzleIndicator } from '@/components/ProblemNav/PuzzleNavCarousel';

// Mock scrollIntoView which isn't available in jsdom
Element.prototype.scrollIntoView = vi.fn();

describe('PuzzleNavCarousel', () => {
  const mockPuzzles: PuzzleIndicator[] = [
    { index: 0, status: 'correct' },
    { index: 1, status: 'wrong' },
    { index: 2, status: 'unsolved' },
    { index: 3, status: 'unsolved' },
    { index: 4, status: 'correct' },
  ];

  let mockOnSelectPuzzle: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnSelectPuzzle = vi.fn();
  });

  describe('Rendering', () => {
    it('should render carousel container', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      expect(screen.getByRole('tablist')).toBeDefined();
    });

    it('should render all puzzle cards', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tabs = screen.getAllByRole('tab');
      expect(tabs.length).toBe(5);
    });

    it('should render progress bar', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      expect(screen.getByRole('progressbar')).toBeDefined();
    });

    it('should mark correct card as current', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={2} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tabs = screen.getAllByRole('tab');
      expect(tabs[2].getAttribute('aria-selected')).toBe('true');
    });

    it('should apply compact class when compact=true', () => {
      const { container } = render(
        <PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} compact={true} />
      );

      const carousel = container.querySelector('.puzzle-nav-carousel');
      expect(carousel?.className).toContain('compact');
    });
  });

  describe('Card Click Handling', () => {
    it('should call onSelectPuzzle when card is clicked', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tabs = screen.getAllByRole('tab');
      fireEvent.click(tabs[2]);

      expect(mockOnSelectPuzzle).toHaveBeenCalledWith(2);
    });

    it('should call onSelectPuzzle for different cards', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tabs = screen.getAllByRole('tab');
      fireEvent.click(tabs[4]);

      expect(mockOnSelectPuzzle).toHaveBeenCalledWith(4);
    });
  });

  describe('Keyboard Navigation', () => {
    it('should navigate to next puzzle on ArrowRight', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={1} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      fireEvent.keyDown(tablist, { key: 'ArrowRight' });

      expect(mockOnSelectPuzzle).toHaveBeenCalledWith(2);
    });

    it('should navigate to previous puzzle on ArrowLeft', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={2} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      fireEvent.keyDown(tablist, { key: 'ArrowLeft' });

      expect(mockOnSelectPuzzle).toHaveBeenCalledWith(1);
    });

    it('should navigate to first puzzle on Home', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={3} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      fireEvent.keyDown(tablist, { key: 'Home' });

      expect(mockOnSelectPuzzle).toHaveBeenCalledWith(0);
    });

    it('should navigate to last puzzle on End', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={1} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      fireEvent.keyDown(tablist, { key: 'End' });

      expect(mockOnSelectPuzzle).toHaveBeenCalledWith(4);
    });

    it('should not navigate left from first puzzle', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      fireEvent.keyDown(tablist, { key: 'ArrowLeft' });

      expect(mockOnSelectPuzzle).not.toHaveBeenCalled();
    });

    it('should not navigate right from last puzzle', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={4} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      fireEvent.keyDown(tablist, { key: 'ArrowRight' });

      expect(mockOnSelectPuzzle).not.toHaveBeenCalled();
    });

    it('should prevent default on navigation keys', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={1} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      const event = new KeyboardEvent('keydown', { key: 'ArrowRight' });
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

      tablist.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });

  describe('Touch Gestures', () => {
    it('should navigate to previous on swipe right', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={2} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');

      // Swipe right (start at x=200, end at x=300 = deltaX > 0)
      fireEvent.touchStart(tablist, {
        touches: [{ clientX: 200, clientY: 100 }],
      });

      fireEvent.touchEnd(tablist, {
        changedTouches: [{ clientX: 300, clientY: 100 }],
      });

      expect(mockOnSelectPuzzle).toHaveBeenCalledWith(1);
    });

    it('should navigate to next on swipe left', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={1} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');

      // Swipe left (start at x=300, end at x=200 = deltaX < 0)
      fireEvent.touchStart(tablist, {
        touches: [{ clientX: 300, clientY: 100 }],
      });

      fireEvent.touchEnd(tablist, {
        changedTouches: [{ clientX: 200, clientY: 100 }],
      });

      expect(mockOnSelectPuzzle).toHaveBeenCalledWith(2);
    });

    it('should not navigate on small swipe', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={1} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');

      // Small swipe (delta < 50px)
      fireEvent.touchStart(tablist, {
        touches: [{ clientX: 100, clientY: 100 }],
      });

      fireEvent.touchEnd(tablist, {
        changedTouches: [{ clientX: 130, clientY: 100 }],
      });

      expect(mockOnSelectPuzzle).not.toHaveBeenCalled();
    });

    it('should not navigate on vertical swipe', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={1} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');

      // Vertical swipe (large deltaY)
      fireEvent.touchStart(tablist, {
        touches: [{ clientX: 100, clientY: 100 }],
      });

      fireEvent.touchEnd(tablist, {
        changedTouches: [{ clientX: 200, clientY: 250 }],
      });

      expect(mockOnSelectPuzzle).not.toHaveBeenCalled();
    });

    it('should not navigate right from last puzzle via swipe', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={4} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');

      // Swipe left
      fireEvent.touchStart(tablist, {
        touches: [{ clientX: 300, clientY: 100 }],
      });

      fireEvent.touchEnd(tablist, {
        changedTouches: [{ clientX: 200, clientY: 100 }],
      });

      expect(mockOnSelectPuzzle).not.toHaveBeenCalled();
    });

    it('should not navigate left from first puzzle via swipe', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');

      // Swipe right
      fireEvent.touchStart(tablist, {
        touches: [{ clientX: 200, clientY: 100 }],
      });

      fireEvent.touchEnd(tablist, {
        changedTouches: [{ clientX: 300, clientY: 100 }],
      });

      expect(mockOnSelectPuzzle).not.toHaveBeenCalled();
    });
  });

  describe('Progress Calculation', () => {
    it('should calculate correct puzzles correctly', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const progressbar = screen.getByRole('progressbar');
      // 2 correct out of 5 = 40%
      expect(progressbar.getAttribute('aria-valuenow')).toBe('40');
    });

    it('should show correct progress label', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      expect(screen.getByText('2/5 (40%)')).toBeDefined();
    });

    it('should handle all puzzles unsolved', () => {
      const unsolvedPuzzles: PuzzleIndicator[] = [
        { index: 0, status: 'unsolved' },
        { index: 1, status: 'unsolved' },
      ];

      render(<PuzzleNavCarousel puzzles={unsolvedPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('0');
    });

    it('should handle all puzzles solved', () => {
      const solvedPuzzles: PuzzleIndicator[] = [
        { index: 0, status: 'correct' },
        { index: 1, status: 'correct' },
        { index: 2, status: 'correct' },
      ];

      render(<PuzzleNavCarousel puzzles={solvedPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('100');
    });
  });

  describe('Accessibility', () => {
    it('should have role="tablist" on container', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      expect(screen.getByRole('tablist')).toBeDefined();
    });

    it('should have aria-label on tablist', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      expect(tablist.getAttribute('aria-label')).toBe('Puzzle navigation');
    });

    it('should have aria-orientation="horizontal"', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      expect(tablist.getAttribute('aria-orientation')).toBe('horizontal');
    });

    it('should be focusable with tabIndex=0', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tablist = screen.getByRole('tablist');
      expect(tablist.getAttribute('tabIndex')).toBe('0');
    });

    it('should have screen reader announcement region', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={2} onSelectPuzzle={mockOnSelectPuzzle} />);

      const status = screen.getByRole('status');
      expect(status.getAttribute('aria-live')).toBe('polite');
      expect(status.getAttribute('aria-atomic')).toBe('true');
    });

    it('should announce current puzzle to screen readers', async () => {
      const { rerender } = render(
        <PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />
      );

      const status = screen.getByRole('status');
      expect(status.textContent).toContain('Puzzle 1');

      // Navigate to next puzzle
      rerender(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={1} onSelectPuzzle={mockOnSelectPuzzle} />);

      await waitFor(() => {
        expect(status.textContent).toContain('Puzzle 2');
      });
    });

    it('should include status in announcement', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const status = screen.getByRole('status');
      // Puzzle 1 has status 'correct'
      expect(status.textContent).toContain('completed');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty puzzle list', () => {
      expect(() => {
        render(<PuzzleNavCarousel puzzles={[]} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);
      }).not.toThrow();
    });

    it('should handle single puzzle', () => {
      const singlePuzzle: PuzzleIndicator[] = [{ index: 0, status: 'unsolved' }];

      render(<PuzzleNavCarousel puzzles={singlePuzzle} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} />);

      const tabs = screen.getAllByRole('tab');
      expect(tabs.length).toBe(1);
    });

    it('should handle large number of puzzles', () => {
      const manyPuzzles: PuzzleIndicator[] = Array.from({ length: 50 }, (_, i) => ({
        index: i,
        status: 'unsolved' as const,
      }));

      expect(() => {
        render(<PuzzleNavCarousel puzzles={manyPuzzles} currentIndex={25} onSelectPuzzle={mockOnSelectPuzzle} />);
      }).not.toThrow();
    });
  });

  describe('Compact Mode', () => {
    it('should pass compact prop to ProgressBar', () => {
      render(<PuzzleNavCarousel puzzles={mockPuzzles} currentIndex={0} onSelectPuzzle={mockOnSelectPuzzle} compact={true} />);

      // Progress bar should not show label in compact mode
      expect(screen.queryByText(/\/5/)).toBeNull();
    });
  });
});
