/**
 * QualityBreakdown Component Tests
 * @module tests/unit/qualityBreakdown.test
 *
 * Tests for T060: QualityBreakdown component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { QualityBreakdown } from '@components/QualityBreakdown';

// Mock StarDisplay from QualityFilter
// New quality scale: tier 1 = 1 star (worst), tier 5 = 5 stars (best)
vi.mock('@components/QualityFilter', () => ({
  StarDisplay: ({ tier }: { tier: number }) => (
    <span data-testid="star-display" data-tier={tier}>
      {'★'.repeat(tier)}{'☆'.repeat(5 - tier)}
    </span>
  ),
}));

describe('QualityBreakdown Component (T060)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render tier name in header', () => {
      render(<QualityBreakdown tier={5} />);
      expect(screen.getByText(/Premium Quality/)).toBeDefined();
    });

    it('should render star display', () => {
      render(<QualityBreakdown tier={4} />);
      expect(screen.getByTestId('star-display')).toBeDefined();
    });

    it('should render expand/collapse button', () => {
      const { container } = render(<QualityBreakdown tier={3} />);
      const button = container.querySelector('button');
      expect(button).toBeDefined();
    });
  });

  describe('Tier Names', () => {
    it('should show Unverified for tier 1', () => {
      render(<QualityBreakdown tier={1} />);
      expect(screen.getByText(/Unverified/)).toBeDefined();
    });

    it('should show Basic for tier 2', () => {
      render(<QualityBreakdown tier={2} />);
      expect(screen.getByText(/Basic/)).toBeDefined();
    });

    it('should show Standard for tier 3', () => {
      render(<QualityBreakdown tier={3} />);
      expect(screen.getByText(/Standard/)).toBeDefined();
    });

    it('should show High for tier 4', () => {
      render(<QualityBreakdown tier={4} />);
      expect(screen.getByText(/High/)).toBeDefined();
    });

    it('should show Premium for tier 5', () => {
      render(<QualityBreakdown tier={5} />);
      expect(screen.getByText(/Premium/)).toBeDefined();
    });
  });

  describe('Expand/Collapse', () => {
    it('should be collapsed by default', () => {
      const { container } = render(<QualityBreakdown tier={5} />);
      // When collapsed, should show ▶
      expect(container.textContent).toContain('▶');
    });

    it('should expand when initiallyExpanded is true', () => {
      const { container } = render(<QualityBreakdown tier={5} initiallyExpanded />);
      // When expanded, should show ▼
      expect(container.textContent).toContain('▼');
    });

    it('should toggle expand state on click', () => {
      const { container } = render(<QualityBreakdown tier={5} />);
      const button = container.querySelector('button')!;
      
      // Initially collapsed
      expect(container.textContent).toContain('▶');
      
      // Click to expand
      fireEvent.click(button);
      expect(container.textContent).toContain('▼');
      
      // Click to collapse
      fireEvent.click(button);
      expect(container.textContent).toContain('▶');
    });
  });

  describe('Requirements Display (T058)', () => {
    it('should show checkmark for met requirements', () => {
      const { container } = render(
        <QualityBreakdown
          tier={5}
          metrics={{ tier: 5, refutationCount: 5, hasComments: true }}
          initiallyExpanded
        />
      );
      
      // Premium tier (5) requires 3+ refutations and comments
      // With 5 refutations and comments=true, both should be met
      const checkmarks = container.querySelectorAll('span');
      const greenCheckmarks = Array.from(checkmarks).filter(
        (el) => el.textContent === '✓'
      );
      expect(greenCheckmarks.length).toBeGreaterThan(0);
    });

    it('should show red X for unmet requirements', () => {
      const { container } = render(
        <QualityBreakdown
          tier={5}
          metrics={{ tier: 5, refutationCount: 1, hasComments: false }}
          initiallyExpanded
        />
      );
      
      // Premium tier requires 3+ refutations and comments
      // With 1 refutation and no comments, requirements are NOT met
      const xMarks = container.querySelectorAll('span');
      const redXs = Array.from(xMarks).filter(
        (el) => el.textContent === '✗'
      );
      expect(redXs.length).toBeGreaterThan(0);
    });

    it('should show refutation count value', () => {
      const { container } = render(
        <QualityBreakdown
          tier={4}
          metrics={{ tier: 4, refutationCount: 3, hasComments: true }}
          initiallyExpanded
        />
      );
      
      expect(container.textContent).toContain('3 branches');
    });
  });

  describe('Accessibility', () => {
    it('should have aria-expanded attribute', () => {
      const { container } = render(<QualityBreakdown tier={3} />);
      const button = container.querySelector('button')!;
      
      expect(button.getAttribute('aria-expanded')).toBe('false');
      
      fireEvent.click(button);
      expect(button.getAttribute('aria-expanded')).toBe('true');
    });

    it('should have descriptive aria-label', () => {
      const { container } = render(<QualityBreakdown tier={4} />);
      const button = container.querySelector('button')!;
      
      expect(button.getAttribute('aria-label')).toContain('Quality');
      expect(button.getAttribute('aria-label')).toContain('expand');
    });
  });

  describe('Custom className', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <QualityBreakdown tier={3} className="my-custom-class" />
      );
      
      expect(container.querySelector('.quality-breakdown.my-custom-class')).toBeDefined();
    });
  });
});
