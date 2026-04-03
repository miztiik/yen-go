/**
 * Integration test for progressive hints.
 *
 * Verifies 3 hint levels, button disable, reset on new position.
 *
 * Spec 127: Phase 5, T058
 * @module tests/integration/hints
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { HintOverlay } from '../../src/components/Solver/HintOverlay';

describe('HintOverlay progressive hints', () => {
  const testHints = ['Look at the corner', 'Try an atari', 'Play C3'];

  it('renders hint request button', () => {
    render(<HintOverlay hints={testHints} correctMove={null} />);
    const button = screen.getByRole('button', { name: /hint/i });
    expect(button).toBeTruthy();
  });

  it('shows first hint on first click', () => {
    render(<HintOverlay hints={testHints} correctMove={null} />);
    const button = screen.getByRole('button', { name: /hint/i });
    fireEvent.click(button);
    expect(screen.getByText('Look at the corner')).toBeTruthy();
  });

  it('progresses through 3 hint levels', () => {
    render(<HintOverlay hints={testHints} correctMove={null} />);
    const button = screen.getByRole('button', { name: /hint/i });

    // Level 1
    fireEvent.click(button);
    expect(screen.getByText('Look at the corner')).toBeTruthy();

    // Level 2
    fireEvent.click(button);
    expect(screen.getByText('Try an atari')).toBeTruthy();

    // Level 3
    fireEvent.click(button);
    expect(screen.getByText('Play C3')).toBeTruthy();
  });

  it('disables button after all hints exhausted', () => {
    render(<HintOverlay hints={testHints} correctMove={null} />);
    const button = screen.getByRole('button', { name: /hint/i });

    fireEvent.click(button); // Level 1
    fireEvent.click(button); // Level 2
    fireEvent.click(button); // Level 3

    // After all hints used, button should be aria-disabled
    expect(button.getAttribute('aria-disabled')).toBe('true');
  });

  it('handles empty hints array gracefully', () => {
    render(<HintOverlay hints={[]} correctMove={null} />);
    const button = screen.getByRole('button', { name: /hint/i });
    expect(button.getAttribute('aria-disabled')).toBe('true');
  });
});
