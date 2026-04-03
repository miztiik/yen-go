/**
 * QualityBadge Component Tests
 * @module tests/unit/qualityBadge.test
 *
 * Tests for T049: QualityBadge component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { QualityBadge } from '@components/QualityBadge';

// Mock QualityFilter's StarDisplay
// New quality scale: tier 1 = 1 star (worst), tier 5 = 5 stars (best)
vi.mock('@components/QualityFilter', () => ({
  StarDisplay: ({ tier, size }: { tier: number; size: number }) => (
    <span data-testid="star-display" data-tier={tier} data-size={size}>
      {'★'.repeat(tier)}{'☆'.repeat(5 - tier)}
    </span>
  ),
}));

describe('QualityBadge Component (T049)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Stars Variant (default)', () => {
    it('should render stars for tier 5 (Premium)', () => {
      const { container } = render(<QualityBadge tier={5} />);
      
      expect(container.querySelector('.quality-badge--stars')).toBeDefined();
      expect(screen.getByTestId('star-display')).toBeDefined();
    });

    it('should render stars for tier 3 (Standard)', () => {
      const { container } = render(<QualityBadge tier={3} />);
      
      const badge = container.querySelector('.quality-badge--stars');
      expect(badge).toBeDefined();
      expect(badge?.getAttribute('title')).toBe('Standard');
    });

    it('should render stars for tier 1 (Unverified)', () => {
      const { container } = render(<QualityBadge tier={1} />);
      
      const badge = container.querySelector('.quality-badge--stars');
      expect(badge).toBeDefined();
      expect(badge?.getAttribute('title')).toBe('Unverified');
    });
  });

  describe('Compact Variant', () => {
    it('should render compact badge with tier number', () => {
      const { container } = render(<QualityBadge tier={4} variant="compact" />);
      
      const badge = container.querySelector('.quality-badge--compact');
      expect(badge).toBeDefined();
      expect(badge?.textContent).toContain('4');
    });

    it('should show correct color for Premium (tier 5)', () => {
      const { container } = render(<QualityBadge tier={5} variant="compact" />);
      
      const badge = container.querySelector('.quality-badge--compact') as HTMLElement;
      // Gold background for Premium (CSS var in jsdom)
      expect(badge.style.backgroundColor).toBe('var(--color-quality-5)');
    });

    it('should show correct color for Standard (tier 3)', () => {
      const { container } = render(<QualityBadge tier={3} variant="compact" />);
      
      const badge = container.querySelector('.quality-badge--compact') as HTMLElement;
      // Bronze background for Standard (CSS var in jsdom)
      expect(badge.style.backgroundColor).toBe('var(--color-quality-3)');
    });
  });

  describe('Full Variant', () => {
    it('should render stars and label', () => {
      const { container } = render(<QualityBadge tier={5} variant="full" />);
      
      const badge = container.querySelector('.quality-badge--full');
      expect(badge).toBeDefined();
      expect(badge?.textContent).toContain('Premium');
    });

    it('should render stars and label for High tier', () => {
      const { container } = render(<QualityBadge tier={4} variant="full" />);
      
      expect(screen.getByText('High')).toBeDefined();
    });
  });

  describe('Size Prop', () => {
    it('should use small size', () => {
      render(<QualityBadge tier={3} size="small" />);
      
      const starDisplay = screen.getByTestId('star-display');
      expect(starDisplay.getAttribute('data-size')).toBe('10');
    });

    it('should use medium size (default)', () => {
      render(<QualityBadge tier={3} size="medium" />);
      
      const starDisplay = screen.getByTestId('star-display');
      expect(starDisplay.getAttribute('data-size')).toBe('14');
    });

    it('should use large size', () => {
      render(<QualityBadge tier={3} size="large" />);
      
      const starDisplay = screen.getByTestId('star-display');
      expect(starDisplay.getAttribute('data-size')).toBe('18');
    });
  });

  describe('Tooltip (T047)', () => {
    it('should show tooltip on hover when enabled', async () => {
      const { container } = render(<QualityBadge tier={5} showTooltip />);
      
      const badge = container.querySelector('.quality-badge--stars') as HTMLElement;
      
      // Simulate mouse enter
      fireEvent.mouseEnter(badge, { clientX: 100, clientY: 100 });
      
      // Tooltip should be visible
      const tooltip = container.querySelector('.quality-badge-tooltip');
      expect(tooltip).toBeDefined();
      expect(tooltip?.textContent).toContain('Premium');
      expect(tooltip?.textContent).toContain('3+ refutations with comments');
    });

    it('should hide tooltip on mouse leave', () => {
      const { container } = render(<QualityBadge tier={4} showTooltip />);
      
      const badge = container.querySelector('.quality-badge--stars') as HTMLElement;
      
      // Show tooltip
      fireEvent.mouseEnter(badge, { clientX: 100, clientY: 100 });
      expect(container.querySelector('.quality-badge-tooltip')).toBeDefined();
      
      // Hide tooltip
      fireEvent.mouseLeave(badge);
      expect(container.querySelector('.quality-badge-tooltip')).toBeNull();
    });

    it('should not show tooltip when disabled', () => {
      const { container } = render(<QualityBadge tier={3} showTooltip={false} />);
      
      const badge = container.querySelector('.quality-badge--stars') as HTMLElement;
      
      fireEvent.mouseEnter(badge, { clientX: 100, clientY: 100 });
      
      // Tooltip should not appear
      expect(container.querySelector('.quality-badge-tooltip')).toBeNull();
    });

    it('should show correct description for each tier', () => {
      const tierDescriptions = [
        { tier: 1, description: 'Single solution, no tree' },
        { tier: 2, description: 'Basic solution tree' },
        { tier: 3, description: 'Solution with refutation' },
        { tier: 4, description: '2+ refutations with comments' },
        { tier: 5, description: '3+ refutations with comments' },
      ];

      tierDescriptions.forEach(({ tier, description }) => {
        const { container, unmount } = render(
          <QualityBadge tier={tier as 1 | 2 | 3 | 4 | 5} showTooltip />
        );
        
        const badge = container.querySelector('.quality-badge--stars') as HTMLElement;
        fireEvent.mouseEnter(badge, { clientX: 100, clientY: 100 });
        
        const tooltip = container.querySelector('.quality-badge-tooltip');
        expect(tooltip?.textContent).toContain(description);
        
        unmount();
      });
    });
  });

  describe('Custom className', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <QualityBadge tier={3} className="my-custom-class" />
      );
      
      expect(container.querySelector('.quality-badge.my-custom-class')).toBeDefined();
    });
  });
});
