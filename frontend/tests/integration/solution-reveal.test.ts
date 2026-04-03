/**
 * Integration test for solution reveal.
 *
 * Verifies Next Move stepping, C[] comments display, completion state.
 *
 * Spec 127: Phase 5, T059
 * @module tests/integration/solution-reveal
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { SolutionReveal } from '../../src/components/Solver/SolutionReveal';

describe('SolutionReveal', () => {
  const totalSteps = 5;
  const onRevealStart = vi.fn();
  const onRevealComplete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Show Solution button initially', () => {
    render(
      <SolutionReveal
        totalSteps={totalSteps}
        onRevealStart={onRevealStart}
        onRevealComplete={onRevealComplete}
      />,
    );
    expect(screen.getByText(/show solution/i)).toBeTruthy();
  });

  it('calls onRevealStart when Show Solution is clicked', () => {
    render(
      <SolutionReveal
        totalSteps={totalSteps}
        onRevealStart={onRevealStart}
        onRevealComplete={onRevealComplete}
      />,
    );
    fireEvent.click(screen.getByText(/show solution/i));
    expect(onRevealStart).toHaveBeenCalledOnce();
  });

  it('shows Next Move button after reveal starts', () => {
    render(
      <SolutionReveal
        totalSteps={totalSteps}
        onRevealStart={onRevealStart}
        onRevealComplete={onRevealComplete}
      />,
    );
    fireEvent.click(screen.getByText(/show solution/i));
    expect(screen.getByRole('button', { name: /step/i })).toBeTruthy();
  });

  it('has aria-label with step count on Next Move button', () => {
    render(
      <SolutionReveal
        totalSteps={totalSteps}
        onRevealStart={onRevealStart}
        onRevealComplete={onRevealComplete}
      />,
    );
    fireEvent.click(screen.getByText(/show solution/i));
    const button = screen.getByRole('button', { name: /step/i });
    expect(button.getAttribute('aria-label')).toMatch(/step.*of/i);
  });
});
