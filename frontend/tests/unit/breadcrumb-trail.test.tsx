/**
 * BreadcrumbTrail Component Tests
 * @module tests/unit/breadcrumb-trail.test
 *
 * Tests for breadcrumb navigation path display (Spec 125 gobanRef API).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/preact';
import { BreadcrumbTrail } from '../../src/components/SolutionTree';

// ============================================================================
// Goban Mock Factory
// ============================================================================

type Listener = (...args: unknown[]) => void;

interface MockMoveNode {
  x?: number;
  y?: number;
  parent?: MockMoveNode;
}

function createMockGoban(curMove?: MockMoveNode) {
  const listeners: Record<string, Listener[]> = {};

  return {
    engine: {
      cur_move: curMove || null,
    },
    showFirst: vi.fn(),
    on(event: string, fn: Listener) {
      if (!listeners[event]) listeners[event] = [];
      listeners[event].push(fn);
    },
    off(event: string, fn: Listener) {
      if (listeners[event]) {
        listeners[event] = listeners[event].filter((f) => f !== fn);
      }
    },
    _emit(event: string) {
      listeners[event]?.forEach((fn) => fn());
    },
    _setMove(move: MockMoveNode | null) {
      this.engine.cur_move = move;
      this._emit('update');
    },
  };
}

/**
 * Build a linear chain: root → m1 → m2 → ... → mN
 * Each node has x/y coordinates.
 */
function buildPath(length: number): MockMoveNode {
  const root: MockMoveNode = {};
  let current = root;
  for (let i = 1; i < length; i++) {
    const child: MockMoveNode = { x: i, y: 18 - i, parent: current };
    current = child;
  }
  return current; // returns the LAST node (deepest)
}

// ============================================================================
// Tests
// ============================================================================

describe('BreadcrumbTrail', () => {
  let mockGoban: ReturnType<typeof createMockGoban>;
  let gobanRef: { current: unknown };

  beforeEach(() => {
    mockGoban = createMockGoban();
    gobanRef = { current: mockGoban };
  });

  describe('Rendering', () => {
    it('should render breadcrumb navigation', () => {
      // Path: root → D4 (x=3, y=15)
      const leaf: MockMoveNode = { x: 3, y: 15, parent: {} };
      mockGoban.engine.cur_move = leaf;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} />);

      expect(screen.getByTestId('breadcrumb-trail')).toBeTruthy();
    });

    it('should show Start label for root', () => {
      const leaf: MockMoveNode = { x: 3, y: 15, parent: {} };
      mockGoban.engine.cur_move = leaf;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} />);

      expect(screen.getByText('Start')).toBeTruthy();
    });

    it('should display move coordinates in path', () => {
      // root → child at D4
      const root: MockMoveNode = {};
      const child: MockMoveNode = { x: 3, y: 15, parent: root };
      mockGoban.engine.cur_move = child;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} />);

      expect(screen.getByText('D4')).toBeTruthy();
    });

    it('should show separator arrows between crumbs', () => {
      const root: MockMoveNode = {};
      const child: MockMoveNode = { x: 3, y: 15, parent: root };
      mockGoban.engine.cur_move = child;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} />);

      expect(screen.getByText('→')).toBeTruthy();
    });

    it('should highlight last crumb as current', () => {
      const root: MockMoveNode = {};
      const child: MockMoveNode = { x: 3, y: 15, parent: root };
      mockGoban.engine.cur_move = child;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} />);

      const lastButton = screen.getByText('D4').closest('button');
      expect(lastButton?.getAttribute('aria-current')).toBe('step');
    });

    it('should handle null goban gracefully', () => {
      const nullRef = { current: null };
      render(<BreadcrumbTrail gobanRef={nullRef as never} />);

      // Should render without crashing — shows "Start" fallback
      expect(screen.getByText('Start')).toBeTruthy();
    });
  });

  describe('Interaction', () => {
    it('should call onNavigate when breadcrumb is clicked', () => {
      const onNavigate = vi.fn();
      const root: MockMoveNode = {};
      const child: MockMoveNode = { x: 3, y: 15, parent: root };
      mockGoban.engine.cur_move = child;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} onNavigate={onNavigate} />);

      fireEvent.click(screen.getByText('Start'));

      expect(onNavigate).toHaveBeenCalledWith(0);
    });

    it('should call onNavigate with move number for non-root click', () => {
      const onNavigate = vi.fn();
      const root: MockMoveNode = {};
      const child: MockMoveNode = { x: 3, y: 15, parent: root };
      mockGoban.engine.cur_move = child;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} onNavigate={onNavigate} />);

      fireEvent.click(screen.getByText('D4'));

      expect(onNavigate).toHaveBeenCalledWith(1);
    });
  });

  describe('Live Updates', () => {
    it('should update when goban emits update event', () => {
      render(<BreadcrumbTrail gobanRef={gobanRef as never} />);

      // Initially shows Start only
      expect(screen.getByText('Start')).toBeTruthy();

      // Move to D4
      act(() => {
        const root: MockMoveNode = {};
        const child: MockMoveNode = { x: 3, y: 15, parent: root };
        mockGoban._setMove(child);
      });

      expect(screen.getByText('D4')).toBeTruthy();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible navigation label', () => {
      const root: MockMoveNode = {};
      const child: MockMoveNode = { x: 3, y: 15, parent: root };
      mockGoban.engine.cur_move = child;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} />);

      const nav = screen.getByTestId('breadcrumb-trail');
      expect(nav.getAttribute('aria-label')).toBe('Move history');
    });

    it('should have aria-current on last crumb only', () => {
      const root: MockMoveNode = {};
      const m1: MockMoveNode = { x: 3, y: 15, parent: root };
      const m2: MockMoveNode = { x: 15, y: 3, parent: m1 };
      mockGoban.engine.cur_move = m2;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} />);

      const startButton = screen.getByText('Start').closest('button');
      expect(startButton?.getAttribute('aria-current')).toBeNull();

      const lastButton = screen.getByText('Q16').closest('button');
      expect(lastButton?.getAttribute('aria-current')).toBe('step');
    });
  });

  describe('Custom Styling', () => {
    it('should accept custom className', () => {
      const root: MockMoveNode = {};
      const child: MockMoveNode = { x: 3, y: 15, parent: root };
      mockGoban.engine.cur_move = child;

      render(<BreadcrumbTrail gobanRef={gobanRef as never} className="custom-class" />);

      const nav = screen.getByTestId('breadcrumb-trail');
      expect(nav.className).toContain('custom-class');
    });
  });
});
