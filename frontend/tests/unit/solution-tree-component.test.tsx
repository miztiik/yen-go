/**
 * Solution Tree Component Tests
 * @module tests/unit/solution-tree-component.test
 *
 * Tests for SolutionTreePanel, EmptyTreeState, and TreeErrorState.
 *
 * Note: SolutionTreePanel wraps goban's canvas tree — core tree rendering
 * is tested via goban library itself. These tests verify our wrapper behavior.
 *
 * T053: Empty state for root-only puzzles
 * T054: Error state for malformed tree
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import {
  SolutionTreePanel,
  EmptyTreeState,
  TreeErrorState,
} from '../../src/components/SolutionTree';

// ============================================================================
// SolutionTreePanel Tests
// ============================================================================

describe('SolutionTreePanel', () => {
  it('should render the tree container', () => {
    const gobanRef = { current: null };
    render(<SolutionTreePanel gobanRef={gobanRef as never} />);

    expect(screen.getByTestId('solution-tree-panel')).toBeTruthy();
  });

  it('should have accessible region role and label', () => {
    const gobanRef = { current: null };
    render(<SolutionTreePanel gobanRef={gobanRef as never} />);

    const panel = screen.getByTestId('solution-tree-panel');
    expect(panel.getAttribute('role')).toBe('region');
    expect(panel.getAttribute('aria-label')).toBe('Solution tree');
  });

  it('should show hidden message when not visible', () => {
    const gobanRef = { current: null };
    render(<SolutionTreePanel gobanRef={gobanRef as never} isVisible={false} />);

    expect(screen.getByTestId('tree-hidden-message')).toBeTruthy();
    expect(screen.getByText(/Complete the puzzle/)).toBeTruthy();
  });

  it('should not show hidden message when visible', () => {
    const gobanRef = { current: null };
    render(<SolutionTreePanel gobanRef={gobanRef as never} isVisible={true} />);

    expect(screen.queryByTestId('tree-hidden-message')).toBeNull();
  });

  it('should accept custom className', () => {
    const gobanRef = { current: null };
    render(<SolutionTreePanel gobanRef={gobanRef as never} className="custom-tree" />);

    const panel = screen.getByTestId('solution-tree-panel');
    expect(panel.className).toContain('custom-tree');
  });
});

// ============================================================================
// EmptyTreeState Tests (T053)
// ============================================================================

describe('EmptyTreeState', () => {
  it('should render empty state message', () => {
    render(<EmptyTreeState />);

    expect(screen.getByTestId('tree-empty-state')).toBeTruthy();
    expect(screen.getByText('No variations to explore')).toBeTruthy();
  });

  it('should show subtext about single solution', () => {
    render(<EmptyTreeState />);

    expect(screen.getByText(/single solution path/)).toBeTruthy();
  });

  it('should have status role', () => {
    render(<EmptyTreeState />);

    const el = screen.getByTestId('tree-empty-state');
    expect(el.getAttribute('role')).toBe('status');
  });

  it('should accept custom className', () => {
    render(<EmptyTreeState className="custom-empty" />);

    const el = screen.getByTestId('tree-empty-state');
    expect(el.className).toContain('custom-empty');
  });
});

// ============================================================================
// TreeErrorState Tests (T054)
// ============================================================================

describe('TreeErrorState', () => {
  it('should render default error message', () => {
    render(<TreeErrorState />);

    expect(screen.getByTestId('tree-error-state')).toBeTruthy();
    expect(screen.getByText('Unable to display solution tree')).toBeTruthy();
  });

  it('should render custom error message', () => {
    render(<TreeErrorState message="SGF parse error" />);

    expect(screen.getByText('SGF parse error')).toBeTruthy();
  });

  it('should have alert role', () => {
    render(<TreeErrorState />);

    const el = screen.getByTestId('tree-error-state');
    expect(el.getAttribute('role')).toBe('alert');
  });

  it('should accept custom className', () => {
    render(<TreeErrorState className="custom-error" />);

    const el = screen.getByTestId('tree-error-state');
    expect(el.className).toContain('custom-error');
  });
});
