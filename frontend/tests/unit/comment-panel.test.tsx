/**
 * Comment Panel Tests
 * @module tests/unit/comment-panel.test.tsx
 *
 * Unit tests for CommentPanel component (Spec 125 gobanRef API).
 * Covers: T022-T025, T024/T042c (comment display + coordinate)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/preact';
import { CommentPanel } from '../../src/components/SolutionTree';

// ============================================================================
// Goban Mock Factory
// ============================================================================

type Listener = (...args: unknown[]) => void;

function createMockGoban(curMove: { text?: string; x?: number; y?: number; player?: number } = {}) {
  const listeners: Record<string, Listener[]> = {};

  return {
    engine: {
      cur_move: curMove,
    },
    on(event: string, fn: Listener) {
      if (!listeners[event]) listeners[event] = [];
      listeners[event].push(fn);
    },
    off(event: string, fn: Listener) {
      if (listeners[event]) {
        listeners[event] = listeners[event].filter((f) => f !== fn);
      }
    },
    /** Helper: emit an event to simulate goban updates */
    _emit(event: string) {
      listeners[event]?.forEach((fn) => fn());
    },
    /** Helper: update cur_move and trigger update */
    _setMove(move: { text?: string; x?: number; y?: number; player?: number }) {
      this.engine.cur_move = move;
      this._emit('update');
    },
  };
}

// ============================================================================
// Tests
// ============================================================================

describe('CommentPanel', () => {
  let mockGoban: ReturnType<typeof createMockGoban>;
  let gobanRef: { current: unknown };

  beforeEach(() => {
    mockGoban = createMockGoban();
    gobanRef = { current: mockGoban };
  });

  describe('Basic Comment Display', () => {
    it('should show comment text from current move', () => {
      mockGoban._setMove({ text: 'Good move! This captures the group.' });
      render(<CommentPanel gobanRef={gobanRef as never} />);

      expect(screen.getByText(/Good move/)).toBeTruthy();
    });

    it('should show empty state when no comment', () => {
      mockGoban._setMove({});
      render(<CommentPanel gobanRef={gobanRef as never} />);

      expect(screen.getByText(/No comment for this move/)).toBeTruthy();
    });

    it('should have data-testid comment-panel', () => {
      render(<CommentPanel gobanRef={gobanRef as never} />);

      expect(screen.getByTestId('comment-panel')).toBeTruthy();
    });
  });

  describe('Accessible Label', () => {
    it('should have role region', () => {
      render(<CommentPanel gobanRef={gobanRef as never} />);

      const panel = screen.getByTestId('comment-panel');
      expect(panel.getAttribute('role')).toBe('region');
    });

    it('should have aria-label for move comment', () => {
      render(<CommentPanel gobanRef={gobanRef as never} />);

      const panel = screen.getByTestId('comment-panel');
      expect(panel.getAttribute('aria-label')).toBe('Move comment');
    });
  });

  describe('Move Coordinate Display (T024/T042c)', () => {
    it('should display coordinate for black move', () => {
      mockGoban._setMove({ x: 3, y: 15, player: 1 });
      render(<CommentPanel gobanRef={gobanRef as never} />);

      expect(screen.getByTestId('move-coordinate')).toBeTruthy();
      expect(screen.getByText('B: D4')).toBeTruthy();
    });

    it('should display coordinate for white move', () => {
      mockGoban._setMove({ x: 15, y: 3, player: 2 });
      render(<CommentPanel gobanRef={gobanRef as never} />);

      expect(screen.getByText('W: Q16')).toBeTruthy();
    });

    it('should not show coordinate when no move coords', () => {
      mockGoban._setMove({ text: 'Just a comment' });
      render(<CommentPanel gobanRef={gobanRef as never} />);

      expect(screen.queryByTestId('move-coordinate')).toBeNull();
    });

    it('should show coordinate alongside comment', () => {
      mockGoban._setMove({ text: 'Good move!', x: 3, y: 15, player: 1 });
      render(<CommentPanel gobanRef={gobanRef as never} />);

      expect(screen.getByText('B: D4')).toBeTruthy();
      expect(screen.getByText('Good move!')).toBeTruthy();
    });
  });

  describe('Line Break Preservation', () => {
    it('should preserve whitespace in comments', () => {
      mockGoban._setMove({ text: 'Line 1\nLine 2\nLine 3' });
      render(<CommentPanel gobanRef={gobanRef as never} />);

      // pre-wrap style handles line breaks
      expect(screen.getByText(/Line 1/)).toBeTruthy();
    });
  });

  describe('Live Updates', () => {
    it('should have aria-live polite for screen reader updates', () => {
      render(<CommentPanel gobanRef={gobanRef as never} />);

      const panel = screen.getByTestId('comment-panel');
      expect(panel.getAttribute('aria-live')).toBe('polite');
    });

    it('should have aria-atomic true', () => {
      render(<CommentPanel gobanRef={gobanRef as never} />);

      const panel = screen.getByTestId('comment-panel');
      expect(panel.getAttribute('aria-atomic')).toBe('true');
    });

    it('should update when goban emits update event', () => {
      render(<CommentPanel gobanRef={gobanRef as never} />);

      // Initially no comment
      expect(screen.getByText(/No comment/)).toBeTruthy();

      // Update move
      act(() => {
        mockGoban._setMove({ text: 'New comment' });
      });

      expect(screen.getByText('New comment')).toBeTruthy();
    });
  });

  describe('Security', () => {
    it('should handle HTML in comments safely', () => {
      mockGoban._setMove({ text: "<script>alert('xss')</script>" });
      render(<CommentPanel gobanRef={gobanRef as never} />);

      // Should render as text, not execute
      const panel = screen.getByTestId('comment-panel');
      expect(panel.querySelector('script')).toBeNull();
      expect(panel.textContent).toContain('alert');
    });
  });

  describe('Null Goban', () => {
    it('should handle null gobanRef gracefully', () => {
      const nullRef = { current: null };
      render(<CommentPanel gobanRef={nullRef as never} />);

      expect(screen.getByTestId('comment-panel')).toBeTruthy();
      expect(screen.getByText(/No comment/)).toBeTruthy();
    });
  });

  describe('Custom Styling', () => {
    it('should accept custom className', () => {
      render(<CommentPanel gobanRef={gobanRef as never} className="custom-class" />);

      const panel = screen.getByTestId('comment-panel');
      // className is applied via Preact's className prop
      expect(panel.className).toContain('custom-class');
    });
  });
});
