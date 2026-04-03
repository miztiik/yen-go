/**
 * Unit tests for ContentTypeFilter component.
 *
 * Tests:
 * - Renders 4 options (All Types, Curated, Practice, Training Lab)
 * - Uses FilterBar under the hood
 * - Renders testId
 * - Shows counts when provided
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/preact';
import { ContentTypeFilter } from '@/components/shared/ContentTypeFilter';
import { _resetContentTypeForTesting } from '@/hooks/useContentType';

describe('ContentTypeFilter', () => {
  beforeEach(() => {
    _resetContentTypeForTesting();
    localStorage.clear();
  });

  it('renders testId', () => {
    const { getByTestId } = render(<ContentTypeFilter />);
    expect(getByTestId('content-type-filter')).toBeTruthy();
  });

  it('renders All Types, Curated, Practice, and Training Lab options in correct order', () => {
    const { getByRole } = render(<ContentTypeFilter />);
    const group = getByRole('radiogroup');
    const buttons = group.querySelectorAll('[role="radio"]');
    expect(buttons.length).toBe(4);
    expect(buttons[0]!.textContent).toContain('All Types');
    expect(buttons[1]!.textContent).toContain('Curated');
    expect(buttons[2]!.textContent).toContain('Practice');
    expect(buttons[3]!.textContent).toContain('Training Lab');
  });

  it('renders with role radiogroup', () => {
    const { getByRole } = render(<ContentTypeFilter />);
    expect(getByRole('radiogroup')).toBeTruthy();
  });

  it('defaults to All Types selected', () => {
    const { getByTestId } = render(<ContentTypeFilter />);
    const container = getByTestId('content-type-filter');
    // The first button (All Types) should have aria-checked="true" since default is 0
    const buttons = container.querySelectorAll('[role="radio"]');
    expect(buttons.length).toBe(4);
    // Order: All Types(0), Curated(1), Practice(2), Training Lab(3) — All Types is at index 0
    expect(buttons[0]!.getAttribute('aria-checked')).toBe('true');
  });

  it('renders count badges when counts provided', () => {
    const { container } = render(
      <ContentTypeFilter counts={{ 1: 50, 2: 100, 3: 25 }} />,
    );
    // "All" should show total count (175)
    expect(container.textContent).toContain('175');
    expect(container.textContent).toContain('50');
    expect(container.textContent).toContain('100');
    expect(container.textContent).toContain('25');
  });
});
