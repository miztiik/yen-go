/**
 * Unit tests for ErrorState component.
 *
 * Spec 132 — T090
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { ErrorState } from '../../src/components/shared/ErrorState';

describe('ErrorState Component', () => {
  describe('Rendering', () => {
    it('should render message text', () => {
      render(<ErrorState message="Something went wrong" />);
      expect(screen.getByText('Something went wrong')).toBeTruthy();
    });

    it('should render with role="alert"', () => {
      render(<ErrorState message="Error occurred" />);
      expect(screen.getByRole('alert')).toBeTruthy();
    });

    it('should render default icon when none provided', () => {
      const { container } = render(<ErrorState message="Oops" />);
      // Default icon is an SVG alert triangle (not an emoji)
      const svg = container.querySelector('svg');
      expect(svg).toBeTruthy();
    });

    it('should render custom icon when provided', () => {
      render(<ErrorState message="Not found" icon="🔍" />);
      const { container } = render(<ErrorState message="Not found" icon="🔍" />);
      expect(container.textContent).toContain('🔍');
    });

    it('should apply custom testId', () => {
      render(<ErrorState message="Error" testId="daily-error" />);
      expect(screen.getByTestId('daily-error')).toBeTruthy();
    });

    it('should apply additional className', () => {
      render(<ErrorState message="Error" className="mt-8" />);
      const el = screen.getByTestId('error-state');
      expect(el.className).toContain('mt-8');
    });
  });

  describe('Actions', () => {
    it('should render Retry button when onRetry is provided', () => {
      const onRetry = vi.fn();
      render(<ErrorState message="Failed" onRetry={onRetry} />);
      const btn = screen.getByText('Retry');
      expect(btn).toBeTruthy();
    });

    it('should call onRetry when Retry button is clicked', () => {
      const onRetry = vi.fn();
      render(<ErrorState message="Failed" onRetry={onRetry} />);
      fireEvent.click(screen.getByText('Retry'));
      expect(onRetry).toHaveBeenCalledOnce();
    });

    it('should render Go Back button when onGoBack is provided', () => {
      const onGoBack = vi.fn();
      render(<ErrorState message="Failed" onGoBack={onGoBack} />);
      expect(screen.getByText('Go Back')).toBeTruthy();
    });

    it('should call onGoBack when Go Back button is clicked', () => {
      const onGoBack = vi.fn();
      render(<ErrorState message="Failed" onGoBack={onGoBack} />);
      fireEvent.click(screen.getByText('Go Back'));
      expect(onGoBack).toHaveBeenCalledOnce();
    });

    it('should not render action buttons when neither onRetry nor onGoBack provided', () => {
      render(<ErrorState message="Info only" />);
      expect(screen.queryByText('Retry')).toBeNull();
      expect(screen.queryByText('Go Back')).toBeNull();
    });

    it('should render both buttons when both actions provided', () => {
      render(
        <ErrorState message="Error" onRetry={() => {}} onGoBack={() => {}} />
      );
      expect(screen.getByText('Retry')).toBeTruthy();
      expect(screen.getByText('Go Back')).toBeTruthy();
    });
  });

  describe('Technical Details Disclosure', () => {
    it('should not render details section when details is undefined', () => {
      render(<ErrorState message="Error" />);
      expect(screen.queryByText('Technical details')).toBeNull();
    });

    it('should render details disclosure when details is provided', () => {
      render(
        <ErrorState message="Error" details="TypeError: fetch failed" />
      );
      expect(screen.getByText('Technical details')).toBeTruthy();
    });

    it('should render raw error text inside details', () => {
      render(
        <ErrorState message="Error" details="Network timeout at /api/daily" />
      );
      expect(screen.getByText('Network timeout at /api/daily')).toBeTruthy();
    });

    it('should have details closed by default', () => {
      render(
        <ErrorState message="Error" details="some error" />
      );
      const details = screen.getByTestId('error-state-details');
      expect(details.hasAttribute('open')).toBe(false);
    });

    it('should have details open when detailsOpen is true', () => {
      render(
        <ErrorState message="Error" details="some error" detailsOpen={true} />
      );
      const details = screen.getByTestId('error-state-details');
      expect(details.hasAttribute('open')).toBe(true);
    });
  });
});
