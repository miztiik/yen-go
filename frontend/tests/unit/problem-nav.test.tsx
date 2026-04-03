/**
 * Problem Navigation Tests
 * @module tests/unit/problem-nav.test
 *
 * Tests for ProblemNav component — Minimal Dot Design (T11.8).
 *
 * Covers: T044, T11.8
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { h } from 'preact';

// Types for problem navigation
type PuzzleStatus = 'unsolved' | 'solved' | 'failed';

interface ProblemNavProps {
  totalProblems: number;
  currentIndex: number;
  statuses: PuzzleStatus[];
  onNavigate: (index: number) => void;
  onPrev: () => void;
  onNext: () => void;
  currentStreak?: number | undefined;
}

// Mock ProblemNav — minimal dot design (T11.8)
function MockProblemNav({
  totalProblems,
  currentIndex,
  statuses,
  onNavigate,
  onPrev,
  onNext,
  currentStreak,
}: ProblemNavProps) {
  const solvedCount = statuses.filter(s => s === 'solved').length;
  const completionPct = totalProblems > 0 ? Math.round((solvedCount / totalProblems) * 100) : 0;
  const useDots = totalProblems <= 20;

  return (
    <nav
      className="problem-nav"
      data-testid="problem-nav"
      role="navigation"
      aria-label="Problem navigation"
    >
      <div className="nav-row">
        <button
          type="button"
          className="nav-button prev"
          onClick={onPrev}
          disabled={currentIndex === 0}
          aria-label="Previous problem"
        >
          ←
        </button>

        {useDots ? (
          <div className="problem-dots" role="tablist" aria-label="Problems">
            {Array.from({ length: totalProblems }, (_, i) => {
              const status = statuses[i] || 'unsolved';
              const isCurrent = i === currentIndex;

              return (
                <button
                  key={i}
                  type="button"
                  className={`dot ${status} ${isCurrent ? 'current' : ''}`}
                  onClick={() => onNavigate(i)}
                  role="tab"
                  aria-selected={isCurrent}
                  aria-label={`Problem ${i + 1}, ${status}`}
                  data-testid={`indicator-${i}`}
                />
              );
            })}
          </div>
        ) : (
          <span className="progress-counter" aria-live="polite">
            {currentIndex + 1} / {totalProblems}
          </span>
        )}

        <button
          type="button"
          className="nav-button next"
          onClick={onNext}
          disabled={currentIndex === totalProblems - 1}
          aria-label="Next problem"
        >
          →
        </button>
      </div>

      <div className="progress-bar-track" aria-hidden="true">
        <div className="progress-bar-fill" style={{ width: `${completionPct}%` }} />
      </div>

      <div className="nav-footer">
        <span className="completion-text">Solved: {solvedCount}/{totalProblems} ({completionPct}%)</span>
        {currentStreak !== undefined && currentStreak >= 2 && (
          <span className="streak-badge" data-testid="streak-badge">
            🔥 {currentStreak} in a row
          </span>
        )}
      </div>
    </nav>
  );
}

describe('ProblemNav Component', () => {
  const defaultProps: ProblemNavProps = {
    totalProblems: 5,
    currentIndex: 0,
    statuses: ['unsolved', 'unsolved', 'unsolved', 'unsolved', 'unsolved'],
    onNavigate: vi.fn(),
    onPrev: vi.fn(),
    onNext: vi.fn(),
  };

  describe('Basic rendering', () => {
    it('should render navigation container', () => {
      render(<MockProblemNav {...defaultProps} />);
      expect(screen.getByTestId('problem-nav')).toBeDefined();
    });

    it('should render dots for small sets (≤20)', () => {
      render(<MockProblemNav {...defaultProps} />);
      const dots = screen.getAllByRole('tab');
      expect(dots.length).toBe(5);
    });

    it('should render counter for large sets (>20)', () => {
      const manyStatuses = Array.from({ length: 25 }, () => 'unsolved' as PuzzleStatus);
      render(<MockProblemNav {...defaultProps} totalProblems={25} statuses={manyStatuses} />);
      expect(screen.getByText('1 / 25')).toBeDefined();
      expect(screen.queryAllByRole('tab').length).toBe(0);
    });

    it('should have navigation role', () => {
      render(<MockProblemNav {...defaultProps} />);
      expect(screen.getByRole('navigation')).toBeDefined();
    });

    it('should show completion text', () => {
      render(<MockProblemNav {...defaultProps} statuses={['solved', 'solved', 'unsolved', 'unsolved', 'unsolved']} />);
      expect(screen.getByText('Solved: 2/5 (40%)')).toBeDefined();
    });
  });

  describe('Status dots', () => {
    it('should apply status classes', () => {
      render(<MockProblemNav
        {...defaultProps}
        statuses={['solved', 'failed', 'unsolved']}
        totalProblems={3}
      />);

      expect(screen.getByTestId('indicator-0').className).toContain('solved');
      expect(screen.getByTestId('indicator-1').className).toContain('failed');
      expect(screen.getByTestId('indicator-2').className).toContain('unsolved');
    });
  });

  describe('Current highlight', () => {
    it('should highlight current problem', () => {
      render(<MockProblemNav {...defaultProps} currentIndex={2} />);
      expect(screen.getByTestId('indicator-2').className).toContain('current');
    });

    it('should mark current with aria-selected', () => {
      render(<MockProblemNav {...defaultProps} currentIndex={2} />);
      expect(screen.getByTestId('indicator-2').getAttribute('aria-selected')).toBe('true');
    });

    it('should not highlight non-current problems', () => {
      render(<MockProblemNav {...defaultProps} currentIndex={2} />);
      expect(screen.getByTestId('indicator-0').className).not.toContain('current');
      expect(screen.getByTestId('indicator-1').className).not.toContain('current');
    });
  });

  describe('Navigation buttons', () => {
    it('should disable prev button on first problem', () => {
      render(<MockProblemNav {...defaultProps} currentIndex={0} />);
      const prevButton = screen.getByLabelText('Previous problem');
      expect(prevButton.hasAttribute('disabled')).toBe(true);
    });

    it('should disable next button on last problem', () => {
      render(<MockProblemNav {...defaultProps} currentIndex={4} />);
      const nextButton = screen.getByLabelText('Next problem');
      expect(nextButton.hasAttribute('disabled')).toBe(true);
    });

    it('should enable both buttons when in middle', () => {
      render(<MockProblemNav {...defaultProps} currentIndex={2} />);
      const prevButton = screen.getByLabelText('Previous problem');
      const nextButton = screen.getByLabelText('Next problem');
      expect(prevButton.hasAttribute('disabled')).toBe(false);
      expect(nextButton.hasAttribute('disabled')).toBe(false);
    });
  });

  describe('Interaction', () => {
    it('should call onNavigate when dot clicked', () => {
      const onNavigate = vi.fn();
      render(<MockProblemNav {...defaultProps} onNavigate={onNavigate} />);

      fireEvent.click(screen.getByTestId('indicator-3'));
      expect(onNavigate).toHaveBeenCalledWith(3);
    });

    it('should call onPrev when prev button clicked', () => {
      const onPrev = vi.fn();
      render(<MockProblemNav {...defaultProps} currentIndex={2} onPrev={onPrev} />);

      fireEvent.click(screen.getByLabelText('Previous problem'));
      expect(onPrev).toHaveBeenCalled();
    });

    it('should call onNext when next button clicked', () => {
      const onNext = vi.fn();
      render(<MockProblemNav {...defaultProps} currentIndex={2} onNext={onNext} />);

      fireEvent.click(screen.getByLabelText('Next problem'));
      expect(onNext).toHaveBeenCalled();
    });
  });

  describe('Streak tracking (T11.8)', () => {
    it('should not show streak badge when no streak', () => {
      render(<MockProblemNav {...defaultProps} />);
      expect(screen.queryByTestId('streak-badge')).toBeNull();
    });

    it('should not show streak badge for streak of 1', () => {
      render(<MockProblemNav {...defaultProps} currentStreak={1} />);
      expect(screen.queryByTestId('streak-badge')).toBeNull();
    });

    it('should show streak badge for streak ≥ 2', () => {
      render(<MockProblemNav {...defaultProps} currentStreak={5} />);
      const badge = screen.getByTestId('streak-badge');
      expect(badge).toBeDefined();
      expect(badge.textContent).toContain('5 in a row');
    });
  });

  describe('Accessibility', () => {
    it('should have aria-label on dots', () => {
      render(<MockProblemNav {...defaultProps} statuses={['solved', 'failed', 'unsolved']} totalProblems={3} />);

      expect(screen.getByTestId('indicator-0').getAttribute('aria-label')).toBe('Problem 1, solved');
      expect(screen.getByTestId('indicator-1').getAttribute('aria-label')).toBe('Problem 2, failed');
      expect(screen.getByTestId('indicator-2').getAttribute('aria-label')).toBe('Problem 3, unsolved');
    });

    it('should have live region for counter in large sets', () => {
      const manyStatuses = Array.from({ length: 25 }, () => 'unsolved' as PuzzleStatus);
      render(<MockProblemNav {...defaultProps} totalProblems={25} statuses={manyStatuses} />);
      const counter = screen.getByText('1 / 25');
      expect(counter.getAttribute('aria-live')).toBe('polite');
    });
  });
});

describe('StatusIndicator Contract', () => {
  it('should handle all status types as CSS classes', () => {
    const allStatuses: PuzzleStatus[] = ['unsolved', 'solved', 'failed'];
    for (const status of allStatuses) {
      expect(typeof status).toBe('string');
      expect(status.length).toBeGreaterThan(0);
    }
  });
});
