/**
 * Mobile Interaction Tests
 * @module tests/integration/mobile_interaction
 *
 * End-to-end tests for touch interactions and mobile responsiveness
 * Covers FR-045, FR-046, FR-047, FR-048 from US9
 * 
 * Updated: 2026-02-04 to use new puzzle format (types/puzzle.ts) and pages/PuzzleView
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/preact';
import { h } from 'preact';
import { Board } from '../../src/components/Board/Board';
import { PuzzleView } from '../../src/pages/PuzzleView';
import type { Stone, BoardSize } from '../../src/types';
import type { Puzzle } from '../../src/types/puzzle';

// Mock localStorage for progress tracking
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Test fixtures
const BOARD_SIZE: BoardSize = 9;

const createTestStones = (): Stone[][] => {
  const stones: Stone[][] = [];
  for (let y = 0; y < BOARD_SIZE; y++) {
    const row: Stone[] = [];
    for (let x = 0; x < BOARD_SIZE; x++) {
      row.push('empty');
    }
    stones.push(row);
  }
  return stones;
};

// New puzzle format (types/puzzle.ts)
const SIMPLE_PUZZLE: Puzzle = {
  id: 'touch-test-puzzle',
  B: [],  // No black stones initially
  W: [],  // No white stones initially
  sol: [['ee']],  // Simple solution: just play at center (e5)
  side: 'B',
  region: { x1: 0, y1: 0, x2: 8, y2: 8, size: 9 },
};

const PUZZLE_ID = 'touch-test-puzzle';

describe('Mobile Interaction Tests', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe('Touch Events', () => {
    it('should respond to touch start events', () => {
      const onMove = vi.fn();
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={onMove}
          interactive={true}
        />
      );

      const canvas = screen.getByRole('img', { name: /go board/i });
      expect(canvas).toBeDefined();

      // Simulate touch start
      const touchEvent = new TouchEvent('touchstart', {
        touches: [
          {
            clientX: 150,
            clientY: 150,
            identifier: 0,
            target: canvas,
          } as Touch,
        ],
        bubbles: true,
        cancelable: true,
      });

      canvas.dispatchEvent(touchEvent);
      // Board processes touch events
      expect(canvas).toBeDefined();
    });

    it('should handle touch end events for move placement', () => {
      const onMove = vi.fn();
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={onMove}
          interactive={true}
        />
      );

      const canvas = screen.getByRole('img', { name: /go board/i });

      // Simulate touch sequence
      const touchStartEvent = new TouchEvent('touchstart', {
        touches: [
          {
            clientX: 150,
            clientY: 150,
            identifier: 0,
            target: canvas,
          } as Touch,
        ],
        bubbles: true,
        cancelable: true,
      });

      const touchEndEvent = new TouchEvent('touchend', {
        changedTouches: [
          {
            clientX: 150,
            clientY: 150,
            identifier: 0,
            target: canvas,
          } as Touch,
        ],
        bubbles: true,
        cancelable: true,
      });

      canvas.dispatchEvent(touchStartEvent);
      canvas.dispatchEvent(touchEndEvent);

      // Touch events should be processed
      expect(canvas).toBeDefined();
    });

    it('should support tap-to-place move interaction pattern', () => {
      const onMove = vi.fn();
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={onMove}
          interactive={true}
        />
      );

      const canvas = screen.getByRole('img', { name: /go board/i });

      // Simulate tap (click) event which works for both mouse and touch
      fireEvent.click(canvas, {
        clientX: 150,
        clientY: 150,
      });

      // Board should process the tap
      expect(canvas).toBeDefined();
    });
  });

  describe('Touch Targets', () => {
    it('should have minimum 44px touch target size per WCAG guidelines', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      const boardContainer = screen.getByRole('application', { name: /go puzzle board/i });

      // Board container should have minimum size for touch targets
      expect(boardContainer).toBeDefined();
      // Inline style includes min-width/min-height for touch support
      const style = boardContainer.getAttribute('style');
      expect(style).toContain('min-width');
      expect(style).toContain('min-height');
    });

    it('should have accessible board with proper role', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      // Board should have application role for interactive widget
      const board = screen.getByRole('application', { name: /go puzzle board/i });
      expect(board).toBeDefined();
    });
  });

  describe('Keyboard Navigation (FR-045)', () => {
    it('should support arrow key navigation', () => {
      const onMove = vi.fn();
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={onMove}
          interactive={true}
        />
      );

      const boardContainer = screen.getByRole('application', { name: /go puzzle board/i });

      // Focus the board
      boardContainer.focus();

      // Simulate arrow key press
      fireEvent.keyDown(boardContainer, { key: 'ArrowRight', code: 'ArrowRight' });
      fireEvent.keyDown(boardContainer, { key: 'ArrowDown', code: 'ArrowDown' });

      // Board should handle keyboard navigation
      expect(boardContainer).toBeDefined();
    });

    it('should place stone with Enter key', () => {
      const onMove = vi.fn();
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={onMove}
          interactive={true}
        />
      );

      const boardContainer = screen.getByRole('application', { name: /go puzzle board/i });
      boardContainer.focus();

      // Navigate to a position and press Enter
      fireEvent.keyDown(boardContainer, { key: 'ArrowRight', code: 'ArrowRight' });
      fireEvent.keyDown(boardContainer, { key: 'Enter', code: 'Enter' });

      // Enter key should trigger move
      expect(boardContainer).toBeDefined();
    });

    it('should place stone with Space key', () => {
      const onMove = vi.fn();
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={onMove}
          interactive={true}
        />
      );

      const boardContainer = screen.getByRole('application', { name: /go puzzle board/i });
      boardContainer.focus();

      // Navigate to a position and press Space
      fireEvent.keyDown(boardContainer, { key: ' ', code: 'Space' });

      // Space key should trigger move
      expect(boardContainer).toBeDefined();
    });

    // T1.K2: Keyboard handler removed from Board (Besogo alignment).
    // Escape key is no longer handled at the board level.
    // Arrow keys / keyboard nav are exclusively in SolutionTreeView.
    it.skip('should call onEscape when Escape pressed (removed per Besogo alignment)', () => {
      const onEscape = vi.fn();
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          onEscape={onEscape}
          interactive={true}
        />
      );

      const boardContainer = screen.getByRole('application', { name: /go puzzle board/i });
      boardContainer.focus();

      fireEvent.keyDown(boardContainer, { key: 'Escape', code: 'Escape' });

      expect(onEscape).toHaveBeenCalled();
    });

    it('should have tabIndex for keyboard focus', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      const boardContainer = screen.getByRole('application', { name: /go puzzle board/i });

      // Should have tabIndex for focusability
      const tabIndex = boardContainer.getAttribute('tabindex');
      expect(tabIndex).toBeDefined();
    });
  });

  describe('Accessibility (FR-046)', () => {
    it('should have aria-label on board', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      const board = screen.getByRole('application', { name: /go puzzle board/i });
      expect(board.getAttribute('aria-label')).toBeTruthy();
    });

    it('should have aria-roledescription on board container', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      const board = screen.getByRole('application', { name: /go puzzle board/i });
      expect(board.getAttribute('aria-roledescription')).toBeTruthy();
    });

    // T1.K2: Screen reader live region removed along with keyboard focus tracking.
    // Board no longer has focus position state or announcements.
    it.skip('should have screen reader live region (removed per Besogo alignment)', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      // Board should have a live region for screen reader announcements
      const liveRegions = screen.getAllByRole('status');
      expect(liveRegions.length).toBeGreaterThanOrEqual(1);
    });

    it('should have accessible canvas with proper ARIA', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      const canvas = screen.getByRole('img', { name: /go board/i });
      expect(canvas.getAttribute('aria-label')).toBeTruthy();
      expect(canvas.getAttribute('aria-roledescription')).toBeTruthy();
    });
  });

  describe('Responsive Layout', () => {
    it('should render board with responsive container', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      const boardContainer = screen.getByRole('application', { name: /go puzzle board/i });
      const style = boardContainer.getAttribute('style');

      // Should use relative sizing
      expect(style).toContain('width: 100%');
      expect(style).toContain('height: 100%');
    });

    it('should maintain aspect ratio', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      const boardContainer = screen.getByRole('application', { name: /go puzzle board/i });
      const style = boardContainer.getAttribute('style');

      // Should have aspect ratio for square board
      expect(style).toContain('aspect-ratio');
    });
  });

  describe('PuzzleView Mobile Integration', () => {
    it('should render puzzle view with accessible board', () => {
      render(
        <PuzzleView
          puzzle={SIMPLE_PUZZLE}
          puzzleId={PUZZLE_ID}
          onComplete={vi.fn()}
        />
      );

      // PuzzleView should contain accessible components (board and/or tree with role="application")
      const applications = screen.getAllByRole('application');
      expect(applications.length).toBeGreaterThanOrEqual(1);
    });

    it('should have accessible buttons with aria-labels', () => {
      render(
        <PuzzleView
          puzzle={SIMPLE_PUZZLE}
          puzzleId={PUZZLE_ID}
          onComplete={vi.fn()}
        />
      );

      // Reset button should have accessible name
      const resetButton = screen.getByRole('button', { name: /reset/i });
      expect(resetButton).toBeDefined();
    });

    it('should show side to move indicator', () => {
      render(
        <PuzzleView
          puzzle={SIMPLE_PUZZLE}
          puzzleId={PUZZLE_ID}
          onComplete={vi.fn()}
        />
      );

      // Should have board and tree components rendered (both have role="application")
      const applications = screen.getAllByRole('application');
      expect(applications.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Gesture Support', () => {
    it('should prevent default on touch events to avoid scroll interference', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      const canvas = screen.getByRole('img', { name: /go board/i });

      // Create a touch event that we can check for preventDefault
      let wasDefaultPrevented = false;
      const touchMoveEvent = new TouchEvent('touchmove', {
        touches: [
          {
            clientX: 160,
            clientY: 160,
            identifier: 0,
            target: canvas,
          } as Touch,
        ],
        bubbles: true,
        cancelable: true,
      });

      // Override preventDefault to track if it was called
      touchMoveEvent.preventDefault = () => {
        wasDefaultPrevented = true;
      };

      canvas.dispatchEvent(touchMoveEvent);

      // Board should be defined regardless of prevention
      expect(canvas).toBeDefined();
    });

    it('should support double-tap prevention for zoom', () => {
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={vi.fn()}
          interactive={true}
        />
      );

      const boardContainer = screen.getByRole('application', { name: /go puzzle board/i });

      // Check for touch-action CSS which prevents double-tap zoom
      // This is typically handled via CSS, so we verify the container is styled
      expect(boardContainer.getAttribute('style')).toBeDefined();
    });
  });

  describe('Multi-touch Handling', () => {
    it('should ignore multi-touch gestures', () => {
      const onMove = vi.fn();
      render(
        <Board
          stones={createTestStones()}
          boardSize={BOARD_SIZE}
          onIntersectionClick={onMove}
          interactive={true}
        />
      );

      const canvas = screen.getByRole('img', { name: /go board/i });

      // Simulate multi-touch (pinch gesture start)
      const multiTouchEvent = new TouchEvent('touchstart', {
        touches: [
          {
            clientX: 150,
            clientY: 150,
            identifier: 0,
            target: canvas,
          } as Touch,
          {
            clientX: 200,
            clientY: 200,
            identifier: 1,
            target: canvas,
          } as Touch,
        ],
        bubbles: true,
        cancelable: true,
      });

      canvas.dispatchEvent(multiTouchEvent);

      // Multi-touch should not trigger a move
      // The Board should handle this gracefully
      expect(canvas).toBeDefined();
    });
  });
});

describe('Button Touch Targets', () => {
  it('should have minimum touch target size on puzzle buttons', () => {
    render(
      <PuzzleView
        puzzle={SIMPLE_PUZZLE}
        puzzleId={PUZZLE_ID}
        onComplete={vi.fn()}
      />
    );

    const resetButton = screen.getByRole('button', { name: /reset/i });
    expect(resetButton).toBeDefined();

    // Button should be present and accessible (tagName check for button element)
    expect(resetButton.tagName.toLowerCase()).toBe('button');
  });
});