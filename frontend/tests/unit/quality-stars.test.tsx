/**
 * Unit tests for QualityStars component.
 *
 * Tests:
 * - Returns null for quality 0
 * - Renders correct number of filled stars
 * - Renders aria-label with quality value
 * - Renders testId
 */

import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/preact';
import { QualityStars } from '@/components/shared/QualityStars';

describe('QualityStars', () => {
  it('returns null for quality 0', () => {
    const { container } = render(<QualityStars quality={0} />);
    expect(container.innerHTML).toBe('');
  });

  it('returns null for negative quality', () => {
    const { container } = render(<QualityStars quality={-1} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders 5 star icons for any valid quality', () => {
    const { container } = render(<QualityStars quality={3} />);
    const stars = container.querySelectorAll('svg');
    expect(stars.length).toBe(5);
  });

  it('renders correct number of filled stars for quality=3', () => {
    const { container } = render(<QualityStars quality={3} />);
    const stars = container.querySelectorAll('svg');
    // First 3 should be gold (filled), last 2 gray (empty)
    let filledCount = 0;
    stars.forEach((svg) => {
      if ((svg as HTMLElement).style.color === 'rgb(255, 215, 0)') filledCount++;
    });
    expect(filledCount).toBe(3);
  });

  it('renders all 5 filled for quality=5', () => {
    const { container } = render(<QualityStars quality={5} />);
    const stars = container.querySelectorAll('svg');
    let filledCount = 0;
    stars.forEach((svg) => {
      if ((svg as HTMLElement).style.color === 'rgb(255, 215, 0)') filledCount++;
    });
    expect(filledCount).toBe(5);
  });

  it('renders accessible aria-label', () => {
    const { getByLabelText } = render(<QualityStars quality={4} />);
    expect(getByLabelText('Quality: 4 out of 5')).toBeTruthy();
  });

  it('renders testId', () => {
    const { getByTestId } = render(<QualityStars quality={2} />);
    expect(getByTestId('quality-stars')).toBeTruthy();
  });

  it('renders aria-roledescription="rating"', () => {
    const { getByTestId } = render(<QualityStars quality={3} />);
    expect(getByTestId('quality-stars').getAttribute('aria-roledescription')).toBe('rating');
  });

  it('clamps quality > 5 to 5 filled stars', () => {
    const { container } = render(<QualityStars quality={8} />);
    const stars = container.querySelectorAll('svg');
    let filledCount = 0;
    stars.forEach((svg) => {
      if ((svg as HTMLElement).style.color === 'rgb(255, 215, 0)') filledCount++;
    });
    expect(filledCount).toBe(5);
  });
});
