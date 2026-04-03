/**
 * ProgressBar Component Tests
 * @module tests/unit/progress-bar.test
 *
 * Spec 118 - T3.8: Unit Tests for Carousel Components
 * Tests for progress indicator below carousel
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { ProgressBar } from '@/components/ProblemNav/ProgressBar';

describe('ProgressBar', () => {
  describe('Rendering', () => {
    it('should render progress bar', () => {
      render(<ProgressBar completed={5} total={10} />);

      expect(screen.getByRole('progressbar')).toBeDefined();
    });

    it('should display progress label', () => {
      render(<ProgressBar completed={3} total={10} />);

      expect(screen.getByText('3/10 (30%)')).toBeDefined();
    });

    it('should hide label in compact mode', () => {
      render(<ProgressBar completed={3} total={10} compact={true} />);

      expect(screen.queryByText('3/10 (30%)')).toBeNull();
    });

    it('should render track and fill', () => {
      const { container } = render(<ProgressBar completed={5} total={10} />);

      expect(container.querySelector('.progress-bar-track')).toBeDefined();
      expect(container.querySelector('.progress-bar-fill')).toBeDefined();
    });
  });

  describe('Percentage Calculation', () => {
    it('should calculate 50% correctly', () => {
      render(<ProgressBar completed={5} total={10} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('50');
    });

    it('should calculate 100% correctly', () => {
      render(<ProgressBar completed={10} total={10} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('100');
    });

    it('should calculate 0% correctly', () => {
      render(<ProgressBar completed={0} total={10} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('0');
    });

    it('should handle partial percentages correctly', () => {
      render(<ProgressBar completed={3} total={7} />);

      const progressbar = screen.getByRole('progressbar');
      // 3/7 = 42.857% rounds to 43%
      expect(progressbar.getAttribute('aria-valuenow')).toBe('43');
    });

    it('should handle zero total without errors', () => {
      render(<ProgressBar completed={0} total={0} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('0');
    });

    it('should display 0% when total is zero', () => {
      render(<ProgressBar completed={0} total={0} />);

      expect(screen.getByText('0/0 (0%)')).toBeDefined();
    });
  });

  describe('Progress Bar Width', () => {
    it('should set width to 50% for half completion', () => {
      const { container } = render(<ProgressBar completed={5} total={10} />);

      const fill = container.querySelector('.progress-bar-fill') as HTMLElement;
      expect(fill.style.width).toBe('50%');
    });

    it('should set width to 100% for full completion', () => {
      const { container } = render(<ProgressBar completed={10} total={10} />);

      const fill = container.querySelector('.progress-bar-fill') as HTMLElement;
      expect(fill.style.width).toBe('100%');
    });

    it('should set width to 0% for no completion', () => {
      const { container } = render(<ProgressBar completed={0} total={10} />);

      const fill = container.querySelector('.progress-bar-fill') as HTMLElement;
      expect(fill.style.width).toBe('0%');
    });

    it('should round percentage for width', () => {
      const { container } = render(<ProgressBar completed={1} total={3} />);

      const fill = container.querySelector('.progress-bar-fill') as HTMLElement;
      // 1/3 = 33.333% rounds to 33%
      expect(fill.style.width).toBe('33%');
    });
  });

  describe('Accessibility', () => {
    it('should have role="progressbar"', () => {
      render(<ProgressBar completed={5} total={10} />);

      expect(screen.getByRole('progressbar')).toBeDefined();
    });

    it('should have aria-valuenow', () => {
      render(<ProgressBar completed={7} total={10} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('70');
    });

    it('should have aria-valuemin=0', () => {
      render(<ProgressBar completed={5} total={10} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuemin')).toBe('0');
    });

    it('should have aria-valuemax=100', () => {
      render(<ProgressBar completed={5} total={10} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuemax')).toBe('100');
    });

    it('should have descriptive aria-label', () => {
      render(<ProgressBar completed={3} total={8} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-label')).toBe('Progress: 3 of 8 puzzles completed');
    });

    it('should update aria-label for different values', () => {
      render(<ProgressBar completed={10} total={20} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-label')).toBe('Progress: 10 of 20 puzzles completed');
    });
  });

  describe('Compact Mode', () => {
    it('should apply compact class when compact=true', () => {
      const { container } = render(<ProgressBar completed={5} total={10} compact={true} />);

      const progressBar = container.querySelector('.progress-bar');
      expect(progressBar?.className).toContain('compact');
    });

    it('should not apply compact class when compact=false', () => {
      const { container } = render(<ProgressBar completed={5} total={10} compact={false} />);

      const progressBar = container.querySelector('.progress-bar');
      expect(progressBar?.className).not.toContain('compact');
    });

    it('should not apply compact class by default', () => {
      const { container } = render(<ProgressBar completed={5} total={10} />);

      const progressBar = container.querySelector('.progress-bar');
      expect(progressBar?.className).not.toContain('compact');
    });
  });

  describe('Edge Cases', () => {
    it('should handle completed > total', () => {
      render(<ProgressBar completed={15} total={10} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('150');
    });

    it('should handle very large numbers', () => {
      render(<ProgressBar completed={500} total={1000} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('50');
      expect(screen.getByText('500/1000 (50%)')).toBeDefined();
    });

    it('should handle single puzzle completion', () => {
      render(<ProgressBar completed={1} total={1} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar.getAttribute('aria-valuenow')).toBe('100');
      expect(screen.getByText('1/1 (100%)')).toBeDefined();
    });
  });
});
