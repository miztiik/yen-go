/**
 * Unit tests for ProgressBar component.
 *
 * Spec 132 — T011, T043
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { ProgressBar } from '../../src/components/shared/ProgressBar';

describe('ProgressBar Component', () => {
  describe('Rendering states', () => {
    it('should render nothing when total is 0', () => {
      const { container } = render(<ProgressBar solved={0} total={0} />);
      expect(container.innerHTML).toBe('');
    });

    it('should show "Ready to begin" when solved is 0 and total > 0', () => {
      render(<ProgressBar solved={0} total={10} />);
      expect(screen.getByText('Ready to begin')).toBeTruthy();
    });

    it('should show progress bar and label when solved > 0', () => {
      render(<ProgressBar solved={5} total={10} />);
      expect(screen.getByText('5 of 10 solved')).toBeTruthy();
      expect(screen.getByRole('progressbar')).toBeTruthy();
    });

    it('should show correct label for full completion', () => {
      render(<ProgressBar solved={10} total={10} />);
      expect(screen.getByText('10 of 10 solved')).toBeTruthy();
    });
  });

  describe('Progress calculation', () => {
    it('should set progressbar aria attributes correctly', () => {
      render(<ProgressBar solved={3} total={12} />);
      const bar = screen.getByRole('progressbar');
      expect(bar.getAttribute('aria-valuenow')).toBe('3');
      expect(bar.getAttribute('aria-valuemin')).toBe('0');
      expect(bar.getAttribute('aria-valuemax')).toBe('12');
    });

    it('should clamp percentage at 100% when solved > total', () => {
      render(<ProgressBar solved={15} total={10} />);
      const bar = screen.getByRole('progressbar');
      // Width should be 100%, not 150%
      expect(bar.style.width).toBe('100%');
    });
  });

  describe('Mode prop', () => {
    it('should apply mode-specific fill color', () => {
      render(<ProgressBar solved={5} total={10} mode="daily" />);
      const bar = screen.getByRole('progressbar');
      expect(bar.style.backgroundColor).toContain('--color-mode-daily-border');
    });

    it('should use accent fallback when no mode specified', () => {
      render(<ProgressBar solved={5} total={10} />);
      const bar = screen.getByRole('progressbar');
      expect(bar.style.backgroundColor).toContain('--color-accent');
    });
  });

  describe('Test IDs', () => {
    it('should render with default testId', () => {
      render(<ProgressBar solved={5} total={10} />);
      expect(screen.getByTestId('progress-bar')).toBeTruthy();
    });

    it('should render with custom testId', () => {
      render(<ProgressBar solved={5} total={10} testId="custom-bar" />);
      expect(screen.getByTestId('custom-bar')).toBeTruthy();
    });
  });

  describe('Styling', () => {
    it('should apply additional className', () => {
      render(<ProgressBar solved={5} total={10} className="extra-class" />);
      const el = screen.getByTestId('progress-bar');
      expect(el.className).toContain('extra-class');
    });

    it('should show muted italic text for ready state', () => {
      render(<ProgressBar solved={0} total={10} />);
      const el = screen.getByTestId('progress-bar');
      expect(el.className).toContain('italic');
      expect(el.className).toContain('text-[--color-text-muted]');
    });
  });
});
