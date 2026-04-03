/**
 * PuzzleCard Component Tests
 * @module tests/unit/puzzle-card.test
 *
 * Spec 118 - T3.8: Unit Tests for Carousel Components
 * Tests for individual puzzle card in carousel navigation
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { PuzzleCard, type PuzzleCardStatus } from '@/components/ProblemNav/PuzzleCard';

describe('PuzzleCard', () => {
  describe('Rendering', () => {
    it('should render puzzle number', () => {
      render(<PuzzleCard number={5} status="unsolved" />);

      expect(screen.getByText('5')).toBeDefined();
    });

    it('should render unsolved status symbol', () => {
      render(<PuzzleCard number={1} status="unsolved" />);

      expect(screen.getByText('○')).toBeDefined();
    });

    it('should render correct status symbol', () => {
      render(<PuzzleCard number={1} status="correct" />);

      expect(screen.getByText('✓')).toBeDefined();
    });

    it('should render wrong status symbol', () => {
      render(<PuzzleCard number={1} status="wrong" />);

      expect(screen.getByText('✗')).toBeDefined();
    });

    it('should render as button element', () => {
      render(<PuzzleCard number={1} status="unsolved" />);

      expect(screen.getByRole('tab')).toBeDefined();
    });
  });

  describe('Status Classes', () => {
    it('should apply correct status class', () => {
      const { container } = render(<PuzzleCard number={1} status="correct" />);

      const button = container.querySelector('.puzzle-card');
      expect(button?.className).toContain('status-correct');
    });

    it('should apply wrong status class', () => {
      const { container } = render(<PuzzleCard number={1} status="wrong" />);

      const button = container.querySelector('.puzzle-card');
      expect(button?.className).toContain('status-wrong');
    });

    it('should apply unsolved status class', () => {
      const { container } = render(<PuzzleCard number={1} status="unsolved" />);

      const button = container.querySelector('.puzzle-card');
      expect(button?.className).toContain('status-unsolved');
    });

    it('should apply is-current class when current', () => {
      const { container } = render(<PuzzleCard number={1} status="unsolved" isCurrent={true} />);

      const button = container.querySelector('.puzzle-card');
      expect(button?.className).toContain('is-current');
    });

    it('should not apply is-current class when not current', () => {
      const { container } = render(<PuzzleCard number={1} status="unsolved" isCurrent={false} />);

      const button = container.querySelector('.puzzle-card');
      expect(button?.className).not.toContain('is-current');
    });
  });

  describe('Click Handling', () => {
    it('should call onClick when clicked', () => {
      const handleClick = vi.fn();
      render(<PuzzleCard number={1} status="unsolved" onClick={handleClick} />);

      const button = screen.getByRole('tab');
      fireEvent.click(button);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should not throw error if onClick is undefined', () => {
      render(<PuzzleCard number={1} status="unsolved" />);

      const button = screen.getByRole('tab');
      expect(() => fireEvent.click(button)).not.toThrow();
    });
  });

  describe('Accessibility', () => {
    it('should have role="tab"', () => {
      render(<PuzzleCard number={1} status="unsolved" />);

      expect(screen.getByRole('tab')).toBeDefined();
    });

    it('should have aria-label with puzzle number and status', () => {
      render(<PuzzleCard number={5} status="correct" />);

      const button = screen.getByRole('tab');
      expect(button.getAttribute('aria-label')).toBe('Puzzle 5, completed');
    });

    it('should have aria-label for unsolved puzzle', () => {
      render(<PuzzleCard number={3} status="unsolved" />);

      const button = screen.getByRole('tab');
      expect(button.getAttribute('aria-label')).toBe('Puzzle 3, unsolved');
    });

    it('should have aria-label for wrong puzzle', () => {
      render(<PuzzleCard number={2} status="wrong" />);

      const button = screen.getByRole('tab');
      expect(button.getAttribute('aria-label')).toBe('Puzzle 2, incorrect');
    });

    it('should have aria-selected=true when current', () => {
      render(<PuzzleCard number={1} status="unsolved" isCurrent={true} />);

      const button = screen.getByRole('tab');
      expect(button.getAttribute('aria-selected')).toBe('true');
    });

    it('should have aria-selected=false when not current', () => {
      render(<PuzzleCard number={1} status="unsolved" isCurrent={false} />);

      const button = screen.getByRole('tab');
      expect(button.getAttribute('aria-selected')).toBe('false');
    });

    it('should have aria-current when current', () => {
      render(<PuzzleCard number={1} status="unsolved" isCurrent={true} />);

      const button = screen.getByRole('tab');
      expect(button.getAttribute('aria-current')).toBe('true');
    });

    it('should have tabIndex=0 when current', () => {
      render(<PuzzleCard number={1} status="unsolved" isCurrent={true} />);

      const button = screen.getByRole('tab');
      expect(button.getAttribute('tabIndex')).toBe('0');
    });

    it('should have tabIndex=-1 when not current', () => {
      render(<PuzzleCard number={1} status="unsolved" isCurrent={false} />);

      const button = screen.getByRole('tab');
      expect(button.getAttribute('tabIndex')).toBe('-1');
    });

    it('should have aria-hidden on visual elements', () => {
      const { container } = render(<PuzzleCard number={1} status="correct" />);

      const cardNumber = container.querySelector('.card-number');
      const cardStatus = container.querySelector('.card-status');

      expect(cardNumber?.getAttribute('aria-hidden')).toBe('true');
      expect(cardStatus?.getAttribute('aria-hidden')).toBe('true');
    });
  });

  describe('Different Statuses', () => {
    const statuses: PuzzleCardStatus[] = ['unsolved', 'correct', 'wrong', 'current'];

    statuses.forEach((status) => {
      it(`should render with status="${status}" without errors`, () => {
        expect(() => {
          render(<PuzzleCard number={1} status={status} />);
        }).not.toThrow();
      });
    });
  });
});
