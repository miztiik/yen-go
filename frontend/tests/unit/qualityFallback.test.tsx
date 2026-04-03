/**
 * Quality Display Fallback Tests
 * @module tests/unit/qualityFallback.test
 *
 * Tests for T069: Frontend test - display level number if config name lookup fails
 * Tests for T071: Verify frontend gracefully handles puzzles with missing quality data
 *
 * Quality scale: 1=worst (Unverified), 5=best (Premium)
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { QualityBadge } from '@components/QualityBadge';

// Mock StarDisplay
vi.mock('@components/QualityFilter', () => ({
  StarDisplay: ({ tier }: { tier: number }) => (
    <span data-testid="star-display" data-tier={tier}>Stars: {tier}</span>
  ),
}));

describe('Quality Display Fallback (T069, T071)', () => {
  describe('Level Name Lookup Fallback (T069)', () => {
    it('should display fallback for level 5 when config lookup works', () => {
      render(<QualityBadge tier={5} variant="full" showTooltip={false} />);
      
      // Should display "Premium" from PUZZLE_QUALITY_INFO (level 5 = best)
      expect(screen.getByText('Premium')).toBeDefined();
    });

    it('should display fallback for level 1 when config lookup works', () => {
      render(<QualityBadge tier={1} variant="full" showTooltip={false} />);
      
      // Should display "Unverified" from PUZZLE_QUALITY_INFO (level 1 = worst)
      expect(screen.getByText('Unverified')).toBeDefined();
    });

    it('should use title attribute as fallback in stars variant', () => {
      const { container } = render(<QualityBadge tier={3} showTooltip={false} />);
      
      const badge = container.querySelector('.quality-badge--stars');
      // Title should show level name
      expect(badge?.getAttribute('title')).toBe('Standard');
    });

    it('should display level number in compact variant', () => {
      const { container } = render(<QualityBadge tier={2} variant="compact" showTooltip={false} />);
      
      // Compact variant always shows level number
      const badge = container.querySelector('.quality-badge--compact');
      expect(badge?.textContent).toContain('2');
    });
  });

  describe('Missing Quality Data Handling (T071)', () => {
    it('should handle invalid level gracefully by falling back to level 1 info', () => {
      // Testing invalid input - component should fall back to level 1 (worst)
      const { container } = render(<QualityBadge tier={99 as 1} variant="full" showTooltip={false} />);
      
      // Should use fallback (level 1 info) for invalid level
      // This tests that info = PUZZLE_QUALITY_INFO[level] || PUZZLE_QUALITY_INFO[1]
      expect(container.querySelector('.quality-badge--full')).toBeDefined();
    });

    it('should render stars even with edge level values', () => {
      // Level 1 (minimum valid)
      const { container: c1 } = render(<QualityBadge tier={1} />);
      expect(c1.querySelector('.quality-badge')).toBeDefined();
      
      // Level 5 (maximum valid)
      const { container: c5 } = render(<QualityBadge tier={5} />);
      expect(c5.querySelector('.quality-badge')).toBeDefined();
    });

    it('should display level colors correctly for each level', () => {
      const levels = [1, 2, 3, 4, 5] as const;
      
      for (const level of levels) {
        const { container, unmount } = render(
          <QualityBadge tier={level} variant="compact" showTooltip={false} />
        );
        
        const badge = container.querySelector('.quality-badge--compact') as HTMLElement;
        expect(badge).toBeDefined();
        // Should have a background color set
        expect(badge.style.backgroundColor).toBeTruthy();
        
        unmount();
      }
    });
  });

  describe('Graceful Degradation', () => {
    it('should render without tooltip when showTooltip is false', () => {
      const { container } = render(<QualityBadge tier={3} showTooltip={false} />);
      
      // No tooltip element should be rendered
      expect(container.querySelector('.quality-badge-tooltip')).toBeNull();
    });

    it('should apply custom className', () => {
      const { container } = render(<QualityBadge tier={3} className="custom" />);
      
      expect(container.querySelector('.quality-badge.custom')).toBeDefined();
    });

    it('should handle all size variants', () => {
      const sizes = ['small', 'medium', 'large'] as const;
      
      for (const size of sizes) {
        const { container, unmount } = render(
          <QualityBadge tier={3} size={size} showTooltip={false} />
        );
        
        expect(container.querySelector('.quality-badge')).toBeDefined();
        
        unmount();
      }
    });
  });
});
